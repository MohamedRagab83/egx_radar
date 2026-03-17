"""Database manager for EGX Radar - connection management and CRUD operations."""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from egx_radar.database.models import (
    Base, BacktestResult, Trade, Signal, StrategyMetrics, EquityHistory
)


class DatabaseManager:
    """Database connection and operations manager."""
    
    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        """
        Initialize database manager.
        
        Args:
            database_url: Connection string (default: sqlite:///egx_radar.db)
            echo: Enable SQLAlchemy query logging
        """
        if database_url is None:
            database_url = os.environ.get(
                'DATABASE_URL',
                'sqlite:///egx_radar.db'
            )
        
        self.database_url = database_url
        self.echo = echo
        
        # Create engine with appropriate pool configuration
        if database_url.startswith('sqlite'):
            # SQLite: use StaticPool for better concurrent access
            self.engine = create_engine(
                database_url,
                connect_args={'check_same_thread': False},
                poolclass=StaticPool,
                echo=echo
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                database_url,
                echo=echo,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections hourly
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,  # Don't expire objects after commit
            bind=self.engine
        )
    
    def init_db(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_db(self) -> None:
        """Drop all tables (be careful with this)."""
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ==================== BACKTEST RESULTS ====================
    
    def save_backtest(
        self,
        backtest_id: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        metrics: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> int:
        """
        Save backtest result to database.
        
        Args:
            backtest_id: Unique backtest identifier
            start_date: Backtest start date
            end_date: Backtest end date
            symbols: List of symbols tested
            metrics: Performance metrics dict
            parameters: Configuration parameters used
        
        Returns:
            Backtest ID (use with get_backtest() to retrieve full object)
        """
        backtest = BacktestResult(
            backtest_id=backtest_id,
            backtest_date=datetime.utcnow(),
            start_date=start_date,
            end_date=end_date,
            symbols=','.join(symbols),
            symbol_count=len(symbols),
            
            total_trades=metrics.get('total_trades', 0),
            winning_trades=metrics.get('winning_trades', 0),
            losing_trades=metrics.get('losing_trades', 0),
            win_rate=metrics.get('win_rate', 0.0),
            
            total_pnl=metrics.get('total_pnl', 0),
            gross_profit=metrics.get('gross_profit', 0),
            gross_loss=metrics.get('gross_loss', 0),
            profit_factor=metrics.get('profit_factor', 0.0),
            
            max_drawdown=metrics.get('max_drawdown', 0.0),
            max_drawdown_pct=metrics.get('max_drawdown_pct', 0.0),
            sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
            sortino_ratio=metrics.get('sortino_ratio', 0.0),
            calmar_ratio=metrics.get('calmar_ratio', 0.0),
            
            avg_trade_return=metrics.get('avg_trade_return', 0.0),
            std_dev_returns=metrics.get('std_dev_returns', 0.0),
            expectancy=metrics.get('expectancy', 0.0),
            recovery_factor=metrics.get('recovery_factor', 0.0),
            
            execution_time_seconds=metrics.get('execution_time_seconds'),
            workers_used=metrics.get('workers_used', 1),
            status=metrics.get('status', 'completed'),
            notes=metrics.get('notes'),
            parameters=parameters,
        )
        
        with self.get_session() as session:
            session.add(backtest)
            session.flush()
            backtest_id_result = backtest.id
        
        return backtest_id_result
    
    def get_backtest(self, backtest_id: int) -> Optional[BacktestResult]:
        """Get backtest by ID."""
        with self.get_session() as session:
            return session.query(BacktestResult).filter(
                BacktestResult.id == backtest_id
            ).first()
    
    def get_backtests(
        self,
        limit: int = 100,
        offset: int = 0,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = None
    ) -> List[BacktestResult]:
        """
        Get backtests with optional filtering.
        
        Args:
            limit: Number of results to return
            offset: Number of results to skip
            symbol: Filter by symbol
            status: Filter by status
            days: Filter by last N days
        
        Returns:
            List of BacktestResult objects
        """
        with self.get_session() as session:
            query = session.query(BacktestResult)
            
            if symbol:
                query = query.filter(BacktestResult.symbols.ilike(f'%{symbol}%'))
            if status:
                query = query.filter(BacktestResult.status == status)
            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(BacktestResult.backtest_date >= cutoff)
            
            return query.order_by(BacktestResult.backtest_date.desc()).offset(offset).limit(limit).all()
    
    # ==================== TRADES ====================
    
    def save_trade(
        self,
        backtest_id: int,
        symbol: str,
        entry_date: datetime,
        entry_price: float,
        entry_signal: str,
        quantity: int,
        exit_date: Optional[datetime] = None,
        exit_price: Optional[float] = None,
        exit_reason: Optional[str] = None,
        pnl: Optional[float] = None,
        pnl_pct: Optional[float] = None
    ) -> int:
        """Save individual trade. Returns trade ID."""
        trade = Trade(
            backtest_id=backtest_id,
            symbol=symbol,
            entry_date=entry_date,
            entry_price=entry_price,
            entry_signal=entry_signal,
            quantity=quantity,
            exit_date=exit_date,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl=pnl,
            pnl_pct=pnl_pct,
            result='win' if (pnl and pnl > 0) else ('loss' if (pnl and pnl < 0) else 'breakeven'),
        )
        if exit_date and entry_date:
            trade.duration_minutes = int(
                (exit_date - entry_date).total_seconds() / 60
            )
        
        with self.get_session() as session:
            session.add(trade)
            session.flush()
            trade_id = trade.id
        
        return trade_id
    
    def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID."""
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.id == trade_id).first()
    
    def get_trades(
        self,
        backtest_id: int,
        symbol: Optional[str] = None,
        result: Optional[str] = None
    ) -> List[Trade]:
        """Get trades for a backtest."""
        with self.get_session() as session:
            query = session.query(Trade).filter(
                Trade.backtest_id == backtest_id
            )
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if result:
                query = query.filter(Trade.result == result)
            
            return query.order_by(Trade.entry_date).all()
    
    def save_trade_signal(self, trade_data: Dict[str, Any]) -> Optional[int]:
        """
        Save a live scanner trade signal to the database.
        
        This is used by the core scanner to persist live trading signals
        to the database. Unlike backtest trades, these are not associated
        with a backtest_id (backtest_id is None).
        
        Args:
            trade_data: Dictionary containing:
                - sym (str): Symbol
                - sector (str): Sector
                - entry (float): Entry price
                - stop (float): Stop loss price
                - target (float): Target price
                - atr (float): ATR value
                - smart_rank (float): SmartRank score
                - anticipation (float): Anticipation score
                - action (str): Action type (buy, sell, accumulate, etc.)
                - recorded_at (str): ISO datetime string
        
        Returns:
            Trade ID if successful, None on error
        """
        try:
            # Parse the recorded_at timestamp
            recorded_at = None
            if 'recorded_at' in trade_data:
                try:
                    recorded_at = datetime.fromisoformat(trade_data['recorded_at'])
                except (ValueError, TypeError):
                    recorded_at = datetime.utcnow()
            else:
                recorded_at = datetime.utcnow()
            
            # Create trade with minimal required fields
            # backtest_id is None for live signals (not from a backtest)
            trade = Trade(
                backtest_id=None,  # Live signal, not from backtest
                symbol=trade_data.get('sym', 'UNKNOWN'),
                entry_date=recorded_at,
                entry_price=float(trade_data.get('entry', 0.0)),
                entry_signal=trade_data.get('action', 'buy').lower(),
                quantity=1,  # Scanner does not compute shares yet
                exit_date=None,
                exit_price=None,
                exit_reason=None,
                pnl=None,
                pnl_pct=None,
                result=None,  # Not resolved yet
                max_profit=None,
                max_loss=None,
                duration_minutes=None,
            )
            
            with self.get_session() as session:
                session.add(trade)
                session.flush()
                trade_id = trade.id
            
            return trade_id
        
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(
                "Failed to save trade signal: %s", e
            )
            return None
    
    def update_trade_outcome(
        self,
        symbol: str,
        entry_date: datetime,
        exit_date: datetime,
        exit_price: float,
        pnl_pct: float,
        outcome: str,  # 'WIN', 'LOSS', 'TIMEOUT'
        exit_reason: Optional[str] = None,
    ) -> bool:
        """
        Update an open trade with its resolution outcome.
        
        Finds the most recent open trade for the symbol and entry_date,
        then updates it with exit information: exit_date, exit_price, pnl_pct,
        result (calculated from pnl_pct), and exit_reason.
        
        Args:
            symbol: Stock symbol
            entry_date: Original entry date (used to match the trade)
            exit_date: Date when trade was resolved
            exit_price: Price at resolution
            pnl_pct: P&L percentage
            outcome: 'WIN', 'LOSS', or 'TIMEOUT'
            exit_reason: Optional exit reason (hit stop, hit target, etc.)
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            with self.get_session() as session:
                # Find the open trade for this symbol and entry date
                trade = session.query(Trade).filter(
                    Trade.symbol == symbol,
                    Trade.entry_date <= entry_date + timedelta(days=1),
                    Trade.entry_date >= entry_date - timedelta(days=1),
                    Trade.result.is_(None)  # Still open
                ).order_by(Trade.entry_date.desc()).first()
                
                if not trade:
                    return False
                
                # Update with outcome information
                trade.exit_date = exit_date
                trade.exit_price = exit_price
                trade.pnl_pct = pnl_pct
                trade.pnl = (trade.entry_price * pnl_pct / 100.0) if trade.entry_price else 0.0
                
                # Determine result from outcome
                if outcome == "WIN":
                    trade.result = "win"
                elif outcome == "LOSS":
                    trade.result = "loss"
                elif outcome == "TIMEOUT":
                    trade.result = "timeout" if pnl_pct < 0 else "win"
                else:
                    trade.result = "unknown"
                
                trade.exit_reason = exit_reason or ("Hit " + outcome.lower())
                
                # Calculate duration
                if trade.exit_date and trade.entry_date:
                    trade.duration_minutes = int(
                        (trade.exit_date - trade.entry_date).total_seconds() / 60
                    )
                
                session.merge(trade)
            
            return True
        
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(
                "Failed to update trade outcome for %s: %s", symbol, e
            )
            return False
    
    # ==================== SIGNALS ====================
    
    def save_signal(
        self,
        backtest_id: int,
        symbol: str,
        signal_date: datetime,
        signal_type: str,
        strength: int = 50,
        momentum: Optional[float] = None,
        trend: Optional[str] = None,
        volatility: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        indicators: Optional[List[str]] = None,
        source: Optional[str] = None,
        trade_taken: bool = False
    ) -> int:
        """Save trading signal. Returns signal ID."""
        signal = Signal(
            backtest_id=backtest_id,
            symbol=symbol,
            signal_date=signal_date,
            signal_type=signal_type,
            strength=strength,
            momentum=momentum,
            trend=trend,
            volatility=volatility,
            volume_ratio=volume_ratio,
            indicators=indicators,
            source=source,
            trade_taken=trade_taken,
        )
        
        with self.get_session() as session:
            session.add(signal)
            session.flush()
            signal_id = signal.id
        
        return signal_id
    
    def get_signal(self, signal_id: int) -> Optional[Signal]:
        """Get signal by ID."""
        with self.get_session() as session:
            return session.query(Signal).filter(Signal.id == signal_id).first()
    
    def get_signals(
        self,
        backtest_id: int,
        symbol: Optional[str] = None,
        signal_type: Optional[str] = None
    ) -> List[Signal]:
        """Get signals for a backtest."""
        with self.get_session() as session:
            query = session.query(Signal).filter(
                Signal.backtest_id == backtest_id
            )
            if symbol:
                query = query.filter(Signal.symbol == symbol)
            if signal_type:
                query = query.filter(Signal.signal_type == signal_type)
            
            return query.order_by(Signal.signal_date).all()
    
    # ==================== STRATEGY METRICS ====================
    
    def save_strategy_metrics(
        self,
        backtest_id: int,
        symbol: str,
        metrics: Dict[str, Any]
    ) -> int:
        """Save per-symbol strategy metrics. Returns metrics ID."""
        strategy_metric = StrategyMetrics(
            backtest_id=backtest_id,
            symbol=symbol,
            num_trades=metrics.get('num_trades', 0),
            winning_trades=metrics.get('winning_trades', 0),
            losing_trades=metrics.get('losing_trades', 0),
            win_rate=metrics.get('win_rate', 0.0),
            total_return=metrics.get('total_return', 0.0),
            avg_win=metrics.get('avg_win', 0.0),
            avg_loss=metrics.get('avg_loss', 0.0),
            largest_win=metrics.get('largest_win', 0.0),
            largest_loss=metrics.get('largest_loss', 0.0),
            max_drawdown=metrics.get('max_drawdown', 0.0),
            sharpe=metrics.get('sharpe', 0.0),
            sortino=metrics.get('sortino', 0.0),
            signals_generated=metrics.get('signals_generated', 0),
            signals_acted=metrics.get('signals_acted', 0),
            signal_accuracy=metrics.get('signal_accuracy', 0.0),
            recommendation=metrics.get('recommendation', 'hold'),
            confidence=metrics.get('confidence', 0.0),
        )
        
        with self.get_session() as session:
            session.add(strategy_metric)
            session.flush()
            metric_id = strategy_metric.id
        
        return metric_id
    
    def get_strategy_metrics(self, metric_id: int) -> Optional[StrategyMetrics]:
        """Get strategy metrics by ID."""
        with self.get_session() as session:
            return session.query(StrategyMetrics).filter(
                StrategyMetrics.id == metric_id
            ).first()
    
    def get_strategy_metrics_by_symbol(
        self,
        backtest_id: int,
        symbol: str
    ) -> Optional[StrategyMetrics]:
        """Get strategy metrics for a specific symbol in a backtest."""
        with self.get_session() as session:
            return session.query(StrategyMetrics).filter(
                and_(
                    StrategyMetrics.backtest_id == backtest_id,
                    StrategyMetrics.symbol == symbol
                )
            ).first()
    
    # ==================== STATISTICS & REPORTS ====================
    
    def get_summary_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary statistics for the last N days.
        
        Args:
            days: Number of days to include
        
        Returns:
            Dictionary with summary statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            backtests = session.query(BacktestResult).filter(
                BacktestResult.backtest_date >= cutoff
            ).all()
            
            total_backtests = len(backtests)
            total_trades = sum(b.total_trades for b in backtests)
            total_pnl = sum(float(b.total_pnl) for b in backtests if b.total_pnl)
            avg_win_rate = sum(b.win_rate for b in backtests) / total_backtests if backtests else 0
            avg_sharpe = sum(b.sharpe_ratio for b in backtests) / total_backtests if backtests else 0
            
            return {
                'period_days': days,
                'total_backtests': total_backtests,
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'avg_win_rate': avg_win_rate,
                'avg_sharpe_ratio': avg_sharpe,
                'best_trade_day': max(
                    (b.backtest_date for b in backtests if b.total_pnl and b.total_pnl > 0),
                    default=None
                ),
            }
    
    def get_symbol_performance(self, symbol: str, days: int = 90) -> Dict[str, Any]:
        """Get performance statistics for a specific symbol."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            metrics = session.query(StrategyMetrics).join(
                BacktestResult
            ).filter(
                and_(
                    StrategyMetrics.symbol == symbol,
                    BacktestResult.backtest_date >= cutoff
                )
            ).all()
            
            if not metrics:
                return {}
            
            return {
                'symbol': symbol,
                'backtests': len(metrics),
                'total_trades': sum(m.num_trades for m in metrics),
                'avg_win_rate': sum(m.win_rate for m in metrics) / len(metrics),
                'avg_return': sum(m.total_return for m in metrics) / len(metrics),
                'avg_sharpe': sum(m.sharpe for m in metrics) / len(metrics),
                'recommendation': metrics[-1].recommendation if metrics else 'hold',
            }
    
    def cleanup_old_data(self, days: int = 180) -> int:
        """
        Delete backtests older than N days.
        
        Args:
            days: Age threshold in days
        
        Returns:
            Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            deleted = session.query(BacktestResult).filter(
                BacktestResult.backtest_date < cutoff
            ).delete()
            
            return deleted
