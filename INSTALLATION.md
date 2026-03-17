# Installation Guide — EGX Radar

> Detailed installation and setup instructions for all operating systems

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Methods](#installation-methods)
3. [Virtual Environment Setup](#virtual-environment-setup)
4. [Dependency Installation](#dependency-installation)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Development Installation](#development-installation)

---

## System Requirements

### Minimum Requirements

- **Python**: 3.8, 3.9, 3.10, or 3.11
- **RAM**: 2 GB (4+ GB recommended for backtesting)
- **Disk**: 500 MB for installation + data
- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)

### Tested Configurations

| OS | Python | Status |
|----|--------|--------|
| Windows 10/11 | 3.8 - 3.11 | ✅ Verified |
| macOS 11+ | 3.8 - 3.11 | ✅ Verified |
| Ubuntu 18.04+ | 3.8 - 3.11 | ✅ Verified |
| CentOS 7+ | 3.8 - 3.11 | ✅ Verified |

### Required Software

- **Git**: For cloning repository
- **pip**: Python package manager (included with Python 3.4+)
- **Visual C++ Build Tools** (Windows only): For compiling C extensions

---

## Installation Methods

### Method 1: Pip Install (Recommended)

```bash
# Install directly from GitHub
pip install git+https://github.com/yourusername/egx-radar.git

# Verify installation
python -m egx_radar --version
```

### Method 2: Clone & Install from Source

```bash
# Clone repository
git clone https://github.com/yourusername/egx-radar.git
cd egx-radar

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install package in development mode
pip install -e .

# Verify installation
python -m egx_radar --version
```

### Method 3: Docker

```bash
# Build Docker image
docker build -t egx-radar:latest .

# Run container
docker run -it egx-radar:latest bash

# Test inside container
python -m egx_radar --help
```

---

## Virtual Environment Setup

### Why Virtual Environments?

Virtual environments isolate project dependencies from your system Python, preventing conflicts.

### Step-by-Step Setup

**Step 1: Create Virtual Environment**

```bash
# Navigate to project directory
cd egx-radar

# Create .venv directory
python -m venv .venv
```

**Step 2: Activate Virtual Environment**

```bash
# On Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# On Windows (CMD)
.venv\Scripts\activate.bat

# On macOS/Linux
source .venv/bin/activate
```

You should see `(.venv)` prefix in your terminal.

**Step 3: Upgrade pip, setuptools, wheel**

```bash
python -m pip install --upgrade pip setuptools wheel
```

**Step 4: Verify Activation**

```bash
which python  # On macOS/Linux
# Or on Windows:
where python

# Should show path inside .venv directory
```

---

## Dependency Installation

### Core Dependencies

```bash
# From requirements.txt (recommended)
pip install -r requirements.txt

# Or manually
pip install pandas>=2.0,<3.0
pip install numpy>=1.24,<2.0
pip install yfinance>=0.2.40,<0.3
pip install pandas_ta>=0.3.14b0
pip install requests>=2.31,<3.0
```

### Optional Dependencies (Development)

```bash
# Testing framework
pip install pytest>=7.0
pip install pytest-cov>=4.0
pip install pytest-mock>=3.10

# Code quality
pip install black>=23.0
pip install flake8>=5.0
pip install isort>=5.0

# Documentation
pip install sphinx>=5.0
pip install sphinx-rtd-theme>=1.0
```

### Dependency Compatibility Notes

| Package | Version | Notes |
|---------|---------|-------|
| pandas | 2.0+ | Requires NumPy 1.24+; older versions may have issues |
| numpy | 1.24-1.26 | Must match pandas version; 2.0 incompatible yet |
| yfinance | 0.2.40+ | Earlier versions have data stability issues |
| pandas_ta | 0.3.14+ | Known thread-safety issues in <0.3.14; always set SCAN_MAX_WORKERS=1 after upgrade |

---

## Verification

### Quick Verification

```bash
# Check Python version
python --version
# Expected: Python 3.8+ or higher

# Check installation
python -c "import egx_radar; print(egx_radar.__version__)"

# Run import test
python -m egx_radar --version
```

### Full Verification Suite

```bash
# Run all verification tests
python -m pytest tests/test_unit_engine.py -v

# Check specific components
python -c "from egx_radar.backtest.engine import run_backtest; print('✓ Engine OK')"
python -c "from egx_radar.config.settings import K; print('✓ Settings OK')"
python -c "from egx_radar.data_validator import DataValidator; print('✓ Validator OK')"
python -c "from egx_radar.error_handler import ErrorHandler; print('✓ Error Handler OK')"
```

### Expected Output

```
Python 3.10.6 (or similar)
EGX Radar v0.8.3
✓ Engine OK
✓ Settings OK
✓ Validator OK
✓ Error Handler OK
```

---

## Troubleshooting

### Common Issues

#### Issue: `ModuleNotFoundError: No module named 'egx_radar'`

**Solution:**
```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
# or
.\.venv\Scripts\activate   # Windows

# Reinstall in development mode
pip install -e .
```

#### Issue: `ImportError: No module named 'pandas_ta'`

**Solution:**
```bash
# pandas_ta may not install correctly on some systems
pip install --no-cache-dir pandas_ta>=0.3.14b0

# If still failing, try:
pip uninstall pandas_ta -y
pip install pandas-ta>=0.3.14b0  # Note: pandas-ta (with hyphen)
```

#### Issue: `numpy` version conflicts

**Solution:**
```bash
# Clear cache and reinstall
pip cache purge
pip install --upgrade --force-reinstall numpy==1.24.3
pip install --upgrade --force-reinstall pandas==2.0.3
```

#### Issue: Permission denied on Linux/macOS

**Solution:**
```bash
# Use --user flag
pip install --user -r requirements.txt

# Or use sudo (not recommended)
sudo pip install -r requirements.txt

# Better: Use virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Issue: `yfinance` SSL certificate errors

**Solution:**
```bash
# Update certificates on macOS
/Applications/Python\ 3.x/Install\ Certificates.command

# On Linux/Windows, upgrade requests
pip install --upgrade certifi

# Test connection
python -c "import yfinance as yf; print(yf.download('AAPL', period='1d'))"
```

#### Issue: Tests fail with `pytest` not found

**Solution:**
```bash
# Install testing dependencies
pip install pytest>=7.0 pytest-cov>=4.0

# Run tests
pytest tests/ -v
```

### Diagnostic Commands

```bash
# Show installed packages and versions
pip list | grep egx-radar

# Check virtual environment
python -m site

# Verify imports work
python -c "import sys; print(sys.path)"

# Test specific module
python -c "from egx_radar.backtest.engine import run_backtest; print(run_backtest.__doc__)"
```

---

## Development Installation

For developers who want to contribute:

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/egx-radar.git
cd egx-radar

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=egx_radar --cov-report=html

# Run specific test file
pytest tests/test_unit_engine.py -v

# Run with markers
pytest tests/ -m unit -v
pytest tests/ -m integration -v
pytest tests/ -m performance -v
```

### Code Quality

```bash
# Format code with black
black egx_radar tests

# Sort imports with isort
isort egx_radar tests

# Lint with flake8
flake8 egx_radar tests

# All in one
black egx_radar tests && isort egx_radar tests && flake8 egx_radar tests
```

### Building Documentation

```bash
# Generate HTML documentation
cd docs
make html

# View in browser
open _build/html/index.html  # macOS
# or xdg-open on Linux, start on Windows
```

---

## Post-Installation Steps

### 1. Configure Settings

Edit `egx_radar/config/settings.py` to customize:

```python
# Number of parallel workers
WORKERS_COUNT = 4

# Backtest symbols
BT_SYMBOLS = ['HRHO', 'ORHD', 'TMGH', ...]

# Performance profile
PERFORMANCE_PROFILE = "optimized"
```

### 2. Verify Sample Backtest

```bash
# Run included sample
python _run_single_bt.py

# Expected output: CSV file with trade results
```

### 3. Run the UI (Optional)

```bash
# Launch interactive interface
python -m egx_radar
```

### 4. Run Tests

```bash
# Run full test suite
pytest tests/ -v

# Should see: passed in X.XXs
```

---

## Advanced Configuration

### Environment Variables

```bash
# Set before running
export EGX_RADAR_WORKERS=4
export EGX_RADAR_TIMEOUT=60
export EGX_RADAR_VERBOSE=1

# Or in code
import os
os.environ['EGX_RADAR_WORKERS'] = '4'
```

### Using Different Python Versions

```bash
# Create venv with specific Python version
python3.10 -m venv .venv_py310
source .venv_py310/bin/activate

# Install for that version
pip install -r requirements.txt
```

### Poetry Installation (Alternative)

```bash
# If you prefer Poetry over pip
poetry install
poetry run python -m egx_radar
```

---

## Next Steps

Once installation is complete:

1. **Read the README**: Overview of features and architecture
2. **Check Examples**: See `examples/` directory for sample code
3. **Review Settings**: Customize `egx_radar/config/settings.py`
4. **Run Tests**: Execute `pytest tests/ -v` to verify setup
5. **Review API Docs**: Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
6. **Explore Code**: Start with `egx_radar/__main__.py`

---

## Getting Help

- **Installation Issues**: Check [Troubleshooting](#troubleshooting) section
- **API Questions**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **GitHub Issues**: Report bugs or ask questions
- **Documentation**: Read [README.md](README.md) and [DEVELOPMENT.md](DEVELOPMENT.md)

---

**Last Updated:** March 16, 2026  
**Version:** EGX Radar 0.8.3
