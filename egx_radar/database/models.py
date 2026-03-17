"""SQLAlchemy ORM models for EGX Radar database."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Numeric, Text, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class BacktestResult(Base):
    """Backtest execution results and performance metrics."""
    
    __tablename__ = 'backtest_results'
    __table_args__ = (
        Index('idx_backtest_date', 'backtest_date'),
        Index('idx_backtest_symbols', 'symbols'),
        Index('idx_backtest_status', 'status'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(String(100), unique=True, nullable=False, index=True)
    backtest_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    symbols = Column(String(1000), nullable=False)  # Comma-separated
    symbol_count = Column(Integer, nullable=False)
    
    # Performance Metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    total_pnl = Column(Numeric(15, 2), default=0)  # Total P&L
    gross_profit = Column(Numeric(15, 2), default=0)
    gross_loss = Column(Numeric(15, 2), default=0)
    profit_factor = Column(Float, default=0.0)
    
    # Risk Metrics
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    calmar_ratio = Column(Float, default=0.0)
    
    # Statistical
    avg_trade_return = Column(Float, default=0.0)
    std_dev_returns = Column(Float, default=0.0)
    expectancy = Column(Float, default=0.0)
    recovery_factor = Column(Float, default=0.0)
    
    # Execution
    execution_time_seconds = Column(Float, nullable=True)
    workers_used = Column(Integer, default=1)
    
    # Status & Details
    status = Column(String(50), default='completed')  # completed, failed, partial
    notes = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True)  # Settings used
    
    trades = relationship('Trade', back_populates='backtest', cascade='all, delete-orphan')
    signals = relationship('Signal', back_populates='backtest', cascade='all, delete-orphan')
    metrics = relationship('StrategyMetrics', back_populates='backtest', cascade='all, delete-orphan')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BacktestResult(id={self.backtest_id}, symbols={self.symbol_count}, trades={self.total_trades})>"


class Trade(Base):
    """Individual trades from backtest execution or live signals."""
    
    __tablename__ = 'trades'
    __table_args__ = (
        Index('idx_trade_backtest', 'backtest_id'),
        Index('idx_trade_symbol', 'symbol'),
        Index('idx_trade_entry_date', 'entry_date'),
        Index('idx_trade_result', 'result'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=True)
    
    symbol = Column(String(20), nullable=False)
    entry_date = Column(DateTime, nullable=False)
    entry_price = Column(Numeric(15, 6), nullable=False)
    entry_signal = Column(String(50), nullable=False)  # buy, sell, short
    
    exit_date = Column(DateTime, nullable=True)
    exit_price = Column(Numeric(15, 6), nullable=True)
    exit_reason = Column(String(100), nullable=True)  # take_profit, stop_loss, signal, timeout
    
    quantity = Column(Integer, nullable=False)
    result = Column(String(20), nullable=True)  # win, loss, breakeven
    pnl = Column(Numeric(15, 2), nullable=True)
    pnl_pct = Column(Float, nullable=True)
    
    max_profit = Column(Numeric(15, 2), nullable=True)  # Highest unrealized profit
    max_loss = Column(Numeric(15, 2), nullable=True)    # Lowest unrealized profit
    
    duration_minutes = Column(Integer, nullable=True)
    
    backtest = relationship('BacktestResult', back_populates='trades')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade(symbol={self.symbol}, entry={self.entry_date.strftime('%Y-%m-%d')}, pnl={self.pnl})>"


class Signal(Base):
    """Trading signals generated during backtest."""
    
    __tablename__ = 'signals'
    __table_args__ = (
        Index('idx_signal_backtest', 'backtest_id'),
        Index('idx_signal_symbol', 'symbol'),
        Index('idx_signal_date', 'signal_date'),
        Index('idx_signal_type', 'signal_type'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=False)
    
    symbol = Column(String(20), nullable=False)
    signal_date = Column(DateTime, nullable=False)
    signal_type = Column(String(50), nullable=False)  # buy, sell, strong_buy, strong_sell
    strength = Column(Integer, default=50)  # 0-100 confidence
    
    # Signal components
    momentum = Column(Float, nullable=True)
    trend = Column(String(20), nullable=True)  # uptrend, downtrend, sideways
    volatility = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    
    # Indicators used
    indicators = Column(JSON, nullable=True)  # List of indicators that contributed
    source = Column(String(100), nullable=True)  # Which module generated signal
    
    # Outcome tracking
    trade_taken = Column(Boolean, default=False)
    trade_successful = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
    
    backtest = relationship('BacktestResult', back_populates='signals')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Signal(symbol={self.symbol}, type={self.signal_type}, strength={self.strength})>"


class StrategyMetrics(Base):
    """Per-symbol strategy performance metrics."""
    
    __tablename__ = 'strategy_metrics'
    __table_args__ = (
        Index('idx_metrics_backtest', 'backtest_id'),
        Index('idx_metrics_symbol', 'symbol'),
        UniqueConstraint('backtest_id', 'symbol', name='uq_backtest_symbol'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=False)
    
    symbol = Column(String(20), nullable=False)
    
    # Trade Statistics
    num_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # Returns
    total_return = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    
    # Risk
    max_drawdown = Column(Float, default=0.0)
    sharpe = Column(Float, default=0.0)
    sortino = Column(Float, default=0.0)
    
    # Signal performance
    signals_generated = Column(Integer, default=0)
    signals_acted = Column(Integer, default=0)
    signal_accuracy = Column(Float, default=0.0)
    
    # Recommendation
    recommendation = Column(String(50), default='hold')  # buy, sell, hold, avoid
    confidence = Column(Float, default=0.0)
    
    backtest = relationship('BacktestResult', back_populates='metrics')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<StrategyMetrics(symbol={self.symbol}, trades={self.num_trades}, win_rate={self.win_rate:.2%})>"


class EquityHistory(Base):
    """Daily equity curve tracking for risk analysis."""
    
    __tablename__ = 'equity_history'
    __table_args__ = (
        Index('idx_equity_backtest', 'backtest_id'),
        Index('idx_equity_date', 'date'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=False)
    
    date = Column(DateTime, nullable=False)
    starting_equity = Column(Numeric(15, 2), nullable=False)
    ending_equity = Column(Numeric(15, 2), nullable=False)
    daily_pnl = Column(Numeric(15, 2), nullable=False)
    daily_return = Column(Float, nullable=False)
    
    cumulative_return = Column(Float, nullable=False)
    drawdown = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<EquityHistory(date={self.date.strftime('%Y-%m-%d')}, equity={self.ending_equity})>"
