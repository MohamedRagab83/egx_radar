"""Error handling and recovery framework for backtesting."""

import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class BacktestError:
    """Structured error information."""
    timestamp: datetime
    severity: ErrorSeverity
    message: str
    component: str
    exception_type: Optional[str] = None
    traceback_info: Optional[str] = None
    context: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'message': self.message,
            'component': self.component,
            'exception_type': self.exception_type,
            'context': self.context,
        }


class ErrorHandler:
    """Centralized error handling for backtest engine."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize error handler."""
        self.errors: List[BacktestError] = []
        self.recovery_strategies: Dict[str, Callable] = {}
        self.log_file = log_file
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        self.logger.setLevel(logging.DEBUG)
    
    def register_recovery_strategy(
        self,
        error_type: str,
        strategy: Callable
    ):
        """Register a recovery strategy for error type."""
        self.recovery_strategies[error_type] = strategy
    
    def handle_error(
        self,
        message: str,
        component: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        exception: Optional[Exception] = None,
        context: Optional[Dict] = None,
        recover: bool = True,
    ) -> Optional[Dict]:
        """
        Handle an error with optional recovery.
        
        Args:
            message: Error message
            component: Component where error occurred
            severity: Error severity level
            exception: Original exception if any
            context: Contextual information
            recover: Attempt recovery if strategy available
            
        Returns:
            Recovery result if recovery was attempted
        """
        # Create error record
        error = BacktestError(
            timestamp=datetime.now(),
            severity=severity,
            message=message,
            component=component,
            exception_type=type(exception).__name__ if exception else None,
            traceback_info=traceback.format_exc() if exception else None,
            context=context,
        )
        
        self.errors.append(error)
        
        # Log error
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }[severity]
        
        self.logger.log(
            log_level,
            f"[{component}] {message}",
            extra={'exception': exception}
        )
        
        # Attempt recovery
        if recover and error.exception_type in self.recovery_strategies:
            try:
                recovery_strategy = self.recovery_strategies[error.exception_type]
                result = recovery_strategy(error, context or {})
                self.logger.info(f"Recovery successful for {error.exception_type}")
                return result
            except Exception as recovery_error:
                self.logger.error(
                    f"Recovery failed: {recovery_error}",
                    exc_info=True
                )
                return None
        
        return None
    
    def get_error_summary(self) -> Dict:
        """Get summary of all errors."""
        by_severity = {}
        by_component = {}
        
        for error in self.errors:
            # By severity
            sev = error.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            # By component
            comp = error.component
            by_component[comp] = by_component.get(comp, 0) + 1
        
        return {
            'total_errors': len(self.errors),
            'by_severity': by_severity,
            'by_component': by_component,
            'recent_errors': [e.to_dict() for e in self.errors[-5:]],  # Last 5
        }
    
    def clear_errors(self):
        """Clear error log."""
        self.errors = []
    
    def export_errors(self, filepath: str):
        """Export errors to JSON file."""
        import json
        
        data = {
            'summary': self.get_error_summary(),
            'errors': [e.to_dict() for e in self.errors],
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)


class RetryManager:
    """Manage retry logic for transient failures."""
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        backoff_max: float = 10.0,
    ):
        """Initialize retry manager."""
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.backoff_max = backoff_max
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple[Any, bool]:
        """
        Execute function with automatic retries.
        
        Returns:
            (result, success) tuple
        """
        import time
        
        last_exception = None
        backoff = 1.0
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                return result, True
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = min(
                        backoff * self.backoff_factor,
                        self.backoff_max
                    )
                    logging.warning(
                        f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                    backoff *= 2
        
        return None, False


class TimeoutManager:
    """Manage execution timeouts."""
    
    def __init__(self, timeout_seconds: int = 60):
        """Initialize timeout manager."""
        self.timeout_seconds = timeout_seconds
    
    def execute_with_timeout(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple[Optional[Any], bool]:
        """
        Execute function with timeout.
        
        Returns:
            (result, completed_in_time) tuple
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Execution exceeded {self.timeout_seconds}s")
        
        try:
            # Set timeout signal
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_seconds)
            
            result = func(*args, **kwargs)
            
            # Cancel alarm
            signal.alarm(0)
            
            return result, True
        except TimeoutError as e:
            signal.alarm(0)
            logging.error(f"Timeout: {e}")
            return None, False
        except Exception as e:
            signal.alarm(0)
            raise


class RecoveryStrategy:
    """Pre-built recovery strategies."""
    
    @staticmethod
    def skip_symbol(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Skip current symbol and continue with others."""
        symbol = context.get('symbol')
        logging.info(f"Skipping symbol '{symbol}' due to error")
        return {'action': 'skip', 'symbol': symbol}
    
    @staticmethod
    def reduce_date_range(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Reduce date range for current backtest."""
        logging.info("Reducing date range due to memory/timeout constraints")
        return {'action': 'reduce_range'}
    
    @staticmethod
    def fallback_to_sequential(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Fall back from parallel to sequential processing."""
        logging.info("Falling back to sequential processing")
        return {'action': 'sequential', 'workers': 1}
    
    @staticmethod
    def clear_cache(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Clear cache to free memory."""
        logging.info("Clearing cache to free memory")
        import gc
        gc.collect()
        return {'action': 'cleared_cache'}


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get or create global error handler."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_backtest_error(
    message: str,
    component: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    exception: Optional[Exception] = None,
    context: Optional[Dict] = None,
) -> Optional[Dict]:
    """Convenience function to use global error handler."""
    handler = get_error_handler()
    return handler.handle_error(
        message=message,
        component=component,
        severity=severity,
        exception=exception,
        context=context,
    )
