"""Advanced risk management tools."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics."""
    value_at_risk: float  # VaR at 95% confidence
    conditional_var: float  # CVaR (Expected Shortfall)
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    return_per_unit_risk: float


class RiskManager:
    """Advanced risk management and sizing."""
    
    def __init__(self, account_size: float = 100000):
        """Initialize risk manager.
        
        Args:
            account_size: Total account size in dollars
        """
        self.account_size = account_size
        self.max_drawdown_pct = 0.20  # 20% max drawdown
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.daily_loss_limit = account_size * 0.05  # 5% daily loss limit
        self.correlation_threshold = 0.7
    
    def calculate_position_size(
        self,
        entry: float,
        stop_loss: float,
        confidence: float = 0.5
    ) -> float:
        """Calculate position size based on risk.
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price
            confidence: Confidence in trade (0-1)
            
        Returns:
            Position size in dollars
        """
        risk_amount = self.account_size * self.risk_per_trade
        risk_per_unit = abs(entry - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        # Adjust for confidence
        position_size = (risk_amount / risk_per_unit) * confidence
        
        # Cap at max drawdown limits
        max_position = self.account_size * (self.max_drawdown_pct / 100)
        position_size = min(position_size, max_position)
        
        return float(position_size)
    
    def calculate_value_at_risk(
        self,
        returns: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """Calculate Value at Risk.
        
        Args:
            returns: Array of returns
            confidence: Confidence level (default 95%)
            
        Returns:
            VaR value
        """
        var = np.percentile(returns, (1 - confidence) * 100)
        return float(var * self.account_size)
    
    def calculate_conditional_var(
        self,
        returns: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall).
        
        Args:
            returns: Array of returns
            confidence: Confidence level
            
        Returns:
            CVaR value
        """
        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()
        return float(cvar * self.account_size)
    
    def calculate_drawdown_metrics(
        self,
        equity_curve: np.ndarray
    ) -> Tuple[float, float, List[float]]:
        """Calculate maximum and current drawdown.
        
        Args:
            equity_curve: Array of equity values over time
            
        Returns:
            (max_drawdown, current_drawdown, drawdown_series)
        """
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max * 100
        
        max_drawdown = np.min(drawdown)
        current_drawdown = drawdown[-1] if len(drawdown) > 0 else 0
        
        return float(max_drawdown), float(current_drawdown), drawdown.tolist()
    
    def calculate_sharpe_ratio(
        self,
        returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe Ratio.
        
        Args:
            returns: Array of daily returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sharpe ratio (annualized)
        """
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        if len(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        return float(sharpe)
    
    def calculate_sortino_ratio(
        self,
        returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sortino Ratio (only penalizes downside volatility).
        
        Args:
            returns: Array of daily returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sortino ratio (annualized)
        """
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        # Downside deviation
        downside = excess_returns[excess_returns < 0]
        downside_std = np.std(downside) if len(downside) > 0 else np.std(excess_returns)
        
        if downside_std == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_std * np.sqrt(252)
        return float(sortino)
    
    def calculate_calmar_ratio(
        self,
        returns: np.ndarray,
        equity_curve: np.ndarray
    ) -> float:
        """Calculate Calmar Ratio (return per unit of max drawdown).
        
        Args:
            returns: Array of daily returns
            equity_curve: Array of equity values
            
        Returns:
            Calmar ratio
        """
        annual_return = np.mean(returns) * 252
        max_dd, _, _ = self.calculate_drawdown_metrics(equity_curve)
        max_dd = abs(max_dd) / 100  # Convert percentage to decimal
        
        if max_dd == 0:
            return 0.0
        
        calmar = annual_return / max_dd
        return float(calmar)
    
    def check_correlation_risk(
        self,
        positions: Dict[str, float],
        correlation_matrix: pd.DataFrame
    ) -> List[Tuple[str, str, float]]:
        """Check for concentration risk in correlated positions.
        
        Args:
            positions: Dict of symbol -> position_size
            correlation_matrix: Correlation matrix of symbols
            
        Returns:
            List of (symbol1, symbol2, correlation) with high correlation
        """
        high_corr_pairs = []
        
        symbols = list(positions.keys())
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                if sym1 in correlation_matrix.index and sym2 in correlation_matrix.columns:
                    corr = correlation_matrix.loc[sym1, sym2]
                    if abs(corr) > self.correlation_threshold:
                        high_corr_pairs.append((sym1, sym2, float(corr)))
        
        return high_corr_pairs
    
    def check_daily_loss_limit(self, daily_pnl: float) -> bool:
        """Check if daily loss limit has been exceeded.
        
        Args:
            daily_pnl: Daily P&L
            
        Returns:
            True if limit exceeded
        """
        return daily_pnl < -self.daily_loss_limit
    
    def calculate_risk_metrics(
        self,
        returns: np.ndarray,
        equity_curve: np.ndarray
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics.
        
        Args:
            returns: Array of daily returns
            equity_curve: Array of equity values
            
        Returns:
            RiskMetrics object
        """
        return RiskMetrics(
            value_at_risk=self.calculate_value_at_risk(returns),
            conditional_var=self.calculate_conditional_var(returns),
            max_drawdown=self.calculate_drawdown_metrics(equity_curve)[0],
            sharpe_ratio=self.calculate_sharpe_ratio(returns),
            sortino_ratio=self.calculate_sortino_ratio(returns),
            calmar_ratio=self.calculate_calmar_ratio(returns, equity_curve),
            return_per_unit_risk=np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        )


class PositionSizer:
    """Intelligent position sizing."""
    
    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate Kelly Criterion for optimal position sizing.
        
        Args:
            win_rate: Percentage of winning trades (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount
            
        Returns:
            Kelly fraction (% of capital to risk)
        """
        if avg_loss == 0 or win_rate == 0 or win_rate == 1:
            return 0.0
        
        loss_rate = 1 - win_rate
        ratio = avg_win / avg_loss
        
        kelly = (win_rate * ratio - loss_rate) / ratio
        
        # Apply safety factor (never bet full Kelly)
        kelly = kelly / 4  # Quarter Kelly is safer
        
        return float(max(0, min(kelly, 0.25)))  # Cap at 25%
    
    @staticmethod
    def optimal_position_size(
        account_size: float,
        entry: float,
        stop_loss: float,
        kelly_fraction: float
    ) -> float:
        """Calculate position size using Kelly fraction.
        
        Args:
            account_size: Total account size
            entry: Entry price
            stop_loss: Stop loss price
            kelly_fraction: Kelly fraction (from Kelly Criterion)
            
        Returns:
            Position size
        """
        risk_amount = account_size * kelly_fraction
        risk_per_unit = abs(entry - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        position_size = risk_amount / risk_per_unit
        return float(position_size)


# Global instance
_risk_manager: Optional[RiskManager] = None


def get_risk_manager(account_size: float = 100000) -> RiskManager:
    """Get or create global risk manager."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager(account_size)
    return _risk_manager
