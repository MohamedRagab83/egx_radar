"""Scan core: orchestrates all layers into one scan pass."""

import json
import logging
import math
import os
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pandas_ta as pta

from egx_radar.config.settings import (
    K,
    SECTORS,
    SYMBOLS,
    DECISION_PRIORITY,
    get_account_size,
    get_sector,
)
from egx_radar.core.indicators import (
    safe_clamp,
    last_val,
    compute_atr,
    compute_atr_risk,
    compute_vwap_dist,
    compute_vol_zscore,
    detect_ema_cross,
    detect_vol_divergence,
    compute_ud_ratio,
    detect_vcp,
    compute_cmf,
    is_atr_shrinking,
    compute_liquidity_shock,
)
from egx_radar.core.signals import get_signal_direction
from egx_radar.core.portfolio import compute_portfolio_guard
from egx_radar.core.signal_engine import (
    apply_regime_gate,
    detect_conservative_market_regime,
    evaluate_symbol_snapshot,
    is_high_probability_trade,
)
from egx_radar.core.data_guard import DataGuard
from egx_radar.core.momentum_guard import MomentumGuard
from egx_radar.core.alpha_monitor import AlphaMonitor, AlphaStatus
from egx_radar.core.position_manager import PositionManager, AddOnResult
from egx_radar.state.app_state import STATE

_data_guard = DataGuard()
_momentum_guard = MomentumGuard()
STATE.momentum_guard = _momentum_guard
_alpha_monitor = AlphaMonitor()
_position_manager = PositionManager()
STATE.position_manager = _position_manager
from egx_radar.data.data_engine import get_data_engine
from egx_radar.data.merge import _source_labels, _source_labels_lock
from egx_radar.outcomes.engine import (
    oe_load_log,
    oe_process_open_trades,
    oe_record_signal,
    oe_save_rejections,
    oe_save_daily_scan,
)
from egx_radar.ui.components import (
    _enqueue,
    _pulse,
    draw_gauge,
    _update_heatmap,
    _update_rotation_map,
    _update_flow_map,
    _update_guard_bar,
    _update_regime_label,
    _update_brain_label,
)

try:
    from egx_radar.dashboard.websocket import emit_scan_complete  # Phase 9 — GAP-3 fix
except Exception:
    emit_scan_complete = None  # Phase 9 — GAP-3 fix — expected when running without Flask dashboard

try:
    from egx_radar.dashboard.telegram_service import dispatch_latest_snapshot_alerts
    from egx_radar.database import DatabaseManager
except Exception:
    dispatch_latest_snapshot_alerts = None
    DatabaseManager = None

log = logging.getLogger(__name__)
_telegram_db_manager = None
_telegram_db_lock = threading.Lock()


def _get_telegram_db_manager():
    """Lazy-load a DB manager for post-scan Telegram dispatch."""
    global _telegram_db_manager
    if _telegram_db_manager is not None:
        return _telegram_db_manager
    if DatabaseManager is None:
        return None
    with _telegram_db_lock:
        if _telegram_db_manager is not None:
            return _telegram_db_manager
        try:
            _telegram_db_manager = DatabaseManager()
            _telegram_db_manager.init_db()
        except Exception as exc:
            log.debug("Telegram alert DB unavailable: %s", exc)
            _telegram_db_manager = None
        return _telegram_db_manager


def build_capital_flow_map(results: List[dict], sector_strength: Dict[str, float]) -> Tuple[Dict[str, float], str]:
    sec_cpi  = {k: [] for k in SECTORS}
    sec_rank = {k: [] for k in SECTORS}
    for r in results:
        s = r["sector"]
        if s in sec_cpi:
            sec_cpi[s].append(r["cpi"])
            sec_rank[s].append(r["smart_rank"])

    flow_scores: Dict[str, float] = {}
    for sec in SECTORS:
        if not sec_cpi[sec]:
            flow_scores[sec] = 0.0
            continue
        avg_cpi  = sum(sec_cpi[sec])  / len(sec_cpi[sec])
        avg_rank = sum(sec_rank[sec]) / len(sec_rank[sec])
        prev_avg = STATE.get_sector_flow_avg(sec)
        delta    = avg_cpi - prev_avg
        flow_scores[sec] = delta + avg_rank * 0.05
        STATE.update_sector_flow(sec, avg_cpi)

    leader = max(flow_scores, key=flow_scores.get)
    return flow_scores, leader


_scan_lock = threading.Lock()
_INDICATOR_CACHE: Dict[str, dict] = {}
_INDICATOR_CACHE_LOCK = threading.Lock()

_shutdown_requested = False


def request_shutdown():
    global _shutdown_requested
    _shutdown_requested = True


