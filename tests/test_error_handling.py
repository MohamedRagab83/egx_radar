"""Tests for error handling and recovery frameworks."""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.mark.unit
class TestErrorHandler:
    """Test error handling framework."""
    
    def test_error_handler_init(self):
        """Test ErrorHandler initialization."""
        from egx_radar.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        assert handler.logger is not None
        assert handler.errors == []
    
    def test_handle_error(self):
        """Test error handling."""
        from egx_radar.error_handler import ErrorHandler, ErrorSeverity
        
        handler = ErrorHandler()
        
        handler.handle_error(
            message="Test error",
            component="test",
            severity=ErrorSeverity.ERROR,
        )
        
        assert len(handler.errors) == 1
        assert handler.errors[0].message == "Test error"
        assert handler.errors[0].component == "test"
    
    def test_handle_exception(self):
        """Test error handling with exception."""
        from egx_radar.error_handler import ErrorHandler, ErrorSeverity
        
        handler = ErrorHandler()
        
        try:
            raise ValueError("Test exception")
        except Exception as e:
            handler.handle_error(
                message="Caught exception",
                component="test",
                exception=e,
                severity=ErrorSeverity.ERROR,
            )
        
        assert len(handler.errors) == 1
        assert handler.errors[0].exception_type == "ValueError"
    
    def test_error_summary(self):
        """Test error summary reporting."""
        from egx_radar.error_handler import ErrorHandler, ErrorSeverity
        
        handler = ErrorHandler()
        
        handler.handle_error("Error 1", "component1", ErrorSeverity.ERROR)
        handler.handle_error("Error 2", "component1", ErrorSeverity.WARNING)
        handler.handle_error("Error 3", "component2", ErrorSeverity.ERROR)
        
        summary = handler.get_error_summary()
        
        assert summary['total_errors'] == 3
        assert summary['by_severity']['ERROR'] == 2
        assert summary['by_severity']['WARNING'] == 1
        assert summary['by_component']['component1'] == 2
        assert summary['by_component']['component2'] == 1
    
    def test_clear_errors(self):
        """Test clearing error log."""
        from egx_radar.error_handler import ErrorHandler, ErrorSeverity
        
        handler = ErrorHandler()
        handler.handle_error("Error", "component", ErrorSeverity.ERROR)
        
        assert len(handler.errors) == 1
        
        handler.clear_errors()
        
        assert len(handler.errors) == 0


@pytest.mark.unit
class TestRecoveryStrategy:
    """Test recovery strategies."""
    
    def test_skip_symbol_strategy(self):
        """Test skip symbol recovery strategy."""
        from egx_radar.error_handler import (
            RecoveryStrategy,
            BacktestError,
            ErrorSeverity,
        )
        
        error = BacktestError(
            timestamp=datetime.now(),
            severity=ErrorSeverity.ERROR,
            message="Symbol error",
            component="engine",
        )
        
        result = RecoveryStrategy.skip_symbol(
            error,
            {'symbol': 'TEST'}
        )
        
        assert result['action'] == 'skip'
        assert result['symbol'] == 'TEST'
    
    def test_reduce_date_range_strategy(self):
        """Test reduce date range recovery strategy."""
        from egx_radar.error_handler import (
            RecoveryStrategy,
            BacktestError,
            ErrorSeverity,
        )
        
        error = BacktestError(
            timestamp=datetime.now(),
            severity=ErrorSeverity.ERROR,
            message="Timeout",
            component="engine",
        )
        
        result = RecoveryStrategy.reduce_date_range(error, {})
        
        assert result['action'] == 'reduce_range'
    
    def test_fallback_to_sequential(self):
        """Test fallback to sequential processing."""
        from egx_radar.error_handler import (
            RecoveryStrategy,
            BacktestError,
            ErrorSeverity,
        )
        
        error = BacktestError(
            timestamp=datetime.now(),
            severity=ErrorSeverity.ERROR,
            message="Parallel error",
            component="engine",
        )
        
        result = RecoveryStrategy.fallback_to_sequential(error, {})
        
        assert result['action'] == 'sequential'
        assert result['workers'] == 1
    
    def test_clear_cache_strategy(self):
        """Test cache clearing strategy."""
        from egx_radar.error_handler import (
            RecoveryStrategy,
            BacktestError,
            ErrorSeverity,
        )
        
        error = BacktestError(
            timestamp=datetime.now(),
            severity=ErrorSeverity.ERROR,
            message="Memory error",
            component="engine",
        )
        
        result = RecoveryStrategy.clear_cache(error, {})
        
        assert result['action'] == 'cleared_cache'


