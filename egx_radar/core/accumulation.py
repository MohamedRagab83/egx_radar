from __future__ import annotations

"""Accumulation detection primitives for EGX position trading."""

from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

from egx_radar.config.settings import K
from egx_radar.core.indicators import safe_clamp


def _last(series: pd.Series, default: float = 0.0) -> float:
    data = pd.Series(series).dropna()
    return float(data.iloc[-1]) if not data.empty else default


def _finite_float(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def _series_mean(series: pd.Series, default: float = 0.0) -> float:
    data = pd.Series(series).dropna()
    if data.empty:
        return default
    return _finite_float(data.mean(), default)


def _series_std(series: pd.Series, default: float = 0.0) -> float:
    data = pd.Series(series).dropna()
    if data.empty:
        return default
    return _finite_float(data.std(ddof=0), default)


def _norm_score(value: float, low: float, high: float, inverse: bool = False) -> float:
    if high <= low:
        return 0.0
    numeric = _finite_float(value, float("nan"))
    if not np.isfinite(numeric):
        return 50.0
    clipped = safe_clamp((numeric - low) / (high - low), 0.0, 1.0)
    return round((1.0 - clipped if inverse else clipped) * 100.0, 2)


def _slope_pct(series: pd.Series, bars: int) -> float:
    window = pd.Series(series).dropna().tail(bars)
    if len(window) < max(3, bars):
        return 0.0
    x = np.arange(len(window), dtype=float)
    slope = float(np.polyfit(x, window.astype(float).values, 1)[0])
    base = max(float(window.mean()), 1e-9)
    return (slope / base) * 100.0


def _support_slope_pct(low: pd.Series, window: int) -> float:
    supports = low.tail(window).rolling(3, min_periods=3).min().dropna()
    if len(supports) < 3:
        return 0.0
    return _slope_pct(supports, len(supports))


def _compression_profile(df: pd.DataFrame, price: float) -> Dict[str, float]:
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    candidates: List[Dict[str, float]] = []

    for window in range(K.ACCUM_COMPRESSION_MIN_DAYS, K.ACCUM_COMPRESSION_MAX_DAYS + 1):
        if len(df) < window + 5:
            continue
        w_high = float(high.tail(window).max())
        w_low = float(low.tail(window).min())
        range_pct = ((w_high - w_low) / max(price, 1e-9)) * 100.0

        recent_span = max(3, window // 2)
        recent_returns = close.tail(recent_span).pct_change(fill_method=None).dropna()
        prior_slice = close.tail(window).iloc[:-recent_span]
        prior_returns = prior_slice.pct_change(fill_method=None).dropna()
        recent_vol = _series_std(recent_returns, 0.0)
        prior_vol = _series_std(prior_returns, 0.0)
        if len(recent_returns) < 2 or len(prior_returns) < 2:
            contraction_ratio = 1.0
        else:
            contraction_ratio = _finite_float(recent_vol / max(prior_vol, 1e-6), 1.0)

        range_score = _norm_score(range_pct, K.ACCUM_COMPRESSION_RANGE_MAX_PCT, 14.0, inverse=True)
        contraction_score = _norm_score(contraction_ratio, 0.70, 1.25, inverse=True)
        position_in_range = safe_clamp((price - w_low) / max(w_high - w_low, 1e-9), 0.0, 1.0)
        location_score = _norm_score(abs(position_in_range - 0.72), 0.0, 0.42, inverse=True)

        total = range_score * 0.50 + contraction_score * 0.35 + location_score * 0.15
        candidates.append(
            {
                "window": float(window),
                "range_pct": round(range_pct, 2),
                "contraction_ratio": round(_finite_float(contraction_ratio, 1.0), 3),
                "position_in_range": round(position_in_range, 3),
                "compression_score": round(total, 2),
                "base_low": round(w_low, 3),
                "base_high": round(w_high, 3),
            }
        )

    if not candidates:
        return {
            "window": float(K.ACCUM_COMPRESSION_MIN_DAYS),
            "range_pct": 99.0,
            "contraction_ratio": 2.0,
            "position_in_range": 0.0,
            "compression_score": 0.0,
            "base_low": price,
            "base_high": price,
        }
    return max(candidates, key=lambda item: item["compression_score"])


def _up_down_volume_ratio(close: pd.Series, volume: pd.Series, window: int) -> float:
    close_tail = close.tail(window)
    vol_tail = volume.tail(window)
    delta = close_tail.diff().fillna(0.0)
    up_vol = _series_mean(vol_tail[delta >= 0], 0.0)
    down_vol = _series_mean(vol_tail[delta < 0], 0.0)
    if down_vol <= 1e-6:
        return 2.0 if up_vol > 0 else 1.0
    return _finite_float(up_vol / down_vol, 1.0)


def _volume_variation_ratio(volume: pd.Series, window: int) -> float:
    vol_tail = volume.tail(window)
    mean = _series_mean(vol_tail, 0.0)
    std = _series_std(vol_tail, 0.0)
    return _finite_float(std / max(mean, 1e-6), 0.0)


def _count_large_gain_days(close: pd.Series, threshold_pct: float, lookback: int) -> int:
    gains = close.pct_change(fill_method=None).tail(lookback).fillna(0.0) * 100.0
    return int((gains >= threshold_pct).sum())


def evaluate_accumulation_context(
    df_ta: pd.DataFrame,
    *,
    price: float,
    ema20: float,
    ema50: float,
    ema200: float,
    ema20_slope_pct: float,
    ema50_slope_pct: float,
    ema200_slope_pct: float,
    rsi: float,
    adx: float,
    avg_turnover: float,
    spread_pct: float,
    avg_vol: float,
    vol_ratio: float,
    vol_zscore: float,
) -> Dict[str, float]:
    close = df_ta["Close"].astype(float)
    open_ = df_ta["Open"].astype(float)
    high = df_ta["High"].astype(float)
    low = df_ta["Low"].astype(float)
    volume = df_ta["Volume"].fillna(0.0).astype(float)

    compression = _compression_profile(df_ta, price)
    window = int(compression["window"])
    window_high = float(compression["base_high"])
    window_low = float(compression["base_low"])
    prior_highs = high.tail(window).iloc[:-1]
    prior_closes = close.tail(window).iloc[:-1]
    if len(prior_highs) > 0:
        cluster_high = float(prior_highs.quantile(0.75))
        close_ceiling = float(prior_closes.max()) if not prior_closes.empty else cluster_high
        wick_high = float(prior_highs.max())
        minor_resistance = max(close_ceiling, min(wick_high, cluster_high * 1.01))
    else:
        minor_resistance = window_high
    minor_break_pct = ((price / max(minor_resistance, 1e-9)) - 1.0) * 100.0

    rolling_supports = low.tail(window).rolling(3, min_periods=3).min().dropna()
    support_floor = float(rolling_supports.quantile(0.35)) if not rolling_supports.empty else window_low
    support_floor = max(window_low, min(support_floor, price))
    support_slope_pct = _support_slope_pct(low, window)
    higher_lows = support_slope_pct > 0.02 and float(low.tail(3).min()) >= window_low * 1.01
    structure_slope_score = _norm_score(support_slope_pct, 0.0, 0.20)
    ma50_score = 100.0 if price >= ema50 * 0.998 else _norm_score((price / max(ema50, 1e-9)) - 1.0, -0.03, 0.03)
    ema20_score = _norm_score(ema20_slope_pct, -0.10, 0.18)
    ema50_trend_score = _norm_score(ema50_slope_pct, -0.08, 0.15)
    resistance_tightness = _norm_score(abs(minor_break_pct - 0.9), 0.0, K.ACCUM_MAX_MINOR_BREAK_PCT)
    structure_strength = round(
        safe_clamp(
            structure_slope_score * 0.40
            + ma50_score * 0.25
            + ema20_score * 0.20
            + resistance_tightness * 0.15,
            0.0,
            100.0,
        ),
        2,
    )

    volume_5 = _series_mean(volume.tail(5), 0.0)
    volume_20 = _series_mean(volume.tail(20), 0.0)
    volume_10 = _series_mean(volume.tail(10), 0.0)
    gradual_volume_ratio = volume_5 / max(volume_20, 1e-6)
    up_down_ratio = _up_down_volume_ratio(close, volume, window)
    turnover_multiple = avg_turnover / max(K.MIN_TURNOVER_EGP, 1.0)
    volume_variation = _volume_variation_ratio(volume, window)
    erratic_volume = (
        vol_ratio > K.ACCUM_VOL_CONFIRM_MAX
        or volume_variation > K.ACCUM_ERRATIC_VOLUME_CV
        or float(volume.tail(window).max()) > max(volume_20, 1e-6) * K.ANTI_FAKE_ABNORMAL_VOL_RATIO
    )

    turnover_score = _norm_score(turnover_multiple, 1.0, 3.0)
    gradual_volume_score = _norm_score(abs(gradual_volume_ratio - 1.18), 0.0, 0.85, inverse=True)
    up_down_score = _norm_score(up_down_ratio, 0.95, 1.45)
    smooth_volume_score = _norm_score(volume_variation, 0.20, K.ACCUM_ERRATIC_VOLUME_CV, inverse=True)
    volume_quality = round(
        safe_clamp(
            turnover_score * 0.35
            + gradual_volume_score * 0.25
            + up_down_score * 0.25
            + smooth_volume_score * 0.15
            - (20.0 if erratic_volume else 0.0),
            0.0,
            100.0,
        ),
        2,
    )

    range_today_pct = ((float(high.iloc[-1]) - float(low.iloc[-1])) / max(price, 1e-9)) * 100.0
    body_today_pct = abs(float(close.iloc[-1]) - float(open_.iloc[-1])) / max(price, 1e-9) * 100.0
    one_day_gain_pct = close.pct_change(fill_method=None).iloc[-1] * 100.0 if len(close) >= 2 else 0.0
    two_day_gain_pct = ((price / max(float(close.iloc[-3]), 1e-9)) - 1.0) * 100.0 if len(close) >= 3 else one_day_gain_pct
    last_3_days_gain_pct = ((price / max(float(close.iloc[-4]), 1e-9)) - 1.0) * 100.0 if len(close) >= 4 else two_day_gain_pct
    gap_up_pct = ((float(open_.iloc[-1]) / max(float(close.iloc[-2]), 1e-9)) - 1.0) * 100.0 if len(close) >= 2 else 0.0

    sudden_spike = max(one_day_gain_pct, two_day_gain_pct) > K.ACCUM_MAX_2DAY_SPIKE_PCT
    abnormal_candle = range_today_pct > K.ACCUM_ABNORMAL_CANDLE_RANGE_PCT and body_today_pct > K.ACCUM_ABNORMAL_BODY_PCT
    too_many_shock_days = _count_large_gain_days(close, K.ACCUM_MAX_2DAY_SPIKE_PCT, window) >= 2
    fake_move = sudden_spike or abnormal_candle or too_many_shock_days or gap_up_pct > K.MAX_GAP_UP_PCT

    rsi_score = _norm_score(abs(rsi - 52.0), 0.0, 12.0, inverse=True)
    compression_score = float(compression["compression_score"])
    base_position_score = _norm_score(abs(compression["position_in_range"] - 0.72), 0.0, 0.40, inverse=True)
    volatility_score = _norm_score(vol_zscore, 0.2, 2.4, inverse=True)
    accumulation_quality = round(
        safe_clamp(
            compression_score * 0.45
            + rsi_score * 0.20
            + base_position_score * 0.15
            + volatility_score * 0.20
            - (20.0 if fake_move else 0.0),
            0.0,
            100.0,
        ),
        2,
    )

    adx_score = 100.0 - _norm_score(abs(adx - 20.0), 0.0, 15.0)
    ema200_score = _norm_score(ema200_slope_pct, -0.10, 0.18)
    stack_score = 100.0 if price > ema50 > ema200 else 60.0 if price > ema50 and ema50 >= ema200 * 0.99 else 10.0
    stability_score = _norm_score(spread_pct, 0.4, K.MAX_SPREAD_PCT, inverse=True)
    trend_alignment = round(
        safe_clamp(
            stack_score * 0.35
            + ema20_score * 0.20
            + ema50_trend_score * 0.15
            + ema200_score * 0.15
            + adx_score * 0.10
            + stability_score * 0.05,
            0.0,
            100.0,
        ),
        2,
    )

    volume_confirmed = (
        not erratic_volume
        and vol_ratio <= K.ACCUM_VOL_CONFIRM_MAX
        and up_down_ratio >= 0.95
        and (
            vol_ratio >= K.ACCUM_VOL_CONFIRM_MIN
            or (gradual_volume_ratio >= 0.98 and up_down_ratio >= 1.05 and volume_quality >= 58.0)
        )
    )
    risk_anchor = support_floor * 0.995
    base_risk_pct = ((price - risk_anchor) / max(price, 1e-9)) if risk_anchor > 0 else 1.0
    stop_capped = base_risk_pct > K.MAX_STOP_LOSS_PCT
    risk_viable = 0.0 < base_risk_pct <= 0.10

    accumulation_detected = bool(
        not fake_move
        and sum([
            accumulation_quality >= 58.0,
            structure_strength >= 55.0,
            volume_quality >= 52.0,
            trend_alignment >= 52.0,
            higher_lows,
            price >= ema50 * 0.995,
            ema20_slope_pct >= -0.15,
            38.0 <= rsi <= 65.0,
        ]) >= 6
    )
    break_confirmed = minor_break_pct > 0.0
    trigger_price = minor_resistance * 1.001
    entry_ready = bool(
        accumulation_detected
        and -K.ACCUM_PREBREAK_BUFFER_PCT <= minor_break_pct <= K.ACCUM_MAX_MINOR_BREAK_PCT
        and volume_confirmed
        and risk_viable
    )

    return {
        "accumulation_quality_score": accumulation_quality,
        "structure_strength_score": structure_strength,
        "volume_quality_score": volume_quality,
        "trend_alignment_score": trend_alignment,
        "compression_window": window,
        "compression_range_pct": float(compression["range_pct"]),
        "compression_score": compression_score,
        "contraction_ratio": float(compression["contraction_ratio"]),
        "position_in_range": float(compression["position_in_range"]),
        "support_slope_pct": round(support_slope_pct, 4),
        "higher_lows": bool(higher_lows),
        "gradual_volume_ratio": round(gradual_volume_ratio, 3),
        "up_down_volume_ratio": round(up_down_ratio, 3),
        "volume_variation_ratio": round(volume_variation, 3),
        "turnover_multiple": round(turnover_multiple, 3),
        "minor_resistance": round(minor_resistance, 3),
        "trigger_price": round(trigger_price, 3),
        "minor_break_pct": round(minor_break_pct, 2),
        "base_low": round(support_floor, 3),
        "base_wick_low": round(window_low, 3),
        "base_high": round(window_high, 3),
        "volume_confirmed": bool(volume_confirmed),
        "erratic_volume": bool(erratic_volume),
        "abnormal_candle": bool(abnormal_candle),
        "sudden_spike": bool(sudden_spike),
        "fake_move": bool(fake_move),
        "one_day_gain_pct": round(one_day_gain_pct, 2),
        "two_day_gain_pct": round(two_day_gain_pct, 2),
        "last_3_days_gain_pct": round(last_3_days_gain_pct, 2),
        "gap_up_pct": round(gap_up_pct, 2),
        "range_today_pct": round(range_today_pct, 2),
        "body_today_pct": round(body_today_pct, 2),
        "avg_vol_5": round(volume_5, 2),
        "avg_vol_10": round(volume_10, 2),
        "avg_vol_20": round(volume_20, 2),
        "base_risk_pct": round(base_risk_pct, 4),
        "risk_viable": bool(risk_viable),
        "stop_capped": bool(stop_capped),
        "accumulation_detected": accumulation_detected,
        "break_confirmed": bool(break_confirmed),
        "entry_ready": entry_ready,
    }


__all__ = ["evaluate_accumulation_context"]
