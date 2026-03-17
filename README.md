# EGX Radar v0.8.3 — Algorithmic Trading System

> **High-performance backtesting engine with reinforced safety guards for Egyptian stock market trading**

![Status](https://img.shields.io/badge/status-production--ready-success)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-proprietary-red)
![Version](https://img.shields.io/badge/version-0.8.3-green)

## 🎯 Overview

**EGX Radar** is a sophisticated algorithmic trading system optimized for the Egyptian Exchange (EGX). It combines multi-layered risk management with high-performance backtesting capabilities to deliver robust trading signals and comprehensive performance analysis.

### Key Features

✅ **4-Layer Safety Guard System**
- **DataGuard**: Validates data quality and detects anomalies
- **MomentumGuard**: Confirms signal momentum and trend alignment
- **AlphaMonitor**: Tracks strategy alpha and risk metrics
- **PositionManager**: Controls position sizing and exposure limits

✅ **High-Performance Backtesting**
- Parallel processing with 4-worker multiprocessing (3x-4x speedup)
- Vectorized calculations using NumPy/Pandas
- 11-symbol backtest in ~15-20 seconds (optimized from 60s)
- Automatic timeout enforcement (60s max)

✅ **Comprehensive Risk Management**
- Real-time position monitoring
- Drawdown protection and recovery
- Trade exit signals and stop-loss enforcement
- Portfolio performance metrics and Sharpe ratio tracking

✅ **Production-Ready Infrastructure**
- 60+ automated tests (unit, integration, performance, validation)
- CI/CD pipeline with GitHub Actions (Python 3.8-3.11)
- Data validation framework with OHLC constraint checking
- Centralized error handling with recovery strategies

✅ **Professional UI**
- PyQt/Tkinter-based graphical interface
- Real-time symbol scanning
- Historical backtest comparison
- Performance analytics and charts

---

## 🚀 Quick Start

### Installation

**Requirements:** Python 3.8+ (tested on 3.8, 3.9, 3.10, 3.11)

```bash
# Clone repository
git clone https://github.com/yourusername/egx-radar.git
cd egx-radar

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m egx_radar --version
```

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions.

### Running Your First Backtest

```python
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics

# Run a simple backtest
trades, equity_curve, params = run_backtest(
    date_from="2025-01-01",
    date_to="2025-12-31",
    progress_callback=lambda msg: print(f"  {msg}")
)

# Compute performance metrics
metrics = compute_metrics(trades)
print(f"Total Trades: {metrics.get('total_trades')}")
print(f"Win Rate: {metrics.get('win_rate_pct'):.2f}%")
print(f"Sharpe Ratio: {metrics.get('sharpe_ratio'):.2f}")
```

### Run the Interactive UI

```bash
# Launch main trading interface
python -m egx_radar

# Or start the backtest runner
python _run_single_bt.py
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [INSTALLATION.md](INSTALLATION.md) | Detailed setup, virtual environment, dependency resolution |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Complete API reference for all modules and classes |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment, configuration, monitoring |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development setup, testing, contributing guidelines |
| [CONFIGURATION.md](CONFIGURATION.md) | Settings reference, symbol lists, tuning parameters |

---

## 🏗️ Architecture

### Core Components

```
egx_radar/
├── backtest/          → Backtesting engine
│   ├── engine.py      → Main backtest logic (parallel processing)
│   └── metrics.py     → Performance calculation
├── core/              → Guard system & position management
│   ├── data_guard.py  → Data validation
│   ├── momentum_guard.py → Signal confirmation
│   ├── alpha_monitor.py → Risk tracking
│   └── position_manager.py → Position control
├── config/            → Configuration & settings
│   └── settings.py    → Centralized configuration
├── data/              → Data acquisition
├── scan/              → Symbol scanning
├── ui/                → User interface
├── tools/             → Utility functions
├── data_validator.py  → Data quality framework
└── error_handler.py   → Error handling & recovery
```

### Execution Flow

```
Data Input
    ↓
DataGuard (Quality Check)
    ↓
MomentumGuard (Signal Confirmation)
    ↓
AlphaMonitor (Risk Assessment)
    ↓
PositionManager (Position Sizing)
    ↓
Trade Execution / Exit
    ↓
Metrics & Reporting
```

---

## ⚡ Performance

### Optimization Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Backtest Suite (11 symbols)** | 60s | 15-20s | **3-4x faster** |
| **Parallel Workers** | Sequential | 4 workers | **75% reduction** |
| **Memory Usage** | Optimized | Optimized | **Chunked processing** |
| **Timeout Compliance** | 60-90s | <60s | **Guaranteed** |

### Parallelization Benefits

- 11 symbols on 4 workers = ~3 batches (vs 11 sequential)
- Expected speedup: 3.67x (actual: 3-4x with overhead)
- Works across all major workload types

---

## 🧪 Testing

### Test Suite (60+ tests)

```bash
# Run all tests
pytest tests/ -v

# Run by category
pytest tests/ -m unit -v           # Unit tests
pytest tests/ -m integration -v    # Integration tests
pytest tests/ -m performance -v    # Performance benchmarks
pytest tests/ -m datavalidation -v # Data quality tests

# Generate coverage report
pytest tests/ --cov=egx_radar --cov-report=html
```

### Test Coverage

- **Unit Tests** (26 tests): Engine, metrics, configuration, guards
- **Integration Tests** (15 tests): Full pipeline, data flow, end-to-end
- **Performance Tests** (17 tests): Timing, parallelization, memory
- **Data Validation** (18 tests): OHLCV, metrics, quality checks
- **Error Handling** (16 tests): Recovery strategies, retries, timeouts

### Performance Targets (Enforced)

- ✅ Backtest suite: < 20 seconds
- ✅ Single symbol: < 2 seconds
- ✅ Memory: < 500 MB
- ✅ Parallel speedup: >= 2.5x
- ✅ Timeout: 60 seconds max

---

## 🔧 Configuration

### Basic Settings (`egx_radar/config/settings.py`)

```python
# Performance
WORKERS_COUNT = 4              # Parallel workers
CHUNK_SIZE = 2                 # Batch size
MAX_BACKTEST_SECONDS = 60      # Timeout (seconds)
PERFORMANCE_PROFILE = "optimized"

# Trading
BT_MIN_SMARTRANK = 50          # Signal strength threshold
BT_SYMBOLS = [                 # Backtest symbols
    'HRHO', 'ORHD', 'TMGH', ...
]

# Data
DATA_MIN_BARS = 250            # Minimum historical data
DATA_START = "2020-01-01"      # Backtest start date
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete reference.

---

## 🚨 Error Handling

### Recovery Strategies

When errors occur, EGX Radar automatically applies recovery strategies:

1. **Skip Symbol** - Continue with other symbols
2. **Reduce Date Range** - Shrink backtest period
3. **Fallback to Sequential** - Disable parallel processing
4. **Clear Cache** - Free memory

### Example Error Handling

```python
from egx_radar.error_handler import (
    get_error_handler,
    ErrorSeverity
)

handler = get_error_handler()

try:
    # Your code here
    results = backtest_engine.run()
except Exception as e:
    handler.handle_error(
        message=str(e),
        component="backtest_engine",
        severity=ErrorSeverity.ERROR,
        exception=e,
        recover=True  # Auto-apply recovery strategy
    )
```

### Error Monitoring

```python
# Check error summary
summary = handler.get_error_summary()
print(f"Total errors: {summary['total_errors']}")
print(f"By component: {summary['by_component']}")

# Export errors
handler.export_errors('errors.json')
```

---

## 📊 Data Validation

### Built-in Quality Checks

```python
from egx_radar.data_validator import DataValidator, validate_dataset

# Validate single dataset
validator = DataValidator()
result = validator.validate_ohlc_data(df, "TEST")

print(f"Valid: {result['valid']}")
print(f"Errors: {result['errors']}")
print(f"Warnings: {result['warnings']}")

# Generate report
report = validator.generate_validation_report()
print(report)
```

### Validations Performed

- ✅ Required columns (Open, High, Low, Close, Volume)
- ✅ NaN and negative value detection
- ✅ High >= Low logic verification
- ✅ Close within H-L range
- ✅ Zero volume detection
- ✅ Date continuity and gaps
- ✅ Minimum bars requirement
- ✅ Trade structure validation

---

## 🐳 Docker Deployment

### Quick Start with Docker

```bash
# Build image
docker build -t egx-radar:latest .

# Run backtest
docker run --rm egx-radar:latest python _run_single_bt.py

# Run tests
docker run --rm egx-radar:latest pytest tests/ -v

# Interactive shell
docker run -it egx-radar:latest bash
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for Kubernetes and production deployments.

---

## 📈 Example: Full Backtest with Analysis

```python
import pandas as pd
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics
from egx_radar.data_validator import validate_dataset, generate_validation_report

# Run backtest
print("Running backtest...")
trades, equity_curve, params = run_backtest(
    date_from="2024-01-01",
    date_to="2024-12-31",
    progress_callback=lambda msg: print(f"  {msg}")
)

# Compute metrics
metrics = compute_metrics(trades)
print("\n=== BACKTEST RESULTS ===")
print(f"Total Trades: {metrics['total_trades']}")
print(f"Win Rate: {metrics['win_rate_pct']:.2f}%")
print(f"Profit Factor: {metrics['profit_factor']:.2f}x")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")

# Export results
trade_df = pd.DataFrame(trades)
trade_df.to_csv('backtest_results.csv', index=False)
print("\n✓ Results exported to backtest_results.csv")
```

---

## 🔐 Security & Compliance

- **Data Validation**: Multi-layer quality checks before processing
- **Error Isolation**: Errors don't crash the system, recovery strategies applied
- **Timeout Protection**: Prevents runaway processes
- **Audit Logging**: All errors and warnings logged with timestamps
- **Position Limits**: Hard stops on position sizing and exposure

---

## 🤝 Contributing

### Development Setup

```bash
# Setup development environment
git clone https://github.com/yourusername/egx-radar.git
cd egx-radar

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed contribution guidelines.

---

## 📝 License

Proprietary © 2026 EGX Radar Team. All rights reserved.

---

## 📞 Support & Contact

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@egx-radar.local

---

## 🎓 Learning Resources

- [API Documentation](API_DOCUMENTATION.md) - Complete API reference
- [Configuration Guide](CONFIGURATION.md) - Settings and tuning
- [Examples](examples/) - Sample scripts and use cases
- [Tests](tests/) - Test suite as documentation

---

## 📊 Project Status

| Phase | Status | Completion |
|-------|--------|-----------|
| Phase 1: Core Engine | ✅ Complete | 100% |
| Phase 2: Data Validation | ✅ Complete | 100% |
| Phase 3: Guard System | ✅ Complete | 100% |
| Phase 4: Performance Optimization | ✅ Complete | 100% |
| Phase 5: Testing & Infrastructure | ✅ Complete | 100% |
| Phase 6A: Documentation & Deployment | 🔄 In Progress | 50% |
| Phase 6B: Database Layer | ⏳ Planned | 0% |
| Phase 6C: Web Dashboard | ⏳ Planned | 0% |

---

**Last Updated:** March 16, 2026  
**Version:** 0.8.3  
**Status:** Production Ready ✅
