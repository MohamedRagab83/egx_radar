from __future__ import annotations

"""
Backtest engine: walk-forward simulation with no look-ahead.
Replays existing signal logic (build_signal, smart_rank_score, compute_portfolio_guard)
on historical OHLCV; backs up and restores STATE so signal code is unchanged.
"""

import logging
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
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
from egx_radar.state.app_state import STATE

from egx_radar.backtest.data_loader import load_backtest_data

log = logging.getLogger(__name__)

# Map regime from detect_market_regime to BULL/BEAR/NEUTRAL for reporting
REGIME_MAP = {"MOMENTUM": "BULL", "ACCUMULATION": "BULL", "DISTRIBUTION": "BEAR", "BEAR": "BEAR", "NEUTRAL": "NEUTRAL"}


def _backup_state() -> dict:
    """Copy STATE fields that are mutated during scan so we can restore after backtest."""
    with STATE._lock:
        backup = {
            "neural_weights": dict(STATE.neural_weights),
            "prev_ranks": dict(STATE.prev_ranks),
            "neural_memory": deque(STATE.neural_memory),
            "neural_win_memory": deque(STATE.neural_win_memory),
            "neural_loss_memory": deque(STATE.neural_loss_memory),
            "neural_bias_memory": deque(STATE.neural_bias_memory),
            "signal_history": {k: deque(v) for k, v in STATE.signal_history.items()},
            "sector_flow_memory": {k: deque(v) for k, v in STATE.sector_flow_memory.items()},
            "sector_rotation_memory": {k: deque(v) for k, v in STATE.sector_rotation_memory.items()},
            "brain_mode": STATE.brain_mode,
            "brain_vol_req": STATE.brain_vol_req,
            "brain_score_req": STATE.brain_score_req,
        }
    with STATE._momentum_lock:
        backup["momentum_history"] = {
            k: deque(v, maxlen=v.maxlen)
            for k, v in STATE.momentum_history.items()
        }
    return backup


def _restore_state(backup: dict) -> None:
    with STATE._lock:
        STATE.neural_weights = backup["neural_weights"]
        STATE.prev_ranks = backup["prev_ranks"]
        STATE.neural_memory = backup["neural_memory"]
        STATE.neural_win_memory = backup["neural_win_memory"]
        STATE.neural_loss_memory = backup["neural_loss_memory"]
        STATE.neural_bias_memory = backup["neural_bias_memory"]
        STATE.signal_history = backup["signal_history"]
        STATE.sector_flow_memory = backup["sector_flow_memory"]
        STATE.sector_rotation_memory = backup["sector_rotation_memory"]
        STATE.brain_mode = backup["brain_mode"]
        STATE.brain_vol_req = backup["brain_vol_req"]
        STATE.brain_score_req = backup["brain_score_req"]
    with STATE._momentum_lock:
        STATE.momentum_history = defaultdict(
            lambda: deque(maxlen=4),
            {
                k: deque(v, maxlen=v.maxlen)
                for k, v in backup.get("momentum_history", {}).items()
            },
        )


def _yahoo_to_sym() -> Dict[str, str]:
    return {v: k for k, v in SYMBOLS.items()}


