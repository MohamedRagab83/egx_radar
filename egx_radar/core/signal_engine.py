from __future__ import annotations

"""Unified EGX accumulation signal engine for live scan and backtest."""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from egx_radar.config.settings import K, get_account_size, get_risk_per_trade
from egx_radar.core.accumulation import evaluate_accumulation_context
from egx_radar.core.indicators import (
    compute_atr,
    compute_atr_risk,
    compute_cmf,
    compute_liquidity_shock,
    compute_vol_zscore,
    compute_vwap_dist,
    detect_ema_cross,
    detect_vol_divergence,
    safe_clamp,
)
from egx_radar.core.multi_factor import (
    compute_momentum_score,
    compute_multi_factor_rank,
    compute_trend_score,
    compute_volatility_score,
    compute_volume_score,
)

log = logging.getLogger(__name__)


def _last(series: pd.Series, default: float = 0.0) -> float:
    data = pd.Series(series).dropna()
    return float(data.iloc[-1]) if not data.empty else default


def compute_rsi_value(close: pd.Series, period: int = 14) -> float:
    """Wilder RSI implemented locally for deterministic live/backtest parity."""
    if close is None or len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    gain_v = _last(avg_gain, 0.0)
    loss_v = _last(avg_loss, 0.0)
    if loss_v <= 1e-9:
        return 100.0 if gain_v > 0 else 50.0
    rs = gain_v / loss_v
    return float(100.0 - (100.0 / (1.0 + rs)))


def compute_adx_value(df: pd.DataFrame, period: int = 14) -> float:
    """Wilder ADX implemented locally to avoid live/backtest divergence."""
    required = {"High", "Low", "Close"}
    if df is None or len(df) < period * 2 or not required.issubset(df.columns):
        return 0.0

    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    if _last(atr, 0.0) <= 1e-9:
        return 0.0

    plus_di = 100.0 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return float(np.nan_to_num(_last(adx, 0.0), nan=0.0, posinf=0.0, neginf=0.0))


def _avg_turnover(close: pd.Series, volume: pd.Series, window: int = 20) -> float:
    turnover = close * volume
    return _last(turnover.rolling(window).mean(), 0.0)


def _spread_proxy_pct(df: pd.DataFrame, window: int = 5) -> float:
    spread = ((df["High"] - df["Low"]) / df["Close"].replace(0.0, np.nan)).abs() * 100.0
    return float(np.nan_to_num(_last(spread.tail(window).median(), 0.0), nan=0.0))


def _ema_slope_pct(series: pd.Series, bars: int = 10) -> float:
    if len(series) < bars + 1:
        return 0.0
    base = float(series.iloc[-bars - 1]) if float(series.iloc[-bars - 1]) != 0 else 1e-9
    return ((float(series.iloc[-1]) - base) / base) * 100.0


def _confidence_label(score: float) -> str:
    if score >= 82:
        return "ELITE"
    if score >= 75:
        return "STRONG"
    if score >= 70:
        return "GOOD"
    if score >= 60:
        return "BUILDING"
    return "WEAK"


def _phase_from_context(accumulation_detected: bool, fake_move: bool, entry_ready: bool) -> str:
    if fake_move:
        return "Exhaustion"
    if accumulation_detected:
        return "Accumulation"
    if entry_ready:
        return "Transition"
    return "Base"


def _zone_from_context(accumulation_detected: bool, fake_move: bool, minor_break_pct: float) -> str:
    if fake_move or minor_break_pct > K.ACCUM_MAX_MINOR_BREAK_PCT:
        return "🔴 LATE"
    if accumulation_detected:
        return "🟢 EARLY"
    return "🟡 MID"


def _fetch_symbol_news(sym: str) -> List[dict]:  # noqa: ARG001 — AI layer disabled
    return []


