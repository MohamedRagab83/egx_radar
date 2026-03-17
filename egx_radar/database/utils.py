"""Database utilities and initialization functions."""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from egx_radar.database.manager import DatabaseManager
from egx_radar.database.config import DatabaseConfig
from egx_radar.database.models import BacktestResult


def init_database(database_url: str = None) -> DatabaseManager:
    """
    Initialize database with tables.
    
    Args:
        database_url: Connection URL (uses env or default if None)
    
    Returns:
        DatabaseManager instance
    """
    db_url = database_url or DatabaseConfig.get_url()
    manager = DatabaseManager(database_url=db_url)
    manager.init_db()
    return manager


def import_backtest_from_csv(
    manager: DatabaseManager,
    csv_file: str,
    backtest_id: str,
    start_date: datetime,
    end_date: datetime,
    symbols: List[str],
    metrics: Dict[str, Any]
) -> BacktestResult:
    """
    Import backtest results from CSV file.
    
    Args:
        manager: DatabaseManager instance
        csv_file: Path to backtest CSV file
        backtest_id: Unique backtest identifier
        start_date: Backtest start date
        end_date: Backtest end date
        symbols: List of symbols backtested
        metrics: Performance metrics
    
    Returns:
        BacktestResult object
    """
    import pandas as pd
    
    # Read trades from CSV
    trades_df = pd.read_csv(csv_file)
    
    # Save backtest
    backtest = manager.save_backtest(
        backtest_id=backtest_id,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        metrics=metrics,
        parameters={
            'imported_from': csv_file,
            'import_date': datetime.utcnow().isoformat(),
        }
    )
    
    # Save individual trades
    for _, row in trades_df.iterrows():
        manager.save_trade(
            backtest_id=backtest.id,
            symbol=row['Symbol'],
            entry_date=pd.to_datetime(row['Entry Date']),
            entry_price=float(row['Entry Price']),
            entry_signal=row.get('Entry Signal', 'buy'),
            quantity=int(row.get('Quantity', 1)),
            exit_date=pd.to_datetime(row['Exit Date']) if 'Exit Date' in row else None,
            exit_price=float(row['Exit Price']) if 'Exit Price' in row else None,
            exit_reason=row.get('Exit Reason'),
            pnl=float(row['PnL']) if 'PnL' in row else None,
            pnl_pct=float(row['PnL %']) if 'PnL %' in row else None,
        )
    
    return backtest


def export_backtest_to_json(
    manager: DatabaseManager,
    backtest_id: int,
    output_file: str
) -> None:
    """
    Export backtest results to JSON.
    
    Args:
        manager: DatabaseManager instance
        backtest_id: Backtest ID to export
        output_file: Path to output JSON file
    """
    backtest = manager.get_backtest(backtest_id)
    if not backtest:
        raise ValueError(f'Backtest {backtest_id} not found')
    
    trades = manager.get_trades(backtest_id)
    signals = manager.get_signals(backtest_id)
    
    data = {
        'backtest': {
            'id': backtest.id,
            'backtest_id': backtest.backtest_id,
            'date': backtest.backtest_date.isoformat(),
            'start_date': backtest.start_date.isoformat(),
            'end_date': backtest.end_date.isoformat(),
            'symbols': backtest.symbols.split(','),
            'metrics': {
                'total_trades': backtest.total_trades,
                'winning_trades': backtest.winning_trades,
                'losing_trades': backtest.losing_trades,
                'win_rate': backtest.win_rate,
                'total_pnl': float(backtest.total_pnl),
                'profit_factor': backtest.profit_factor,
                'max_drawdown': backtest.max_drawdown,
                'max_drawdown_pct': backtest.max_drawdown_pct,
                'sharpe_ratio': backtest.sharpe_ratio,
                'sortino_ratio': backtest.sortino_ratio,
                'steadiness': backtest.calmar_ratio,
            },
            'execution': {
                'execution_time_seconds': backtest.execution_time_seconds,
                'workers_used': backtest.workers_used,
            },
        },
        'trades': [
            {
                'symbol': t.symbol,
                'entry_date': t.entry_date.isoformat(),
                'entry_price': float(t.entry_price),
                'entry_signal': t.entry_signal,
                'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                'exit_price': float(t.exit_price) if t.exit_price else None,
                'exit_reason': t.exit_reason,
                'quantity': t.quantity,
                'result': t.result,
                'pnl': float(t.pnl) if t.pnl else None,
                'pnl_pct': t.pnl_pct,
                'duration_minutes': t.duration_minutes,
            }
            for t in trades
        ],
        'signals': [
            {
                'symbol': s.symbol,
                'date': s.signal_date.isoformat(),
                'type': s.signal_type,
                'strength': s.strength,
                'trend': s.trend,
                'volatility': s.volatility,
                'trade_taken': s.trade_taken,
            }
            for s in signals
        ],
    }
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def generate_performance_report(
    manager: DatabaseManager,
    days: int = 30,
    output_file: str = None
) -> Dict[str, Any]:
    """
    Generate comprehensive performance report.
    
    Args:
        manager: DatabaseManager instance
        days: Number of days to include
        output_file: Optional file to save report
    
    Returns:
        Report dictionary
    """
    summary = manager.get_summary_stats(days=days)
    
    with manager.get_session() as session:
        backtests = session.query(BacktestResult).limit(100).all()
        top_symbols = {}
        
        for backtest in backtests:
            for symbol in backtest.symbols.split(','):
                if symbol not in top_symbols:
                    top_symbols[symbol] = manager.get_symbol_performance(symbol, days=days)
    
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'period_days': days,
        'summary': summary,
        'top_performers': sorted(
            top_symbols.items(),
            key=lambda x: x[1].get('avg_win_rate', 0),
            reverse=True
        )[:10],
    }
    
    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
    
    return report
