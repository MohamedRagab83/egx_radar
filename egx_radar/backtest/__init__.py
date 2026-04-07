"""Backtest module: walk-forward replay of signal logic on historical OHLCV."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from egx_radar.backtest.data_loader import load_backtest_data
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics
from egx_radar.backtest.missed_trades import run_missed_trade_analysis
from egx_radar.backtest.tracking_dashboard import run_dashboard

__all__ = [
    "load_backtest_data",
    "run_backtest",
    "compute_metrics",
    "run_missed_trade_analysis",
    "run_dashboard",
]


def open_backtest_window(root) -> None:
    """Lazy import to avoid circular import with ui."""
    from egx_radar.backtest.report import open_backtest_window as _open
    _open(root)
