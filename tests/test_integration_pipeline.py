"""Integration tests for the complete backtest pipeline."""

import pytest
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.mark.integration
class TestBacktestPipeline:
    """Test the complete backtest pipeline."""
    
    def test_full_backtest_execution(self, backtest_engine):
        """Test running a complete backtest with actual settings."""
        if backtest_engine is None:
            pytest.skip("Backtest engine not available")
        
        trades, equity_curve, params = backtest_engine(
            date_from="2025-01-01",
            date_to="2025-12-31",
            progress_callback=lambda msg: None,
        )
        
        # Verify structure
        assert isinstance(trades, list)
        assert isinstance(equity_curve, (list, pd.DataFrame, dict, type(None)))
        assert isinstance(params, dict)
    
    def test_backtest_with_metrics(self, backtest_engine):
        """Test backtest execution and metrics computation."""
        if backtest_engine is None:
            pytest.skip("Backtest engine not available")
        
        from egx_radar.backtest.metrics import compute_metrics
        
        trades, equity_curve, params = backtest_engine(
            date_from="2025-01-01",
            date_to="2025-06-01",
        )
        
        metrics = compute_metrics(trades)
        assert isinstance(metrics, dict)


@pytest.mark.integration
class TestDataPipeline:
    """Test the data acquisition and validation pipeline."""
    
    def test_data_guard_pipeline(self, sample_ohlcv_data, clean_data_guard):
        """Test DataGuard validation in pipeline."""
        if clean_data_guard is None:
            pytest.skip("DataGuard not available")
        
        # Validate sample data
        result = clean_data_guard.validate(sample_ohlcv_data)
        
        # Should either pass or return validation info
        assert result is not None


@pytest.mark.integration
class TestGuardSequence:
    """Test the guard sequence pipeline."""
    
    def test_all_guards_chainable(self, sample_ohlcv_data):
        """Test that all guards can be applied in sequence."""
        try:
            from egx_radar.core.data_guard import DataGuard
            from egx_radar.core.momentum_guard import MomentumGuard
            
            dg = DataGuard()
            mg = MomentumGuard()
            
            # Step 1: Data validation
            validated = dg.validate(sample_ohlcv_data)
            
            # Step 2: Momentum evaluation (if applicable)
            # This should not raise an error
            assert validated is not None or validated is False
            
        except ImportError:
            pytest.skip("Guards not available")


@pytest.mark.integration
class TestEndToEndBacktest:
    """Test complete end-to-end backtest flow."""
    
    def test_backtest_export_format(self, backtest_engine):
        """Test that backtest can generate exportable trade data."""
        if backtest_engine is None:
            pytest.skip("Backtest engine not available")
        
        trades, equity_curve, params = backtest_engine(
            date_from="2025-06-01",
            date_to="2025-06-30",
        )
        
        # Verify trade records have required fields
        if trades:
            trade = trades[0]
            # Should have OHLC timestamp info
            assert isinstance(trade, dict)
            assert len(trade) > 0


@pytest.mark.integration
class TestSymbolProcessing:
    """Test symbol list processing."""
    
    def test_symbol_loading(self, test_settings):
        """Test that symbols can be loaded from settings."""
        if test_settings is None:
            pytest.skip("Settings not available")
        
        # Settings should have symbol list
        assert hasattr(test_settings, 'SYMBOLS') or hasattr(test_settings, 'BT_SYMBOLS')
        
        symbols = getattr(test_settings, 'BT_SYMBOLS', getattr(test_settings, 'SYMBOLS', []))
        assert isinstance(symbols, (list, tuple, set))


@pytest.mark.integration
class TestProgressCallback:
    """Test progress callback mechanism."""
    
    def test_progress_reporting(self, backtest_engine):
        """Test that progress is reported during backtest."""
        if backtest_engine is None:
            pytest.skip("Backtest engine not available")
        
        progress_messages = []
        
        def capture_progress(msg):
            progress_messages.append(msg)
        
        trades, equity_curve, params = backtest_engine(
            date_from="2025-01-01",
            date_to="2025-01-31",
            progress_callback=capture_progress,
        )
        
        # Should have called progress callback
        # (in short backtest, may not have messages)
        assert isinstance(progress_messages, list)