def _build_results_for_day(
    all_data: Dict[str, pd.DataFrame],
    date: pd.Timestamp,
    yahoo_to_sym: Dict[str, str],
) -> Tuple[List[dict], Dict[str, float], str]:
    """
    Build same result dicts as scan for one day. Uses only data df.loc[:date] (no look-ahead).
    Returns (results, sector_strength, regime).
    """
    results: List[dict] = []
    sec_quant: Dict[str, List[float]] = {k: [] for k in SECTORS}
    ema200_slopes: Dict[str, float] = {}

    for yahoo, df in all_data.items():
        sym = yahoo_to_sym.get(yahoo)
        if not sym:
            continue
        df_slice = df[df.index <= date]
        if df_slice.empty or len(df_slice) < K.MIN_BARS:
            continue
        if df_slice.index[-1] != date:
            continue
        df_ta = df_slice.tail(250).copy()
        required = {"Close", "High", "Low", "Open"}
        if not required.issubset(set(df_ta.columns)):
            continue
        if "Volume" not in df_ta.columns:
            df_ta["Volume"] = 0.0

        close = df_ta["Close"].dropna()
        if len(close) < K.MIN_BARS:
            continue
        price = float(close.iloc[-1])
        if price < K.PRICE_FLOOR:
            continue
        last5 = df_ta["Close"].iloc[-5:]
        if last5.nunique() <= 1:
            continue

        ema200_s = close.ewm(span=200, adjust=False).mean()
        ema50_s = close.ewm(span=50, adjust=False).mean()
        ema200 = last_val(ema200_s)
        ema50 = last_val(ema50_s)
        pct_ema200 = safe_clamp(((price - ema200) / (ema200 + 1e-9)) * 100, -50.0, 50.0)
        if len(ema200_s) >= K.REGIME_SLOPE_BARS + 2:
            slope = float(ema200_s.iloc[-1] - ema200_s.iloc[-K.REGIME_SLOPE_BARS]) / (price + 1e-9)
            ema200_slopes[sym] = slope

        raw_mom = close.pct_change(5).rolling(3).mean().iloc[-1]
        momentum = float(raw_mom) * 100 if pd.notna(raw_mom) else 0.0
        try:
            adf = pta.adx(df_ta["High"], df_ta["Low"], df_ta["Close"], length=K.ADX_LENGTH)
            col_name = f"ADX_{K.ADX_LENGTH}"
            adx_val = last_val(adf[col_name]) if (adf is not None and col_name in adf.columns) else 0.0
            rsi_val = last_val(pta.rsi(close, length=14))
        except Exception:
            adx_val, rsi_val = 0.0, 50.0
        if adx_val >= 99.0 or rsi_val >= 99.0:
            continue
        adx_factor = min(1.4, max(0.6, adx_val / 25.0))
        adaptive_mom = momentum * adx_factor

        avg_vol_raw = df_ta["Volume"].rolling(20).mean().iloc[-1]
        if pd.isna(avg_vol_raw):
            continue
        avg_vol = float(avg_vol_raw)
        has_vol = avg_vol > 0
        if has_vol and avg_vol < K.LOW_LIQ_FILTER:
            continue
        vol_ratio = safe_clamp(float(df_ta["Volume"].iloc[-1]) / (avg_vol + 1e-9), 0.0, 5.0) if has_vol else 1.0

        vwap_dist = compute_vwap_dist(df_ta, price)
        vol_zscore = compute_vol_zscore(df_ta)
        atr = compute_atr(df_ta)
        atr_label, atr_pct_rank = compute_atr_risk(df_ta, price)
        cmf_val = compute_cmf(df_ta)
        ud_ratio = compute_ud_ratio(df_ta["Close"])
        is_vcp_flag = detect_vcp(df_ta)
        liq_shock_val = compute_liquidity_shock(df_ta, atr, avg_vol)

        # [P3-E2] VCP Score Multiplier
        vcp_detected = False
        if K.VCP_MULTIPLIER_ENABLED:
            atr_is_shrinking = is_atr_shrinking(df_ta)
            volume_declining = vol_ratio < 0.8
            price_above_ema50 = price > ema50
            if atr_is_shrinking and volume_declining and price_above_ema50:
                vcp_detected = True
        bar_h = float(df_ta["High"].iloc[-1])
        bar_l = float(df_ta["Low"].iloc[-1])
        bar_o = float(df_ta["Open"].iloc[-1])
        bar_rng = bar_h - bar_l
        clv = (
            safe_clamp(((price - bar_l) - (bar_h - price)) / (bar_rng + 1e-9), -1.0, 1.0)
            if bar_rng > 1e-9 else 0.0
        )
        ma_fast = close.ewm(span=10, adjust=False).mean()
        if len(ma_fast) >= 8:
            raw_acc = float(
                (ma_fast.iloc[-1] - ma_fast.iloc[-3]) - (ma_fast.iloc[-5] - ma_fast.iloc[-8])
            )
        else:
            raw_acc = 0.0
        trend_acc = safe_clamp(raw_acc / (price + 1e-9), -0.05, 0.05)
        recent_hi = float(df_ta["High"].iloc[-6:-1].max())
        body = abs(price - bar_o)
        breakout = (
            price > recent_hi and vol_ratio > 1.3
            and (body / (bar_rng + 1e-9)) > K.FAKE_BREAK_BODY
        )
        hidden_score = 0.0
        if adx_val < 20 and 45 < rsi_val < 60:
            hidden_score += 1.5
        if vol_ratio < 1.2 and clv > 0.4:
            hidden_score += 1.0
        if trend_acc > 0:
            hidden_score += 1.0
        if body / (bar_rng + 1e-9) < 0.35:
            hidden_score += 0.5
        phase = detect_phase(
            adx_val, rsi_val, vol_ratio, trend_acc, clv, adaptive_mom, ema50, price,
            body_ratio=body / (bar_rng + 1e-9),
        )
        zone = detect_predictive_zone(rsi_val, adaptive_mom, pct_ema200, vol_ratio)
        expansion = (
            adx_val > K.ADX_MID and momentum > 1.2 and vol_ratio > 1.1 and trend_acc > 0
        )
        fake_exp = (
            expansion and rsi_val > 66 and vol_ratio < 1.25 and clv < 0.35 and momentum < 2.8
        )
        silent = (
            45 <= rsi_val <= 60 and trend_acc > 0 and clv > 0.5 and vol_ratio < 1.3
            and (body / (bar_rng + 1e-9)) < 0.35
        )
        hunter = adx_val > 18 and 40 <= rsi_val <= 65 and vol_ratio > 1.25 and trend_acc > 0
        whale_flag = (
            "🐳 Whale"
            if (
                vol_zscore > K.WHALE_ZSCORE_THRESH
                and clv > K.WHALE_CLV_SIGNAL
                and vol_ratio > K.WHALE_VOL_THRESH
            )
            else ""
        )
        cpi_n = score_capital_pressure(clv, trend_acc, vol_ratio, price, ema50, vwap_dist, ud_ratio, is_vcp_flag)
        iet_n = score_institutional_entry(rsi_val, adx_val, clv, trend_acc, vol_ratio, pct_ema200)
        whale_n = score_whale_footprint(adx_val, clv, trend_acc, vol_ratio, rsi_val)
        ant_n = score_flow_anticipation(
            rsi_val, adx_val, clv, trend_acc, vol_ratio, pct_ema200
        )
        quantum_n = score_quantum(rsi_val, momentum, trend_acc, clv, vol_ratio)
        grav_lbl, grav_n = score_gravity(clv, trend_acc, vol_ratio, rsi_val, adaptive_mom)
        ema_cross = detect_ema_cross(close)
        vol_div = detect_vol_divergence(close, df_ta["Volume"])
        mom_arr = STATE.momentum_arrow(sym, momentum)
        _, _, brain_score_req = STATE.snapshot_brain()
        signal, tag, tech_score = build_signal(
            price, ema200, ema50, adx_val, rsi_val,
            adaptive_mom, vol_ratio, breakout, pct_ema200, phase,
            brain_score_req=brain_score_req,
        )
        ant_n_effective = 0.0 if tag == "sell" else ant_n
        sector = get_sector(sym)
        if sector in sec_quant:
            sec_quant[sector].append(quantum_n)
        results.append({
            "sym": sym, "sector": sector, "price": price,
            "adx": adx_val, "rsi": rsi_val, "momentum": momentum,
            "adaptive_mom": adaptive_mom, "pct_ema200": pct_ema200,
            "vol_ratio": vol_ratio, "tech_score": tech_score,
            "signal": signal, "tag": tag, "phase": phase,
            "trend_acc": trend_acc, "breakout": breakout, "clv": clv,
            "whale": whale_flag, "hunter": "🎯 Hunter" if hunter else "",
            "silent": silent, "expansion": expansion, "fake_expansion": fake_exp,
            "cpi": cpi_n, "iet": iet_n, "whale_score": whale_n,
            "anticipation": ant_n_effective, "quantum": quantum_n,
            "gravity_label": grav_lbl, "gravity_score": grav_n,
            "zone": zone, "hidden": hidden_score,
            "ema_cross": ema_cross, "vol_div": vol_div,
            "mom_arrow": mom_arr, "atr": atr,
            "atr_risk": atr_label, "atr_pct_rank": atr_pct_rank,
            "vwap_dist": vwap_dist, "vol_zscore": vol_zscore,
            "cmf": cmf_val, "liq_shock": liq_shock_val,
            "vcp_detected": vcp_detected, "ema50": ema50,
            "smart_rank": 0.0, "confidence": 0.0, "leader": False,
            "plan": None, "inst_conf": "—",
            "signal_dir": "⏸️ NEUTRAL", "signal_reason": "",
            "signal_display": "", "guard_reason": "",
        })

    if not results:
        return [], {}, "NEUTRAL"

    sector_strength: Dict[str, float] = {
        sec: (sum(v) / len(v) if v else 0.0) for sec, v in sec_quant.items()
    }
    regime = detect_market_regime(results, ema200_slopes)
    buy_count = sum(1 for r in results if r["tag"] in ("buy", "ultra", "early"))
    STATE.set_brain(
        "aggressive" if buy_count >= 4 else ("defensive" if buy_count <= 1 else "neutral")
    )
    brain_mode, brain_vol_req, _ = STATE.snapshot_brain()
    STATE.update_neural_weights(results)
    nw = STATE.get_neural_weights()
    market_soft = (
        sum(r["adx"] for r in results) / len(results) < 30
        and sum(r["momentum"] for r in results) / len(results) < 1.5
        and sum(r["vol_ratio"] for r in results) / len(results) < 1.3
    )
    # Phase 2: Sector bias calibrated from Phase 1 backtest (993 trades, 2020-2026)
    # Formula: WR delta from 42% baseline → ±multiplier
    _BT_SECTOR_BIAS = {
        "BANKS":       1.15,   # WR 47.6% — best sector
        "REAL_ESTATE": 1.05,   # WR 43.3% — slightly above average
        "SERVICES":    1.00,   # WR 42.0% — baseline
        "ENERGY":      0.97,   # WR 40.7% — slightly below
        "INDUSTRIAL":  0.97,   # WR 40.7% — slightly below
    }
    # ── Sector bias calibration metadata (Phase 4) ──────────────────────────────
    # IMPORTANT — CIRCULAR CALIBRATION RISK:
    # _BT_SECTOR_BIAS values were derived from a 993-trade backtest covering
    # the period 2020-01-01 through 2024-12-31. Using these biases to evaluate
    # any backtest window within that period is circular — the evaluation set
    # is the same data the biases were fitted to. Performance metrics for any
    # backtest using date_from < "2025-01-01" may be optimistically biased.
    #
    # For an unbiased out-of-sample evaluation, use date_from >= BT_OOS_START.
    _BT_SECTOR_BIAS_TRAIN_END = "2024-12-31"
    BT_OOS_START              = "2025-01-01"
    sector_bias_map = {
        sec: _BT_SECTOR_BIAS.get(sec, 1.0) * (1.10 if avg > 0.6 else (0.90 if avg < 0.28 else 1.0))
        for sec, avg in sector_strength.items()
    }
    momentum_series = pd.Series([r.get("adaptive_mom", 0.0) for r in results]) if len(results) >= 5 else None
    for r in results:
        sec_avg_q = sector_strength.get(r["sector"], 0.0)
        r["leader"] = (
            r["quantum"] - sec_avg_q > _norm(K.LEADER_QUANTUM_DELTA, 0, 5.5)
            and r["trend_acc"] > 0
        )
        sig_hist = STATE.append_signal_history(r["sym"], r["tag"])
        new_rank = smart_rank_score(
            cpi_n=r["cpi"], iet_n=r["iet"], whale_n=r["whale_score"],
            gravity_n=r["gravity_score"], quantum_n=r["quantum"],
            tech_score=r["tech_score"], trend_acc=r["trend_acc"],
            hidden_score=r["hidden"], adaptive_mom=r["adaptive_mom"],
            phase=r["phase"], zone=r["zone"], tag=r["tag"],
            silent=r["silent"], hunter=bool(r["hunter"]),
            expansion=r["expansion"], fake_expansion=r["fake_expansion"],
            leader=r["leader"], ema_cross=r["ema_cross"], vol_div=r["vol_div"],
            rsi=r["rsi"], adx=r["adx"], pct_ema200=r["pct_ema200"], vol_ratio=r["vol_ratio"],
            brain_mode=brain_mode, brain_vol_req=brain_vol_req,
            sig_hist=sig_hist, market_soft=market_soft, nw=nw,
            sector_bias=sector_bias_map.get(r["sector"], 1.0),
            anticipation_n=r["anticipation"], regime=regime,
            cmf=r.get("cmf", 0.0),
            vwap_dist=r.get("vwap_dist", 0.0),
            vcp_detected=r.get("vcp_detected", False),
            price=r["price"],
            clv=r["clv"],
            liq_shock=r.get("liq_shock", 0.0),
            momentum_series=momentum_series,
        )
        prev_rank = STATE.get_prev_rank(r["sym"], new_rank)
        smoothed = safe_clamp(
            K.SMART_RANK_SMOOTHING * prev_rank + (1 - K.SMART_RANK_SMOOTHING) * new_rank,
            0.0, K.SMART_RANK_SCALE,
        )
        if r["adx"] < K.ADX_SOFT_LO and smoothed > K.SMART_RANK_ADX_CAP:
            smoothed = K.SMART_RANK_ADX_CAP
        r["smart_rank"] = round(smoothed, 3)
        STATE.set_prev_rank(r["sym"], smoothed)
        winrate = STATE.estimate_winrate(
            r["smart_rank"], r["anticipation"],
            sector=r["sector"], tag=r["tag"], regime=regime,
        )
        r["plan"] = build_trade_plan(
            r["price"], r["rsi"], r["adx"], r["clv"],
            r["trend_acc"], r["smart_rank"], r["anticipation"],
            atr_risk_label=r["atr_risk"], atr=r["atr"],
            tech_score=r["tech_score"], vol_ratio=r["vol_ratio"],
        )
        r["plan"]["winrate"] = winrate if not r["plan"]["force_wait"] else 0.0
        r["plan"]["winrate_na"] = r["plan"]["force_wait"]
        if r["plan"]["force_wait"] and r["tag"] in ("buy", "ultra", "early"):
            r["signal"] = "⏳ WAIT (ADX)"
            r["tag"] = "watch"
        if r["plan"]["action"] == "PROBE" and r["tag"] == "sell":
            r["plan"] = {**r["plan"], "action": "WAIT"}
        if (
            r["plan"]["action"] == "ACCUMULATE"
            and r["rsi"] > K.RSI_OVERBOUGHT
            and r["tag"] == "watch"
        ):
            r["plan"] = {**r["plan"], "action": "PROBE"}
        # --- Post-scoring gates (parity with runner.py) ---
        if K.LATE_ZONE_FILTER_ENABLED and r["zone"] == "\U0001f534 LATE" and r["tag"] in ("buy", "ultra", "watch"):
            r["tag"] = "watch"
            r["plan"] = {**r["plan"], "action": "WAIT"}
        if K.RSI_OB_GATE_ENABLED:
            if r["rsi"] >= K.RSI_OB_HARD_LIMIT:
                r["tag"] = "watch"
                r["plan"] = {**r["plan"], "action": "WAIT"}
            elif r["rsi"] >= K.RSI_OB_SOFT_LIMIT and r["tag"] in ("buy", "ultra"):
                r["tag"] = "watch"
        if K.EMA50_GUARD_ENABLED and r["price"] < r.get("ema50", 0) and r.get("plan", {}).get("action") == "BUY":
            r["plan"] = {**r["plan"], "action": "PROBE"}
        if K.ATR_PCT_FILTER_ENABLED and r.get("atr") and r.get("price"):
            _atr_pct = (r["atr"] / r["price"]) * 100
            if _atr_pct >= K.ATR_PCT_HARD_LIMIT and r["tag"] in ("buy", "ultra", "early"):
                r["tag"] = "watch"
                r["plan"] = {**r["plan"], "action": "WAIT"}
            elif _atr_pct >= K.ATR_PCT_SOFT_LIMIT and r.get("plan", {}).get("action") == "ACCUMULATE":
                r["plan"] = {**r["plan"], "action": "PROBE"}
        r["signal_dir"] = get_signal_direction(r["tag"])
        r["signal_reason"] = build_signal_reason(
            r["rsi"], r["adx"], r["pct_ema200"], r["phase"],
            r["vol_div"], r["ema_cross"], r["adaptive_mom"],
            r["clv"], r["vol_ratio"], tag=r["tag"],
        )
        r["inst_conf"] = institutional_confidence(
            winrate, r["smart_rank"], sector_strength.get(r["sector"], 0.0)
        )
    STATE.record_signal_bias(results)
    results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))
    return results, sector_strength, regime


