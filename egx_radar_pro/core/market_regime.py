"""
core/market_regime.py — EGX Radar Pro
==========================================
Market-wide and sector-level regime detection.

Regime classification is used as an execution gate in signal_engine.py:
  - BEAR  → no new entries allowed
  - NEUTRAL / BULL → entries allowed per SmartRank threshold

Regime detection uses breadth metrics across the full universe snapshot,
not individual symbol data.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from config.settings import Snapshot


def detect_market_regime(universe_snaps: List[Snapshot]) -> str:
    """
    Classify the current broad market as BULL, BEAR, or NEUTRAL.

    Methodology
    -----------
    - Breadth above EMA50  : fraction of symbols trading above their 50-day EMA
    - Breadth above EMA200 : fraction of symbols trading above their 200-day EMA
    - Average SmartRank    : mean SmartRank across the universe

    BULL  : breadth_ema50 >= 60%, breadth_ema200 >= 55%, avg_rank >= 52
    BEAR  : breadth_ema50 <= 35%  OR  avg_rank < 42
    NEUTRAL : everything in between

    Parameters
    ----------
    universe_snaps : all Snapshot objects computed for the current bar

    Returns
    -------
    "BULL" | "BEAR" | "NEUTRAL"
    """
    if not universe_snaps:
        return "NEUTRAL"

    n = len(universe_snaps)
    breadth_ema50  = sum(1 for s in universe_snaps if s.close > s.ema50)  / n
    breadth_ema200 = sum(1 for s in universe_snaps if s.close > s.ema200) / n
    avg_rank       = sum(s.smart_rank for s in universe_snaps) / n

    if breadth_ema50 >= 0.60 and breadth_ema200 >= 0.55 and avg_rank >= 52:
        return "BULL"
    if breadth_ema50 <= 0.35 or avg_rank < 42:
        return "BEAR"
    return "NEUTRAL"


def sector_strength(snaps: List[Snapshot]) -> Dict[str, float]:
    """
    Compute average SmartRank per sector.

    This is a display / monitoring metric — it does not affect execution.

    Returns
    -------
    dict mapping sector name → average SmartRank (rounded to 2 dp)
    """
    bucket: Dict[str, List[float]] = {}
    for s in snaps:
        bucket.setdefault(s.sector, []).append(s.smart_rank)
    return {k: round(float(np.mean(v)), 2) for k, v in bucket.items() if v}