@pytest.mark.unit
class TestRetryManager:
    """Test retry management."""
    
    def test_retry_manager_init(self):
        """Test RetryManager initialization."""
        from egx_radar.error_handler import RetryManager
        
        manager = RetryManager(max_retries=3, backoff_factor=2.0)
        assert manager.max_retries == 3
        assert manager.backoff_factor == 2.0
    
    def test_successful_execution(self):
        """Test successful execution without retry."""
        from egx_radar.error_handler import RetryManager
        
        manager = RetryManager()
        
        def successful_func():
            return "success"
        
        result, success = manager.execute_with_retry(successful_func)
        
        assert success is True
        assert result == "success"
    
    def test_eventual_success(self):
        """Test eventual success after retries."""
        from egx_radar.error_handler import RetryManager
        
        manager = RetryManager(max_retries=2)
        
        counter = [0]
        
        def eventually_succeeds():
            counter[0] += 1
            if counter[0] < 2:
                raise ValueError("Not yet")
            return "success"
        
        result, success = manager.execute_with_retry(eventually_succeeds)
        
        assert success is True
        assert result == "success"
        assert counter[0] == 2
    
    def test_all_retries_exhausted(self):
        """Test failure after all retries exhausted."""
        from egx_radar.error_handler import RetryManager
        
        manager = RetryManager(max_retries=2)
        
        def always_fails():
            raise ValueError("Always fails")
        
        result, success = manager.execute_with_retry(always_fails)
        
        assert success is False
        assert result is None


@pytest.mark.unit
class TestErrorStructure:
    """Test error data structure."""
    
    def test_backtest_error_creation(self):
        """Test BacktestError creation."""
        from egx_radar.error_handler import BacktestError, ErrorSeverity
        
        error = BacktestError(
            timestamp=datetime.now(),
            severity=ErrorSeverity.ERROR,
            message="Test error",
            component="test_component",
            exception_type="ValueError",
        )
        
        assert error.message == "Test error"
        assert error.component == "test_component"
        assert error.severity == ErrorSeverity.ERROR
    
    def test_backtest_error_to_dict(self):
        """Test BacktestError serialization."""
        from egx_radar.error_handler import BacktestError, ErrorSeverity
        
        error = BacktestError(
            timestamp=datetime.now(),
            severity=ErrorSeverity.ERROR,
            message="Test error",
            component="test_component",
            context={'key': 'value'},
        )
        
        error_dict = error.to_dict()
        
        assert 'timestamp' in error_dict
        assert error_dict['message'] == "Test error"
        assert error_dict['component'] == "test_component"
        assert error_dict['severity'] == "ERROR"
        assert error_dict['context'] == {'key': 'value'}


@pytest.mark.unit
class TestGlobalErrorHandler:
    """Test global error handler."""
    
    def test_get_error_handler(self):
        """Test getting global error handler."""
        from egx_radar.error_handler import get_error_handler
        
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        # Should return same instance
        assert handler1 is handler2
    
    def test_handle_backtest_error(self):
        """Test convenience error handling function."""
        from egx_radar.error_handler import handle_backtest_error, ErrorSeverity
        
        handle_backtest_error(
            message="Test error",
            component="test",
            severity=ErrorSeverity.WARNING,
        )
        
        # Should not raise


@pytest.mark.unit
class TestErrorSeverityLevels:
    """Test error severity level handling."""
    
    def test_severity_levels(self):
        """Test different severity levels."""
        from egx_radar.error_handler import ErrorSeverity
        
        assert ErrorSeverity.INFO.value == "INFO"
        assert ErrorSeverity.WARNING.value == "WARNING"
        assert ErrorSeverity.ERROR.value == "ERROR"
        assert ErrorSeverity.CRITICAL.value == "CRITICAL"