def run_backtest(
    date_from: str,
    date_to: str,
    max_bars: int = K.BT_MAX_BARS,
    max_concurrent_trades: int = 5,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[List[dict], List[Tuple[str, float]], Dict[str, Any]]:
    """
    Walk-forward backtest. No look-ahead.
    Returns (trades, equity_curve, params).
    trades: list of closed trade dicts (entry_date, exit_date, sym, sector, signal_type, regime, entry, exit, pnl_pct, outcome, ...).
    equity_curve: [(date_str, cumulative_return_pct), ...].
    """
    backup = _backup_state()
    try:
        all_data = load_backtest_data(date_from, date_to)
        if not all_data:
            return [], [], {"date_from": date_from, "date_to": date_to, "max_bars": max_bars}

        # Phase 4: Warn if backtest overlaps calibration period (circular calibration risk)
        _BT_SECTOR_BIAS_TRAIN_END = "2024-12-31"
        BT_OOS_START = "2025-01-01"
        if date_from < BT_OOS_START:
            log.warning(
                "CIRCULAR CALIBRATION: _BT_SECTOR_BIAS was derived from data "
                "through %s. Your backtest window (%s to %s) overlaps the "
                "calibration period — results may be optimistically biased. "
                "For unbiased evaluation, use date_from='%s'.",
                _BT_SECTOR_BIAS_TRAIN_END, date_from, date_to, BT_OOS_START,
            )

        yahoo_to_sym = _yahoo_to_sym()
        all_dates: List[pd.Timestamp] = []
        for df in all_data.values():
            all_dates.extend(df.index.tolist())
        all_dates = sorted(set(all_dates))
        if not all_dates:
            return [], [], {}
        min_date = all_dates[0]
        max_date = all_dates[-1]
        trading_days = [d for d in all_dates if d >= min_date]
        if len(trading_days) < K.MIN_BARS + 1:
            return [], [], {}

        account = get_account_size()
        atr_exposure = 0.04  # 4% per trade
        max_atr_per_trade = account * atr_exposure

        open_trades: List[dict] = []
        closed_trades: List[dict] = []
        equity = 100.0
        equity_curve: List[Tuple[str, float]] = [(trading_days[0].strftime("%Y-%m-%d"), 0.0)]
        total_symbols = len(all_data)

        for day_idx, date in enumerate(trading_days):
            if progress_callback and day_idx % 5 == 0:
                progress_callback(
                    f"Scanning {date.strftime('%Y-%m-%d')}... ({day_idx + 1}/{len(trading_days)})"
                )
            results, sector_strength, regime_raw = _build_results_for_day(
                all_data, date, yahoo_to_sym
            )
            regime_tag = REGIME_MAP.get(regime_raw, "NEUTRAL")

            # First: update open trades (exit conditions) using today's bar
            date_str = date.strftime("%Y-%m-%d")
            still_open: List[dict] = []
            for t in open_trades:
                yahoo = SYMBOLS.get(t["sym"])
                if not yahoo or yahoo not in all_data:
                    still_open.append(t)
                    continue
                df = all_data[yahoo]
                if date not in df.index:
                    t["bars_held"] += 1
                    still_open.append(t)
                    continue
                row = df.loc[date]
                high = float(row["High"])
                low = float(row["Low"])
                close = float(row["Close"])
                t["bars_held"] += 1
                outcome = None
                exit_price = close
                if t["is_short"]:
                    if low <= t["target"]:
                        outcome = "WIN"
                        exit_price = t["target"]
                    elif high >= t["stop"]:
                        outcome = "LOSS"
                        exit_price = t["stop"]
                    elif t["bars_held"] >= max_bars:
                        outcome = "EXIT"
                else:
                    if high >= t["target"]:
                        outcome = "WIN"
                        exit_price = t["target"]
                    elif low <= t["stop"]:
                        outcome = "LOSS"
                        exit_price = t["stop"]
                    elif t["bars_held"] >= max_bars:
                        outcome = "EXIT"

                if outcome:
                    if t["is_short"]:
                        pnl_pct = (t["entry"] - exit_price) / (t["entry"] + 1e-9) * 100
                    else:
                        pnl_pct = (exit_price - t["entry"]) / (t["entry"] + 1e-9) * 100
                    pnl_pct -= K.BT_TOTAL_COST_PCT * 100   # FIX-4: round-trip cost
                    rps = max(abs(t["entry"] - t["stop"]), 0.01)
                    rr = abs(exit_price - t["entry"]) / rps if rps else 0.0
                    # FIX-B: Skip NaN trades entirely — do not append to closed_trades or equity
                    if not np.isfinite(pnl_pct):
                        log.warning(
                            "FIX-B: NaN pnl_pct for %s exit=%s — trade skipped, symbol: check data source",
                            t.get("sym"), exit_price,
                        )
                        still_open.append(t)   # keep in open_trades to close properly next bar
                        continue
                    closed_trades.append({
                        **t,
                        "exit_date": date_str,
                        "exit": exit_price,
                        "pnl_pct": round(pnl_pct, 2),
                        "rr": round(rr, 2),
                        "outcome": outcome,
                    })
                    # FIX-2C: ATR-based position sizing instead of hardcoded 20%
                    entry_p = t.get("entry", 1.0)
                    stop_p = t.get("stop", entry_p * 0.955)
                    stop_dist = abs(entry_p - stop_p) / max(entry_p, 1e-9)
                    # Allocation = risk_per_trade / stop_distance, capped at 25% max
                    alloc = min(0.01 / max(stop_dist, 0.005), 0.25)
                    equity *= (1 + alloc * pnl_pct / 100)
                else:
                    still_open.append(t)
            open_trades = still_open

            # Then: open new trades from today's guarded signals
            guarded_list, _, guard_exp, _, _ = compute_portfolio_guard(results)
            # Phase 2b: direct SmartRank threshold filter
            _sr_threshold = getattr(K, "BT_MIN_SMARTRANK", 0.0)
            allowed = [
                gr for gr in guarded_list
                if not gr.is_blocked
                and gr.result.get("tag")
                and gr.result.get("tag") not in ("watch", "blocked", "sell")
                and gr.result.get("plan")
                and gr.result["plan"].get("action") in ("ACCUMULATE", "PROBE")
                and gr.result.get("smart_rank", 0.0) >= _sr_threshold
                and gr.result.get("sector") not in getattr(K, "BLACKLISTED_SECTORS_BT", set())
            ]
            allowed.sort(
                key=lambda gr: (
                    DECISION_PRIORITY.get(gr.result["tag"], 99),
                    -gr.result["smart_rank"],
                )
            )
            # Phase 2: Top-N daily selection — only enter best N signals per day
            if K.BT_DAILY_TOP_N > 0:
                allowed = allowed[:K.BT_DAILY_TOP_N]

            for gr in allowed:
                if len(open_trades) >= max_concurrent_trades:
                    break
                r = gr.result
                if r["sym"] in [t["sym"] for t in open_trades]:
                    continue
                plan = r["plan"]
                atr_val = r.get("atr") or 0.0
                size = plan.get("size", 0)
                contrib = atr_val * size
                if contrib > max_atr_per_trade:
                    continue
                entry = plan["entry"]
                stop = plan["stop"]
                target = plan["target"]
                is_short = r["tag"] == "sell"
                if is_short:
                    entry = r["price"]
                    stop = round(r["price"] * 1.03, 2)
                    target = round(r["price"] * 0.97, 2)
                open_trades.append({
                    "sym": r["sym"],
                    "sector": r["sector"],
                    "signal_type": r["tag"],
                    "regime": regime_tag,
                    "entry_date": date.strftime("%Y-%m-%d"),
                    "entry": entry,
                    "stop": stop,
                    "target": target,
                    "bars_held": 0,
                    "is_short": is_short,
                    "smart_rank": round(r.get("smart_rank", 0.0), 2),
                })

            cum_return = (equity - 100.0)
            equity_curve.append((date_str, round(cum_return, 2)))

        return closed_trades, equity_curve, {
            "date_from": date_from,
            "date_to": date_to,
            "max_bars": max_bars,
            "max_concurrent_trades": max_concurrent_trades,
        }
    finally:
        _restore_state(backup)
