"""Phase 6B: Database Integration verification script.

This script verifies that the database integration is working correctly
by creating tables, inserting sample data, and running queries.
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

from egx_radar.database import DatabaseManager
from egx_radar.database.config import DatabaseConfig
from egx_radar.database.utils import generate_performance_report


def verify_database_integration():
    """Verify database module is functional."""
    
    print("=" * 80)
    print("PHASE 6B: DATABASE INTEGRATION VERIFICATION")
    print("=" * 80)
    
    # Test 1: Connection
    print("\n✓ Testing database connection...")
    try:
        db = DatabaseManager(database_url=DatabaseConfig.get_testing_url())
        print("  ✓ Database manager created successfully")
    except Exception as e:
        print(f"  ✗ Failed to create database manager: {e}")
        return False
    
    # Test 2: Table creation
    print("\n✓ Testing table creation...")
    try:
        db.init_db()
        print("  ✓ All tables created successfully")
        print("    Tables: BacktestResult, Trade, Signal, StrategyMetrics, EquityHistory")
    except Exception as e:
        print(f"  ✗ Failed to create tables: {e}")
        return False
    
    # Test 3: Insert backtest
    print("\n✓ Testing backtest insertion...")
    try:
        now = datetime.utcnow()
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        bt_id_str = f'TEST_BT_{now.strftime("%Y%m%d_%H%M%S")}_{unique_id}'
        backtest_id = db.save_backtest(
            backtest_id=bt_id_str,
            start_date=now - timedelta(days=365),
            end_date=now,
            symbols=['CAIB', 'EBANK', 'ETELECOM'],
            metrics={
                'total_trades': 42,
                'winning_trades': 28,
                'losing_trades': 14,
                'win_rate': 0.667,
                'total_pnl': 5250.50,
                'gross_profit': 7500.00,
                'gross_loss': 2250.00,
                'profit_factor': 2.15,
                'max_drawdown': -0.12,
                'max_drawdown_pct': -12.0,
                'sharpe_ratio': 1.85,
                'sortino_ratio': 2.15,
                'calmar_ratio': 1.25,
                'avg_trade_return': 0.0375,
                'std_dev_returns': 0.0225,
                'expectancy': 125.00,
                'recovery_factor': 2.33,
                'execution_time_seconds': 18.5,
                'workers_used': 4,
                'status': 'completed',
            },
            parameters={
                'workers': 4,
                'chunk_size': 2,
                'strategy_version': '0.8.3',
                'test': True,
            }
        )
        backtest = db.get_backtest(backtest_id)
        print(f"  ✓ Backtest saved: {backtest.backtest_id}")
        print(f"    Trades: {backtest.total_trades}, Win Rate: {backtest.win_rate:.2%}")
    except Exception as e:
        print(f"  ✗ Failed to save backtest: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Insert trades
    print("\n✓ Testing trade insertion...")
    try:
        trade_data = [
            {
                'symbol': 'CAIB',
                'entry_date': now - timedelta(days=180),
                'entry_price': 25.50,
                'entry_signal': 'buy',
                'quantity': 100,
                'exit_date': now - timedelta(days=170),
                'exit_price': 26.75,
                'exit_reason': 'take_profit',
                'pnl': 125.00,
                'pnl_pct': 0.0490,
            },
            {
                'symbol': 'EBANK',
                'entry_date': now - timedelta(days=160),
                'entry_price': 15.25,
                'entry_signal': 'buy',
                'quantity': 200,
                'exit_date': now - timedelta(days=150),
                'exit_price': 14.75,
                'exit_reason': 'stop_loss',
                'pnl': -100.00,
                'pnl_pct': -0.0328,
            },
            {
                'symbol': 'ETELECOM',
                'entry_date': now - timedelta(days=140),
                'entry_price': 30.00,
                'entry_signal': 'strong_buy',
                'quantity': 150,
                'exit_date': now - timedelta(days=130),
                'exit_price': 32.50,
                'exit_reason': 'take_profit',
                'pnl': 375.00,
                'pnl_pct': 0.0833,
            },
        ]
        
        trade_ids = []
        for trade in trade_data:
            trade_id = db.save_trade(
                backtest_id=backtest.id,
                **trade
            )
            trade_ids.append(trade_id)
        
        print(f"  ✓ Saved {len(trade_ids)} trades")
        for trade_id in trade_ids:
            t = db.get_trade(trade_id)
            print(f"    {t.symbol}: {t.result.upper()} - P&L: {t.pnl:,.2f} ({t.pnl_pct:+.2%})")
    except Exception as e:
        print(f"  ✗ Failed to save trades: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Insert signals
    print("\n✓ Testing signal insertion...")
    try:
        signal_data = [
            {
                'symbol': 'CAIB',
                'signal_date': now - timedelta(days=70),
                'signal_type': 'buy',
                'strength': 75,
                'momentum': 0.35,
                'trend': 'uptrend',
                'volatility': 0.18,
                'volume_ratio': 1.5,
                'indicators': ['RSI', 'MACD', 'Volume_Profile'],
                'source': 'DataGuard',
                'trade_taken': True,
            },
            {
                'symbol': 'EBANK',
                'signal_date': now - timedelta(days=60),
                'signal_type': 'strong_sell',
                'strength': 88,
                'momentum': -0.45,
                'trend': 'downtrend',
                'volatility': 0.22,
                'volume_ratio': 2.1,
                'indicators': ['RSI', 'Bollinger_Bands'],
                'source': 'MomentumGuard',
                'trade_taken': False,
            },
        ]
        
        signal_ids = []
        for signal in signal_data:
            s_id = db.save_signal(
                backtest_id=backtest.id,
                **signal
            )
            signal_ids.append(s_id)
        
        print(f"  ✓ Saved {len(signal_ids)} signals")
        for s_id in signal_ids:
            s = db.get_signal(s_id)
            print(f"    {s.symbol}: {s.signal_type} (strength: {s.strength})")
    except Exception as e:
        print(f"  ✗ Failed to save signals: {e}")
        return False
    
    # Test 6: Insert strategy metrics
    print("\n✓ Testing strategy metrics insertion...")
    try:
        metrics_data = {
            'CAIB': {
                'num_trades': 15,
                'winning_trades': 11,
                'losing_trades': 4,
                'win_rate': 0.733,
                'total_return': 0.1850,
                'avg_win': 0.0245,
                'avg_loss': -0.0125,
                'largest_win': 0.0890,
                'largest_loss': -0.0450,
                'max_drawdown': -0.08,
                'sharpe': 2.15,
                'sortino': 2.65,
                'signals_generated': 25,
                'signals_acted': 15,
                'signal_accuracy': 0.6,
                'recommendation': 'buy',
                'confidence': 0.78,
            },
            'EBANK': {
                'num_trades': 14,
                'winning_trades': 10,
                'losing_trades': 4,
                'win_rate': 0.714,
                'total_return': 0.1250,
                'avg_win': 0.0180,
                'avg_loss': -0.0100,
                'largest_win': 0.0650,
                'largest_loss': -0.0380,
                'max_drawdown': -0.10,
                'sharpe': 1.85,
                'sortino': 2.25,
                'signals_generated': 22,
                'signals_acted': 14,
                'signal_accuracy': 0.57,
                'recommendation': 'hold',
                'confidence': 0.65,
            },
            'ETELECOM': {
                'num_trades': 13,
                'winning_trades': 7,
                'losing_trades': 6,
                'win_rate': 0.538,
                'total_return': 0.0850,
                'avg_win': 0.0165,
                'avg_loss': -0.0145,
                'largest_win': 0.0750,
                'largest_loss': -0.0520,
                'max_drawdown': -0.14,
                'sharpe': 1.35,
                'sortino': 1.65,
                'signals_generated': 23,
                'signals_acted': 13,
                'signal_accuracy': 0.54,
                'recommendation': 'hold',
                'confidence': 0.58,
            },
        }
        
        for symbol, metrics in metrics_data.items():
            m_id = db.save_strategy_metrics(backtest.id, symbol, metrics)
            m = db.get_strategy_metrics(m_id)
            print(f"  ✓ {symbol}: {m.num_trades} trades, {m.win_rate:.1%} win rate, {m.recommendation}")
    except Exception as e:
        print(f"  ✗ Failed to save strategy metrics: {e}")
        return False
    
    # Test 7: Query data
    print("\n✓ Testing data queries...")
    try:
        # Get backtest
        bt = db.get_backtest(backtest.id)
        assert bt is not None
        print(f"  ✓ Retrieved backtest: {bt.backtest_id}")
        
        # Get trades
        all_trades = db.get_trades(backtest.id)
        winning = db.get_trades(backtest.id, result='win')
        losing = db.get_trades(backtest.id, result='loss')
        print(f"  ✓ Retrieved trades: {len(all_trades)} total, {len(winning)} wins, {len(losing)} losses")
        
        # Get signals
        all_signals = db.get_signals(backtest.id)
        buy_signals = db.get_signals(backtest.id, signal_type='buy')
        print(f"  ✓ Retrieved signals: {len(all_signals)} total, {len(buy_signals)} buy signals")
        
        # Get summary stats
        summary = db.get_summary_stats(days=30)
        print(f"  ✓ Summary stats: {summary['total_backtests']} backtests, "
              f"{summary['total_trades']} trades, {summary['avg_win_rate']:.1%} avg win rate")
        
        # Get symbol performance
        caib_perf = db.get_symbol_performance('CAIB', days=90)
        print(f"  ✓ CAIB performance: {caib_perf['total_trades']} trades, "
              f"{caib_perf['avg_win_rate']:.1%} win rate, {caib_perf['recommendation']}")
    except Exception as e:
        print(f"  ✗ Failed to query data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 8: Generate report
    print("\n✓ Testing report generation...")
    try:
        report = generate_performance_report(db, days=30)
        print(f"  ✓ Generated performance report")
        print(f"    Period: {report['period_days']} days")
        print(f"    Backtests: {report['summary']['total_backtests']}")
        print(f"    Total trades: {report['summary']['total_trades']}")
        print(f"    Top performers: {len(report['top_performers'])} symbols")
    except Exception as e:
        print(f"  ✗ Failed to generate report: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ PHASE 6B VERIFICATION PASSED")
    print("=" * 80)
    print("\nDatabase Integration Complete:")
    print("  ✅ Connection management (SQLite/PostgreSQL)")
    print("  ✅ Model definitions (5 core tables)")
    print("  ✅ CRUD operations (save/get/query)")
    print("  ✅ Relationship management")
    print("  ✅ Statistical queries")
    print("  ✅ Report generation")
    print("  ✅ Environment configuration")
    print("\nFiles Created:")
    print("  • egx_radar/database/__init__.py")
    print("  • egx_radar/database/models.py")
    print("  • egx_radar/database/manager.py")
    print("  • egx_radar/database/config.py")
    print("  • egx_radar/database/utils.py")
    print("  • egx_radar/database/alembic_env.py")
    print("  • DATABASE_INTEGRATION.md")
    print("\nNext: Phase 6C - Dashboard & Web UI")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    success = verify_database_integration()
    sys.exit(0 if success else 1)
