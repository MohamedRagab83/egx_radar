"""Database module for EGX Radar - persistent data management."""

from egx_radar.database.manager import DatabaseManager
from egx_radar.database.models import Base, BacktestResult, Trade, Signal, StrategyMetrics

__all__ = [
    'DatabaseManager',
    'Base',
    'BacktestResult',
    'Trade',
    'Signal',
    'StrategyMetrics',
]
