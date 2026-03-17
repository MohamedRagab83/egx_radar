# Configuration Reference — EGX Radar v0.8.3

> Complete configuration settings and tuning guide

## Overview

Configuration is managed through `egx_radar/config/settings.py` and environment variables. Settings are exposed via the global `K` object.

```python
from egx_radar.config.settings import K

# Access settings
print(K.WORKERS_COUNT)  # 4
print(K.BT_MIN_SMARTRANK)  # 50
```

---

## Performance Settings

### `WORKERS_COUNT`

Number of parallel workers for multiprocessing.

```python
WORKERS_COUNT = 4  # Default: 4
```

**Range:** 1-16  
**Recommendation:**
- Single-threaded debugging: 1
- Standard deployment: = CPU cores (or CPU cores - 1)
- High-volume: = CPU cores

**Impact:** 4 workers = 3-4x speedup vs sequential

---

### `CHUNK_SIZE`

Batch size for task chunking in parallel processing.

```python
CHUNK_SIZE = 2  # Default: 2
```

**Range:** 1-10  
**Recommendation:**
- Memory-constrained: 1
- Normal: 2-3
- High memory: 4+

**Impact:** Affects memory usage and scheduling efficiency

---

### `MAX_BACKTEST_SECONDS`

Maximum execution time for backtest before timeout.

```python
MAX_BACKTEST_SECONDS = 60  # Default: 60
```

**Range:** 10-300  
**Recommendation:**
- Development: 30-60
- Production single-symbol: 30
- Production suite: 60-120

**Impact:** Enforced via timeout mechanism

---

### `PERFORMANCE_PROFILE`

Performance optimization profile.

```python
PERFORMANCE_PROFILE = "optimized"  # Options: "default", "optimized", "aggressive"
```

| Profile | Settings | Speed | Risk |
|---------|----------|-------|------|
| default | Conservative | Baseline | Low |
| optimized | Balanced (recommended) | 3-4x faster | Medium |
| aggressive | Maximum speed | 4-5x faster | High |

---

## Trading Settings

### Symbol Configuration

#### `BT_SYMBOLS`

Symbols to backtest.

```python
BT_SYMBOLS = [
    'HRHO',  # Housing & Real Estate
    'ORHD',  # Orascom Telecom
    'TMGH',  # Telecom Egypt
    'COMI',  # Commercial International Bank
    ...
]
```

**Type:** List[str]  
**Impact:** Number of tests runs and total backtest time

#### `SCAN_SYMBOLS`

Symbols to scan for new opportunities.

```python
SCAN_SYMBOLS = BT_SYMBOLS  # Same as backtest symbols
```

#### `REJECTED_SYMBOLS`

Symbols to exclude from processing.

```python
REJECTED_SYMBOLS = []

# Example: Exclude illiquid symbols
REJECTED_SYMBOLS = ['SYMBOL1', 'SYMBOL2']
```

---

### Signal Strength

#### `BT_MIN_SMARTRANK`

Minimum signal strength threshold (0-100 scale).

```python
BT_MIN_SMARTRANK = 50  # Default: 50 (scale 0-100)
```

**Range:** 0-100  
**Recommendation:**
- Conservative: 60-70
- Balanced: 50
- Aggressive: 30-40

**Impact:** Fewer trades at higher threshold, better quality signals at lower threshold

---

### Position Management

#### `BT_POSITION_SIZE`

Default position size per trade.

```python
BT_POSITION_SIZE = 1.0  # 100% of risk capital
```

**Range:** 0.1-1.0  
**Recommendation:**
- Conservative: 0.5-0.7 (50-70%)
- Balanced: 1.0 (100%)
- Aggressive: >1.0 (margin/leverage)

#### `BT_STOP_LOSS_PERCENT`

Stop-loss distance in percent below entry.

```python
BT_STOP_LOSS_PERCENT = 2.0  # 2% stop loss
```

**Range:** 0.5-5.0  
**Recommendation:**
- Tight: 0.5-1.0%
- Standard: 2.0%
- Wide: 3.0-5.0%

#### `BT_TAKE_PROFIT_PERCENT`

Take-profit distance in percent above entry.

```python
BT_TAKE_PROFIT_PERCENT = 5.0  # 5% target
```

**Range:** 1.0-20.0  
**Recommendation:**
- Conservative: 2-3%
- Balanced: 5%
- Aggressive: 10%+

---

## Data Settings

### Data Requirements

#### `DATA_MIN_BARS`

Minimum historical bars required for analysis.

```python
DATA_MIN_BARS = 250  # ~1 year of trading days
```

**Range:** 20-1000  
**Recommendation:**
- Minimum viable: 50 (2 months)
- Standard: 250 (1 year)
- Robust: 500+ (2 years)

