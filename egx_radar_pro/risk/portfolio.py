"""
risk/portfolio.py — EGX Radar Pro
=====================================
Portfolio-level position tracking and concentration rules.

Functions here enforce the outer risk shell that wraps every entry
decision — regardless of which signal triggered it.

Limits
------
  max_open_trades      : Global cap on concurrent positions
  max_sector_positions : Per-sector concentration limit
  max_sector_exposure  : Max capital fraction in one sector

All limits are read from RISK (RiskConfig singleton in config.settings).
"""

from __future__ import annotations

from typing import Dict, List

from config.settings import RISK, Trade


def sector_positions(open_trades: List[Trade]) -> Dict[str, int]:
    """
    Count currently open positions per sector.

    Parameters
    ----------
    open_trades : Full list of Trade objects (open and closed mixed)

    Returns
    -------
    dict mapping sector name → count of OPEN positions in that sector
    """
    counts: Dict[str, int] = {}
    for t in open_trades:
        if t.status == "OPEN":
            counts[t.sector] = counts.get(t.sector, 0) + 1
    return counts


def can_open_position(sector: str, open_trades: List[Trade]) -> bool:
    """
    Check all portfolio-level constraints before opening a new position.

    Checks
    ------
    1. Global open trade cap (RISK.max_open_trades)
    2. Per-sector concentration limit (RISK.max_sector_positions)

    Returns
    -------
    True if a new position is within all limits, False otherwise.
    """
    open_count = sum(1 for t in open_trades if t.status == "OPEN")
    if open_count >= RISK.max_open_trades:
        return False

    if sector_positions(open_trades).get(sector, 0) >= RISK.max_sector_positions:
        return False

    return True


def portfolio_exposure(open_trades: List[Trade]) -> float:
    """
    Total allocated capital as a fraction of account size.

    Used for monitoring and dashboard display — not for execution gating.

    Returns
    -------
    float in [0, ∞)  — typically < 1.0 in a healthy portfolio.
    Values above 1.0 indicate leverage (should not occur in this system).
    """
    total = sum(
        t.entry * t.size
        for t in open_trades
        if t.status == "OPEN"
    )
    return total / max(RISK.account_size, 1e-9)


def portfolio_summary(open_trades: List[Trade]) -> dict:
    """
    Summary statistics for the current open portfolio.

    Returns
    -------
    dict with keys:
      open_positions   : int
      exposure_pct     : float  (fraction of account allocated)
      sector_breakdown : dict[sector → count]
    """
    open_count    = sum(1 for t in open_trades if t.status == "OPEN")
    exposure      = portfolio_exposure(open_trades)
    sectors       = sector_positions(open_trades)
    return {
        "open_positions":   open_count,
        "exposure_pct":     round(exposure * 100.0, 2),
        "sector_breakdown": sectors,
    }
