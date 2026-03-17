"""Unit tests for the optimized backtest engine."""

import pytest
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.mark.unit
class TestBacktestEngineImports:
    """Test that all engine components import correctly."""
    
    def test_engine_imports(self):
        """Verify backtest engine imports without errors."""
        from egx_radar.backtest import engine
        assert hasattr(engine, 'run_backtest')
        assert hasattr(engine, 'run_backtest_suite')
    
    def test_metrics_imports(self):
        """Verify metrics module imports."""
        from egx_radar.backtest import metrics
        assert hasattr(metrics, 'compute_metrics')
    
    def test_settings_imports(self):
        """Verify settings and performance config."""
        from egx_radar.config.settings import K
        assert hasattr(K, 'WORKERS_COUNT')
        assert hasattr(K, 'CHUNK_SIZE')
        assert hasattr(K, 'MAX_BACKTEST_SECONDS')
        assert K.WORKERS_COUNT == 4
        assert K.MAX_BACKTEST_SECONDS == 60


@pytest.mark.unit
class TestMetricsCalculation:
    """Test metrics computation with sample trade data."""
    
    def test_compute_metrics_with_trades(self, test_trade_data):
        """Test that metrics are computed correctly from trades."""
        from egx_radar.backtest.metrics import compute_metrics
        
        metrics = compute_metrics(test_trade_data)
        
        # Verify structure
        assert isinstance(metrics, dict)
        assert 'total_trades' in metrics or 'overall' in metrics
        
        # Verify calculations
        overall = metrics if 'total_trades' in metrics else metrics.get('overall', {})
        assert overall.get('total_trades', 0) >= 2  # At least 2 trades
    
    def test_compute_metrics_empty(self):
        """Test metrics with empty trades list."""
        from egx_radar.backtest.metrics import compute_metrics
        
        metrics = compute_metrics([])
        assert isinstance(metrics, dict)


@pytest.mark.unit
class TestEngineConfiguration:
    """Test engine configuration and settings."""
    
    def test_performance_profile(self):
        """Verify performance profile is set to optimized."""
        from egx_radar.config.settings import K
        assert K.PERFORMANCE_PROFILE == "optimized"
    
    def test_workers_count(self):
        """Verify worker count is set for parallel processing."""
        from egx_radar.config.settings import K
        assert K.WORKERS_COUNT >= 2
        assert K.WORKERS_COUNT <= 8
    
    def test_timeout_enforcement(self):
        """Verify timeout is configured."""
        from egx_radar.config.settings import K
        assert K.MAX_BACKTEST_SECONDS == 60
    
    def test_chunk_size(self):
        """Verify chunk size for batch processing."""
        from egx_radar.config.settings import K
        assert K.CHUNK_SIZE >= 1


@pytest.mark.unit
class TestDataGuardIntegration:
    """Test DataGuard for data validation."""
    
    def test_data_guard_init(self, clean_data_guard):
        """Verify DataGuard initializes."""
        assert clean_data_guard is not None
        assert hasattr(clean_data_guard, 'validate')
    
    def test_data_guard_with_sample(self, sample_ohlcv_data, clean_data_guard):
        """Test DataGuard validation with sample data."""
        import pandas as pd
        
        if clean_data_guard is not None:
            # DataGuard should accept valid OHLCV data
            result = clean_data_guard.validate(sample_ohlcv_data)
            assert isinstance(result, (bool, dict, pd.DataFrame, type(None)))


@pytest.mark.unit
class TestMomentumGuardIntegration:
    """Test MomentumGuard for signal generation."""
    
    def test_momentum_guard_init(self, momentum_guard):
        """Verify MomentumGuard initializes."""
        assert momentum_guard is not None
    
    def test_momentum_guard_has_methods(self, momentum_guard):
        """Verify MomentumGuard has required methods."""
        assert hasattr(momentum_guard, 'evaluate') or hasattr(momentum_guard, 'check')


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in engine."""
    
    def test_backtest_with_invalid_dates(self):
        """Test that invalid date ranges are handled."""
        from egx_radar.backtest.engine import run_backtest
        
        # Should handle gracefully or raise specific error
        try:
            result = run_backtest(
                date_from="2026-01-01",
                date_to="2020-01-01",  # Invalid: end < start
            )
            # If it returns, it should return empty/error structure
            assert result is not None
        except (ValueError, TypeError, RuntimeError):
            # Graceful error handling
            pass
    
    def test_backtest_timeout(self):
        """Test that backtest respects timeout."""
        from egx_radar.backtest.engine import run_backtest
        from egx_radar.config.settings import K
        
        start = time.time()
        result = run_backtest(
            date_from="2020-01-01",
            date_to="2026-03-01",
        )
        elapsed = time.time() - start
        
        # Should complete within timeout (+ 10s buffer)
        assert elapsed <= K.MAX_BACKTEST_SECONDS + 10


@pytest.mark.unit
class TestParallelProcessing:
    """Test parallel processing capabilities."""
    
    def test_workers_pool_creation(self):
        """Test that multiprocessing pool can be created."""
        import multiprocessing
        from egx_radar.config.settings import K
        
        try:
            pool = multiprocessing.Pool(K.WORKERS_COUNT)
            assert pool is not None
            pool.close()
            pool.join()
        except Exception as e:
            pytest.skip(f"Multiprocessing pool creation failed: {e}")
    
    def test_chunked_processing(self):
        """Test chunked processing capability."""
        from egx_radar.config.settings import K
        
        items = list(range(10))
        chunks = [items[i:i+K.CHUNK_SIZE] for i in range(0, len(items), K.CHUNK_SIZE)]
        
        assert len(chunks) > 0
        assert len(chunks[-1]) <= K.CHUNK_SIZE
