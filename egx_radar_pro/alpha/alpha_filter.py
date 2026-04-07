"""
alpha/alpha_filter.py — EGX Radar Pro
=========================================
Alpha opportunity filter — DISPLAY / RESEARCH ONLY.

Evaluates whether alpha conditions are technically sound.
The result is used for research, logging, and advisory display.

It must NEVER be used as an execution gate in generate_trade_signal().

Filter criteria
---------------
  alpha_score >= 60     : Minimum alpha signal strength
  atr_pct <= 6%         : Volatility not excessive
  volume_ratio >= 1.3   : Volume confirmation present
  rsi >= 45             : Not technically oversold
"""

from __future__ import annotations

from typing import Tuple

from config.settings import Snapshot


def alpha_filter(snapshot: Snapshot, alpha_score: float) -> Tuple[bool, str]:
    """
    Evaluate alpha quality conditions.

    Parameters
    ----------
    snapshot    : Market snapshot for the symbol
    alpha_score : Computed alpha score from compute_alpha_score()

    Returns
    -------
    Tuple (passed: bool, reason: str)
      passed=True  → "alpha_pass"
      passed=False → reason code describing the failing condition
    """
    if alpha_score < 60:
        return False, "alpha_below_60"
    if snapshot.atr_pct > 0.06:
        return False, "atr_too_high"
    if snapshot.volume_ratio < 1.3:
        return False, "volume_too_low"
    if snapshot.rsi < 45:
        return False, "rsi_too_low"
    return True, "alpha_pass"


def alpha_quality_score(snapshot: Snapshot, alpha_score: float) -> float:
    """
    Quantify overall alpha signal quality on a [0, 1] scale.

    Used for ranking / display in a scanner UI.
    Does not affect execution.
    """
    passed, _ = alpha_filter(snapshot, alpha_score)
    if not passed:
        return 0.0

    quality = 0.0
    quality += min((alpha_score - 60.0) / 40.0, 1.0) * 0.40
    quality += min(snapshot.volume_ratio / 3.0, 1.0)  * 0.30
    quality += min((snapshot.rsi - 45.0) / 30.0, 1.0) * 0.30
    return round(quality, 4)
