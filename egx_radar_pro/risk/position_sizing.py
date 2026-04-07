"""
risk/position_sizing.py — EGX Radar Pro
==========================================
Fixed-fractional position sizing calculator.

Sizing Rule
-----------
  risk_amount    = account_size × risk_used_fraction
  risk_per_share = max(entry - stop, entry × 0.5%)
  size           = risk_amount / risk_per_share  (integer, minimum 1)

This produces dollar-risk-based sizing: the position size is set so that
a stop-loss hit costs exactly risk_amount in base currency.

The function is deterministic and has no side-effects.
"""

from __future__ import annotations


def compute_position_size(
    entry:        float,
    stop:         float,
    risk_used:    float,
    account_size: float,
) -> int:
    """
    Calculate the number of shares to purchase for a new position.

    Parameters
    ----------
    entry        : Actual entry price (post-slippage)
    stop         : Stop-loss price
    risk_used    : Fraction of account to risk on this trade
                   (e.g. 0.005 = 0.5%, typical for SmartRank MAIN entries)
    account_size : Current account equity in base currency

    Returns
    -------
    int — number of shares, floored to whole units.
    Returns 0 only if risk_amount <= 0 (should not occur in normal usage).
    Returns at least 1 share when risk_amount > 0.

    Notes
    -----
    The minimum risk_per_share floor (entry × 0.5%) prevents absurdly
    large position sizes when stop is very close to entry.
    """
    risk_amount    = account_size * risk_used
    risk_per_share = max(entry - stop, entry * 0.005)

    if risk_amount <= 0:
        return 0

    return max(1, int(risk_amount / max(risk_per_share, 1e-9)))