def _apply_news_risk_filter(snapshot: Dict[str, object]) -> None:
    """News stays secondary: only a hard-negative context trims size conservatively."""
    plan = snapshot.get("plan")
    if not isinstance(plan, dict):
        return

    sentiment_score = float(snapshot.get("sentiment_score") or 0.5)
    action = str(plan.get("action") or "WAIT")
    size = int(plan.get("size") or 0)

    if sentiment_score < 0.25 and action in {"ACCUMULATE", "PROBE"} and size > 0:
        reduced_size = max(1, int(round(size * 0.5)))
        plan["news_risk_flag"] = True
        plan["news_original_size"] = size
        plan["news_size_multiplier"] = 0.5
        plan["size"] = reduced_size
        plan["risk_used"] = round(float(plan.get("risk_used") or 0.0) * 0.5, 4)
    else:
        plan["news_risk_flag"] = False
        plan["news_size_multiplier"] = 1.0


def _build_alpha_metadata(snapshot: Dict[str, object], symbol_news: List[dict]) -> None:  # noqa: ARG001
    snapshot["alpha_score"] = 0.0
    snapshot["alpha_trade"] = None
    snapshot["alpha_filter_reason"] = "ai_disabled"


def _enrich_ai_snapshot(snapshot: Dict[str, object]) -> Dict[str, object]:
    atr = float(snapshot.get("atr") or 0.0)
    price = float(snapshot.get("price") or 0.0)

    snapshot["atr_pct"] = round(atr / price, 6) if price > 0 else 0.0
    snapshot["volume_ratio"] = float(snapshot.get("volume_ratio") or snapshot.get("vol_ratio") or 1.0)

    tech_score = float(snapshot.get("tech_score_pct") or snapshot.get("tech_score") or 50.0)
    gravity_score = snapshot.get("gravity_score_pct")
    if gravity_score is None:
        gravity_score = float(snapshot.get("gravity_score") or 50.0)
        if gravity_score <= 1.0:
            gravity_score *= 100.0
    gravity_score = float(gravity_score)

    snapshot["gravity_score_pct"] = round(gravity_score, 2)
    snapshot["structure_score"] = round((0.6 * tech_score) + (0.4 * gravity_score), 2)

    # AI layer disabled — use neutral fixed values
    snapshot["sentiment_score"] = 0.5
    snapshot["probability"] = 0.5
    snapshot["trade_class"] = "MEDIUM"
    _build_alpha_metadata(snapshot, [])
    _apply_news_risk_filter(snapshot)
    return snapshot


def classify_trade_type(score: float) -> Optional[str]:
    if score >= K.TRADE_TYPE_STRONG_MIN:
        return "STRONG"
    if score >= K.TRADE_TYPE_MEDIUM_MIN:
        return "MEDIUM"
    return None


def trade_risk_fraction(trade_type: Optional[str]) -> float:
    base_risk = min(float(get_risk_per_trade()), float(K.RISK_PER_TRADE_STRONG))
    if trade_type == "STRONG":
        return base_risk
    if trade_type == "MEDIUM":
        return min(base_risk * 0.5, float(K.RISK_PER_TRADE_MEDIUM))
    return 0.0


def _regime_allows_trade_type(regime: str, trade_type: Optional[str]) -> bool:
    normalized_regime = str(regime or "BULL").upper()
    normalized_type = str(trade_type or "").upper()
    if normalized_regime == "BULL":
        return True
    if normalized_regime == "NEUTRAL":
        return normalized_type == "STRONG"
    return False


def _force_wait_plan(plan: Optional[dict]) -> Dict[str, float]:
    forced = dict(plan or {})
    forced["action"] = "WAIT"
    forced["size"] = 0
    forced["force_wait"] = True
    forced["winrate"] = 0.0
    forced["winrate_na"] = True
    forced["risk_used"] = 0.0
    forced["trade_type"] = "SKIP"
    return forced


def trigger_fill_tolerance(trigger_price: float) -> float:
    if trigger_price <= 0:
        return 0.0
    return max(0.01, float(trigger_price) * float(K.TRIGGER_FILL_TOLERANCE_PCT))


def candle_hits_trigger(high_price: float, trigger_price: float) -> bool:
    if trigger_price <= 0:
        return True
    return float(high_price) + trigger_fill_tolerance(trigger_price) >= float(trigger_price)


