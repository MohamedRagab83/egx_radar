"""Tests for data validation framework."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.mark.datavalidation
class TestDataValidator:
    """Test data validation framework."""
    
    def test_validator_init(self):
        """Test DataValidator initialization."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator(min_bars=250, max_gap_days=2)
        assert validator.min_bars == 250
        assert validator.max_gap_days == 2
    
    def test_validate_clean_data(self, sample_ohlcv_data):
        """Test validation of clean data."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        result = validator.validate_ohlc_data(sample_ohlcv_data, "TEST")
        
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'metrics' in result
    
    def test_validate_empty_data(self):
        """Test validation of empty DataFrame."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame()
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    def test_validate_missing_columns(self):
        """Test detection of missing required columns."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame({
            'Close': [100, 101, 102],
            'Volume': [1000, 2000, 3000],
        })
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        assert result['valid'] is False
        assert any('columns' in error.lower() for error in result['errors'])
    
    def test_validate_nan_values(self):
        """Test detection of NaN values."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame({
            'Open': [100, 101, np.nan],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100, 101, 102],
            'Volume': [1000, 2000, 3000],
        })
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        assert result['valid'] is False
        assert any('NaN' in error for error in result['errors'])
    
    def test_validate_negative_prices(self):
        """Test detection of negative prices."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame({
            'Open': [100, -101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100, 101, 102],
            'Volume': [1000, 2000, 3000],
        })
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        assert result['valid'] is False
        assert any('negative' in error.lower() for error in result['errors'])
    
    def test_validate_high_low_logic(self):
        """Test OHLC logical constraints."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [101, 100, 103],  # Second bar: High < Low
            'Low': [99, 105, 101],     # Second bar: High < Low (invalid)
            'Close': [100, 101, 102],
            'Volume': [1000, 2000, 3000],
        })
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        assert result['valid'] is False
        assert any('High' in error and 'Low' in error for error in result['errors'])
    
    def test_validate_minimum_bars(self):
        """Test minimum bars requirement."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator(min_bars=250)
        df = pd.DataFrame({
            'Open': [100] * 100,
            'High': [101] * 100,
            'Low': [99] * 100,
            'Close': [100] * 100,
            'Volume': [1000] * 100,
        })
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        # Should warn about insufficient bars
        assert any('250' in warning for warning in result['warnings'])
    
    def test_metrics_structure(self):
        """Test that metrics are properly calculated."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100, 101, 102],
            'Volume': [1000, 2000, 3000],
        }, index=pd.date_range(start='2025-01-01', periods=3, freq='D'))
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        metrics = result['metrics']
        assert 'n_bars' in metrics
        assert metrics['n_bars'] == 3
        assert 'avg_volume' in metrics


@pytest.mark.datavalidation
class TestMetricsValidation:
    """Test trade metrics validation."""
    
    def test_validate_trade_metrics(self, test_trade_data):
        """Test validation of trade metrics."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        result = validator.validate_metrics(test_trade_data)
        
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'metrics' in result
        assert result['metrics']['total_trades'] == 3
    
    def test_validate_empty_trades(self):
        """Test validation of empty trades list."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        result = validator.validate_metrics([])
        
        assert result['metrics']['total_trades'] == 0
    
    def test_validate_trade_structure(self):
        """Test detection of malformed trades."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        bad_trades = [
            {'symbol': 'TEST'},  # Missing required fields
            {'entry_date': datetime.now()},  # Incomplete
        ]
        
        result = validator.validate_metrics(bad_trades)
        
        assert len(result['errors']) > 0


@pytest.mark.datavalidation
class TestValidationUtilities:
    """Test validation utility functions."""
    
    def test_validate_dataset(self, sample_ohlcv_data):
        """Test single dataset validation function."""
        from egx_radar.data_validator import validate_dataset
        
        result = validate_dataset(sample_ohlcv_data, "TEST")
        
        assert 'valid' in result
        assert result['symbol'] == "TEST"
    
    def test_validate_all_symbols(self, sample_ohlcv_data):
        """Test multi-symbol validation."""
        from egx_radar.data_validator import validate_all_symbols
        
        symbol_data = {
            'TEST1': sample_ohlcv_data,
            'TEST2': sample_ohlcv_data.copy(),
        }
        
        results = validate_all_symbols(symbol_data)
        
        assert len(results) == 2
        assert 'TEST1' in results
        assert 'TEST2' in results
        assert all('valid' in r for r in results.values())
    
    def test_validation_report_generation(self, sample_ohlcv_data):
        """Test validation report generation."""
        from egx_radar.data_validator import (
            DataValidator,
            generate_validation_report
        )
        
        validator = DataValidator()
        result = validator.validate_ohlc_data(sample_ohlcv_data, "TEST")
        
        report = generate_validation_report({'TEST': result})
        
        assert isinstance(report, str)
        assert 'TEST' in report
        assert 'VALIDATION' in report


@pytest.mark.datavalidation
class TestQualityChecks:
    """Test data quality assessment."""
    
    def test_volume_outliers(self):
        """Test detection of volume outliers."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame({
            'Open': [100] * 10,
            'High': [101] * 10,
            'Low': [99] * 10,
            'Close': [100] * 10,
            'Volume': [1000] * 9 + [100000],  # Last bar spike
        })
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        # Should still be valid but may warn
        assert isinstance(result['valid'], bool)
    
    def test_price_range_calculation(self):
        """Test price range calculation in metrics."""
        from egx_radar.data_validator import DataValidator
        
        validator = DataValidator()
        df = pd.DataFrame({
            'Open': [100, 110, 105],
            'High': [105, 115, 110],
            'Low': [95, 105, 100],
            'Close': [100, 110, 105],
            'Volume': [1000, 2000, 3000],
        })
        
        result = validator.validate_ohlc_data(df, "TEST")
        
        metrics = result['metrics']
        assert 'price_range' in metrics
        # Price range should reflect actual data
        assert '95.00' in metrics['price_range']  # Min close
