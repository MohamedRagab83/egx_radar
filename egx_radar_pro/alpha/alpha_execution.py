"""
alpha/alpha_execution.py — EGX Radar Pro
==========================================
Alpha trade parameter builder — CALCULATION ONLY, NOT EXECUTED.

Computes what an alpha-driven trade WOULD look like: entry, stop, target,
and position scale.  These parameters are returned for display, research,
and reporter logging.

IMPORTANT: The output of this module is NEVER passed to the backtest
engine or used to open a real position.  Trade execution is exclusively
driven by SmartRank via core/signal_engine.py.
"""

from __future__ import annotations

from config.settings import Snapshot
from utils.helpers import clamp


def build_alpha_trade(snapshot: Snapshot, alpha_score: float) -> dict:
    """
    Compute alpha-driven trade parameters for display / research.

    Entry logic
    -----------
    - Pullback entry below close (ATR-scaled pullback, capped at 1.5%)
    - Stop defined by recent low with a small buffer
    - Target set at 2.2× the risk
    - Position scale proportional to alpha score (8–20% of base risk)

    Parameters
    ----------
    snapshot    : Market snapshot at evaluation time
    alpha_score : Alpha score from compute_alpha_score() — must be >= 60

    Returns
    -------
    dict with keys:
      entry          : float — suggested entry price
      stop           : float — suggested stop-loss price
      target         : float — suggested profit target
      risk_pct       : float — estimated risk as fraction of entry
      target_pct     : float — estimated gain potential as fraction of entry
      position_scale : float — fraction of base risk to allocate (8–20%)
      alpha_score    : float — the alpha score used in this calculation
      display_only   : bool  — always True; documents intended use
    """
    pullback   = min(
        max(snapshot.atr * 0.35, snapshot.close * 0.003),
        snapshot.close * 0.015,
    )
    entry      = max(snapshot.low, snapshot.close - pullback)
    risk_pct   = clamp(
        (entry - snapshot.low * 0.995) / max(entry, 1e-9),
        0.008, 0.025,
    )
    target_pct = max(0.04, risk_pct * 2.2)
    scale      = clamp((alpha_score - 60.0) / 200.0, 0.08, 0.20)

    return {
        "entry":          round(entry, 3),
        "stop":           round(entry * (1.0 - risk_pct), 3),
        "target":         round(entry * (1.0 + target_pct), 3),
        "risk_pct":       round(risk_pct, 4),
        "target_pct":     round(target_pct, 4),
        "position_scale": round(scale, 4),
        "alpha_score":    round(alpha_score, 2),
        "display_only":   True,
    }