#### `DATA_START`

Default backtest start date.

```python
DATA_START = "2020-01-01"
```

**Format:** "YYYY-MM-DD"

#### `DATA_END`

Default backtest end date.

```python
DATA_END = "2026-03-15"
```

**Format:** "YYYY-MM-DD"

---

### Data Quality

#### `DATA_MAX_GAP_DAYS`

Maximum gap allowed between consecutive bars.

```python
DATA_MAX_GAP_DAYS = 2  # e.g., weekend/holiday
```

**Range:** 1-10  
**Recommendation:**
- Strict: 1 (no gaps)
- Standard: 2 (weekends/holidays)
- Permissive: 5+

#### `DATA_NAN_TOLERANCE`

Maximum percentage of NaN values tolerated.

```python
DATA_NAN_TOLERANCE = 0.01  # 1%
```

**Range:** 0.0-0.1  
**Recommendation:**
- Strict: 0.0 (no NaN)
- Standard: 0.01 (1%)
- Permissive: 0.05 (5%)

---

## Guard Settings

### DataGuard

```python
DATAGUARD_ENABLED = True
DATAGUARD_MIN_BARS = 250
DATAGUARD_CHECK_NAN = True
DATAGUARD_CHECK_NEGATIVE = True
DATAGUARD_CHECK_BOUNDS = True
```

### MomentumGuard

```python
MOMENTUMGUARD_ENABLED = True
MOMENTUMGUARD_RSI_PERIOD = 14
MOMENTUMGUARD_RSI_MIN = 30    # Oversold threshold
MOMENTUMGUARD_RSI_MAX = 70    # Overbought threshold
```

### AlphaMonitor

```python
ALPHAMONITOR_ENABLED = True
ALPHAMONITOR_MIN_SHARPE = -0.5  # Minimum acceptable Sharpe
ALPHAMONITOR_MAX_DRAWDOWN = 0.40  # 40% max drawdown
```

### PositionManager

```python
POSITIONMANAGER_ENABLED = True
POSITIONMANAGER_MAX_EXPOSURE = 1.0  # 100% of capital
POSITIONMANAGER_MAX_POSITIONS = 10   # Max concurrent trades
```

---

## Error Handling

### Error Recovery

```python
ENABLE_ERROR_RECOVERY = True
RECOVERY_LOG = "/var/log/egx-radar/errors.json"
RECOVERY_STRATEGIES = {
    'skip_symbol',
    'reduce_date_range',
    'fallback_to_sequential',
    'clear_cache'
}
```

### Retry Configuration

```python
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2.0
RETRY_BACKOFF_MAX = 10.0
```

---

## Logging

### File Logging

```python
ENABLE_LOGGING = True
LOG_FILE = "/var/log/egx-radar/app.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_SIZE = 100_000_000  # 100 MB
LOG_BACKUP_COUNT = 10  # Keep 10 backup logs
```

### Console Logging

```python
CONSOLE_LOGGING = True
CONSOLE_LOG_LEVEL = "INFO"
VERBOSE_OUTPUT = False
```

---

## Scanning Settings

### Symbol Scanning

```python
SCAN_MAX_WORKERS = 1  # WARNING: pandas_ta has thread-safety issues
SCAN_BATCH_SIZE = 1
SCAN_TIMEOUT_PER_SYMBOL = 10  # seconds
```

**Important:** `pandas_ta` has known thread-safety issues. Always set `SCAN_MAX_WORKERS = 1` unless using `PERFORMANCE_PROFILE = "optimized"` which handles it.

---

## Backtesting Settings

### Backtest.py Parameters

```python
BT_COMMISSIONS = 0.001  # 0.1% commission
BT_SLIPPAGE = 0.001     # 0.1% slippage
BT_STARTING_CAPITAL = 100_000  # $100k
BT_MARGIN = 2.0         # 2x leverage (if enabled)
```

### Analysis

```python
BT_ANALYZE = True
BT_PLOT = False  # Requires matplotlib
BT_EXPORT_CSV = True
BT_EXPORT_JSON = True
```

---

## UI Settings

```python
UI_THEME = "dark"  # or "light"
UI_FONT_SIZE = 10  # points
UI_WINDOW_WIDTH = 1200
UI_WINDOW_HEIGHT = 800
UI_AUTO_REFRESH = True
UI_REFRESH_INTERVAL = 5  # seconds
```

---

## Environment Variables

Override settings with environment variables:

