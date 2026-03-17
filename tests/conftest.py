"""Pytest configuration and shared fixtures for EGX Radar tests."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def sample_ohlcv_data():
    """Generate sample OHLCV data for 250 trading days."""
    n_bars = 250
    dates = pd.date_range(end=datetime.now(), periods=n_bars, freq='B')
    
    np.random.seed(42)
    closes = np.cumsum(np.random.randn(n_bars) * 0.5) + 100
    
    return pd.DataFrame({
        'Date': dates,
        'Open': closes + np.random.randn(n_bars) * 0.3,
        'High': closes + np.abs(np.random.randn(n_bars) * 0.5),
        'Low': closes - np.abs(np.random.randn(n_bars) * 0.5),
        'Close': closes,
        'Volume': np.random.randint(1000000, 5000000, n_bars),
        'Adj Close': closes,
    }).set_index('Date')


@pytest.fixture(scope="session")
def clean_data_guard():
    """Initialize DataGuard for tests."""
    try:
        from egx_radar.core.data_guard import DataGuard
        return DataGuard()
    except ImportError as e:
        pytest.skip(f"DataGuard import failed: {e}")


@pytest.fixture(scope="session")
def momentum_guard():
    """Initialize MomentumGuard for tests."""
    try:
        from egx_radar.core.momentum_guard import MomentumGuard
        return MomentumGuard()
    except ImportError as e:
        pytest.skip(f"MomentumGuard import failed: {e}")


@pytest.fixture(scope="session")
def test_settings():
    """Load test configuration settings."""
    try:
        from egx_radar.config.settings import K
        return K
    except ImportError as e:
        pytest.skip(f"Settings import failed: {e}")


@pytest.fixture(scope="session")
def backtest_engine():
    """Initialize backtest engine for tests."""
    try:
        from egx_radar.backtest.engine import run_backtest
        return run_backtest
    except ImportError as e:
        pytest.skip(f"Backtest engine import failed: {e}")


@pytest.fixture
def test_trade_data():
    """Generate sample trade data for metrics tests."""
    return [
        {
            'symbol': 'TEST',
            'entry_date': datetime(2025, 1, 1),
            'exit_date': datetime(2025, 1, 5),
            'entry_price': 100.0,
            'exit_price': 105.0,
            'quantity': 100,
            'pnl': 500.0,
            'pnl_pct': 5.0,
            'duration_days': 4,
        },
        {
            'symbol': 'TEST',
            'entry_date': datetime(2025, 1, 6),
            'exit_date': datetime(2025, 1, 8),
            'entry_price': 105.0,
            'exit_price': 102.0,
            'quantity': 100,
            'pnl': -300.0,
            'pnl_pct': -2.86,
            'duration_days': 2,
        },
        {
            'symbol': 'TEST',
            'entry_date': datetime(2025, 1, 9),
            'exit_date': datetime(2025, 1, 15),
            'entry_price': 102.0,
            'exit_price': 110.0,
            'quantity': 100,
            'pnl': 800.0,
            'pnl_pct': 7.84,
            'duration_days': 6,
        },
    ]


@pytest.fixture
def performance_baseline():
    """Performance target baselines for benchmarks."""
    return {
        'backtest_suite_seconds': 20,  # Should complete in ~20s max with optimization
        'single_symbol_seconds': 2,     # Single symbol in ~2s
        'memory_mb': 500,               # Memory usage under 500MB
        'parallel_speedup_min': 2.5,    # At least 2.5x speedup vs sequential
    }


def pytest_configure(config):
    """Configure pytest markers and setup."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "datavalidation: Data validation tests")


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on file location."""
    for item in items:
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
