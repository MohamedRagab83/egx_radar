from __future__ import annotations

"""Parallel multi-factor scoring engine (experimental).

Computes an independent multi_factor_rank alongside the existing SmartRank.
This module has ZERO coupling to the accumulation strategy — it uses only
raw technical indicator values that are already computed upstream.

The multi_factor_rank is for comparison and research only.
All trade decisions continue to use SmartRank.
"""

from egx_radar.config.settings import K
from egx_radar.core.indicators import safe_clamp


# ── Factor 1: Trend Score ─────────────────────────────────────────────────


def compute_trend_score(
    price: float,
    ema50: float,
    ema200: float,
    ema50_slope_pct: float,
    ema200_slope_pct: float,
) -> float:
    """Trend alignment score [0, 100].

    Rewards:
      - Full EMA stack (price > EMA50 > EMA200)
      - Positive EMA slopes (rising moving averages)
      - Moderate distance from EMA200 (trending but not extended)
    """
    score = 0.0

    # EMA alignment (0–40 pts)
    if price > ema50 > ema200:
        score += 40.0  # full stack
    elif price > ema50:
        score += 25.0  # above short-term
    elif price > ema200:
        score += 15.0  # above long-term only
    # else: below both = 0

    # EMA50 slope (0–25 pts): positive slope = uptrend
    # EGX slope range typically -2% to +2% over 10 bars
    slope50_norm = safe_clamp((ema50_slope_pct + 2.0) / 4.0, 0.0, 1.0)
    score += slope50_norm * 25.0

    # EMA200 slope (0–15 pts): positive = macro uptrend
    slope200_norm = safe_clamp((ema200_slope_pct + 1.0) / 2.0, 0.0, 1.0)
    score += slope200_norm * 15.0

    # Distance from EMA200 (0–20 pts): moderate extension is ideal
    # pct_from_200 = (price - ema200) / ema200 * 100
    if ema200 > 0:
        pct_from_200 = ((price - ema200) / ema200) * 100.0
    else:
        pct_from_200 = 0.0
    # Ideal range: 2–12% above EMA200; penalise if too far or below
    if 2.0 <= pct_from_200 <= 12.0:
        score += 20.0
    elif 0.0 <= pct_from_200 < 2.0:
        score += 10.0 + (pct_from_200 / 2.0) * 10.0
    elif 12.0 < pct_from_200 <= 25.0:
        score += 20.0 - ((pct_from_200 - 12.0) / 13.0) * 15.0
    elif pct_from_200 < 0.0:
        score += max(0.0, 10.0 + pct_from_200)  # linear decay below 0

    return round(safe_clamp(score, 0.0, 100.0), 2)


# ── Factor 2: Momentum Score ─────────────────────────────────────────────


def compute_momentum_score(
    rsi: float,
    adx: float,
    adaptive_mom: float,
    pct_ema200: float,
) -> float:
    """Momentum quality score [0, 100].

    Rewards:
      - RSI in the sweet zone (40–65): room to run, not overbought
      - ADX in directional range (18–35): trending, not exhausted
      - Positive adaptive momentum (controlled, not parabolic)
    """
    score = 0.0

    # RSI positioning (0–30 pts)
    # Ideal zone: 40–65 (accumulation sweet spot for EGX)
    if 40.0 <= rsi <= 65.0:
        score += 30.0
    elif 35.0 <= rsi < 40.0:
        score += 20.0
    elif 65.0 < rsi <= 72.0:
        score += 20.0
    elif 30.0 <= rsi < 35.0:
        score += 10.0
    elif 72.0 < rsi <= 78.0:
        score += 10.0
    # else: extreme RSI = 0

    # ADX strength (0–30 pts)
    # Sweet spot: 18–35 (directional, not exhausted)
    if 18.0 <= adx <= 35.0:
        score += 30.0
    elif 14.0 <= adx < 18.0:
        # Building trend
        score += 15.0 + ((adx - 14.0) / 4.0) * 15.0
    elif 35.0 < adx <= 50.0:
        # Strong but risk of exhaustion
        score += 30.0 - ((adx - 35.0) / 15.0) * 15.0
    elif adx < 14.0:
        # No trend yet
        score += safe_clamp(adx / 14.0, 0.0, 1.0) * 15.0
    # else: ADX > 50 = high exhaustion risk, 0 bonus

    # Adaptive momentum (0–25 pts)
    # Positive is good, but not extreme (which signals overextension)
    if 0.5 <= adaptive_mom <= 5.0:
        score += 25.0
    elif 0.0 < adaptive_mom < 0.5:
        score += adaptive_mom / 0.5 * 15.0
    elif 5.0 < adaptive_mom <= 10.0:
        score += 25.0 - ((adaptive_mom - 5.0) / 5.0) * 10.0
    elif -2.0 <= adaptive_mom <= 0.0:
        score += max(0.0, 10.0 + adaptive_mom * 5.0)
    # else: extreme negative or extreme positive = 0

    # EMA200 proximity (0–15 pts)
    # Moderate above EMA200 is ideal; too far = chasing
    if 0.0 <= pct_ema200 <= 15.0:
        score += 15.0
    elif -5.0 <= pct_ema200 < 0.0:
        score += 10.0 + (pct_ema200 + 5.0) / 5.0 * 5.0
    elif 15.0 < pct_ema200 <= 30.0:
        score += 15.0 - ((pct_ema200 - 15.0) / 15.0) * 10.0
    # else: extreme = 0

    return round(safe_clamp(score, 0.0, 100.0), 2)


# ── Factor 3: Volume Score ────────────────────────────────────────────────


