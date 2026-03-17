# API Documentation — EGX Radar v0.8.3

> Complete API reference for all modules, classes, and functions

## Quick Navigation

- [Backtesting Module](#backtesting-module)
- [Configuration Module](#configuration-module)
- [Data Validation Module](#data-validation-module)
- [Error Handling Module](#error-handling-module)
- [Core Guards Module](#core-guards-module)

---

## Backtesting Module

`egx_radar.backtest.engine` — High-performance backtesting engine

### `run_backtest()`

Run a single backtest on configured symbols.

```python
def run_backtest(
    date_from: str,
    date_to: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Tuple[List[Dict], Union[List, pd.DataFrame, Dict, None], Dict]:
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `date_from` | str | Start date (format: "YYYY-MM-DD") |
| `date_to` | str | End date (format: "YYYY-MM-DD") |
| `progress_callback` | Callable | Optional callback for progress messages |

**Returns:**

```python
(
    trades,      # List[Dict] — executed trades
    equity_curve,# List/pd.DataFrame — equity over time
    params       # Dict — backtest parameters
)
```

**Example:**

```python
from egx_radar.backtest.engine import run_backtest

trades, equity_curve, params = run_backtest(
    date_from="2025-01-01",
    date_to="2025-12-31",
    progress_callback=lambda msg: print(f"  {msg}")
)

print(f"Executed {len(trades)} trades")
```

**Performance:**

- Sequential: ~60 seconds for 11 symbols
- Parallel (4 workers): ~15-20 seconds
- Timeout: 60 seconds maximum

---

### `run_backtest_suite()`

Run backtest across multiple symbols in parallel.

```python
def run_backtest_suite(
    symbols: List[str],
    date_from: str,
    date_to: str,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Dict]:
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `symbols` | List[str] | Symbol list to backtest |
| `date_from` | str | Start date (YYYY-MM-DD) |
| `date_to` | str | End date (YYYY-MM-DD) |
| `progress_callback` | Callable | Progress reporting callback |

**Returns:**

```python
{
    'SYMBOL1': {
        'trades': List[Dict],
        'equity_curve': List,
        'params': Dict
    },
    'SYMBOL2': {...},
    ...
}
```

**Example:**

```python
from egx_radar.backtest.engine import run_backtest_suite
from egx_radar.config.settings import K

results = run_backtest_suite(
    symbols=K.BT_SYMBOLS,  # From configuration
    date_from="2025-01-01",
    date_to="2025-12-31"
)

for symbol, result in results.items():
    print(f"{symbol}: {len(result['trades'])} trades")
```

---

## Metrics Module

`egx_radar.backtest.metrics` — Performance metrics calculation

### `compute_metrics()`

Calculate performance metrics from trade list.

```python
def compute_metrics(trades: List[Dict]) -> Dict:
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `trades` | List[Dict] | Trade records from backtest |

**Returns:**

```python
{
    'total_trades': int,
    'winning_trades': int,
    'losing_trades': int,
    'win_rate_pct': float,
    'total_pnl': float,
    'avg_pnl': float,
    'profit_factor': float,
    'max_consecutive_wins': int,
    'max_consecutive_losses': int,
    'max_drawdown_pct': float,
    'sharpe_ratio': float,
    'return_pct': float,
    'risk_adjusted_return': float,
    'average_trade_duration_days': int,
    'best_trade_pnl': float,
    'worst_trade_pnl': float,
}
```

**Example:**

```python
from egx_radar.backtest.metrics import compute_metrics

metrics = compute_metrics(trades)

print(f"Win Rate: {metrics['win_rate_pct']:.2f}%")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
print(f"Profit Factor: {metrics['profit_factor']:.2f}x")
```

---

## Configuration Module

`egx_radar.config.settings` — Centralized configuration

### Settings Object (`K`)

Access settings via the global `K` object.

```python
from egx_radar.config.settings import K

# Performance
K.WORKERS_COUNT                # int: Number of parallel workers (default: 4)
K.CHUNK_SIZE                   # int: Batch size for processing (default: 2)
K.MAX_BACKTEST_SECONDS         # int: Maximum execution time (default: 60)
K.PERFORMANCE_PROFILE          # str: "optimized" (default)

# Symbols
K.BT_SYMBOLS                   # List[str]: Backtest symbol list
K.SCAN_SYMBOLS                 # List[str]: Scan symbol list
K.REJECTED_SYMBOLS             # List[str]: Excluded symbols

# Trading Parameters
K.BT_MIN_SMARTRANK             # int: Signal strength threshold
K.BT_POSITION_SIZE             # float: Default position size
K.BT_STOP_LOSS_PERCENT         # float: Stop loss percentage
K.BT_TAKE_PROFIT_PERCENT       # float: Take profit percentage

# Data
K.DATA_MIN_BARS                # int: Minimum historical bars (default: 250)
K.DATA_START                   # str: Default start date
K.DATA_MAX_GAP_DAYS            # int: Maximum gap between bars (default: 2)
```

**Example:**

```python
from egx_radar.config.settings import K

print(f"Trading {len(K.BT_SYMBOLS)} symbols")
print(f"Using {K.WORKERS_COUNT} parallel workers")
print(f"Min signal strength: {K.BT_MIN_SMARTRANK}")
```

---

## Data Validation Module

`egx_radar.data_validator` — Data quality framework

### `DataValidator` Class

Comprehensive data quality validation.

```python
class DataValidator:
    def __init__(self, min_bars: int = 250, max_gap_days: int = 2):
        """Initialize validator."""
    
    def validate_ohlc_data(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> Dict:
        """Validate OHLC/OHLCV data."""
    
    def validate_metrics(self, trades: List[Dict]) -> Dict:
        """Validate trade metrics."""
```

**Example:**

```python
from egx_radar.data_validator import DataValidator
import pandas as pd

# Create validator
validator = DataValidator(min_bars=250, max_gap_days=2)

# Validate OHLC data
result = validator.validate_ohlc_data(df, "AAPL")

print(f"Valid: {result['valid']}")
print(f"Errors: {result['errors']}")
print(f"Warnings: {result['warnings']}")
print(f"Metrics: {result['metrics']}")
```

**Validations:**

- ✅ Required columns (Open, High, Low, Close, Volume)
- ✅ Data types (numeric values)
- ✅ NaN and negative values
- ✅ High >= Low (for each bar)
- ✅ Close within [Low, High]
- ✅ Zero volume detection
- ✅ Date continuity and gaps
- ✅ Minimum bars requirement

---

### `validate_dataset()`

Quick validation of single dataset.

```python
def validate_dataset(
    df: pd.DataFrame,
    symbol: str,
    min_bars: int = 250
) -> Dict:
```

**Example:**

```python
from egx_radar.data_validator import validate_dataset

result = validate_dataset(df, "TEST")
if result['valid']:
    print("✓ Data is valid")
else:
    print(f"✗ Data validation failed: {result['errors']}")
```

---

### `validate_all_symbols()`

Batch validation of multiple symbols.

```python
def validate_all_symbols(
    symbol_data: Dict[str, pd.DataFrame]
) -> Dict[str, Dict]:
```

**Example:**

```python
from egx_radar.data_validator import validate_all_symbols

symbol_data = {
    'AAPL': df1,
    'GOOGL': df2,
    'MSFT': df3,
}

results = validate_all_symbols(symbol_data)

for symbol, result in results.items():
    status = "✓" if result['valid'] else "✗"
    print(f"{symbol}: {status}")
```

---

### `generate_validation_report()`

Create human-readable validation report.

```python
def generate_validation_report(results: Dict[str, Dict]) -> str:
```

**Example:**

```python
from egx_radar.data_validator import generate_validation_report

report = generate_validation_report(results)
print(report)

# Output:
# ============================================================
# DATA VALIDATION REPORT
# ============================================================
#
# Summary: 2/3 datasets valid
#
# AAPL     ✓ PASS
# GOOGL    ✓ PASS
# MSFT     ✗ FAIL
#   ERROR: Contains 5 NaN values
```

---

## Error Handling Module

`egx_radar.error_handler` — Error handling & recovery

### `ErrorHandler` Class

Centralized error management.

```python
class ErrorHandler:
    def __init__(self, log_file: Optional[str] = None):
        """Initialize error handler."""
    
    def handle_error(
        self,
        message: str,
        component: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        exception: Optional[Exception] = None,
        context: Optional[Dict] = None,
        recover: bool = True,
    ) -> Optional[Dict]:
        """Handle error with optional recovery."""
    
    def get_error_summary(self) -> Dict:
        """Get summary of all errors."""
    
    def export_errors(self, filepath: str):
        """Export errors to JSON file."""
```

**Example:**

```python
from egx_radar.error_handler import ErrorHandler, ErrorSeverity

handler = ErrorHandler(log_file='app.log')

try:
    result = risky_operation()
except Exception as e:
    handler.handle_error(
        message=str(e),
        component="backtest_engine",
        severity=ErrorSeverity.ERROR,
        exception=e,
        context={'symbol': 'AAPL'},
        recover=True  # Apply recovery strategy
    )

# Check summary
summary = handler.get_error_summary()
print(f"Total errors: {summary['total_errors']}")
print(f"By component: {summary['by_component']}")

# Export for analysis
handler.export_errors('errors.json')
```

---

### `RetryManager` Class

Automatic retry with exponential backoff.

```python
class RetryManager:
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        backoff_max: float = 10.0,
    ):
        """Initialize retry manager."""
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Optional[Any], bool]:
        """Execute function with automatic retries."""
```

**Example:**

```python
from egx_radar.error_handler import RetryManager

manager = RetryManager(max_retries=3, backoff_factor=2.0)

def fetch_data():
    # May fail transiently
    return api.get_data()

result, success = manager.execute_with_retry(fetch_data)

if success:
    print(f"Success: {result}")
else:
    print("Failed after retries")
```

---

### `RecoveryStrategy` Class

Pre-built recovery strategies.

```python
class RecoveryStrategy:
    @staticmethod
    def skip_symbol(error: BacktestError, context: Dict) -> Dict:
        """Skip symbol and continue."""
    
    @staticmethod
    def reduce_date_range(error: BacktestError, context: Dict) -> Dict:
        """Reduce date range."""
    
    @staticmethod
    def fallback_to_sequential(error: BacktestError, context: Dict) -> Dict:
        """Disable parallel processing."""
    
    @staticmethod
    def clear_cache(error: BacktestError, context: Dict) -> Dict:
        """Clear cache to free memory."""
```

**Example:**

```python
from egx_radar.error_handler import RecoveryStrategy

# Skip symbol on error
result = RecoveryStrategy.skip_symbol(
    error,
    {'symbol': 'AAPL'}
)
# result = {'action': 'skip', 'symbol': 'AAPL'}
```

---

### Global Error Handler

```python
from egx_radar.error_handler import (
    get_error_handler,
    handle_backtest_error,
    ErrorSeverity
)

# Get global handler
handler = get_error_handler()

# Convenience function
handle_backtest_error(
    message="Something went wrong",
    component="scanner",
    severity=ErrorSeverity.WARNING,
)
```

---

## Core Guards Module

`egx_radar.core` — Trade signal filtering system

### `DataGuard` Class

Validates data quality before processing.

```python
class DataGuard:
    def validate(self, df: pd.DataFrame) -> Union[bool, pd.DataFrame]:
        """Validate OHLCV data."""
```

**Example:**

```python
from egx_radar.core.data_guard import DataGuard

guard = DataGuard()
valid = guard.validate(df)

if valid:
    print("✓ Data passed validation")
```

---

### `MomentumGuard` Class

Confirms signal momentum and trend alignment.

```python
class MomentumGuard:
    def evaluate(self, df: pd.DataFrame) -> bool:
        """Check if momentum aligns with signal."""
```

**Example:**

```python
from egx_radar.core.momentum_guard import MomentumGuard

guard = MomentumGuard()
has_momentum = guard.evaluate(df)

if has_momentum:
    print("✓ Signal confirmed by momentum")
```

---

### `AlphaMonitor` Class

Tracks strategy performance and risk metrics.

```python
class AlphaMonitor:
    def check_alpha(self, performance: Dict) -> bool:
        """Verify positive alpha."""
```

---

### `PositionManager` Class

Controls position sizing and exposure limits.

```python
class PositionManager:
    def calculate_position_size(
        self,
        account_size: float,
        risk_percent: float
    ) -> float:
        """Calculate position size based on risk."""
```

---

## Utility Functions

### Type Hints

All functions use full type hints for IDE support:

```python
from typing import List, Dict, Tuple, Optional, Callable

# Function with type hints
def run_backtest(
    date_from: str,
    date_to: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Tuple[List[Dict], Union[List, pd.DataFrame, Dict, None], Dict]:
    """..."""
```

---

## Error Codes

Common error scenarios:

| Error Type | Code | Severity | Recovery |
|-----------|------|----------|----------|
| Invalid Date Range | 1001 | ERROR | Reduce range |
| Missing Data | 1002 | ERROR | Skip symbol |
| NaN Values | 1003 | WARNING | Clean data |
| Timeout | 1004 | CRITICAL | Sequential mode |
| Memory Error | 1005 | ERROR | Clear cache |
| Import Error | 1006 | CRITICAL | Manual fix required |

---

## Examples

### Complete Backtest with Analysis

```python
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics
from egx_radar.data_validator import validate_dataset

# Run backtest
trades, equity_curve, params = run_backtest(
    date_from="2025-01-01",
    date_to="2025-12-31"
)

# Validate trades
validator_result = validate_dataset(df, "TEST")
if validator_result['valid']:
    # Compute metrics
    metrics = compute_metrics(trades)
    
    # Display results
    print(f"Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate_pct']:.2f}%")
    print(f"Sharpe: {metrics['sharpe_ratio']:.2f}")
```

### Error Handling Example

```python
from egx_radar.error_handler import (
    get_error_handler,
    ErrorSeverity,
    RecoveryStrategy
)

handler = get_error_handler()

def backtest_with_recovery():
    try:
        return run_backtest(...)
    except Exception as e:
        recovery = handler.handle_error(
            message=str(e),
            component="backtest",
            severity=ErrorSeverity.ERROR,
            exception=e,
            recover=True
        )
        
        if recovery and recovery.get('action') == 'sequential':
            # Fallback to single-worker mode
            pass

backtest_with_recovery()
```

---

## Environment Variables

```bash
# Set before running
export EGX_RADAR_WORKERS=4
export EGX_RADAR_TIMEOUT=60
export EGX_RADAR_LOG_FILE=app.log
export EGX_RADAR_VERBOSE=1
```

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Single backtest | ~2 seconds | Single symbol, 1 year data |
| Suite (11 symbols) | 15-20s | Parallel with 4 workers |
| Data validation | <100ms | For 250 bars |
| Metric computation | ~50ms | For 100 trades |

---

## Thread Safety

- ✅ `DataValidator` - Thread-safe
- ✅ `ErrorHandler` - Thread-safe (uses locks)
- ❌ Config settings - Not thread-safe (read-only okay)
- ❌ Backtest engine - Use separate workers, not threads

---

**Last Updated:** March 16, 2026  
**API Version:** 0.8.3  
[Back to README](README.md)