def run_scan(widgets: dict) -> None:
    """
    FIX-H: All UI updates go through _enqueue() → _pump() on the main thread.
    Worker thread never touches Tkinter directly.
    """
    if _shutdown_requested or sys.is_finalizing():
        return
    if not _scan_lock.acquire(blocking=False):
        return
    scan_start = time.time()

    tree       = widgets["tree"]
    pbar       = widgets["pbar"]
    status_var = widgets["status_var"]
    g_rank     = widgets["gauge_rank"]
    g_flow     = widgets["gauge_flow"]
    heat_lbl   = widgets["heat_labels"]
    rot_lbl    = widgets["rot_labels"]
    flow_lbl   = widgets["flow_labels"]
    regime_lbl = widgets["regime_lbl"]
    brain_lbl  = widgets["brain_lbl"]
    verdict_var= widgets["verdict_var"]
    verdict_frm= widgets["verdict_frm"]
    verdict_w  = widgets["verdict_lbl_w"]
    scan_btn   = widgets["scan_btn"]
    guard_slbl = widgets["guard_sector_labels"]
    guard_elbl = widgets["guard_exposure_lbl"]
    guard_blbl = widgets["guard_blocked_lbl"]

    try:
        force_refresh_var = widgets.get("force_refresh_var")
        is_force = force_refresh_var.get() if force_refresh_var else False
        
        current_time = time.time()
        if is_force:
            _INDICATOR_CACHE.clear()
            if force_refresh_var:
                _enqueue(lambda: force_refresh_var.set(False))

        all_cached = False
        if _INDICATOR_CACHE:
            all_cached = True
            for sym in SYMBOLS.keys():
                c = _INDICATOR_CACHE.get(sym)
                if not c or (current_time - c.get("timestamp", 0)) > K.CACHE_TTL_SECONDS:
                    all_cached = False
                    break

        _enqueue(_pulse.stop)
        _enqueue(lambda: tree.delete(*tree.get_children()))
        _enqueue(lambda: pbar.configure(value=0))

        if all_cached:
            _enqueue(status_var.set, "⚡ Using cached indicator DataFrames (loaded instantly)…")
            all_data = {}
            # Fix: outcomes resolution — fetch OHLCV for open trades even in cache mode.
            # get_data_engine().fetch_live() hits its own disk cache (no re-download).
            # Without this, all_data={} causes oe_process_open_trades to receive df=None
            # for every trade and skip resolution entirely on every cache-hit scan.
            _open_trades_pending = oe_load_log()
            if _open_trades_pending:
                try:
                    all_data = get_data_engine().fetch_live()  # Fix: outcomes resolution
                except Exception as _oe_data_exc:
                    log.debug("Outcomes OHLCV fetch (cache mode) failed: %s", _oe_data_exc)
        else:
            _enqueue(status_var.set, "⏳ Loading data from multiple sources…")
            all_data = get_data_engine().fetch_live()
            if not all_data:
                _enqueue(status_var.set, "❌ Download failed — no data from any source.")
                return
            _enqueue(status_var.set, f"✅ {len(all_data)} symbols loaded — computing signals…")

        oe_open, oe_wins, oe_losses = oe_process_open_trades(all_data)
        if oe_wins or oe_losses:
            _enqueue(status_var.set, f"📊 Outcomes: {oe_wins}W/{oe_losses}L resolved…")

        current_open_trades = oe_load_log()
        results:  List[dict] = []
        sec_quant: Dict[str, List[float]] = {k: [] for k in SECTORS}
        _sec_quant_lock = threading.Lock()
        ema200_slopes: Dict[str, float]   = {}
        _ema200_slopes_lock = threading.Lock()
        whale_global = False
        rejections: List[Dict[str, str]]  = []
        
        # ── Market Breadth Health (internal — no external symbol dependency) ────
        # Strategy: count how many scanned symbols have price > EMA50.
        # If >50% of stocks are above their EMA50, market is healthy.
        # This is computed from raw all_data BEFORE the parallel scan so
        # _process_symbol can use market_healthy to gate breakout signals.
        if all_cached and "_MARKET_HEALTHY" in _INDICATOR_CACHE:
            market_healthy = _INDICATOR_CACHE["_MARKET_HEALTHY"]
        elif not all_data:
            # Cache-only path: no raw data downloaded — keep previous value
            market_healthy = _INDICATOR_CACHE.get("_MARKET_HEALTHY", True)
        else:
            above_ema50 = 0
            total_checked = 0
            for yahoo_sym, df_raw in all_data.items():
                if df_raw is None or df_raw.empty:
                    continue
                close = df_raw["Close"].dropna() if "Close" in df_raw.columns else None
                if close is None or len(close) < 52:
                    continue
                try:
                    ema50_val = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
                    price_val = float(close.iloc[-1])
                    total_checked += 1
                    if price_val > ema50_val:
                        above_ema50 += 1
                except (IndexError, ValueError, TypeError) as e:
                    log.warning("Error calculating EMA50 for %s: %s", yahoo_sym, e)
                    continue

            if total_checked == 0:
                market_healthy = True   # no data to decide — allow all
                log.warning("Market breadth: 0 symbols had sufficient bars — defaulting healthy=True.")
            else:
                breadth_ratio = above_ema50 / total_checked
                market_healthy = breadth_ratio > K.MARKET_BREADTH_THRESHOLD
                log.warning(
                    "Market breadth: %d/%d symbols above EMA50 (%.0f%%) → healthy=%s",
                    above_ema50, total_checked, breadth_ratio * 100, market_healthy,
                )

            _INDICATOR_CACHE["_MARKET_HEALTHY"] = market_healthy

        total = len(SYMBOLS)

        # Map market health → regime for evaluate_symbol_snapshot.
        # BULL: both STRONG and MEDIUM tiers may enter signals.
        # NEUTRAL: only STRONG tier enters (MEDIUM gated by _position_plan).
        pre_regime = "BULL" if market_healthy else "NEUTRAL"

        _reject_lock = threading.Lock()

        def _process_symbol(sym: str, yahoo: str):
            current_time = time.time()
            with _INDICATOR_CACHE_LOCK:
                c_data = _INDICATOR_CACHE.get(sym)
                if c_data and (current_time - c_data.get("timestamp", 0)) <= 3600:
                    res_copy = c_data["res_dict"].copy()
                    # FIX-5.4: Deep copy nested dicts so cache isn't corrupted
                    if "plan" in res_copy and res_copy["plan"] is not None:
                        res_copy["plan"] = dict(res_copy["plan"])
                    return res_copy, c_data["slope"], c_data["quantum_n"]

            if yahoo not in all_data:
                with _reject_lock: rejections.append({"sym": sym, "reason": "No data downloaded"})
                return None
            df = all_data[yahoo].copy()

            required = {"Close", "High", "Low", "Open"}
            if not required.issubset(set(df.columns)):
                with _reject_lock: rejections.append({"sym": sym, "reason": "Missing OHLC columns"})
                return None
            if "Volume" not in df.columns:
                df["Volume"] = 0.0

            # Safety net: squeeze any OHLCV column that is a DataFrame into a 1-D Series.
            # This can happen when yfinance returns a MultiIndex that was not fully flattened.
            for col in ["Close", "High", "Low", "Open", "Volume"]:
                if col in df.columns and isinstance(df[col], pd.DataFrame):
                    df[col] = df[col].iloc[:, 0]

            close = df["Close"].dropna()
            if len(close) < K.MIN_BARS:
                with _reject_lock: rejections.append({"sym": sym, "reason": f"Insufficient bars (<{K.MIN_BARS})"})
                return None
            price = float(close.iloc[-1])
            if price < K.PRICE_FLOOR:
                with _reject_lock: rejections.append({"sym": sym, "reason": f"Price below floor (<{K.PRICE_FLOOR})"})
                return None

            df_ta = df.tail(250).copy()

            last10 = df_ta["Close"].iloc[-10:]
            if len(last10) >= 10 and last10.nunique() <= 1 and df_ta["Volume"].iloc[-5:].sum() == 0:
                log.warning("Stale/frozen OHLC detected for %s — skipping", sym)
                with _reject_lock: rejections.append({"sym": sym, "reason": "Stale/frozen OHLC detected"})
                return None

            # ── Data Guard (Module 1) ────────────────────────────────────
            dg_result = _data_guard.evaluate(df_ta, sym)
            if not dg_result.passed:
                log.warning("DataGuard REJECTED %s (conf=%.1f): %s", sym, dg_result.confidence, dg_result.reason)
                with _reject_lock: rejections.append({"sym": sym, "reason": f"DataGuard: {dg_result.reason}"})
                return None
            dg_confidence = dg_result.confidence
            dg_tier       = dg_result.confidence_tier   # "FULL" or "DEGRADED"

            result = evaluate_symbol_snapshot(
                df_ta=df_ta,
                sym=sym,
                sector=get_sector(sym),
                regime=pre_regime,   # dynamically derived from market_healthy breadth signal
            )
            if result is None:
                with _reject_lock:
                    rejections.append({"sym": sym, "reason": "Failed conservative EGX filters"})
                return None

            mom_series = close.pct_change(5).rolling(3).mean()
            raw_mom_prev = mom_series.iloc[-2] if len(mom_series) >= 2 else float("nan")
            momentum_prev = float(raw_mom_prev) * 100 if pd.notna(raw_mom_prev) else 0.0

            mg_result = _momentum_guard.evaluate(
                symbol=sym,
                momentum_today=result["momentum"],
                momentum_yesterday=momentum_prev,
                adx=result["adx"],
                vol_ratio=result["vol_ratio"],
                df=df_ta,
                price=result["price"],
            )

            result["mom_arrow"] = STATE.momentum_arrow(sym, result["momentum"])
            result["dg_confidence"] = dg_confidence
            result["dg_tier"] = dg_tier
            result["mg_passed"] = mg_result.passed
            result["mg_position_scale"] = mg_result.position_scale
            result["mg_rank_boost"] = mg_result.effective_rank_threshold_boost
            result["mg_defensive"] = mg_result.defensive_mode
            result["mg_fatigue"] = mg_result.fatigue_mode
            result["mg_exemption_threshold"] = mg_result.exemption_threshold
            result["mg_flags"] = mg_result.flags
            result["mg_message"] = mg_result.message
            result["alpha_warning_level"] = _alpha_status.warning_level
            result["size_multiplier"] = mg_result.position_scale * _alpha_status.position_scale
            result["combined_position_scale"] = mg_result.position_scale * _alpha_status.position_scale
            result["combined_rank_boost"] = mg_result.effective_rank_threshold_boost + _alpha_status.rank_threshold_boost
            result["signal_display"] = result["signal"]
            result["signal_dir"] = get_signal_direction(result["tag"])

            slope = float(result.get("ema200_slope_pct", 0.0)) / 100.0
            return result, slope, float(result.get("quantum", 0.0))
        completed_count = 0

        _alpha_status = _alpha_monitor.evaluate()
        if _alpha_status.warning_level >= 1:
            log.warning("[AlphaMonitor] Level %d - %s", _alpha_status.warning_level, _alpha_status.message)
        if _alpha_status.pause_new_entries:
            log.warning("[AlphaMonitor] Level 3 - new entries paused this session. %s", _alpha_status.message)

        try:
            with ThreadPoolExecutor(max_workers=K.SCAN_MAX_WORKERS) as executor:
                future_to_sym = {executor.submit(_process_symbol, k, v): k for k, v in SYMBOLS.items()}
                for future in as_completed(future_to_sym):
                    sym = future_to_sym[future]
                    completed_count += 1
                    if completed_count % 4 == 0:
                        _enqueue(pbar.configure, value=int(completed_count / max(1, total) * 100))
                    try:
                        res = future.result()
                        if res is not None:
                            res_dict, slope, quantum_n = res
                            results.append(res_dict)
                            if slope != 0.0:
                                with _ema200_slopes_lock:
                                    ema200_slopes[res_dict["sym"]] = slope
                            with _sec_quant_lock:
                                sec_quant[res_dict["sector"]].append(quantum_n)
                            if res_dict.get("whale"):
                                whale_global = True
                    except Exception as exc:
                        log.error("Error processing %s: %s", sym, exc)
        except (RuntimeError, KeyboardInterrupt) as exc:
            log.warning("Scan interrupted during executor phase: %s", exc)
            return results if results else []

        if not results:
            _enqueue(
                status_var.set,
                f"No symbols passed conservative EGX filters - {len(all_data)} loaded. "
                f"Check turnover ({K.MIN_TURNOVER_EGP:,.0f} EGP), spread ({K.MAX_SPREAD_PCT:.1f}%), "
                f"price floor ({K.PRICE_FLOOR} EGP), or min bars ({K.MIN_BARS}).",
            )
            return

        sector_strength = {sec: (sum(v) / len(v) if v else 0.0) for sec, v in sec_quant.items()}
        _enqueue(_update_heatmap, heat_lbl, sector_strength)

        regime = detect_conservative_market_regime(results)
        _enqueue(_update_regime_label, regime_lbl, regime)

        rotation_scores = {}
        for sec in SECTORS:
            vals = [r["anticipation"] for r in results if r["sector"] == sec]
            avg = sum(vals) / len(vals) if vals else 0.0
            STATE.update_sector_rotation(sec, avg)
            rotation_scores[sec] = avg
        future_sector = max(rotation_scores, key=rotation_scores.get) if rotation_scores else "-"
        _enqueue(_update_rotation_map, rot_lbl, rotation_scores, future_sector)

        flow_map, flow_leader = build_capital_flow_map(results, sector_strength)
        _enqueue(_update_flow_map, flow_lbl, flow_map, flow_leader)

        buy_count = sum(1 for r in results if (r.get("plan") or {}).get("action") in ("ACCUMULATE", "PROBE"))
        if regime != "BULL" or not market_healthy:
            brain_mode = "defensive"
        elif buy_count >= 3:
            brain_mode = "aggressive"
        else:
            brain_mode = "neutral"
        brain_vol_req = 1.0
        STATE.set_brain(brain_mode)
        _enqueue(_update_brain_label, brain_lbl, brain_mode)

        try:
            STATE.update_neural_weights(results)
            nw = STATE.get_neural_weights()
        except Exception:
            nw = {"flow": 1.0, "structure": 1.0, "timing": 1.0}

        def _set_wait(r: dict, reason: str) -> None:
            plan = dict(r.get("plan") or {})
            plan["action"] = "WAIT"
            plan["size"] = 0
            plan["force_wait"] = True
            plan["winrate"] = 0.0
            plan["winrate_na"] = True
            r["plan"] = plan
            r["tag"] = "watch"
            r["signal"] = "WAIT"
            r["signal_reason"] = (r.get("signal_reason", "") + f" | {reason}").strip(" |")

        def _downgrade_to_probe(r: dict, reason: str) -> None:
            plan = dict(r.get("plan") or {})
            if plan.get("action") == "ACCUMULATE":
                plan["action"] = "PROBE"
            if plan.get("size", 0) > 0:
                plan["size"] = max(1, int(plan["size"] * 0.75))
            r["plan"] = plan
            if r.get("tag") == "buy":
                r["tag"] = "early"
                r["signal"] = "PROBE"
            r["signal_reason"] = (r.get("signal_reason", "") + f" | {reason}").strip(" |")

        weak_sectors = [s for s, _ in sorted(sector_strength.items(), key=lambda x: x[1])[:2] if sector_strength.get(s, 0.0) > 0.0]
        sector_rank_map = {sec: (val * 100.0) for sec, val in sector_strength.items()}

        for r in results:
            r["leader"] = r["smart_rank"] >= sector_rank_map.get(r["sector"], 0.0) + 8.0

            if r["smart_rank"] < K.SMARTRANK_MIN_ACTIONABLE:
                _set_wait(r, f"rank-below-{K.SMARTRANK_MIN_ACTIONABLE:.0f}")

            if regime != "BULL":
                r.update(apply_regime_gate(r, regime))
            elif not market_healthy and r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
                _set_wait(r, "market-breadth-weak")

            if r.get("zone") == "🔴 LATE" and r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
                _set_wait(r, "late-zone")

            if r.get("rsi", 0.0) > 65.0 and r.get("plan", {}).get("action") == "ACCUMULATE":
                _downgrade_to_probe(r, "rsi-high")
            if r.get("rsi", 0.0) >= K.RSI_OB_HARD_LIMIT:
                _set_wait(r, f"rsi-overbought-{r['rsi']:.0f}")

            atr_pct = (r["atr"] / r["price"] * 100.0) if r.get("atr") and r.get("price") else 0.0
            if atr_pct >= K.ATR_PCT_HARD_LIMIT:
                _set_wait(r, f"atr-too-high-{atr_pct:.1f}%")
            elif atr_pct >= K.ATR_PCT_SOFT_LIMIT and r.get("plan", {}).get("action") == "ACCUMULATE":
                _downgrade_to_probe(r, f"atr-elevated-{atr_pct:.1f}%")

            if r.get("sector") in weak_sectors and r.get("plan", {}).get("action") == "ACCUMULATE":
                _downgrade_to_probe(r, "weak-sector")

            if r.get("dg_tier") == "DEGRADED":
                if r.get("plan", {}).get("action") == "ACCUMULATE":
                    _downgrade_to_probe(r, f"dataguard-{r['dg_confidence']:.0f}")
                elif r.get("plan", {}).get("action") == "PROBE":
                    _set_wait(r, f"dataguard-{r['dg_confidence']:.0f}")
                r["confidence"] = round(r.get("confidence", 0.0) * 0.70, 1)

            if not r.get("mg_passed", True):
                mg_flags = " ".join(r.get("mg_flags", []))
                if r.get("accumulation_detected"):
                    if "LOSS_CLUSTER" in mg_flags or "FATIGUE" in mg_flags:
                        if r.get("smart_rank", 0.0) < K.SMARTRANK_ENTRY_THRESHOLD + r.get("mg_rank_boost", 0.0):
                            _set_wait(r, "momentum-guard-hard")
                        elif r.get("plan", {}).get("action") == "ACCUMULATE":
                            _downgrade_to_probe(r, "momentum-guard-hard")
                    elif r.get("plan", {}).get("action") == "ACCUMULATE":
                        _downgrade_to_probe(r, "momentum-guard-soft")
                    r["confidence"] = round(r.get("confidence", 0.0) * 0.92, 1)
                else:
                    if r.get("smart_rank", 0.0) < K.SMARTRANK_ENTRY_THRESHOLD + r.get("mg_rank_boost", 0.0):
                        _set_wait(r, "momentum-guard")
                    elif r.get("plan", {}).get("action") == "ACCUMULATE":
                        _downgrade_to_probe(r, "momentum-guard")
                    r["confidence"] = round(r.get("confidence", 0.0) * 0.85, 1)

            combined_scale = float(r.get("combined_position_scale", 1.0) or 1.0)
            if r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
                r["plan"]["size"] = max(1, int(max(1, r["plan"].get("size", 1)) * combined_scale))

            winrate = STATE.estimate_winrate(
                r["smart_rank"],
                r["anticipation"],
                sector=r["sector"],
                tag=r["tag"],
                regime=regime,
            )
            r["plan"]["winrate"] = winrate if not r["plan"].get("force_wait") else 0.0
            r["plan"]["winrate_na"] = r["plan"].get("force_wait", False)

            if r.get("mg_flags"):
                r["signal_reason"] = (r.get("signal_reason", "") + f" | MomGuard:{','.join(r['mg_flags'])}").strip(" |")

            r["signal_dir"] = get_signal_direction(r["tag"])
            direction = "UP " if r["tag"] in ("buy", "ultra", "early") else "SIDE "
            r["signal_display"] = direction + r["signal"]
            if r["plan"].get("action") == "WAIT":
                r["inst_conf"] = "WEAK"
            elif r["plan"].get("action") == "PROBE":
                r["inst_conf"] = "GOOD"
            else:
                r["inst_conf"] = "STRONG"

        STATE.record_signal_bias(results)

        # ── Post-scoring cache update: Write final results to cache ─────────────
        # FIX: Cache must be written AFTER SmartRank scoring pass, sector blacklist,
        # liquidity gate, and all signal assignments complete. This ensures cached
        # data has correct smart_rank, action, plan, and guard_reason values.
        if K.INDICATOR_CACHE_ENABLED:
            current_time = time.time()
            with _INDICATOR_CACHE_LOCK:
                for r in results:
                    sym = r.get("sym")
                    if sym:
                        _INDICATOR_CACHE[sym] = {
                            "timestamp": current_time,
                            "res_dict": r,  # Full scored result
                            "slope": ema200_slopes.get(sym, 0.0),
                            "quantum_n": r.get("quantum", 0.0)
                        }

        # Pre-sort for guard priority (guard processes in this order)
        results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))

        # ── Portfolio guard (FIX-G: pure function) ────────────────────────────
        guarded_list, guard_counts, guard_exp, guard_blocked, daily_loss_triggered = compute_portfolio_guard(results, open_trades=current_open_trades)

        # Apply guard annotations to results (create new copies — no mutation of scoring data)
        annotated_results: List[dict] = []
        for gr in guarded_list:
            r_copy = dict(gr.result)
            r_copy["guard_reason"] = gr.guard_reason
            if gr.is_blocked:
                r_copy["tag"]            = "watch"
                r_copy["signal"]         = "🛡️ BLOCKED"
                r_copy["signal_display"] = "→ 🛡️ BLOCKED"
                r_copy["plan"]           = {**r_copy["plan"], "action": "WAIT 🛡️"}
                rejections.append({"sym": r_copy["sym"], "reason": f"Guard Blocked: {gr.guard_reason}"})
            annotated_results.append(r_copy)

        # FIX BUG#2: Re-sort using post-guard tag so BLOCKED items no longer
        # appear above active BUY/EARLY signals in the display table.
        annotated_results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))

        if daily_loss_triggered:
            _enqueue(status_var.set, "🛑 DAILY LOSS LIMIT REACHED — new entries blocked")
            log.warning("[PortfolioGuard] Daily loss limit triggered — all new entries blocked.")

        _enqueue(_update_guard_bar, guard_slbl, guard_elbl, guard_blbl,
                 guard_counts, guard_exp, guard_blocked)

        # ── Record new signals ────────────────────────────────────────────────
        # is_high_probability_trade() is the SAME quality gate used in backtest/engine.py.
        # This ensures live recording and backtest entry use identical trade selection.
        smart_rank_entry_threshold = float(getattr(K, "SMARTRANK_ENTRY_THRESHOLD", 20))
        for r in annotated_results:
            if (r.get("plan") and
                r["plan"]["action"] in ("ACCUMULATE", "PROBE") and
                not r["guard_reason"] and
                is_high_probability_trade(r)):
                
                # ── Position Manager: check for add-on opportunity
                _existing = _position_manager.get_open_position(r["sym"])
                if _existing is not None:
                    # Symbol already has an open trade — evaluate add-on instead of new entry
                    _addon = _position_manager.evaluate_addon(
                        symbol=r["sym"],
                        current_price=r["price"],
                        adx=r["adx"],
                        momentum=r["momentum"],
                        smart_rank=r["smart_rank"],
                        smart_rank_threshold=smart_rank_entry_threshold + r.get("combined_rank_boost", 0),
                        bearish_divergence=r.get("bearish_divergence", False),
                    )
                    if _addon.approved:
                        log.info("[PositionManager] Add-on approved for %s | %s", r["sym"], _addon.reason)
                        r["addon_approved"] = True
                        r["addon"] = _addon
                        # NOTE: confirm_addon() called only after broker execution confirms
                        # _position_manager.confirm_addon(sym)  ← call this from UI/execution layer
                    else:
                        log.debug("[PositionManager] Add-on rejected for %s: %s", r["sym"], _addon.reason)
                        r["addon_approved"] = False
                    # Do NOT record a new signal for an already-open position
                    continue

                if not _alpha_status.pause_new_entries:
                    oe_record_signal(
                        sym=r["sym"], sector=r["sector"],
                        entry=r["plan"]["entry"], stop=r["plan"]["stop"],
                        target=r["plan"]["target"],
                        atr=r["atr"] or 0.0,
                        smart_rank=r["smart_rank"], anticipation=r["anticipation"],
                        action=r["plan"]["action"],
                        existing_trades=current_open_trades,
                        tag=r["tag"],
                        trade_type=r["plan"].get("trade_type", "UNCLASSIFIED"),
                        score=r["plan"].get("score", r.get("smart_rank", 0.0)),
                        risk_used=r["plan"].get("risk_used", 0.0),
                        trigger_price=r["plan"].get("trigger_price", r["plan"]["entry"]),
                        partial_target=r["plan"].get("partial_target"),
                        trailing_trigger=r["plan"].get("trailing_trigger"),
                        trailing_stop_pct=r["plan"].get("trailing_stop_pct"),
                    )
                else:
                    log.info("[AlphaMonitor] Signal for %s blocked — system in Level 3 pause", r["sym"])

        # ── Market Health Dashboard ───────────────────────────────────────────
        avg_rank_all = sum(r["smart_rank"] for r in annotated_results) / len(annotated_results) if annotated_results else 0.0
        if annotated_results:
            act_cnt = sum(1 for r in annotated_results if r["smart_rank"] >= K.ACCUM_SCORE_MIN)
            elite_cnt = sum(1 for r in annotated_results if r["smart_rank"] >= K.ACCUM_SCORE_ENTRY)
            sell_cnt = sum(1 for r in annotated_results if r["tag"] == "sell")
            
            if avg_rank_all >= 65: lbl_text, fg = "ACTIVE", "#00ff00"
            elif avg_rank_all >= 55: lbl_text, fg = "BUILDING", "#ffcc33"
            else: lbl_text, fg = "QUIET", "#ff6666"
            
            if all_cached:
                lbl_text += " (cached)"
            
            _enqueue(widgets["health_avg_var"].set, f"Avg Rank: {avg_rank_all:.1f}")
            _enqueue(widgets["health_act_var"].set, f"Actionable (>={int(K.ACCUM_SCORE_MIN)}): {act_cnt}")
            _enqueue(widgets["health_elite_var"].set, f"Elite (>={int(K.ACCUM_SCORE_ENTRY)}): {elite_cnt}")
            _enqueue(widgets["health_sell_var"].set, f"SELL Signals: {sell_cnt}")
            _enqueue(lambda: widgets["health_lbl"].configure(text=f"Label: {lbl_text}", fg=fg))

        # ── Entry window verdict ──────────────────────────────────────────────
        early_cnt    = sum(1 for r in annotated_results if r["zone"] == "🟢 EARLY")
        late_cnt     = sum(1 for r in annotated_results if r["zone"] == "🔴 LATE")
        if avg_rank_all >= 55 and early_cnt >= late_cnt:
            entry_txt, entry_col = "🟢 ACCUMULATION WINDOW", "#062016"
        elif late_cnt > early_cnt:
            entry_txt, entry_col = "🟡 WAIT FOR CLEAN BASES", "#2a260a"
        else:
            entry_txt, entry_col = "🚫 NO POSITION ZONE",    "#2b0a0a"

        # ── Insert rows ───────────────────────────────────────────────────────
        medals       = ["🥇 ", "🥈 ", "🥉 "]
        phase_icon   = {"Accumulation": "🟡", "Transition": "🟢", "Exhaustion": "🔴", "Base": "⚪"}
        accum_syms   = [r["sym"] for r in annotated_results if (r.get("plan") or {}).get("action") == "ACCUMULATE"][:3]
        
        # Auto-highlight TOP 5 opportunities: 3D Gain <1.0, ACCUMULATE/PROBE, non-blocked
        top_candidates = [
            r for r in annotated_results 
            if float(r.get('last_3_days_gain_pct', 100.0)) < 1.0 
            and r["plan"]["action"] in ("ACCUMULATE", "PROBE")
            and not r.get("guard_reason")
        ]
        top_5_syms = [r["sym"] for r in sorted(
            top_candidates, 
            key=lambda x: (x.get('last_3_days_gain_pct', 100.0), -x["smart_rank"])
        )[:5]]
        
        with STATE._lock:
            win_sample = len(STATE.neural_win_memory) + len(STATE.neural_loss_memory)

        def _insert_all():
            # Deduplicate: keep first occurrence of each (sym, tag) pair
            seen = set()
            deduped = []
            for r in annotated_results:
                key = (r.get("sym"), r.get("tag"))
                if key not in seen:
                    seen.add(key)
                    deduped.append(r)
            items = list(enumerate(deduped))

            for i, r in items:
                prefix = medals[i] if i < 3 else f"#{i+1} "
                icons  = phase_icon.get(r["phase"], "⚪")
                if r["breakout"]:                   icons += "💥"
                if r["quantum"] > 0.5:              icons += "🧿"
                if r["fake_expansion"]:             icons += "☠️"
                if r["leader"]:                     icons += "👑"
                if r["ema_cross"] == "BULL_CROSS":  icons += "🔔"
                if r["ema_cross"] == "BEAR_CROSS":  icons += "🔕"
                if r["vol_div"]:                    icons += r["vol_div"]

                extras = (
                    f"{icons} {r['whale']} {r['hunter']} "
                    f"{'🧬' if r['silent'] else ''}{'⚡' if r['expansion'] else ''}"
                ).strip()

                disp = f"{prefix}{r['signal_display']}"

                if r["plan"].get("winrate_na"):
                    wr_str = "—"
                elif win_sample < K.WINRATE_MIN_SAMPLE:
                    wr_str = "⌛ Building"
                else:
                    wr_str = f"{r['plan']['winrate']:.0f}%"

                gain_3d = float(r.get("last_3_days_gain_pct", 0.0))
                gain_str = f"{gain_3d:+.1f}%"
                if gain_3d < 1.0:
                    gain_tag = "buy"
                elif gain_3d <= 2.0:
                    gain_tag = "watch"
                else:
                    gain_tag = "sell"
                row = (
                    r["sym"], r["sector"],
                    f"{r['price']:.2f}", f"{r['adx']:.1f}", f"{r['rsi']:.0f}",
                    f"{r['adaptive_mom']:+.1f}", f"{r['pct_ema200']:+.1f}%", gain_str,
                    f"{r['vol_ratio']:.1f}x",
                    f"{r.get('tech_score_pct', 0):.0f}%", r["gravity_label"], r["zone"],
                    f"{r['anticipation']:.2f}", f"{r['cpi']:.2f}",
                    f"{r['iet']:.2f}", f"{r['whale_score']:.2f}",
                    extras, disp, r["signal_dir"],
                    f"{r['confidence']:.1f}%", f"{r['smart_rank']:.2f}",
                    r["plan"]["action"], r["plan"]["timeframe"],
                    f"{r['plan']['entry']:.2f}", f"{r['plan']['stop']:.2f}",
                    f"{r['plan']['target']:.2f}", str(r["plan"]["size"]),
                    wr_str, f"{r['plan']['rr']:.1f}x",
                    r["inst_conf"], r["atr_risk"],
                    r["mom_arrow"],
                    f"{r['atr']:.2f}" if r["atr"] else "—",
                    f"{r['vwap_dist']*100:.1f}%", f"{r['vol_zscore']:.1f}",
                    r["signal_reason"],
                    r["guard_reason"] if r["guard_reason"] else "✅ OK",
                )
                if r["guard_reason"]:
                    row_tag = "blocked"
                else:
                    row_tag = (
                        "accum_top" if r["sym"] in accum_syms
                        else ("radar" if r["silent"] else r["tag"])
                    )
                if r["sym"] in top_5_syms:
                    row_tag += ("top_opportunity",)
                row_tag = (row_tag, gain_tag)
                tree.insert("", "end", values=row, tags=row_tag)  # Fix: duplicate symbols bug — removed second tree.insert()

        _enqueue(_insert_all)

        # ── Status summary ───────────────────────────────────────────────────
        mood    = ("Institutional Positioning" if avg_rank_all >= 70
                   else ("Bases Building" if avg_rank_all >= 55 else "Capital Protection"))
        
        if not market_healthy:
            mood += " | ⚠️ Market EMA50 Breakdown"
            
        safe_s  = [r["sym"] for r in annotated_results if r["smart_rank"] >= K.ACCUM_SCORE_ENTRY][:3]
        watch_s = [r["sym"] for r in annotated_results if K.ACCUM_SCORE_MIN <= r["smart_rank"] < K.ACCUM_SCORE_ENTRY][:3]
        avoid_s = [r["sym"] for r in annotated_results if r["smart_rank"] < K.ACCUM_SCORE_MIN][:3]

        verdict_txt = (
            f"🧠 BRAIN | {entry_txt} | {mood} | "
            f"🟢 {', '.join(safe_s) or '—'} | "
            f"🟡 {', '.join(watch_s) or '—'} | "
            f"🔴 {', '.join(avoid_s) or '—'}"
        )
        if guard_blocked:
            verdict_txt += f" | 🛡️ BLOCKED: {', '.join(guard_blocked)}"
        _enqueue(verdict_var.set, verdict_txt)
        _enqueue(verdict_frm.configure, bg=entry_col)
        _enqueue(verdict_w.configure, bg=entry_col)

        avg_future = sum(r["anticipation"] for r in annotated_results) / len(annotated_results) if annotated_results else 0.0
        _enqueue(draw_gauge, g_rank, avg_rank_all, K.SMART_RANK_SCALE, "SmartRank", brain_mode)
        _enqueue(draw_gauge, g_flow, avg_future,   1.0,  "FutureFlow", "anticipation")

        if whale_global:
            _enqueue(_pulse.start, verdict_frm, verdict_w, entry_col)

        elapsed   = round(time.time() - scan_start, 1)
        nw_str    = f"F{nw['flow']:.2f} S{nw['structure']:.2f} T{nw['timing']:.2f}"
        guard_pct = (guard_exp / (get_account_size() + 1e-9)) * 100
        guard_sum = f"🛡️{len(guard_blocked)}blk" if guard_blocked else f"🛡️OK({guard_pct:.1f}%)"
        oe_sum    = f"📊{len(current_open_trades)}open/{oe_wins}W/{oe_losses}L"

        with _source_labels_lock:
            src_snap = dict(_source_labels)
        src_counts: Dict[str, int] = {}
        for lbl in src_snap.values():
            base = lbl.split("+")[0].replace("⚠️", "")
            src_counts[base] = src_counts.get(base, 0) + 1
        src_summary = " | ".join(f"{k}:{v}" for k, v in src_counts.items()) or "—"

        _enqueue(status_var.set,
                 f"✅ {len(annotated_results)} symbols | Regime:{regime} | Next:{future_sector} | "
                 f"Brain:{brain_mode} | Neural:{nw_str} | {guard_sum} | {oe_sum} | "
                 f"🌐{src_summary} | ⏱ {elapsed}s | {datetime.now().strftime('%H:%M:%S')}")
        _enqueue(pbar.configure, value=100)
        with STATE._lock:          # FIX: scan_count must be mutated under lock
            STATE.scan_count += 1
            
        # Feature 7: Record Rejections DataFrame
        # Ensure symbols that were never processed are logged as rejections
        processed_syms = {r["sym"] for r in annotated_results}
        rejected_syms  = {r["sym"] for r in rejections}
        all_syms       = set(SYMBOLS.keys())
        ghost_syms     = all_syms - processed_syms - rejected_syms

        for sym in sorted(ghost_syms):
            log.warning("Symbol %s never processed — possibly missing from all_data", sym)
            rejections.append({"sym": sym, "reason": "Never processed (no data from any source)"})

        oe_save_rejections(rejections)

        # ── Auto-save daily scan snapshot ──────────────────────────────────
        if K.SCAN_HISTORY_ENABLED:
            try:
                saved_path = oe_save_daily_scan(annotated_results)
                if saved_path:
                    log.info("Scan history saved: %s", saved_path)
            except Exception as e:
                log.warning("Could not save daily scan: %s", e)

        # ── Save latest scan results for API consumption (thread-safe JSON snapshot) ────
        try:
            _snapshot_path = os.path.join(
                os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
            )
            
            snapshot = [{
                "sym":        r["sym"],
                "sector":     r["sector"],
                "price":      r["price"],
                "signal":     r["signal"],
                "tag":        r["tag"],
                "smart_rank": r.get("smart_rank", 0.0),
                "confidence": r.get("confidence", 0.0),
                "direction":  r.get("signal_dir", ""),
                "phase":      r.get("phase", ""),
                "zone":       r.get("zone", ""),
                "action":     r.get("plan", {}).get("action", "WAIT") if r.get("plan") else "WAIT",
                "entry":      r.get("plan", {}).get("entry", 0.0)    if r.get("plan") else 0.0,
                "stop":       r.get("plan", {}).get("stop", 0.0)     if r.get("plan") else 0.0,
                "target":     r.get("plan", {}).get("target", 0.0)   if r.get("plan") else 0.0,
                "winrate":    r.get("plan", {}).get("winrate", 0.0)  if r.get("plan") else 0.0,
                "scan_time":  datetime.utcnow().isoformat(),
            } for r in annotated_results]
            
            # Atomic write: temp file → replace
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(_snapshot_path), suffix='.tmp')
            with os.fdopen(fd, 'w') as f:
                json.dump(snapshot, f, default=str)
            os.replace(tmp, _snapshot_path)
            log.debug("API scan snapshot saved: %d signals", len(snapshot))
        except Exception as _snap_exc:
            log.debug("scan snapshot write failed: %s", _snap_exc)

        # ── Emit WebSocket event to dashboard clients ─────────────────────────
        try:  # Phase 9 — GAP-3 fix — emit failure must never abort the scan
            if emit_scan_complete:  # Phase 9 — GAP-3 fix
                emit_scan_complete(annotated_results)  # Phase 9 — GAP-3 fix
        except Exception as _ws_exc:  # Phase 9 — GAP-3 fix
            log.debug("WebSocket emit skipped: %s", _ws_exc)  # Phase 9 — GAP-3 fix

        # ── Send Telegram alerts after a successful snapshot write ────────────
        try:
            _tg_db = _get_telegram_db_manager()
            if dispatch_latest_snapshot_alerts and _tg_db is not None:
                _tg_summary = dispatch_latest_snapshot_alerts(_tg_db)
                if _tg_summary.get("sent", 0) or _tg_summary.get("duplicates_skipped", 0):
                    log.info(
                        "Telegram alerts | sent=%s skipped=%s users=%s signals=%s",
                        _tg_summary.get("sent", 0),
                        _tg_summary.get("duplicates_skipped", 0),
                        _tg_summary.get("users_checked", 0),
                        _tg_summary.get("signals_seen", 0),
                    )
        except Exception as _tg_exc:
            log.debug("Telegram alert dispatch skipped: %s", _tg_exc)

    except Exception as exc:
        log.error("Scan fatal: %s", exc, exc_info=True)
        _enqueue(status_var.set, f"❌ Error: {exc}")
    finally:
        _enqueue(scan_btn.configure, state="normal")
        _scan_lock.release()


