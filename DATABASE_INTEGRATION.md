# Database Integration Guide

## Overview

EGX Radar includes a comprehensive database layer for persistent storage of backtest results, trades, signals, and performance metrics. This enables:

- **Historical analysis** of backtests and trades
- **Performance tracking** over time
- **Signal accuracy monitoring** across multiple backtests
- **Strategy comparison** with per-symbol metrics
- **Data export** to JSON and CSV formats

## Supported Databases

### SQLite (Development/Testing)
Perfect for local development and testing:
```python
from egx_radar.database import DatabaseManager

# In-memory (testing)
db = DatabaseManager('sqlite:///:memory:')

# File-based (development)
db = DatabaseManager('sqlite:///egx_radar.db')
```

### PostgreSQL (Production)
Recommended for production deployments:
```python
db = DatabaseManager(
    'postgresql://user:password@localhost:5432/egx_radar'
)
```

## Database Schema

### BacktestResult
Main table storing overall backtest performance:
- `backtest_id`: Unique identifier for each backtest
- `start_date`, `end_date`: Backtest period
- `symbols`: Comma-separated list of tested symbols
- Performance metrics: `total_trades`, `win_rate`, `sharpe_ratio`, etc.
- `parameters`: JSON of configuration used
- Relationships: `trades`, `signals`, `metrics`

### Trade
Individual trades executed during backtest:
- Entry/exit details: dates, prices, signals
- P&L tracking: `pnl`, `pnl_pct`, result
- Duration and exit reason
- Foreign key to `BacktestResult`

### Signal
Trading signals generated during backtest:
- Signal type: `buy`, `sell`, `strong_buy`, `strong_sell`
- Strength (0-100 confidence)
- Indicator information and source
- Trade outcome tracking

### StrategyMetrics
Per-symbol performance summary:
- Win rate, average win/loss
- Maximum drawdown and Sharpe ratio
- Recommendation and confidence
- Unique constraint: (backtest_id, symbol)

### EquityHistory
Daily equity curve tracking:
- Daily P&L and returns
- Cumulative returns and drawdown
- Used for risk analysis and equity curve visualization

## Usage Examples

### Basic Setup

```python
from egx_radar.database import DatabaseManager
from egx_radar.database.config import DatabaseConfig

# Initialize database
db = DatabaseManager()
db.init_db()  # Create tables

# Or with specific configuration
db = DatabaseManager(
    database_url=DatabaseConfig.get_production_url()
)
```

### Saving Backtest Results

```python
# After running a backtest
backtest = db.save_backtest(
    backtest_id='BT_2026-03-16_v083',
    start_date=start_date,
    end_date=end_date,
    symbols=['CAIB', 'EBANK', 'ETELECOM'],
    metrics={
        'total_trades': 42,
        'winning_trades': 28,
        'losing_trades': 14,
        'win_rate': 0.667,
        'total_pnl': 5250.50,
        'profit_factor': 2.15,
        'sharpe_ratio': 1.85,
        'max_drawdown': -0.12,
    },
    parameters={
        'workers': 4,
        'chunk_size': 2,
        'strategy_version': '0.8.3',
    }
)
```

### Recording Trades

```python
# For each trade in the backtest
trade = db.save_trade(
    backtest_id=backtest.id,
    symbol='CAIB',
    entry_date=entry_date,
    entry_price=25.50,
    entry_signal='buy',
    quantity=100,
    exit_date=exit_date,
    exit_price=26.75,
    exit_reason='take_profit',
    pnl=125.00,
    pnl_pct=0.0490
)
```

### Recording Signals

```python
# For each signal generated
signal = db.save_signal(
    backtest_id=backtest.id,
    symbol='EBANK',
    signal_date=signal_datetime,
    signal_type='strong_buy',
    strength=78,
    momentum=0.45,
    trend='uptrend',
    volatility=0.15,
    volume_ratio=1.8,
    indicators=['RSI', 'MACD', 'Volume_Profile'],
    source='DataGuard',
    trade_taken=True
)
```

### Querying Results

```python
# Get recent backtests
backtests = db.get_backtests(limit=10, days=30)

# Get trades for a specific backtest
trades = db.get_trades(backtest.id, symbol='CAIB')

# Filter by result
winning_trades = db.get_trades(backtest.id, result='win')

# Get performance statistics
summary = db.get_summary_stats(days=30)
print(f"Total trades: {summary['total_trades']}")
print(f"Average win rate: {summary['avg_win_rate']:.2%}")

# Get per-symbol performance
performance = db.get_symbol_performance('CAIB', days=90)
print(f"CAIB recommendation: {performance['recommendation']}")
print(f"CAIB average return: {performance['avg_return']:.2%}")
```

### Data Management

```python
# Clean up old data (older than 6 months)
deleted_count = db.cleanup_old_data(days=180)

# Export backtest to JSON
from egx_radar.database.utils import export_backtest_to_json
export_backtest_to_json(db, backtest.id, 'backtest_export.json')

# Generate performance report
from egx_radar.database.utils import generate_performance_report
report = generate_performance_report(db, days=30, output_file='report.json')
```

## Integration with Backtesting Engine

The database module integrates seamlessly with EGX Radar's backtesting engine:

```python
from egx_radar.backtest import run_backtest
from egx_radar.database import DatabaseManager

# Initialize database
db = DatabaseManager()
db.init_db()

# Run backtest
results = run_backtest(
    symbols=['CAIB', 'EBANK'],
    start_date='2024-01-01',
    end_date='2025-12-31'
)

# Save results to database
backtest = db.save_backtest(
    backtest_id=results['backtest_id'],
    start_date=results['start_date'],
    end_date=results['end_date'],
    symbols=results['symbols'],
    metrics=results['metrics'],
    parameters=results['parameters']
)

# Save individual trades
for trade_data in results['trades']:
    db.save_trade(
        backtest_id=backtest.id,
        **trade_data
    )
```

## Environment Configuration

Set up database for different environments:

### Development (SQLite)
```bash
export DATABASE_URL=sqlite:///egx_radar.db
```

### Production (PostgreSQL)
```bash
export DATABASE_URL=postgresql://user:password@db.example.com:5432/egx_radar

# Or use individual variables:
export DB_TYPE=postgresql
export DB_HOST=db.example.com
export DB_PORT=5432
export DB_NAME=egx_radar
export DB_USER=app_user
export DB_PASSWORD=secure_password
```

## Database Migrations

Alembic is configured for managing schema migrations:

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "Add equity_history table"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic current
alembic history
```

## Performance Optimization

### Indexes
The schema includes strategic indexes on:
- `backtest_results.backtest_date` - for time-range queries
- `trades.backtest_id`, `.symbol`, `.entry_date` - for filtering
- `signals.backtest_id`, `.symbol`, `.signal_date` - for signal lookups

### Connection Pooling
- SQLite: StaticPool for concurrent access
- PostgreSQL: 3600s recycle time, connection verification

### Query Optimization
```python
# Use get_sessions context manager for transactions
with db.get_session() as session:
    # Auto-commits on success, rolls back on error
    trades = db.get_trades(backtest_id)
```

## API Reference

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference including:
- `DatabaseManager` class and methods
- Model definitions and relationships
- Query utilities and aggregations
- Data import/export functions