```bash
# Performance
export EGX_RADAR_WORKERS=4
export EGX_RADAR_TIMEOUT=60
export EGX_RADAR_PERFORMANCE_PROFILE=optimized

# Logging
export EGX_RADAR_LOG_FILE=/var/log/egx-radar/app.log
export EGX_RADAR_LOG_LEVEL=INFO

# Data
export EGX_RADAR_DATA_DIR=/var/data/egx-radar
export EGX_RADAR_DATA_START=2020-01-01

# Error Handling
export EGX_RADAR_ERROR_RECOVERY=true
export EGX_RADAR_ERROR_LOG=/var/log/egx-radar/errors.json

# Trading
export EGX_RADAR_MIN_SMARTRANK=50
export EGX_RADAR_POSITION_SIZE=1.0
export EGX_RADAR_STOP_LOSS=2.0
```

Then in code:

```python
import os

WORKERS_COUNT = int(os.getenv('EGX_RADAR_WORKERS', '4'))
LOG_LEVEL = os.getenv('EGX_RADAR_LOG_LEVEL', 'INFO')
```

---

## Configuration Examples

### Conservative Configuration

For low-risk, long-term investing:

```python
BT_MIN_SMARTRANK = 70          # High quality signals only
BT_POSITION_SIZE = 0.5         # Half position
BT_STOP_LOSS_PERCENT = 1.0     # Tight stops
BT_TAKE_PROFIT_PERCENT = 2.0   # Conservative targets
WORKERS_COUNT = 2              # Careful processing
DATA_MIN_BARS = 500            # 2 years minimum
```

### Balanced Configuration

For average case:

```python
BT_MIN_SMARTRANK = 50          # Standard threshold
BT_POSITION_SIZE = 1.0         # Full position
BT_STOP_LOSS_PERCENT = 2.0     # Standard stops
BT_TAKE_PROFIT_PERCENT = 5.0   # Standard targets
WORKERS_COUNT = 4              # Full parallelization
DATA_MIN_BARS = 250            # 1 year minimum
```

### Aggressive Configuration

For maximum returns (high risk):

```python
BT_MIN_SMARTRANK = 30          # Accept weaker signals
BT_POSITION_SIZE = 1.5         # Margin usage
BT_STOP_LOSS_PERCENT = 5.0     # Wide stops
BT_TAKE_PROFIT_PERCENT = 10.0  # Ambitious targets
WORKERS_COUNT = 8              # Maximum parallelization
DATA_MIN_BARS = 50             # Minimum data
```

---

## Tuning Guide

### Optimizing for Speed

```python
WORKERS_COUNT = <CPU_CORES - 1>
CHUNK_SIZE = 4
PERFORMANCE_PROFILE = "aggressive"
DATA_MIN_BARS = 100
DATA_MAX_GAP_DAYS = 5
```

### Optimizing for Accuracy

```python
WORKERS_COUNT = 1
PERFORMANCE_PROFILE = "default"
DATA_MIN_BARS = 500
DATA_MAX_GAP_DAYS = 1
BT_MIN_SMARTRANK = 70
```

### Optimizing for Stability

```python
WORKERS_COUNT = 2
ENABLE_ERROR_RECOVERY = True
MAX_BACKTEST_SECONDS = 120
RETRY_MAX_ATTEMPTS = 5
LOG_LEVEL = "DEBUG"
```

### Optimizing for Memory

```python
CHUNK_SIZE = 1
WORKERS_COUNT = 2
DATA_MIN_BARS = 250
ENABLE_LOGGING = False
```

---

## Monitoring Configuration

Check current configuration:

```python
from egx_radar.config.settings import K

# Print all settings
import inspect
for name, value in inspect.getmembers(K):
    if name.isupper():
        print(f"{name:30} = {value}")
```

Or directly:

```python
from egx_radar.config.settings import K

print(f"Workers: {K.WORKERS_COUNT}")
print(f"Timeout: {K.MAX_BACKTEST_SECONDS}s")
print(f"Profile: {K.PERFORMANCE_PROFILE}")
print(f"Symbols: {len(K.BT_SYMBOLS)}")
```

---

## Validation

Validate configuration:

```bash
# Check settings load without errors
python -c "from egx_radar.config.settings import K; print('✓ Settings OK')"

# Test with sample backtest
python _run_single_bt.py
```

---

## Advanced: Accessing Settings

```python
# Import the global settings object
from egx_radar.config.settings import K

# Access dynamically
setting_name = 'WORKERS_COUNT'
value = getattr(K, setting_name)

# Check if setting exists
if hasattr(K, 'MY_SETTING'):
    print(K.MY_SETTING)

# List all settings
vars(K)  # Returns dict of all attributes
```

---

**Last Updated:** March 16, 2026  
**Version:** EGX Radar 0.8.3  
[Back to README](README.md)
