"""
ai/probability_engine.py — EGX Radar Pro
==========================================
AI probability estimator — DISPLAY ONLY.

Computes the estimated probability that a trade will be profitable,
using a logistic function over a weighted combination of technical
factors.  The output is used exclusively for display/advisory purposes.

CRITICAL: This value must NEVER appear in generate_trade_signal() or
any other execution path.

Architecture
------------
  Input weights
    34%   SmartRank (primary driver)
    20%   Market structure (EMA alignment score)
    16%   RSI timing (ideal accumulation zone)
    10%   Volume confirmation
     8%   Trend momentum
    10%   ATR risk penalty (negative weight)
    +/-   Learning bias (adaptive, bounded ±0.10)

  Activation: logistic sigmoid applied to the weighted sum
  Sentiment:  mild modulation factor applied post-sigmoid
  Output:     clamped to [0.05, 0.95]
"""

from __future__ import annotations

import math

from config.settings import Snapshot
from utils.helpers import clamp


def probability_engine(snapshot: Snapshot, learning_bias: float = 0.0) -> float:
    """
    Estimate trade success probability for a given market snapshot.

    Parameters
    ----------
    snapshot      : Fully-evaluated market Snapshot (all fields populated).
    learning_bias : Adaptive bias from LearningModule.bias.
                    Bounded to [-0.10, +0.10].
                    Has NO effect on SmartRank or execution decisions.

    Returns
    -------
    float in [0.05, 0.95]
    """
    raw = (
        0.34 * (snapshot.smart_rank / 100.0)
        + 0.20 * (snapshot.structure_score / 100.0)
        + 0.16 * clamp((snapshot.rsi - 35.0) / 40.0, 0.0, 1.0)
        + 0.10 * clamp(snapshot.volume_ratio / 2.5,  0.0, 1.0)
        + 0.08 * clamp(snapshot.trend_strength,       0.0, 1.0)
        - 0.10 * clamp(snapshot.atr_pct / 0.08,      0.0, 1.0)
        + learning_bias
    )

    # Logistic activation centred at 0.50
    centered = (raw - 0.50) * 6.0
    p = 1.0 / (1.0 + math.exp(-centered))

    # Mild sentiment modulation (keeps range well within [0.05, 0.95])
    p = p * (0.95 + 0.10 * snapshot.sentiment_score)

    return round(clamp(p, 0.05, 0.95), 4)
