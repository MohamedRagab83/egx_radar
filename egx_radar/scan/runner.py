"""Scan core: orchestrates all layers into one scan pass."""

import logging
import math
import sys
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
from egx_radar.core.scoring import (
    _norm,
    score_capital_pressure,
    score_institutional_entry,
    score_whale_footprint,
    score_flow_anticipation,
    score_quantum,
    score_gravity,
    smart_rank_score,
)
from egx_radar.core.signals import (
    detect_market_regime,
    detect_phase,
    detect_predictive_zone,
    build_signal,
    build_signal_reason,
    get_signal_direction,
)
from egx_radar.core.risk import build_trade_plan, institutional_confidence
from egx_radar.core.portfolio import compute_portfolio_guard
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
from egx_radar.data.merge import download_all, _source_labels, _source_labels_lock
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

log = logging.getLogger(__name__)


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
        else:
            _enqueue(status_var.set, "⏳ Loading data from multiple sources…")
            all_data = download_all()
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

            ema200_s   = close.ewm(span=200, adjust=False).mean()
            ema50_s    = close.ewm(span=50,  adjust=False).mean()
            ema200     = last_val(ema200_s)
            ema50      = last_val(ema50_s)

            # NaN/zero guard — if EMAs are zero, data is insufficient for reliable scoring
            if ema200 <= 0 or ema50 <= 0:
                log.warning("Invalid EMA values for %s (ema200=%.2f, ema50=%.2f) — skipping", sym, ema200, ema50)
                with _reject_lock:
                    rejections.append({"sym": sym, "reason": "Invalid EMA200/EMA50 (zero or NaN)"})
                return None

            pct_ema200 = safe_clamp(((price - ema200) / (ema200 + 1e-9)) * 100, -50.0, 50.0)

            slope = 0.0
            if len(ema200_s) >= K.REGIME_SLOPE_BARS + 2:
                slope = float(ema200_s.iloc[-1] - ema200_s.iloc[-K.REGIME_SLOPE_BARS]) / (price + 1e-9)

            mom_series = close.pct_change(5).rolling(3).mean()
            raw_mom  = mom_series.iloc[-1]
            momentum = float(raw_mom) * 100 if pd.notna(raw_mom) else 0.0
            raw_mom_prev = mom_series.iloc[-2] if len(mom_series) >= 2 else float('nan')
            momentum_prev = float(raw_mom_prev) * 100 if pd.notna(raw_mom_prev) else 0.0

            try:
                adf      = pta.adx(df_ta["High"], df_ta["Low"], df_ta["Close"], length=K.ADX_LENGTH)
                col_name = f"ADX_{K.ADX_LENGTH}"
                adx_val  = last_val(adf[col_name]) if (adf is not None and col_name in adf.columns) else 0.0
                rsi_val  = last_val(pta.rsi(close, length=14))
            except Exception as _indicator_exc:
                # Rate-limit logging to avoid flooding the console under thread contention
                if not hasattr(_process_symbol, '_indicator_fail_count'):
                    _process_symbol._indicator_fail_count = 0
                _process_symbol._indicator_fail_count += 1

                if _process_symbol._indicator_fail_count <= 3:
                    log.warning(
                        "_process_symbol [%s]: pandas_ta computation failed (%s). "
                        "Fallback to adx=0.0, rsi=50.0. "
                        "This may be a thread-safety issue — "
                        "pin pandas_ta version in requirements.txt.",
                        sym, _indicator_exc,
                    )
                elif _process_symbol._indicator_fail_count == 4:
                    log.warning(
                        "Further pandas_ta failures will be suppressed. "
                        "Total failures so far: %d. "
                        "Consider setting SCAN_MAX_WORKERS=1 to isolate the issue.",
                        _process_symbol._indicator_fail_count,
                    )

                adx_val, rsi_val = 0.0, 50.0

            adx_factor   = min(1.4, max(0.6, adx_val / 25.0))
            adaptive_mom = momentum * adx_factor

            if adx_val >= 99.0 or rsi_val >= 99.0:
                log.warning("Degenerate indicators for %s (ADX=%.1f RSI=%.1f) — skipping", sym, adx_val, rsi_val)
                with _reject_lock: rejections.append({"sym": sym, "reason": f"Degenerate logic (ADX={adx_val:.1f}, RSI={rsi_val:.1f})"})
                return None

            avg_vol_raw = df["Volume"].rolling(20).mean().iloc[-1]
            if pd.isna(avg_vol_raw):
                with _reject_lock: rejections.append({"sym": sym, "reason": "NaN volume average"})
                return None
            avg_vol = float(avg_vol_raw)
            has_vol = avg_vol > 0
            if has_vol and avg_vol < K.LOW_LIQ_FILTER:
                with _reject_lock: rejections.append({"sym": sym, "reason": f"Low liquidity (Vol < {K.LOW_LIQ_FILTER})"})
                return None

            # Volume tier for UI display
            if avg_vol >= 1_000_000:
                vol_tier = "🟢 High"
            elif avg_vol >= 100_000:
                vol_tier = "🟡 Mid"
            elif avg_vol >= 50_000:
                vol_tier = "🔴 Low"
            else:
                vol_tier = "⚫ Thin"

            vol_ratio = safe_clamp(float(df["Volume"].iloc[-1]) / (avg_vol + 1e-9), 0.0, 5.0) if has_vol else 1.0

            vwap_dist  = compute_vwap_dist(df_ta, price)
            vol_zscore = compute_vol_zscore(df_ta)
            atr        = compute_atr(df_ta)
            atr_label, atr_pct_rank = compute_atr_risk(df_ta, price)
            cmf_val    = compute_cmf(df_ta)
            liq_shock  = compute_liquidity_shock(df_ta, atr, avg_vol)

            ud_ratio   = compute_ud_ratio(df_ta)
            is_vcp     = detect_vcp(df_ta)

            # [P3-E2] VCP Score Multiplier
            vcp_detected_p3e2 = False
            if K.VCP_MULTIPLIER_ENABLED:
                atr_is_shrinking = is_atr_shrinking(df_ta)
                volume_declining = vol_ratio < 0.8
                price_above_ema50 = price > ema50
                if atr_is_shrinking and volume_declining and price_above_ema50:
                    vcp_detected_p3e2 = True

            bar_h   = float(df_ta["High"].iloc[-1])
            bar_l   = float(df_ta["Low"].iloc[-1])
            bar_o   = float(df_ta["Open"].iloc[-1])
            bar_rng = bar_h - bar_l
            clv = (safe_clamp(((price - bar_l) - (bar_h - price)) / (bar_rng + 1e-9), -1.0, 1.0)
                   if bar_rng > 1e-9 else 0.0)

            ma_fast = close.ewm(span=10, adjust=False).mean()
            if len(ma_fast) >= 8:
                raw_acc = float((ma_fast.iloc[-1] - ma_fast.iloc[-3]) - (ma_fast.iloc[-5] - ma_fast.iloc[-8]))
            else:
                raw_acc = 0.0
            trend_acc = safe_clamp(raw_acc / (price + 1e-9), -0.05, 0.05)

            recent_hi = float(df_ta["High"].iloc[-6:-1].max())
            body      = abs(price - bar_o)
            breakout  = (
                price > recent_hi and vol_ratio > 1.3 and
                (body / (bar_rng + 1e-9)) > K.FAKE_BREAK_BODY
            )
            
            if breakout and not market_healthy:
                breakout = False
                log.debug("Blocked breakout on %s due to unhealthy broad market.", sym)

            hidden_score = 0.0
            if adx_val < 20 and 45 < rsi_val < 60: hidden_score += 1.5
            if vol_ratio < 1.2 and clv > 0.4:       hidden_score += 1.0
            if trend_acc > 0:                        hidden_score += 1.0
            if body / (bar_rng + 1e-9) < 0.35:      hidden_score += 0.5

            phase = detect_phase(adx_val, rsi_val, vol_ratio, trend_acc, clv, adaptive_mom, ema50, price,
                                 body_ratio=body / (bar_rng + 1e-9))
            zone  = detect_predictive_zone(rsi_val, adaptive_mom, pct_ema200, vol_ratio)

            expansion = (adx_val > K.ADX_MID and momentum > 1.2 and vol_ratio > 1.1 and trend_acc > 0)
            fake_exp  = (expansion and rsi_val > 66 and vol_ratio < 1.25 and clv < 0.35 and momentum < 2.8)
            silent    = (45 <= rsi_val <= 60 and trend_acc > 0 and clv > 0.5 and vol_ratio < 1.3 and
                         (body / (bar_rng + 1e-9)) < 0.35)
            hunter    = (adx_val > 18 and 40 <= rsi_val <= 65 and vol_ratio > 1.25 and trend_acc > 0)
            whale_flag = ("🐳 Whale" if (vol_zscore > K.WHALE_ZSCORE_THRESH and
                                          clv > K.WHALE_CLV_SIGNAL and vol_ratio > K.WHALE_VOL_THRESH) else "")

            cpi_n      = score_capital_pressure(clv, trend_acc, vol_ratio, price, ema50, vwap_dist, ud_ratio, is_vcp)
            iet_n      = score_institutional_entry(rsi_val, adx_val, clv, trend_acc, vol_ratio, pct_ema200)
            whale_n    = score_whale_footprint(adx_val, clv, trend_acc, vol_ratio, rsi_val)
            ant_n      = score_flow_anticipation(rsi_val, adx_val, clv, trend_acc, vol_ratio, pct_ema200)
            quantum_n  = score_quantum(rsi_val, momentum, trend_acc, clv, vol_ratio)
            grav_lbl, grav_n = score_gravity(clv, trend_acc, vol_ratio, rsi_val, adaptive_mom)

            # ── Momentum Guard (Module 2) ─────────────────────────────
            mg_result = _momentum_guard.evaluate(
                symbol=sym,
                momentum_today=momentum,
                momentum_yesterday=momentum_prev,
                adx=adx_val,
                vol_ratio=vol_ratio,
                df=df_ta,
                price=price,
            )
            # Track breakout follow-through for fatigue detection
            if breakout:
                _momentum_guard.record_breakout_result(sym, followed_through=True)

            ema_cross  = detect_ema_cross(close)
            vol_div    = detect_vol_divergence(close, df["Volume"])
            mom_arr    = STATE.momentum_arrow(sym, momentum)

            _, _, brain_score_req = STATE.snapshot_brain()
            signal, tag, tech_score = build_signal(
                price, ema200, ema50, adx_val, rsi_val,
                adaptive_mom, vol_ratio, breakout, pct_ema200, phase,
                brain_score_req=brain_score_req,
                vol_div=vol_div,
            )

            ant_n_effective = 0.0 if tag == "sell" else ant_n
            sector = get_sector(sym)

            res_dict = {
                "sym": sym, "sector": sector, "price": price,
                "adx": adx_val, "rsi": rsi_val, "momentum": momentum,
                "adaptive_mom": adaptive_mom, "pct_ema200": pct_ema200, "ema50": ema50,
                "vol_ratio": vol_ratio, "avg_vol": avg_vol, "vol_tier": vol_tier, "tech_score": tech_score,
                "tech_score_pct": round((tech_score / 18) * 100, 1),
                "signal": signal, "tag": tag, "phase": phase,
                "trend_acc": trend_acc, "breakout": breakout, "clv": clv,
                "whale": whale_flag, "hunter": "🎯 Hunter" if hunter else "",
                "silent": silent, "expansion": expansion, "fake_expansion": fake_exp,
                "vcp_detected": vcp_detected_p3e2,
                "cpi": cpi_n, "iet": iet_n, "whale_score": whale_n,
                "anticipation": ant_n_effective, "quantum": quantum_n,
                "gravity_label": grav_lbl, "gravity_score": grav_n,
                "zone": zone, "hidden": hidden_score,
                "ema_cross": ema_cross, "vol_div": vol_div,
                "mom_arrow": mom_arr, "atr": atr,
                "atr_risk": atr_label, "atr_pct_rank": atr_pct_rank,
                "vwap_dist": vwap_dist, "vol_zscore": vol_zscore,
                "cmf": cmf_val,
                "liq_shock": liq_shock,
                "smart_rank": 0.0, "confidence": 0.0, "leader": False,
                "plan": None, "inst_conf": "—",
                "signal_dir": "⏸️ NEUTRAL", "signal_reason": "",
                "signal_display": "", "guard_reason": "",
                "dg_confidence": dg_confidence, "dg_tier": dg_tier,
                "mg_passed": mg_result.passed,
                "mg_position_scale": mg_result.position_scale,
                "mg_rank_boost": mg_result.effective_rank_threshold_boost,
                "mg_defensive": mg_result.defensive_mode,
                "mg_fatigue": mg_result.fatigue_mode,
                "mg_exemption_threshold": mg_result.exemption_threshold,
                "mg_flags": mg_result.flags,
                "mg_message": mg_result.message,
                # Alpha Monitor (session-level)
                "alpha_warning_level": _alpha_status.warning_level,
                "size_multiplier": mg_result.position_scale * _alpha_status.position_scale,
                "combined_position_scale": mg_result.position_scale * _alpha_status.position_scale,
                "combined_rank_boost": mg_result.effective_rank_threshold_boost + _alpha_status.rank_threshold_boost,
            }
            
            return res_dict, slope, quantum_n

        completed_count = 0

        # ── Alpha Monitor: session-level edge check ────────────────────────
        _alpha_status = _alpha_monitor.evaluate()
        if _alpha_status.warning_level >= 1:
            log.warning("[AlphaMonitor] Level %d — %s", _alpha_status.warning_level, _alpha_status.message)
        if _alpha_status.pause_new_entries:
            log.warning("[AlphaMonitor] Level 3 — new entries paused this session. %s",
                        _alpha_status.message)

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
                            if res_dict["whale"]:
                                whale_global = True
                            if res_dict["sector"] in sec_quant:
                                with _sec_quant_lock:
                                    sec_quant[res_dict["sector"]].append(quantum_n)
                    except Exception as exc:
                        log.error("Error processing %s: %s", sym, exc)
        except (RuntimeError, KeyboardInterrupt) as exc:
            log.warning("Scan interrupted during executor phase: %s", exc)
            return results if results else []

        if not results:
            _enqueue(status_var.set,
                     f"⚠️ No symbols passed filters — {len(all_data)} loaded. "
                     f"Check liquidity threshold ({K.LOW_LIQ_FILTER:,.0f}), "
                     f"price floor ({K.PRICE_FLOOR} EGP), "
                     f"min bars ({K.MIN_BARS}), or enable more data sources.")
            return

        # ── Sector strength ────────────────────────────────────────────────────
        # Feature 6: Enhanced Sector Rotation Engine - Rank sectors by strength
        sector_strength: Dict[str, float] = {
            sec: (sum(v) / len(v) if v else 0.0) for sec, v in sec_quant.items()
        }
        
        # Identify the bottom 2 weakly performing sectors for signal downgrades
        sorted_sectors = sorted(sector_strength.items(), key=lambda x: x[1])
        weak_sectors = [s[0] for s in sorted_sectors[:2]] if len(sorted_sectors) >= 5 else []
        
        _enqueue(_update_heatmap, heat_lbl, sector_strength)

        # ── Regime ────────────────────────────────────────────────────────────
        regime = detect_market_regime(results, ema200_slopes)
        # NOTE: regime_weights was previously computed here but never used; removed (FIX: dead code)
        _enqueue(_update_regime_label, regime_lbl, regime)

        # ── Sector rotation ───────────────────────────────────────────────────
        rotation_scores: Dict[str, float] = {}
        for sec in SECTORS:
            vals = [r["anticipation"] for r in results if r["sector"] == sec]
            avg  = sum(vals) / len(vals) if vals else 0.0
            STATE.update_sector_rotation(sec, avg)   # FIX: was direct lock-free dict access
            rotation_scores[sec] = avg
        future_sector = max(rotation_scores, key=rotation_scores.get)
        _enqueue(_update_rotation_map, rot_lbl, rotation_scores, future_sector)

        # ── Capital flow map ──────────────────────────────────────────────────
        flow_map, flow_leader = build_capital_flow_map(results, sector_strength)
        _enqueue(_update_flow_map, flow_lbl, flow_map, flow_leader)

        # ── Brain mode: blend market signals with actual win rate performance ─
        buy_count  = sum(1 for r in results if r["tag"] in ("buy", "ultra", "early"))
        _wm        = list(STATE.neural_win_memory)
        _lm        = list(STATE.neural_loss_memory)
        _sample    = len(_wm) + len(_lm)

        if _sample >= 10:
            _live_wr = len(_wm) / _sample  # 0.0 – 1.0
            if buy_count >= 4 and _live_wr >= 0.50:
                _brain = "aggressive"
            elif buy_count <= 1 or _live_wr < 0.35:
                _brain = "defensive"
            else:
                _brain = "neutral"
        else:
            # Not enough history — use market signals only, default conservative
            _brain = "neutral" if buy_count >= 2 else "defensive"

        STATE.set_brain(_brain)
        brain_mode, brain_vol_req, _ = STATE.snapshot_brain()
        _enqueue(_update_brain_label, brain_lbl, brain_mode)

        # ── Neural weight update ──────────────────────────────────────────────
        STATE.update_neural_weights(results)
        nw = STATE.get_neural_weights()

        # ── Market soft flag ──────────────────────────────────────────────────
        if results:
            market_soft = (
                sum(r["adx"]       for r in results) / len(results) < 30 and
                sum(r["momentum"]  for r in results) / len(results) < 1.5 and
                sum(r["vol_ratio"] for r in results) / len(results) < 1.3
            )
        else:
            market_soft = False

        # ── SmartRank scoring pass ────────────────────────────────────────────
        sector_bias_map: Dict[str, float] = {
            sec: (1.25 if avg > 0.6 else (0.85 if avg < 0.28 else 1.0))
            for sec, avg in sector_strength.items()
        }

        def _wait_plan(price: float, atr: float = None, adx: float = 20.0,
                       clv: float = 0.0, trend_acc: float = 0.0,
                       anticipation: float = 0.0) -> dict:
            """WAIT plan still shows real S/L and target for monitoring purposes.

            This function returns a plan intended only for monitoring (size=1,
            force_wait=True) but computes realistic entry/stop/target levels so
            the trader knows where to watch and what the risk/reward would be.
            """
            px = round(price, 2)

            # Use ATR-based stop if available, else use percentage fallback
            if atr and atr > 0:
                stop   = round(px - 1.5 * atr, 2)
                target = round(px + 3.0 * atr, 2)
            elif adx < 22:
                stop   = round(px * 0.965, 2)
                target = round(px * 1.09,  2)
            else:
                stop   = round(px * 0.955, 2)
                target = round(px * 1.12,  2)

            entry = round(px * 0.995, 2)
            rps   = max(abs(entry - stop), 0.01)
            rr    = round(abs(target - entry) / rps, 1)

            return {
                "action":     "WAIT",
                "entry":      entry,
                "stop":       stop,
                "target":     target,
                "size":       1,         # size=1 signals "do not trade yet"
                "rr":         rr,
                "timeframe":  "📆 Position (wks)",
                "force_wait": True,
                "winrate":    0.0,
                "winrate_na": True,
            }

        # Build cross-sectional momentum series from all scanned symbols this session
        # so quantile normalization has a real EGX distribution to work with.
        all_momentum_values = [r.get("adaptive_mom", 0.0) for r in results if r.get("adaptive_mom") is not None]
        momentum_series = pd.Series(all_momentum_values) if len(all_momentum_values) >= 5 else None

        for r in results:
            # ── Sector blacklist gate ─────────────────────────────────────────
            if K.SECTOR_FILTER_ENABLED and r.get("sector") in K.BLACKLISTED_SECTORS:
                r["action"] = "WAIT"
                r["tag"] = "watch"
                r["signal"] = "⛔ WAIT (Sector)"
                r["plan"] = _wait_plan(
                    r["price"],
                    atr=r.get("atr"),
                    adx=r.get("adx", 20.0),
                    clv=r.get("clv", 0.0),
                    trend_acc=r.get("trend_acc", 0.0),
                    anticipation=r.get("anticipation", 0.0),
                )
                r["signal_reason"] = r.get("signal_reason", "") + (
                    f" | ⛔ Sector blacklisted: {r.get('sector')} (BT: WR<10%, PnL<-25%)"
                )
                r["signal_dir"] = get_signal_direction(r["tag"])
                r["signal_display"] = "→ " + r["signal"]
                continue

            sec_avg_q = sector_strength.get(r["sector"], 0.0)
            r["leader"] = (r["quantum"] - sec_avg_q > _norm(K.LEADER_QUANTUM_DELTA, 0, 5.5) and r["trend_acc"] > 0)

            sig_hist = STATE.append_signal_history(r["sym"], r["tag"])

            new_rank = smart_rank_score(
                cpi_n        = r["cpi"],
                iet_n        = r["iet"],
                whale_n      = r["whale_score"],
                gravity_n    = r["gravity_score"],
                quantum_n    = r["quantum"],
                tech_score   = r["tech_score"],
                trend_acc    = r["trend_acc"],
                hidden_score = r["hidden"],
                adaptive_mom = r["adaptive_mom"],
                phase        = r["phase"],
                zone         = r["zone"],
                tag          = r["tag"],
                silent       = r["silent"],
                hunter       = bool(r["hunter"]),
                expansion    = r["expansion"],
                fake_expansion = r["fake_expansion"],
                leader       = r["leader"],
                ema_cross    = r["ema_cross"],
                vol_div      = r["vol_div"],
                rsi          = r["rsi"],
                adx          = r["adx"],
                pct_ema200   = r["pct_ema200"],
                vol_ratio    = r["vol_ratio"],
                brain_mode   = brain_mode,
                brain_vol_req= brain_vol_req,
                sig_hist     = sig_hist,
                market_soft  = market_soft,
                nw           = nw,
                sector_bias  = sector_bias_map.get(r["sector"], 1.0),
                anticipation_n = r["anticipation"],
                regime       = regime,
                cmf          = r["cmf"],
                vwap_dist    = r["vwap_dist"],
                vcp_detected = r["vcp_detected"],
                price        = r["price"],
                clv          = r["clv"],
                liq_shock    = r.get("liq_shock", 0.0),
                momentum_series=momentum_series,
            )

            prev_rank = STATE.get_prev_rank(r["sym"], new_rank)
            smoothed  = safe_clamp(
                K.SMART_RANK_SMOOTHING * prev_rank + (1 - K.SMART_RANK_SMOOTHING) * new_rank,
                0.0, K.SMART_RANK_SCALE,
            )
            if r["adx"] < K.ADX_SOFT_LO and smoothed > K.SMART_RANK_ADX_CAP:
                smoothed = K.SMART_RANK_ADX_CAP

            r["smart_rank"] = round(smoothed, 3)
            STATE.set_prev_rank(r["sym"], smoothed)

            # ── SmartRank minimum gate ───────────────────────────────────────
            if r["smart_rank"] < K.SMARTRANK_MIN_ACTIONABLE:
                r["action"] = "WAIT"
                r["tag"] = "watch"
                r["signal"] = "📊 WAIT (Rank)"
                r["plan"] = _wait_plan(
                    r["price"],
                    atr=r.get("atr"),
                    adx=r.get("adx", 20.0),
                    clv=r.get("clv", 0.0),
                    trend_acc=r.get("trend_acc", 0.0),
                    anticipation=r.get("anticipation", 0.0),
                )
                r["signal_reason"] = r.get("signal_reason", "")
                r["signal_reason"] += (
                    f" | 📊 Rank too low: {r['smart_rank']:.1f} < {K.SMARTRANK_MIN_ACTIONABLE}"
                )
                r["signal_dir"] = get_signal_direction(r["tag"])
                r["signal_display"] = "→ " + r["signal"]
                continue

            # ── Liquidity gate — soft warning only, do NOT kill the signal ────────
            if r.get("avg_vol", 0) < K.LIQUIDITY_GATE_MIN_VOLUME:
                # Stock is liquid enough to score but below preferred liquidity.
                # Downgrade BUY/ULTRA to WATCH, but keep EARLY signals visible.
                # Do NOT use continue — let the signal flow through to the table.
                if r["tag"] in ("buy", "ultra"):
                    r["tag"] = "watch"
                    r["signal"] = "👁️ WATCH (liq)"
                r["signal_reason"] = r.get("signal_reason", "") + (
                    f" | ⚠️ Low vol: {r.get('avg_vol', 0):,.0f}"
                )

            # ── LATE Zone gate (BUG #2) ──────────────────────────────────
            if K.LATE_ZONE_FILTER_ENABLED and r['zone'] == '🔴 LATE' and r['tag'] in ('buy', 'ultra', 'watch'):
                r["action"] = "WAIT"
                r["tag"] = "watch"
                r["signal"] = "⏳ WAIT (LATE Zone)"
                r["plan"] = _wait_plan(
                    r["price"],
                    atr=r.get("atr"),
                    adx=r.get("adx", 20.0),
                    clv=r.get("clv", 0.0),
                    trend_acc=r.get("trend_acc", 0.0),
                    anticipation=r.get("anticipation", 0.0),
                )
                r["signal_reason"] = r.get("signal_reason", "") + " | ⏳ In LATE zone"
                r["signal_dir"] = get_signal_direction(r["tag"])
                r["signal_display"] = "→ " + r["signal"]
                continue

            # ── RSI Overbought gate (BUG #3) ─────────────────────────────
            if K.RSI_OB_GATE_ENABLED:
                if r['rsi'] >= K.RSI_OB_HARD_LIMIT:
                    r["action"] = "WAIT"
                    r["tag"] = "watch"
                    r["signal"] = f"🥵 WAIT (RSI {r['rsi']:.0f})"
                    r["plan"] = _wait_plan(
                        r["price"],
                        atr=r.get("atr"),
                        adx=r.get("adx", 20.0),
                        clv=r.get("clv", 0.0),
                        trend_acc=r.get("trend_acc", 0.0),
                        anticipation=r.get("anticipation", 0.0),
                    )
                    r["signal_reason"] = r.get("signal_reason", "") + f" | 🥵 RSI Overbought {r['rsi']:.0f}"
                    r["signal_dir"] = get_signal_direction(r["tag"])
                    r["signal_display"] = "→ " + r["signal"]
                    continue
                elif r['rsi'] >= K.RSI_OB_SOFT_LIMIT and r['tag'] in ('buy', 'ultra'):
                    r['tag'] = 'watch'
                    r['signal_reason'] += f" | 🌡️ RSI High {r['rsi']:.0f}"

            # Confidence: blend empirical win-rate (70%) with sigmoid (30%) when
            # enough historical samples exist; fall back to pure sigmoid otherwise.
            _win_mem  = list(STATE.neural_win_memory)
            _loss_mem = list(STATE.neural_loss_memory)
            _sample   = len(_win_mem) + len(_loss_mem)
            if _sample >= 10:
                _empirical = round(len(_win_mem) / _sample * 100, 1)
                _sigmoid = round(
                    100 / (1 + math.exp(-K.CONF_SIGMOID_SCALE * (r["smart_rank"] - K.CONF_SIGMOID_SHIFT))),
                    1,
                )
                r["confidence"] = round(0.7 * _empirical + 0.3 * _sigmoid, 1)
            else:
                r["confidence"] = round(
                    100 / (1 + math.exp(-K.CONF_SIGMOID_SCALE * (r["smart_rank"] - K.CONF_SIGMOID_SHIFT))),
                    1,
                )

            # Win rate (FIX-A)
            winrate = STATE.estimate_winrate(
                r["smart_rank"], r["anticipation"],
                sector=r["sector"], tag=r["tag"], regime=regime,  # FIX-5
            )

            # Trade plan (FIX-F: pass atr_risk_label)
            r["plan"] = build_trade_plan(
                r["price"], r["rsi"], r["adx"], r["clv"],
                r["trend_acc"], r["smart_rank"], r["anticipation"],
                atr_risk_label=r["atr_risk"],
                atr=r["atr"],
                tech_score=r["tech_score"],   # FIX-3
                vol_ratio=r["vol_ratio"],      # FIX-3
                size_multiplier=r.get("size_multiplier", 1.0),
            )
            r["plan"]["winrate"]    = winrate if not r["plan"]["force_wait"] else 0.0
            r["plan"]["winrate_na"] = r["plan"]["force_wait"]

            # Soft downgrade for historically weak sectors: show signal but cap at PROBE
            if K.SECTOR_FILTER_ENABLED and r.get("sector") in getattr(K, "WEAK_SECTOR_DOWNGRADE", set()):
                if r["plan"].get("action") == "ACCUMULATE":
                    r["plan"]["action"] = "PROBE"
                if r["tag"] in ("buy", "ultra"):
                    r["tag"] = "watch"
                    r["signal"] = "⚠️ WATCH (Weak Sector)"
                r["signal_reason"] = r.get("signal_reason", "") + (
                    f" | ⚠️ Weak sector history: {r.get('sector')}"
                )

            # Signal overrides
            if r["plan"]["force_wait"] and r["tag"] in ("buy", "ultra", "early"):
                r["signal"] = "⏳ WAIT (ADX)";  r["tag"] = "watch"
            if r["plan"]["action"] == "PROBE" and r["tag"] == "sell":
                r["plan"] = {**r["plan"], "action": "WAIT"}
            if (r["plan"]["action"] == "ACCUMULATE" and r["rsi"] > K.RSI_OVERBOUGHT and r["tag"] == "watch"):
                r["plan"] = {**r["plan"], "action": "PROBE"}

            # [P3-E1] EMA50 Guard
            if K.EMA50_GUARD_ENABLED and r["price"] < r["ema50"] and r["plan"]["action"] == "BUY":
                r["plan"]["action"] = "PROBE"
                r["signal_reason"] += " | ⚠️ Below EMA50 → PROBE"

            # [P3-G3] ATR% Hard + Soft Limits
            if K.ATR_PCT_FILTER_ENABLED and r.get("atr") and r.get("price"):
                atr_pct = (r["atr"] / r["price"]) * 100
                if atr_pct >= K.ATR_PCT_HARD_LIMIT:
                    r["action"] = "WAIT"
                    r["tag"] = "watch"
                    r["signal"] = f"💥 WAIT (ATR {atr_pct:.1f}%)"
                    r["plan"] = {**r["plan"], "action": "WAIT 💥"}
                    r["signal_reason"] += f" | 💥 High ATR%: {atr_pct:.1f}% ≥ {K.ATR_PCT_HARD_LIMIT}%"
                    r["signal_dir"] = get_signal_direction(r["tag"])
                    r["signal_display"] = "→ " + r["signal"]
                    continue
                elif atr_pct >= K.ATR_PCT_SOFT_LIMIT and r["plan"]["action"] == "ACCUMULATE":
                    r["plan"]["action"] = "PROBE"
                    r["signal_reason"] += f" | ⚡ Med ATR%: {atr_pct:.1f}% → PROBE"

            # [P3-G5] Volume Surge - size multiplier boost
            if K.VOL_SURGE_ENABLED and r.get("vol_ratio", 0) >= K.VOL_SURGE_THRESHOLD:
                current_mult = r.get("size_multiplier", 1.0)
                r["size_multiplier"] = max(K.SIZE_MULTIPLIER_FLOOR, current_mult * 1.20)
                r["signal_reason"] += f" | 📈 Vol Surge: {r['vol_ratio']:.1f}x → ×1.20"

            # [P3-G6] CMF Size Boost - runs AFTER E3, uses r["cmf"]
            if K.CMF_SIZE_BOOST_ENABLED and r.get("cmf", 0) >= K.CMF_SIZE_BOOST_THRESHOLD:
                current_mult = r.get("size_multiplier", 1.0)
                r["size_multiplier"] = max(K.SIZE_MULTIPLIER_FLOOR, current_mult * K.CMF_SIZE_BOOST_MULT)
                r["signal_reason"] += f" | 💧 CMF Boost: {r['cmf']:.2f} → ×{K.CMF_SIZE_BOOST_MULT}"

            r["signal_dir"]    = get_signal_direction(r["tag"])
            # FIX-2.2: Save pre-existing gate annotations before rebuild,
            # so liquidity/RSI/ATR/vol-surge/CMF annotations aren't wiped.
            _pre_annotations = r.get("signal_reason", "")
            r["signal_reason"] = build_signal_reason(
                r["rsi"], r["adx"], r["pct_ema200"], r["phase"],
                r["vol_div"], r["ema_cross"], r["adaptive_mom"],
                r["clv"], r["vol_ratio"], tag=r["tag"],
            )
            if _pre_annotations:
                r["signal_reason"] += _pre_annotations
            if r["tech_score"] <= 3 and r["smart_rank"] > K.SMART_RANK_SCALE * 0.3:
                r["signal_reason"] += " | ⚡ Flow>Tech divergence"
            if r["adx"] < K.ADX_SOFT_LO and r["smart_rank"] >= K.SMART_RANK_ADX_CAP:
                r["signal_reason"] += " | 🔒 Rank capped (ADX<16)"
                
            # Feature 6: Downgrade ACCUMULATE to PROBE if in a mathematically weak sector
            if r["plan"]["action"] == "ACCUMULATE" and r["sector"] in weak_sectors:
                r["plan"]["action"] = "PROBE"
                r["signal_reason"] += " | 🔻 Sector Weakness Downgrade"

            # ── Data Guard tier-based signal cap ─────────────────────────
            if r.get("dg_tier") == "DEGRADED":
                if r["tag"] in ("buy", "ultra", "early"):
                    r["tag"] = "watch"
                    r["signal"] = "👁️ WATCH (data quality)"
                if r["plan"]["action"] in ("ACCUMULATE",):
                    r["plan"] = {**r["plan"], "action": "PROBE"}
                r["signal_reason"] += f" | 🛡️ DataGuard DEGRADED ({r['dg_confidence']:.0f})"
                r["confidence"] = round(r["confidence"] * 0.60, 1)  # FIX: penalise displayed Confidence%

            # ── Momentum Guard scoring adjustments ────────────────────────
            mg_boost = r.get("mg_rank_boost", 0)
            mg_passed = r.get("mg_passed", True)

            # If momentum not persistent and rank doesn't clear boosted threshold
            if not mg_passed and r["tag"] in ("buy", "ultra", "early"):
                boosted_threshold = K.SMART_RANK_SCALE * 0.40 + mg_boost
                if r["smart_rank"] < boosted_threshold:
                    r["tag"] = "watch"
                    r["signal"] = "👀 WATCH (momentum)"
                    if r["plan"]["action"] in ("ACCUMULATE",):
                        r["plan"] = {**r["plan"], "action": "PROBE"}

            if not mg_passed:
                r["confidence"] = round(r["confidence"] * 0.80, 1)  # FIX: MomGuard penalty on Confidence%

            # Annotate signal reason with momentum guard flags
            mg_flags = r.get("mg_flags", [])
            if mg_flags:
                r["signal_reason"] += f" | 🔄 MomGuard: {','.join(mg_flags)}"

            direction = "↑ " if r["tag"] in ("buy","ultra","early") else ("↓ " if r["tag"] == "sell" else "→ ")
            r["signal_display"] = direction + r["signal"]

            r["inst_conf"] = institutional_confidence(
                winrate, r["smart_rank"], sector_strength.get(r["sector"], 0.0),
                dg_tier=r.get("dg_tier", ""),
                mg_passed=r.get("mg_passed", True),
            )

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
        smart_rank_entry_threshold = float(getattr(K, "SMARTRANK_ENTRY_THRESHOLD", 20))
        for r in annotated_results:
            if (r.get("plan") and
                r["plan"]["action"] in ("ACCUMULATE", "PROBE") and
                not r["guard_reason"]):
                
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
                    )
                else:
                    log.info("[AlphaMonitor] Signal for %s blocked — system in Level 3 pause", r["sym"])

        # ── Market Health Dashboard ───────────────────────────────────────────
        avg_rank_all = sum(r["smart_rank"] for r in annotated_results) / len(annotated_results) if annotated_results else 0.0
        if annotated_results:
            act_cnt = sum(1 for r in annotated_results if r["smart_rank"] > 35)
            elite_cnt = sum(1 for r in annotated_results if r["smart_rank"] > 45)
            sell_cnt = sum(1 for r in annotated_results if r["tag"] == "sell")
            
            if avg_rank_all > 30: lbl_text, fg = "ACTIVE", "#00ff00"
            elif avg_rank_all >= 20: lbl_text, fg = "SLOW", "#ff9900"
            else: lbl_text, fg = "DEAD", "#ff3333"
            
            if all_cached:
                lbl_text += " (cached)"
            
            _enqueue(widgets["health_avg_var"].set, f"Avg Rank: {avg_rank_all:.1f}")
            _enqueue(widgets["health_act_var"].set, f"Actionable (>35): {act_cnt}")
            _enqueue(widgets["health_elite_var"].set, f"Elite (>45): {elite_cnt}")
            _enqueue(widgets["health_sell_var"].set, f"SELL Signals: {sell_cnt}")
            _enqueue(lambda: widgets["health_lbl"].configure(text=f"Label: {lbl_text}", fg=fg))

        # ── Entry window verdict ──────────────────────────────────────────────
        early_cnt    = sum(1 for r in annotated_results if r["zone"] == "🟢 EARLY")
        late_cnt     = sum(1 for r in annotated_results if r["zone"] == "🔴 LATE")
        if avg_rank_all >= K.SMART_RANK_SCALE * 0.10 and early_cnt >= late_cnt:
            entry_txt, entry_col = "🔥 ENTRY WINDOW OPEN", "#062016"
        elif late_cnt > early_cnt:
            entry_txt, entry_col = "⚠️ EARLY SETUPS ONLY", "#2a260a"
        else:
            entry_txt, entry_col = "🚫 NO TRADE ZONE",    "#2b0a0a"

        # ── Insert rows ───────────────────────────────────────────────────────
        medals       = ["🥇 ", "🥈 ", "🥉 "]
        phase_icon   = {"Accumulation": "🟡", "Expansion": "🔵", "Exhaustion": "🔴"}
        accum_syms   = [r["sym"] for r in annotated_results if (r.get("plan") or {}).get("action") == "ACCUMULATE"][:3]
        with STATE._lock:
            win_sample = len(STATE.neural_win_memory) + len(STATE.neural_loss_memory)

        def _insert_all():
            for i, r in enumerate(annotated_results):
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

                row = (
                    r["sym"], r["sector"],
                    f"{r['price']:.2f}", f"{r['adx']:.1f}", f"{r['rsi']:.0f}",
                    f"{r['adaptive_mom']:+.1f}", f"{r['pct_ema200']:+.1f}%",
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
                tree.insert("", "end", values=row, tags=(row_tag,))

        _enqueue(_insert_all)

        # ── Status summary ───────────────────────────────────────────────────
        mood    = ("Momentum Strong" if avg_rank_all >= K.SMART_RANK_SCALE * 0.13
                   else ("Balanced Market" if avg_rank_all >= K.SMART_RANK_SCALE * 0.07 else "Capital Protection"))
        
        if not market_healthy:
            mood += " | ⚠️ Market EMA50 Breakdown"
            
        safe_s  = [r["sym"] for r in annotated_results if r["smart_rank"] >= K.SMART_RANK_SCALE * 0.17][:3]
        watch_s = [r["sym"] for r in annotated_results if K.SMART_RANK_SCALE * 0.08 <= r["smart_rank"] < K.SMART_RANK_SCALE * 0.17][:3]
        avoid_s = [r["sym"] for r in annotated_results if r["smart_rank"] < K.SMART_RANK_SCALE * 0.08][:3]

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
            import json
            import tempfile
            import os
            
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
        try:
            from egx_radar.dashboard.websocket import emit_scan_complete
            emit_scan_complete(annotated_results)
        except Exception as _ws_exc:
            log.debug("WebSocket emit skipped: %s", _ws_exc)
            # Expected when running scanner without the Flask dashboard

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
