"""
core/smart_rank.py — EGX Radar Pro
======================================
Legacy and Smart Rank 2.0 scoring logic.

Smart Rank 2.0 uses a filter-first model:
1) Hard filters must pass (trend, momentum zone, volume, ATR control, breakout quality)
2) Only then compute a clean weighted score
"""

from __future__ import annotations

from typing import Dict, Tuple

from config.settings import CFG, Snapshot
from utils.helpers import clamp


def smart_rank_legacy(snapshot: Snapshot) -> float:
    """Legacy score retained for old-vs-new baseline comparison."""
    flow      = clamp(snapshot.volume_ratio / 2.2,      0.0, 1.0)
    structure = clamp(snapshot.structure_score / 100.0, 0.0, 1.0)
    timing    = clamp((snapshot.rsi - 35.0) / 40.0,     0.0, 1.0)
    momentum  = clamp(snapshot.trend_strength,           0.0, 1.0)
    regime    = 1.0 if snapshot.close > snapshot.ema200 else 0.4

    raw_score = (
        0.30 * flow
        + 0.25 * structure
        + 0.20 * timing
        + 0.10 * momentum
        + 0.10 * regime
        + 0.05 * 0.5
    ) * 100.0
    return round(clamp(raw_score, 0.0, 100.0), 2)


def _v2_params(overrides: Dict | None = None) -> Dict[str, float]:
    params = {
        "rsi_min": CFG.v2_rsi_min,
        "rsi_max": CFG.v2_rsi_max,
        "volume_min": CFG.v2_volume_min,
        "atr_pct_max": CFG.v2_atr_pct_max,
        "breakout_min": CFG.v2_breakout_min,
        "score_threshold": CFG.v2_score_threshold,
    }
    if overrides:
        params.update(overrides)
    return params


def smart_rank_v2_filters(snapshot: Snapshot, params: Dict | None = None) -> Tuple[bool, Dict[str, bool]]:
    """Hard filters for Smart Rank 2.0: all must pass."""
    p = _v2_params(params)
    checks = {
        "trend_ok": bool(snapshot.close > snapshot.ema50 and snapshot.close > snapshot.ema200),
        "rsi_ok": bool(p["rsi_min"] <= snapshot.rsi <= p["rsi_max"]),
        "volume_ok": bool(snapshot.volume_ratio > p["volume_min"]),
        "atr_ok": bool(snapshot.atr_pct <= p["atr_pct_max"]),
        "breakout_ok": bool(snapshot.breakout_proximity >= p["breakout_min"]),
    }
    return all(checks.values()), checks


def smart_rank_v2(snapshot: Snapshot, params: Dict | None = None) -> float:
    """
    Smart Rank 2.0 clean score.

    Assumes filters have already passed; still bounded to [0,100].
    """
    p = _v2_params(params)

    trend_score = clamp((snapshot.close / max(snapshot.ema50, 1e-9) - 1.0) / 0.08, 0.0, 1.0)

    mid = (p["rsi_min"] + p["rsi_max"]) / 2.0
    half_range = max((p["rsi_max"] - p["rsi_min"]) / 2.0, 1e-9)
    momentum_score = clamp(1.0 - abs(snapshot.rsi - mid) / half_range, 0.0, 1.0)

    volume_score = clamp((snapshot.volume_ratio - p["volume_min"]) / 1.8, 0.0, 1.0)
    volatility_score = clamp(1.0 - (snapshot.atr_pct / max(p["atr_pct_max"], 1e-9)), 0.0, 1.0)
    breakout_score = clamp(
        (snapshot.breakout_proximity - p["breakout_min"]) / max(1.0 - p["breakout_min"], 1e-9),
        0.0,
        1.0,
    )

    raw_score = (
        0.30 * trend_score
        + 0.20 * momentum_score
        + 0.20 * volume_score
        + 0.15 * volatility_score
        + 0.15 * breakout_score
    ) * 100.0

    return round(clamp(raw_score, 0.0, 100.0), 2)