def start_scan(widgets: dict) -> None:
    if _shutdown_requested:
        return
    widgets["scan_btn"].configure(state="disabled")
    threading.Thread(target=run_scan, args=(widgets,), daemon=True).start()


__all__ = [
    "build_capital_flow_map",
    "_scan_lock",
    "run_scan",
    "start_scan",
    "request_shutdown",
]


# ── CLI Entrypoint: Run scan and output results to file ─────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run EGX Radar scan and output results.")
    parser.add_argument("--output", type=str, required=True, help="Path to output JSON file for scan results.")
    args = parser.parse_args()

    # Minimal widgets mock for headless scan
    class Dummy:
        def set(self, *a, **k): pass
        def configure(self, *a, **k): pass
        def get(self): return False
        def delete(self, *a, **k): pass
    widgets = {k: Dummy() for k in [
        "tree", "pbar", "status_var", "gauge_rank", "gauge_flow", "heat_labels", "rot_labels", "flow_labels", "regime_lbl", "brain_lbl", "verdict_var", "verdict_frm", "verdict_lbl_w", "scan_btn", "guard_sector_labels", "guard_exposure_lbl", "guard_blocked_lbl", "force_refresh_var"
    ]}

    # Patch run_scan to return annotated results
    results_holder = {}
    def run_scan_headless(widgets):
        # Copy of run_scan, but capture annotated_results
        # Only the final annotated_results are needed for output
        # This is a minimal, safe patch: call original run_scan, then fetch from STATE
        # But since run_scan does not return, we must duplicate the logic
        # Instead, re-run the core scan logic here, headless
        from egx_radar.data.data_engine import get_data_engine
        from egx_radar.config.settings import SYMBOLS
        all_data = get_data_engine().fetch_scan()
        # Use the same logic as in run_scan for processing
        # For safety, import and call evaluate_symbol_snapshot etc. as in run_scan
        # This is a minimal, non-UI scan for CLI
        # ---
        # The following is a simplified scan loop for CLI use
        results = []
        for sym, yahoo in SYMBOLS.items():
            df = all_data.get(yahoo)
            if df is None or df.empty:
                continue
            from egx_radar.core.signals import get_signal_direction
            from egx_radar.core.signal_engine import evaluate_symbol_snapshot
            from egx_radar.config.settings import get_sector
            res = evaluate_symbol_snapshot(df_ta=df.tail(250), sym=sym, sector=get_sector(sym), regime="BULL")
            if res is not None:
                res["signal_dir"] = get_signal_direction(res["tag"])
                results.append(res)
        # Sort as in run_scan
        from egx_radar.config.settings import DECISION_PRIORITY
        results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))
        # Output
        results_holder["results"] = results

    run_scan_headless(widgets)
    out_path = args.output
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_holder["results"], f, indent=2, default=str)
    print(f"Scan complete. Results written to {out_path}")