def compute_volume_score(
    vol_ratio: float,
    cmf: float,
    vol_zscore: float,
    avg_turnover: float,
) -> float:
    """Volume strength score [0, 100].

    Rewards:
      - Above-average but not spiking volume (institutional, not retail)
      - Positive Chaikin Money Flow (buying pressure)
      - Moderate volume Z-score (not extreme)
      - Adequate turnover (liquidity)
    """
    score = 0.0

    # Volume ratio (0–30 pts)
    # Ideal: 1.0–2.0 (above average, not a retail spike)
    if 1.0 <= vol_ratio <= 2.0:
        score += 30.0
    elif 0.8 <= vol_ratio < 1.0:
        score += 20.0
    elif 2.0 < vol_ratio <= 3.0:
        score += 30.0 - ((vol_ratio - 2.0) / 1.0) * 15.0
    elif 0.5 <= vol_ratio < 0.8:
        score += 10.0
    elif vol_ratio > 3.0:
        score += max(0.0, 15.0 - (vol_ratio - 3.0) * 5.0)
    # else: very low volume = 0

    # CMF (0–30 pts)
    # Positive CMF = net buying pressure; range typically [-0.5, +0.5]
    if cmf >= 0.15:
        score += 30.0
    elif 0.05 <= cmf < 0.15:
        score += 20.0 + ((cmf - 0.05) / 0.10) * 10.0
    elif 0.0 <= cmf < 0.05:
        score += 15.0
    elif -0.10 <= cmf < 0.0:
        score += 10.0
    elif -0.20 <= cmf < -0.10:
        score += 5.0
    # else: strong outflow = 0

    # Volume Z-score (0–20 pts)
    # Moderate Z-score preferred; extreme Z = retail spike
    abs_z = abs(vol_zscore)
    if abs_z <= 1.0:
        score += 20.0
    elif abs_z <= 2.0:
        score += 20.0 - ((abs_z - 1.0) / 1.0) * 8.0
    elif abs_z <= 3.0:
        score += 12.0 - ((abs_z - 2.0) / 1.0) * 6.0
    else:
        score += max(0.0, 6.0 - (abs_z - 3.0) * 3.0)

    # Turnover adequacy (0–20 pts)
    # MIN_TURNOVER_EGP = 3M; ideal > 10M
    if avg_turnover >= 15_000_000:
        score += 20.0
    elif avg_turnover >= 10_000_000:
        score += 16.0
    elif avg_turnover >= 7_000_000:
        score += 12.0
    elif avg_turnover >= K.MIN_TURNOVER_EGP:
        score += 8.0
    else:
        score += safe_clamp(avg_turnover / K.MIN_TURNOVER_EGP, 0.0, 1.0) * 8.0

    return round(safe_clamp(score, 0.0, 100.0), 2)


# ── Factor 4: Volatility Score ────────────────────────────────────────────


def compute_volatility_score(
    atr_pct_rank: float,
    vwap_dist: float,
    spread_pct: float,
) -> float:
    """Volatility stability score [0, 100].

    Rewards:
      - Low/moderate ATR percentile (stable, not volatile)
      - Close to VWAP (fair value area)
      - Low spread (liquid, tighter market)
    """
    score = 0.0

    # ATR percentile rank (0–40 pts)
    # Lower ATR = more stable entry environment
    # atr_pct_rank is 0–100 (percentile)
    if atr_pct_rank <= 40.0:
        score += 40.0
    elif atr_pct_rank <= 65.0:
        score += 40.0 - ((atr_pct_rank - 40.0) / 25.0) * 15.0
    elif atr_pct_rank <= 85.0:
        score += 25.0 - ((atr_pct_rank - 65.0) / 20.0) * 15.0
    else:
        score += max(0.0, 10.0 - ((atr_pct_rank - 85.0) / 15.0) * 10.0)

    # VWAP proximity (0–35 pts)
    # vwap_dist is (price - vwap) / price; range [-0.5, 0.5]
    # Close to 0 = at fair value
    abs_vwap = abs(vwap_dist)
    if abs_vwap <= 0.01:
        score += 35.0
    elif abs_vwap <= 0.02:
        score += 30.0
    elif abs_vwap <= 0.03:
        score += 25.0
    elif abs_vwap <= 0.05:
        score += 18.0
    elif abs_vwap <= 0.10:
        score += 10.0
    else:
        score += max(0.0, 10.0 - (abs_vwap - 0.10) * 50.0)

    # Spread stability (0–25 pts)
    # Lower spread = tighter market = better
    # MAX_SPREAD_PCT = 4.5 (rejection threshold)
    if spread_pct <= 1.5:
        score += 25.0
    elif spread_pct <= 2.5:
        score += 20.0
    elif spread_pct <= 3.5:
        score += 12.0
    elif spread_pct <= K.MAX_SPREAD_PCT:
        score += 5.0
    # else: too wide = 0

    return round(safe_clamp(score, 0.0, 100.0), 2)


# ── Composite Rank ────────────────────────────────────────────────────────


def compute_multi_factor_rank(
    trend: float,
    momentum: float,
    volume: float,
    volatility: float,
) -> float:
    """Weighted multi-factor composite rank [0, 100].

    Uses configurable weights from K.MF_W_* constants.
    """
    rank = (
        trend * K.MF_W_TREND
        + momentum * K.MF_W_MOMENTUM
        + volume * K.MF_W_VOLUME
        + volatility * K.MF_W_VOLATILITY
    )
    return round(safe_clamp(rank, 0.0, 100.0), 2)
