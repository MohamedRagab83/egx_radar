"""
backtest/metrics.py — EGX Radar Pro
=======================================
Performance metric computation from completed backtest results.

All functions operate on closed Trade lists and equity curves
produced by backtest/engine.py.

Metrics
-------
  trades          : Total number of closed trades
  return_pct      : Cumulative portfolio return (%)
  winrate_pct     : Percentage of trades closed with positive PnL
  drawdown_pct    : Maximum peak-to-trough drawdown (%)
  sharpe          : Annualised Sharpe ratio (assuming 252 trading days)
  expectancy_pct  : Mean PnL per trade (%)
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

from config.settings import Trade


def performance_metrics(
    trades: List[Trade],
    curve:  List[Tuple[str, float]],
) -> Dict[str, float]:
    """
    Compute standard performance metrics from a completed backtest.

    Parameters
    ----------
    trades : List of closed Trade objects
    curve  : Equity curve as [(date_str, cumulative_return_pct), ...]

    Returns
    -------
    dict with keys:
      trades, return_pct, winrate_pct, drawdown_pct, sharpe, expectancy_pct
    """
    if not trades:
        return {
            "trades":          0,
            "return_pct":      0.0,
            "winrate_pct":     0.0,
            "drawdown_pct":    0.0,
            "sharpe":          0.0,
            "expectancy_pct":  0.0,
        }

    pnl_arr    = np.array([t.pnl_pct for t in trades], dtype=float)
    winrate    = float(np.mean(pnl_arr > 0) * 100.0)
    expectancy = float(np.mean(pnl_arr))

    # Equity curve (base = 100)
    eq   = np.array([v for _, v in curve], dtype=float) + 100.0
    peak = np.maximum.accumulate(eq)
    dd   = (eq - peak) / np.maximum(peak, 1e-9)
    drawdown = float(abs(dd.min()) * 100.0)

    # Annualised Sharpe ratio
    rets   = np.diff(eq) / np.maximum(eq[:-1], 1e-9)
    sharpe = 0.0
    if len(rets) > 5 and float(np.std(rets)) > 1e-9:
        sharpe = float((np.mean(rets) / np.std(rets)) * math.sqrt(252))

    return {
        "trades":          int(len(trades)),
        "return_pct":      float(round(eq[-1] - 100.0, 2)),
        "winrate_pct":     float(round(winrate, 2)),
        "drawdown_pct":    float(round(drawdown, 2)),
        "sharpe":          float(round(sharpe, 2)),
        "expectancy_pct":  float(round(expectancy, 2)),
    }


def breakdown_by_signal_type(trades: List[Trade]) -> Dict[str, Dict[str, float]]:
    """
    Split performance metrics by signal type (MAIN vs PROBE).

    Returns
    -------
    dict mapping signal_type → {winrate, count, avg_pnl}
    """
    buckets: Dict[str, List[float]] = {}
    for t in trades:
        buckets.setdefault(t.signal_type, []).append(t.pnl_pct)

    result = {}
    for sig_type, pnls in buckets.items():
        arr = np.array(pnls, dtype=float)
        result[sig_type] = {
            "count":    len(pnls),
            "winrate":  round(float(np.mean(arr > 0) * 100.0), 2),
            "avg_pnl":  round(float(np.mean(arr)), 4),
        }
    return result


def breakdown_by_sector(trades: List[Trade]) -> Dict[str, Dict[str, float]]:
    """
    Split performance metrics by sector.

    Returns
    -------
    dict mapping sector → {count, winrate, avg_pnl}
    """
    buckets: Dict[str, List[float]] = {}
    for t in trades:
        buckets.setdefault(t.sector, []).append(t.pnl_pct)

    result = {}
    for sector, pnls in buckets.items():
        arr = np.array(pnls, dtype=float)
        result[sector] = {
            "count":    len(pnls),
            "winrate":  round(float(np.mean(arr > 0) * 100.0), 2),
            "avg_pnl":  round(float(np.mean(arr)), 4),
        }
    return result


def print_metrics(label: str, metrics: Dict[str, float]) -> None:
    """Pretty-print a metrics dict with a section header."""
    print(f"\n{'─' * 44}")
    print(f"  {label.upper()}")
    print(f"{'─' * 44}")
    for key, val in metrics.items():
        print(f"  {key:16} : {val}")