def _position_plan(
    *,
    price: float,
    entry_price: float,
    base_low: float,
    smart_rank: float,
    entry_ready: bool,
    regime: str,
) -> Dict[str, float]:
    ref_price = max(entry_price, 1e-9)
    raw_stop = base_low * 0.995 if base_low > 0 else ref_price * (1.0 - K.MAX_STOP_LOSS_PCT)
    risk_pct = (ref_price - raw_stop) / max(ref_price, 1e-9)
    stop_capped = risk_pct > K.MAX_STOP_LOSS_PCT
    risk_viable = 0.0 < risk_pct <= 0.10
    stop = raw_stop if not stop_capped else ref_price * (1.0 - K.MAX_STOP_LOSS_PCT)
    stop = min(stop, ref_price * 0.995)
    if stop >= ref_price:
        stop = ref_price * (1.0 - K.MAX_STOP_LOSS_PCT)

    trade_type = classify_trade_type(smart_rank)
    risk_used = trade_risk_fraction(trade_type)
    risk_amount = get_account_size() * risk_used
    risk_per_share = max(ref_price - stop, ref_price * 0.005)
    size = max(1, int(risk_amount / max(risk_per_share, 1e-9))) if risk_amount > 0 else 0
    max_notional = get_account_size() * K.PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT
    if size > 0:
        size = max(1, min(size, int(max_notional / max(ref_price, 1e-9))))

    # Regime gate: BULL→all entries allowed; NEUTRAL→STRONG tier only; BEAR→none.
    # Keep this aligned with apply_regime_gate() via the shared helper.
    _regime_allows_entry = _regime_allows_trade_type(regime, trade_type)
    if not entry_ready or not _regime_allows_entry or not risk_viable or trade_type is None:
        action = "WAIT"
        size = 0
        trade_type = "SKIP"
        risk_used = 0.0
    elif trade_type == "STRONG":
        action = "ACCUMULATE"
    else:
        action = "PROBE"

    target_pct = float(K.POSITION_MAIN_TP_PCT)
    target = ref_price * (1.0 + target_pct)
    partial_target = ref_price * (1.0 + K.PARTIAL_TP_PCT)
    trailing_trigger = ref_price * (1.0 + K.TRAILING_TRIGGER_PCT)
    rr = abs(target - ref_price) / max(abs(ref_price - stop), 1e-9)
    return {
        "action": action,
        "entry": round(ref_price, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "partial_target": round(partial_target, 2),
        "trailing_trigger": round(trailing_trigger, 2),
        "trailing_stop_pct": round(float(K.TRAILING_STOP_PCT), 4),
        "size": int(size),
        "rr": round(rr, 2),
        "timeframe": "Position (5-20d)",
        "force_wait": action == "WAIT",
        "winrate": 0.0,
        "winrate_na": action == "WAIT",
        "risk_pct": round((ref_price - stop) / max(ref_price, 1e-9), 4),
        "risk_used": round(float(risk_used), 4),
        "trade_type": trade_type,
        "score": round(float(smart_rank), 2),
        "target_pct": round(target_pct, 4),
        "max_hold_bars": int(K.BT_MAX_BARS),
        "stop_capped": bool(stop_capped),
        "trigger_price": round(entry_price, 2),
        "trigger_tolerance_pct": round(float(K.TRIGGER_FILL_TOLERANCE_PCT), 4),
    }


def apply_entry_timing_filter(
    plan: dict,
    ctx: dict,
    zone: str,
    pct_ema200: float,
) -> tuple:
    """
    Entry timing filter — blocks late/extended entries.

    Only acts on ACCUMULATE/PROBE signals. Uses existing computed fields.
    Returns (plan, timing_blocked, timing_reasons).
    """
    timing_blocked = False
    timing_reasons: List[str] = []

    if plan.get("action") not in ("ACCUMULATE", "PROBE"):
        return plan, timing_blocked, timing_reasons

    # Condition 1: LATE zone (fake move or minor break > threshold)
    if "LATE" in str(zone).upper():
        timing_reasons.append("zone_late")

    # Condition 2: 3-day gain too large (chasing momentum)
    last_3d = float(ctx.get("last_3_days_gain_pct", 0.0))
    if last_3d > K.ETF_GAIN_3D_THRESHOLD:
        timing_reasons.append(f"3day_gain_{last_3d:.1f}pct")

    # Condition 3: Too far above EMA200 (extended from value)
    if pct_ema200 > K.ETF_EMA200_THRESHOLD:
        timing_reasons.append(f"ema200_dist_{pct_ema200:.1f}pct")

    # Condition 4: Minor break too wide
    minor_break = float(ctx.get("minor_break_pct", 0.0))
    if minor_break > K.ETF_MINOR_BREAK_THRESHOLD:
        timing_reasons.append(f"minor_break_{minor_break:.1f}pct")

    if timing_reasons:
        timing_blocked = True
        plan = _force_wait_plan(plan)
        plan["timing_blocked"] = True
        log.debug("TIMING_BLOCKED %s: %s", ctx.get("sym", "?"), timing_reasons)

    return plan, timing_blocked, timing_reasons


def evaluate_symbol_snapshot(
    df_ta: pd.DataFrame,
    sym: str,
    sector: str,
    regime: str = "BULL",
) -> Optional[dict]:
    """Evaluate one symbol using shared EGX accumulation logic."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    if df_ta is None or len(df_ta) < max(K.MIN_BARS, 210) or not required.issubset(df_ta.columns):
        return None

    df_ta = df_ta.tail(260).copy()
    close = df_ta["Close"].astype(float).dropna()
    if len(close) < max(K.MIN_BARS, 210):
        return None

    price = float(close.iloc[-1])
    if price < K.PRICE_FLOOR:
        return None
    if df_ta["Close"].iloc[-5:].nunique() <= 1:
        return None

    open_ = df_ta["Open"].astype(float)
    high = df_ta["High"].astype(float)
    low = df_ta["Low"].astype(float)
    volume = df_ta["Volume"].fillna(0.0).astype(float)

    ema20_s = close.ewm(span=20, adjust=False).mean()
    ema50_s = close.ewm(span=50, adjust=False).mean()
    ema200_s = close.ewm(span=200, adjust=False).mean()
    ema20 = _last(ema20_s, price)
    ema50 = _last(ema50_s, price)
    ema200 = _last(ema200_s, price)
    ema20_slope_pct = _ema_slope_pct(ema20_s, bars=8)
    ema50_slope_pct = _ema_slope_pct(ema50_s, bars=10)
    ema200_slope_pct = _ema_slope_pct(ema200_s, bars=10)

    adx = compute_adx_value(df_ta, period=K.ADX_LENGTH)
    rsi = compute_rsi_value(close, period=14)
    momentum = _last(close.pct_change(10), 0.0) * 100.0
    adaptive_mom = momentum * min(1.10, max(0.60, adx / 22.0 if adx > 0 else 0.60))
    atr = compute_atr(df_ta)
    atr_label, atr_pct_rank = compute_atr_risk(df_ta, price)
    vwap_dist = compute_vwap_dist(df_ta, price)
    vol_zscore = compute_vol_zscore(df_ta)
    cmf = compute_cmf(df_ta)
    avg_vol = _last(volume.rolling(20).mean(), 0.0)
    vol_ratio = safe_clamp(float(volume.iloc[-1]) / max(avg_vol, 1e-9), 0.0, 4.0) if avg_vol > 0 else 0.0
    avg_turnover = _avg_turnover(close, volume)
    turnover = price * float(volume.iloc[-1])
    spread_pct = _spread_proxy_pct(df_ta)
    pct_ema200 = safe_clamp(((price - ema200) / max(ema200, 1e-9)) * 100.0, -50.0, 50.0)

    if avg_turnover < K.MIN_TURNOVER_EGP:
        return None
    if spread_pct > K.MAX_SPREAD_PCT:
        return None

    ctx = evaluate_accumulation_context(
        df_ta,
        price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        ema20_slope_pct=ema20_slope_pct,
        ema50_slope_pct=ema50_slope_pct,
        ema200_slope_pct=ema200_slope_pct,
        rsi=rsi,
        adx=adx,
        avg_turnover=avg_turnover,
        spread_pct=spread_pct,
        avg_vol=avg_vol,
        vol_ratio=vol_ratio,
        vol_zscore=vol_zscore,
    )

    smart_rank = round(
        ctx["accumulation_quality_score"] * 0.40
        + ctx["structure_strength_score"] * 0.25
        + ctx["volume_quality_score"] * 0.20
        + ctx["trend_alignment_score"] * 0.15,
        2,
    )

    # ── Multi-factor rank (experimental, parallel to SmartRank) ───────
    mf_trend = compute_trend_score(price, ema50, ema200, ema50_slope_pct, ema200_slope_pct)
    mf_momentum = compute_momentum_score(rsi, adx, adaptive_mom, pct_ema200)
    mf_volume = compute_volume_score(vol_ratio, cmf, vol_zscore, avg_turnover)
    mf_volatility = compute_volatility_score(atr_pct_rank, vwap_dist, spread_pct)
    multi_factor_rank = compute_multi_factor_rank(mf_trend, mf_momentum, mf_volume, mf_volatility)

    # ── Hybrid final rank (shadow system) ────────────────────────────
    # Combines production SmartRank (60%) with experimental multi-factor (40%)
    final_rank = round(smart_rank * 0.60 + multi_factor_rank * 0.40, 2)

    phase = _phase_from_context(
        accumulation_detected=ctx["accumulation_detected"],
        fake_move=ctx["fake_move"],
        entry_ready=ctx["entry_ready"],
    )
    zone = _zone_from_context(
        accumulation_detected=ctx["accumulation_detected"],
        fake_move=ctx["fake_move"],
        minor_break_pct=ctx["minor_break_pct"],
    )
    trigger_price = float(ctx["trigger_price"])
    plan = _position_plan(
        price=price,
        entry_price=trigger_price,
        base_low=float(ctx["base_low"]),
        smart_rank=smart_rank,
        entry_ready=bool(ctx["entry_ready"]),
        regime=regime,
    )

    # ── Entry timing filter (blocks extended/late entries) ────────────
    plan, timing_blocked, timing_reasons = apply_entry_timing_filter(
        plan, ctx, zone, pct_ema200,
    )

    if plan["action"] == "ACCUMULATE":
        tag = "buy"
        signal = "ACCUMULATE"
    elif plan["action"] == "PROBE":
        tag = "early"
        signal = "PROBE"
    else:
        tag = "watch"
        signal = "WATCH"

    tech_score = int(
        round(
            safe_clamp(
                (ctx["accumulation_quality_score"] * 0.55 + ctx["structure_strength_score"] * 0.45) / 5.56,
                0.0,
                18.0,
            )
        )
    )
    tech_score_pct = round(safe_clamp((tech_score / 18.0) * 100.0, 0.0, 100.0), 1)
    liq_shock = compute_liquidity_shock(df_ta, atr, avg_vol)
    ema_cross = detect_ema_cross(close)
    vol_div = detect_vol_divergence(close, volume)
    vcp_detected = bool(
        ctx["compression_score"] >= 70.0
        and ctx["contraction_ratio"] <= 0.95
        and not ctx["erratic_volume"]
    )
    body_ratio = abs(float(close.iloc[-1]) - float(open_.iloc[-1])) / max(float(high.iloc[-1]) - float(low.iloc[-1]), 1e-9)
    vol_tier = "High" if avg_turnover >= 15_000_000 else "Mid" if avg_turnover >= 8_000_000 else "Low"

    reasons: List[str] = []
    reasons.append("accum-base" if ctx["accumulation_detected"] else "no-base")
    reasons.append("higher-lows" if ctx["higher_lows"] else "flat-support")
    reasons.append(f"turnover {avg_turnover/1_000_000:.1f}m")
    reasons.append(f"spread {spread_pct:.2f}%")
    reasons.append(f"base {ctx['compression_window']}d/{ctx['compression_range_pct']:.1f}%")
    reasons.append(f"minor-break {ctx['minor_break_pct']:.1f}%")
    if ctx["entry_ready"] and not ctx["break_confirmed"]:
        reasons.append("trigger-ready")
    if not ctx["volume_confirmed"]:
        reasons.append("volume-unconfirmed")
    if ctx["erratic_volume"]:
        reasons.append("erratic-volume")
    if ctx["fake_move"]:
        reasons.append("fake-move")
    if not ctx["risk_viable"]:
        reasons.append("risk-too-wide")
    elif ctx["stop_capped"]:
        reasons.append("stop-capped-5%")
    if regime != "BULL":
        reasons.append(f"regime-{regime.lower()}")

    result = {
        "sym": sym,
        "sector": sector,
        "price": round(price, 3),
        "adx": round(adx, 2),
        "rsi": round(rsi, 2),
        "momentum": round(momentum, 3),
        "adaptive_mom": round(adaptive_mom, 3),
        "pct_ema200": round(pct_ema200, 2),
        "ema20": round(ema20, 3),
        "ema50": round(ema50, 3),
        "ema200": round(ema200, 3),
        "ema20_slope_pct": round(ema20_slope_pct, 3),
        "ema50_slope_pct": round(ema50_slope_pct, 3),
        "ema200_slope_pct": round(ema200_slope_pct, 3),
        "vol_ratio": round(vol_ratio, 3),
        "avg_vol": round(avg_vol, 2),
        "avg_turnover": round(avg_turnover, 2),
        "turnover": round(turnover, 2),
        "spread_pct": round(spread_pct, 3),
        "vol_tier": vol_tier,
        "tech_score": tech_score,
        "tech_score_pct": tech_score_pct,
        "signal": signal,
        "tag": tag,
        "phase": phase,
        "trend_acc": round(ema200_slope_pct / 100.0, 4),
        "breakout": False,
        "minor_breakout": bool(ctx["entry_ready"]),
        "clv": round((price - float(ctx["base_low"])) / max(float(ctx["base_high"]) - float(ctx["base_low"]), 1e-9), 3),
        "whale": "",
        "hunter": "Builder" if ctx["accumulation_detected"] else "",
        "silent": bool(ctx["accumulation_detected"] and body_ratio < 0.35),
        "expansion": False,
        "fake_expansion": bool(ctx["fake_move"]),
        "vcp_detected": vcp_detected,
        "cpi": round(ctx["volume_quality_score"] / 100.0, 3),
        "iet": round(ctx["structure_strength_score"] / 100.0, 3),
        "whale_score": round(safe_clamp((ctx["up_down_volume_ratio"] - 0.9) / 0.8, 0.0, 1.0), 3),
        "anticipation": round(ctx["accumulation_quality_score"] / 100.0, 3),
        "quantum": round(ctx["compression_score"] / 100.0, 3),
        "gravity_label": "ALIGNED" if ctx["trend_alignment_score"] >= 75 else "BUILDING" if ctx["trend_alignment_score"] >= 60 else "LIGHT",
        "gravity_score": round(ctx["trend_alignment_score"] / 100.0, 3),
        "zone": zone,
        "hidden": 0.0,
        "ema_cross": ema_cross,
        "vol_div": vol_div,
        "mom_arrow": "",
        "atr": round(float(atr), 4) if atr else None,
        "atr_risk": atr_label,
        "atr_pct_rank": round(float(atr_pct_rank), 1),
        "vwap_dist": round(vwap_dist, 4),
        "vol_zscore": round(vol_zscore, 3),
        "cmf": round(cmf, 4),
        "liq_shock": round(liq_shock, 3),
        "one_day_gain_pct": ctx["one_day_gain_pct"],
        "two_day_gain_pct": ctx["two_day_gain_pct"],
        "last_3_days_gain_pct": ctx["last_3_days_gain_pct"],
        "gap_up_pct": ctx["gap_up_pct"],
        "smart_rank": round(smart_rank, 2),
        "trade_type": plan.get("trade_type", "SKIP"),
        "multi_factor_rank": round(multi_factor_rank, 2),
        "final_rank": round(final_rank, 2),
        "mf_trend_score": round(mf_trend, 2),
        "mf_momentum_score": round(mf_momentum, 2),
        "mf_volume_score": round(mf_volume, 2),
        "mf_volatility_score": round(mf_volatility, 2),
        "accumulation_quality_score": ctx["accumulation_quality_score"],
        "structure_strength_score": ctx["structure_strength_score"],
        "volume_quality_score": ctx["volume_quality_score"],
        "trend_alignment_score": ctx["trend_alignment_score"],
        "compression_range_pct": ctx["compression_range_pct"],
        "compression_window": ctx["compression_window"],
        "support_slope_pct": ctx["support_slope_pct"],
        "up_down_volume_ratio": ctx["up_down_volume_ratio"],
        "gradual_volume_ratio": ctx["gradual_volume_ratio"],
        "volume_variation_ratio": ctx["volume_variation_ratio"],
        "base_low": ctx["base_low"],
        "base_high": ctx["base_high"],
        "minor_resistance": ctx["minor_resistance"],
        "trigger_price": ctx["trigger_price"],
        "minor_break_pct": ctx["minor_break_pct"],
        "accumulation_detected": ctx["accumulation_detected"],
        "break_confirmed": ctx["break_confirmed"],
        "entry_ready": ctx["entry_ready"],
        "higher_lows": ctx["higher_lows"],
        "volume_confirmed": ctx["volume_confirmed"],
        "erratic_volume": ctx["erratic_volume"],
        "abnormal_candle": ctx["abnormal_candle"],
        "fake_move": ctx["fake_move"],
        "timing_blocked": timing_blocked,
        "timing_reasons": timing_reasons,
        "confidence": round(smart_rank, 1),
        "leader": False,
        "plan": plan,
        "inst_conf": _confidence_label(smart_rank),
        "signal_dir": "BULLISH" if tag in ("buy", "early") else "NEUTRAL",
        "signal_reason": " | ".join(reasons),
        "signal_display": signal,
        "guard_reason": "",
    }
    return _enrich_ai_snapshot(result)


def detect_conservative_market_regime(results: List[dict]) -> str:
    """Broad market regime for EGX accumulation mode."""
    if not results:
        return "NEUTRAL"

    n = len(results)
    breadth_above_50 = sum(1 for r in results if r.get("price", 0.0) > r.get("ema50", 0.0)) / n
    breadth_stacked = sum(1 for r in results if r.get("price", 0.0) > r.get("ema50", 0.0) > r.get("ema200", 0.0)) / n
    avg_slope = sum(r.get("ema200_slope_pct", 0.0) for r in results) / n
    avg_rank = sum(r.get("smart_rank", 0.0) for r in results) / n

    if (breadth_above_50 >= K.MARKET_BREADTH_THRESHOLD
            and breadth_stacked >= K.MARKET_BULL_STACKED_MIN
            and avg_slope >= -0.03
            and avg_rank >= 45.0):
        return "BULL"
    if breadth_above_50 <= K.MARKET_BEAR_BREADTH_MAX or avg_slope < -0.12:
        return "BEAR"
    return "NEUTRAL"


def apply_regime_gate(result: dict, regime: str) -> dict:
    """Apply regime-based capital preservation.

    BULL   -> all signals pass through unchanged.
    NEUTRAL -> STRONG signals (SR >= TRADE_TYPE_STRONG_MIN) pass through;
               weaker signals are gated to WAIT.
    BEAR   -> all signals forced to WAIT.
    """
    if regime == "BULL":
        return result

    action = (result.get("plan") or {}).get("action", "WAIT")
    trade_type = str((result.get("plan") or {}).get("trade_type", "")).upper()
    if not trade_type or trade_type == "SKIP":
        trade_type = classify_trade_type(float(result.get("smart_rank", 0.0) or 0.0)) or ""

    if _regime_allows_trade_type(regime, trade_type) and action in ("ACCUMULATE", "PROBE"):
        gated = dict(result)
        gated["signal_reason"] = f"{result.get('signal_reason', '')} | regime-neutral-pass".strip(" |")
        return gated

    # BEAR or weak NEUTRAL signals -> force WAIT
    plan = _force_wait_plan(result.get("plan") or {})

    gated = dict(result)
    gated["tag"] = "watch"
    gated["signal"] = "WAIT"
    gated["signal_display"] = "WAIT"
    gated["signal_dir"] = "NEUTRAL"
    gated["trade_type"] = plan.get("trade_type", "SKIP")
    gated["plan"] = plan
    gated["signal_reason"] = f"{result.get('signal_reason', '')} | regime-{regime.lower()}".strip(" |")
    return gated


def is_high_probability_trade(snapshot: dict) -> bool:
    """
    Single source of truth for high-probability trade quality gate.

    Used by BOTH live scan (scan/runner.py) and backtest (backtest/engine.py).
    Any change here applies equally to both paths — no live/backtest divergence.

    Hard disqualifiers are checked first (instant reject).
    Soft quality checks are scored; trade must reach minimum score threshold.

    Args:
        snapshot: result dict produced by evaluate_symbol_snapshot().

    Returns:
        True  → trade passes quality gate (may be entered).
        False → trade is rejected by quality gate.
    """
# ── Hard disqualifiers (instant reject) ──────────────────────────────────
    gain_3d = float(snapshot.get("last_3_days_gain_pct", 0.0) or 0.0)
    if gain_3d > K.ETF_GAIN_3D_THRESHOLD:
        return False
    
    if snapshot.get("fake_move", False):
        return False
    if snapshot.get("erratic_volume", False):
        return False
    if float(snapshot.get("smart_rank", 0.0) or 0.0) < K.BT_MIN_SMARTRANK:
        return False
    if float(snapshot.get("avg_turnover", 0.0) or 0.0) < K.HQ_MIN_TURNOVER_EGP:
        return False
    if "LATE" in str(snapshot.get("zone", "")).upper():
        return False

    # ── Trade-type classification ─────────────────────────────────────────────
    trade_type = str(snapshot.get("trade_type", "")).upper()
    if not trade_type:
        sr = float(snapshot.get("smart_rank", 0.0) or 0.0)
        if sr >= K.TRADE_TYPE_STRONG_MIN:
            trade_type = "STRONG"
        elif sr >= K.TRADE_TYPE_MEDIUM_MIN:
            trade_type = "MEDIUM"
    if trade_type == "MEDIUM" and float(snapshot.get("adx", 0.0) or 0.0) < K.HQ_MEDIUM_MIN_ADX:
        return False

    # ── Soft quality score (0–10) ─────────────────────────────────────────────
    score = 0

    if snapshot.get("accumulation_detected", False):
        score += 1
    if snapshot.get("higher_lows", False):
        score += 1
    if float(snapshot.get("price", 0)) > float(snapshot.get("ema50", 0)):
        score += 1
    if float(snapshot.get("price", 0)) > float(snapshot.get("ema200", 0)):
        score += 1
    rsi = float(snapshot.get("rsi", 50) or 50)
    if 40 <= rsi <= 70:
        score += 1
    if snapshot.get("volume_confirmed", False):
        score += 1
    if float(snapshot.get("vol_ratio", 1.0) or 1.0) <= 2.5:
        score += 1
    if abs(float(snapshot.get("two_day_gain_pct", 0) or 0)) <= 5.0:
        score += 1
    if float(snapshot.get("structure_strength_score", 0) or 0) >= 50:
        score += 1
    if float(snapshot.get("accumulation_quality_score", 0) or 0) >= 60:
        score += 1

    return score >= 6  # must pass 6/10 soft checks regardless of tier


__all__ = [
    "apply_entry_timing_filter",
    "apply_regime_gate",
    "compute_adx_value",
    "compute_rsi_value",
    "detect_conservative_market_regime",
    "evaluate_symbol_snapshot",
    "is_high_probability_trade",
]
