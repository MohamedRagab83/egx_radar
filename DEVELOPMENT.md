# Development Guide — EGX Radar v0.8.3

> Contributing guidelines, development setup, and architecture documentation for developers

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Code Style Guide](#code-style-guide)
4. [Testing Guidelines](#testing-guidelines)
5. [Git Workflow](#git-workflow)
6. [Architecture Deep Dive](#architecture-deep-dive)
7. [Adding Features](#adding-features)
8. [Performance Optimization](#performance-optimization)

---

## Development Environment Setup

### Prerequisites

- Python 3.8+ (3.11 recommended)
- Git
- Visual Studio Code (recommended) or your preferred editor
- Virtual environment manager

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/egx-radar.git
cd egx-radar

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.\.venv\Scripts\activate   # Windows

# 4. Upgrade pip/setuptools/wheel
python -m pip install --upgrade pip setuptools wheel

# 5. Install in development mode
pip install -e ".[dev]"

# 6. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 7. Run initial tests
pytest tests/ -v
```

### VS Code Setup

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": ["--max-line-length=100"],
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "ms-python.python",
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/.coverage": true,
        "**/*.egg-info": true
    }
}
```

---

## Project Structure

```
egx-radar/
├── egx_radar/                    # Main package
│   ├── __init__.py              # Package init
│   ├── __main__.py              # Entry point
│   ├── backtest/                # Backtesting engine
│   │   ├── engine.py            # Main engine (parallel processing)
│   │   └── metrics.py           # Performance metrics
│   ├── core/                    # Core trading logic
│   │   ├── data_guard.py        # Data validation
│   │   ├── momentum_guard.py    # Signal confirmation
│   │   ├── alpha_monitor.py     # Risk monitoring
│   │   └── position_manager.py  # Position management
│   ├── config/                  # Configuration
│   │   └── settings.py          # Settings object (K)
│   ├── data/                    # Data acquisition
│   │   ├── fetcher.py           # Data fetching logic
│   │   └── loader.py            # Data loading
│   ├── scan/                    # Symbol scanning
│   │   └── scanner.py           # Main scanner
│   ├── ui/                      # User interface
│   │   └── main_window.py       # Qt/Tk interface
│   ├── tools/                   # Utilities
│   │   ├── indicators.py        # Technical indicators
│   │   └── helpers.py           # Helper functions
│   ├── data_validator.py        # Data validation framework
│   └── error_handler.py         # Error handling framework
│
├── tests/                       # Test suite
│   ├── conftest.py             # Pytest configuration
│   ├── test_unit_engine.py     # Unit tests
│   ├── test_integration_pipeline.py
│   ├── test_performance_benchmarks.py
│   ├── test_data_validation.py
│   └── test_error_handling.py
│
├── examples/                   # Example scripts
│   ├── simple_backtest.py      # Simple backtest example
│   ├── advanced_analysis.py    # Advanced example
│   └── error_recovery.py       # Error handling example
│
├── docs/                       # Documentation (optional)
│   └── index.md
│
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
│
├── README.md                   # Project overview
├── INSTALLATION.md             # Installation guide
├── API_DOCUMENTATION.md        # API reference
├── DEPLOYMENT.md               # Deployment guide
├── DEVELOPMENT.md              # This file
├── CONFIGURATION.md            # Settings reference
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Dependencies
├── setup.py                    # Package setup
├── pyproject.toml              # Project metadata
├── Dockerfile                  # Docker configuration
└── docker-compose.yml          # Docker compose

```

### Module Responsibilities

| Module | Purpose | Key Classes |
|--------|---------|------------|
| **backtest** | Backtesting engine with multiprocessing | `run_backtest()`, `compute_metrics()` |
| **core** | Guard system & trade logic | `DataGuard`, `MomentumGuard`, `AlphaMonitor`, `PositionManager` |
| **config** | Configuration management | `K` (settings object) |
| **data** | Data acquisition | Data fetchers, loaders |
| **scan** | Symbol scanning | Scanner engine |
| **ui** | User interface | Main window, dialogs |
| **tools** | Utilities | Indicators, helpers |
| **data_validator** | Data quality | `DataValidator`, validation utilities |
| **error_handler** | Error management | `ErrorHandler`, `RetryManager`, recovery strategies |

---

## Code Style Guide

### Python Style (PEP 8)

```python
# Imports: builtin, third-party, local
import os
import sys
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import pandas as pd
import numpy as np

from egx_radar.config.settings import K
from egx_radar.error_handler import handle_backtest_error


# Constants: UPPER_CASE
DEFAULT_TIMEOUT = 60
ALLOWED_SYMBOLS = ['AAPL', 'GOOGL']


# Classes: PascalCase
class DataValidator:
    """Class docstring (one line)."""
    
    def __init__(self, min_bars: int = 250):
        """Initialize validator.
        
        Args:
            min_bars: Minimum bars required.
        """
        self.min_bars = min_bars


# Functions: snake_case
def validate_data(df: pd.DataFrame, symbol: str) -> Dict:
    """Function docstring.
    
    Args:
        df: OHLCV data.
        symbol: Symbol name.
        
    Returns:
        Validation result dict.
        
    Raises:
        ValueError: If data is invalid.
    """
    if df is None:
        raise ValueError("DataFrame cannot be None")
    
    return {'valid': True}
```

### Formatting Tools

```bash
# Format code with black (line-length=100)
black egx_radar tests --line-length=100

# Sort imports with isort
isort egx_radar tests

# Lint with flake8
flake8 egx_radar tests --max-line-length=100 --ignore=E501,W503

# All-in-one
black egx_radar tests --line-length=100 && isort egx_radar tests && flake8 egx_radar tests --max-line-length=100
```

### Type Hints

Always use type hints:

```python
# Good
def calculate_metrics(trades: List[Dict]) -> Dict[str, float]:
    """Calculate metrics."""
    return {}

# Bad - no type hints
def calculate_metrics(trades):
    """Calculate metrics."""
    return {}

# Union types
def process_data(data: Union[pd.DataFrame, List[Dict]]) -> Dict:
    """Process data."""
    return {}

# Optional types
def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get configuration value."""
    return default
```

### Docstrings

Use Google-style docstrings:

```python
def run_backtest(
    date_from: str,
    date_to: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Tuple[List[Dict], Union[List, pd.DataFrame, Dict, None], Dict]:
    """Run a single backtest on configured symbols.
    
    This function executes a backtest using parallel processing for
    maximum performance. Results include trades, equity curve, and
    backtest parameters.
    
    Args:
        date_from: Start date in YYYY-MM-DD format.
        date_to: End date in YYYY-MM-DD format.
        progress_callback: Optional callback for progress messages.
        
    Returns:
        Tuple of (trades, equity_curve, params):
        - trades: List of executed trade dictionaries
        - equity_curve: Equity curve as list or DataFrame
        - params: Backtest parameters and configuration
        
    Raises:
        ValueError: If date range is invalid or dates are in wrong order.
        TimeoutError: If backtest exceeds MAX_BACKTEST_SECONDS.
        
    Example:
        >>> trades, equity, params = run_backtest(
        ...     date_from="2025-01-01",
        ...     date_to="2025-12-31"
        ... )
        >>> print(f"Executed {len(trades)} trades")
        
    Note:
        Performance targets (enforced):
        - 11 symbols: ~15-20 seconds (parallel)
        - Single symbol: <2 seconds
        - Timeout: 60 seconds absolute maximum
    """
```

---

## Testing Guidelines

### Test Structure

```python
# tests/test_module_name.py
import pytest
from egx_radar.module import ClassName

@pytest.mark.unit
class TestClassName:
    """Test ClassName functionality."""
    
    def test_initialization(self):
        """Test object initialization."""
        obj = ClassName()
        assert obj is not None
    
    def test_method_with_valid_input(self, sample_data):
        """Test method with valid input."""
        result = obj.method(sample_data)
        assert result is not None
    
    def test_method_with_invalid_input(self):
        """Test method with invalid input."""
        with pytest.raises(ValueError):
            obj.method(None)
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_unit_engine.py -v

# Run specific test class
pytest tests/test_unit_engine.py::TestBacktestEngine -v

# Run specific test method
pytest tests/test_unit_engine.py::TestBacktestEngine::test_run -v

# Run with markers
pytest tests/ -m unit -v
pytest tests/ -m integration -v
pytest tests/ -m performance -v

# Run with coverage
pytest tests/ --cov=egx_radar --cov-report=html --cov-report=term

# Run with specific Python version
python3.10 -m pytest tests/ -v

# Parallel execution (faster)
pytest tests/ -n auto -v
```

### Coverage Targets

| Module | Target | Current |
|--------|--------|---------|
| backtest/engine | 90% | ✅ |
| backtest/metrics | 85% | ✅ |
| core/guards | 85% | ✅ |
| data_validator | 80% | ✅ |
| error_handler | 85% | ✅ |

---

## Git Workflow

### Branch Strategy

```
main (production)
  ├── develop (integration)
  │   ├── feature/add-new-guard
  │   ├── feature/optimize-engine
  │   ├── bugfix/fix-timeout-issue
  │   └── hotfix/urgent-fix
  └── release-0.9.0
```

### Commit Guidelines

```bash
# Feature branch
git checkout -b feature/feature-name develop

# Make changes and commit
git commit -m "feat: Add new feature description"
# Types: feat, fix, docs, style, test, chore, perf, refactor

# Keep commits atomic and focused
git add file1.py file2.py
git commit -m "feat: Implement new feature"

git add test_file.py
git commit -m "test: Add tests for feature"

# Push to remote
git push origin feature/feature-name

# Create pull request
# Fill PR template with:
# - Description
# - Motivation
# - Type of change
# - Testing done
# - Checklist
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>

# Example:
feat(backtest): Optimize parallel processing

Implement worker pool chunking to improve
backtest performance. Reduces suite time from
60s to 15-20s for 11 symbols.

Closes #123
Breaking-change: Requires Python 3.8+
```

### Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Type hints added
- [ ] Docstrings updated
- [ ] Code formatted (`black`, `isort`)
- [ ] No linting issues (`flake8`)
- [ ] Performance targets met
- [ ] New tests added (if applicable)
- [ ] Documentation updated (if applicable)
- [ ] No breaking changes
- [ ] Changelog updated

---

## Architecture Deep Dive

### Execution Flow

```
[Data Input from yfinance]
         ↓
    [DataGuard]      ← Validates OHLCV data quality
         ↓
  [MomentumGuard]    ← Confirms signal + momentum
         ↓
  [AlphaMonitor]     ← Checks risk metrics
         ↓
[PositionManager]    ← Calculates position size
         ↓
   [Trade Signal]    ← Buy/Hold/Sell decision
         ↓
[Backtest Engine]    ← Execute trades (parallel)
         ↓
  [Metrics Engine]   ← Calculate performance
         ↓
   [CSV Export]      ← Save results
```

### Multiprocessing Architecture

```
Main Process
    ├── Symbol List: [SYM1, SYM2, ..., SYM11]
    │
    ├── Worker 1: [Chunk1: SYM1, SYM2]
    │   └─ run_backtest(SYM1)
    │   └─ run_backtest(SYM2)
    │
    ├── Worker 2: [Chunk2: SYM3, SYM4]
    │   └─ run_backtest(SYM3)
    │   └─ run_backtest(SYM4)
    │
    ├── Worker 3: [Chunk3: SYM5, SYM6]
    │   └─ run_backtest(SYM5)
    │   └─ run_backtest(SYM6)
    │
    └── Worker 4: [Chunk4: SYM7-11]
        └─ run_backtest(SYM7-11)
        
Results Aggregation → Final Report
```

### Error Handling Flow

```
[Exception Occurs]
        ↓
[ErrorHandler.handle_error()]
        ↓
[Log Error + Get Severity]
        ↓
[Is Recovery Available?]
    ├─ YES → [ApplyRecoveryStrategy]
    │         ├─ skip_symbol()
    │         ├─ reduce_date_range()
    │         ├─ fallback_to_sequential()
    │         └─ clear_cache()
    │
    └─ NO → [Propagate Error + Alert]
```

---

## Adding Features

### Example: Adding a New Guard

```python
# 1. Create file: egx_radar/core/new_guard.py
from typing import Dict, Union
import pandas as pd

class NewGuard:
    """Description of new guard functionality."""
    
    def __init__(self):
        """Initialize guard."""
        self.name = "NewGuard"
    
    def evaluate(self, df: pd.DataFrame) -> bool:
        """Evaluate trading signal.
        
        Args:
            df: OHLCV data
            
        Returns:
            True if signal passes guard, False otherwise
        """
        # Implementation here
        return True


# 2. Create tests: tests/test_new_guard.py
import pytest
from egx_radar.core.new_guard import NewGuard

@pytest.mark.unit
class TestNewGuard:
    def test_initialization(self):
        guard = NewGuard()
        assert guard.name == "NewGuard"
    
    def test_evaluate(self, sample_data):
        guard = NewGuard()
        result = guard.evaluate(sample_data)
        assert isinstance(result, bool)


# 3. Update configuration if needed
# egx_radar/config/settings.py
NEW_GUARD_ENABLED = True
NEW_GUARD_PARAM_1 = 50


# 4. Integrate into backtest engine
# egx_radar/backtest/engine.py
from egx_radar.core.new_guard import NewGuard

def run_backtest(...):
    new_guard = NewGuard()
    
    for each_signal:
        if not new_guard.evaluate(df):
            continue  # Skip signal that fails guard
        
        # Process signal
        ...


# 5. Update documentation
# README.md, API_DOCUMENTATION.md
```

### Example: Adding a Performance Optimization

```python
# 1. Identify bottleneck
# Use: cProfile, line_profiler, timeit

import cProfile
import pstats

cProfile.run('run_backtest(...)', 'output.prof')
stats = pstats.Stats('output.prof')
stats.sort_stats('cumulative')
stats.print_stats(20)


# 2. Optimize code
# Before:
for i in range(len(df)):
    if df.iloc[i]['High'] > threshold:
        process_bar(df.iloc[i])

# After (vectorized):
mask = df['High'] > threshold
processed = df[mask].apply(process_bar, axis=1)


# 3. Measure improvement
import time

start = time.time()
result = optimized_function()
elapsed = time.time() - start

print(f"Optimized: {elapsed:.2f}s")  # Should be faster


# 4. Add performance test
@pytest.mark.performance
def test_optimization_speedup():
    start = time.time()
    result = run_backtest(...)
    elapsed = time.time() - start
    
    # Target: < 20 seconds
    assert elapsed < 20, f"Expected <20s, got {elapsed:.2f}s"
```

---

## Performance Optimization

### Profiling Tools

```bash
# CPU profiling
python -m cProfile -s cumulative -m egx_radar > profile.txt

# Memory profiling
pip install memory-profiler
python -m memory_profiler run_script.py

# Line profiling
pip install line-profiler
kernprof -l -v run_script.py

# Timing specific functions
python -m timeit -s 'from module import func' 'func()'
```

### Optimization Checklist

- [ ] Use vectorized NumPy/Pandas operations (not loops)
- [ ] Use multiprocessing for CPU-bound tasks
- [ ] Cache results of expensive calculations
- [ ] Minimize data copies (use views instead)
- [ ] Use appropriate data types (int vs float)
- [ ] Profile before optimizing
- [ ] Measure improvement after optimization
- [ ] Add performance tests to prevent regression

---

## Documentation

### Updating Documentation

1. **README.md** - High-level overview
2. **INSTALLATION.md** - Setup instructions
3. **API_DOCUMENTATION.md** - API reference
4. **DEPLOYMENT.md** - Production deployment
5. **DEVELOPMENT.md** - This file
6. **Code Docstrings** - In-code documentation

### Markdown Style

```markdown
# Main Heading (H1)
## Section (H2)
### Subsection (H3)

**Bold** for important terms
`code` for inline code
[Link text](url) for links

- Bullet points
- For lists

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

\`\`\`python
# Code blocks
def example():
    pass
\`\`\`

> Block quotes for important info
```

---

## Common Tasks

### Running Full CI/CD Locally

```bash
#!/bin/bash
set -e

echo "1. Testing..."
pytest tests/ -v

echo "2. Linting..."
flake8 egx_radar tests

echo "3. Formatting check..."
black --check egx_radar tests

echo "4. Import sorting check..."
isort --check egx_radar tests

echo "5. Building..."
python -m build

echo "✓ All checks passed!"
```

### Creating a Release

```bash
# 1. Create release branch
git checkout -b release-0.9.0 develop

# 2. Update version
# In: setup.py, pyproject.toml, __init__.py
VERSION = "0.9.0"

# 3. Update CHANGELOG
# Add release notes

# 4. Commit
git commit -m "chore: Release v0.9.0"

# 5. Create tag
git tag -a v0.9.0 -m "Version 0.9.0"

# 6. Merge to main
git checkout main
git merge release-0.9.0

# 7. Push
git push origin main develop --tags

# 8. Create GitHub Release with changelog
```

---

## Resources

- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/) - Style guide
- [pytest Documentation](https://docs.pytest.org/) - Testing framework
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) - Docstring format
- [Real Python](https://realpython.com/) - Python tutorials
- [Pandas Documentation](https://pandas.pydata.org/) - Data frames

---

**Last Updated:** March 16, 2026  
**Version:** EGX Radar 0.8.3  
[Back to README](README.md)
