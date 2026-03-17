"""Portfolio optimization and allocation strategies."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class OptimalAllocation:
    """Optimal portfolio allocation result."""
    weights: Dict[str, float]  # Symbol -> allocation %
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    portfolio_value: float


class PortfolioOptimizer:
    """Optimize portfolio allocations using modern portfolio theory."""
    
    def __init__(self, target_return: Optional[float] = None):
        """Initialize optimizer.
        
        Args:
            target_return: Target annual return (optional)
        """
        self.target_return = target_return
        self.risk_free_rate = 0.02  # 2% annual
    
    def calculate_returns(
        self,
        prices: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate daily returns from price data.
        
        Args:
            prices: DataFrame with symbols as columns
            
        Returns:
            DataFrame of daily returns
        """
        returns = prices.pct_change().dropna()
        return returns
    
    def calculate_portfolio_metrics(
        self,
        weights: np.ndarray,
        returns: pd.DataFrame,
        cov_matrix: np.ndarray
    ) -> Tuple[float, float, float]:
        """Calculate portfolio return, volatility, and Sharpe ratio.
        
        Args:
            weights: Asset weights array
            returns: DataFrame of returns
            cov_matrix: Covariance matrix
            
        Returns:
            (expected_return, volatility, sharpe_ratio)
        """
        annual_returns = returns.mean() * 252
        portfolio_return = np.sum(annual_returns * weights)
        
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
        
        return float(portfolio_return), float(portfolio_volatility), float(sharpe_ratio)
    
    def minimize_volatility(
        self,
        returns: pd.DataFrame,
        bounds: Optional[List[Tuple[float, float]]] = None
    ) -> OptimalAllocation:
        """Find minimum variance portfolio.
        
        Args:
            returns: DataFrame of returns
            bounds: Min/max weights per asset (default: 0-1)
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov().values * 252
        
        if bounds is None:
            bounds = tuple((0, 1) for _ in range(n_assets))
        
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        def objective(x):
            vol = np.sqrt(np.dot(x, np.dot(cov_matrix, x)))
            return vol
        
        result = minimize(
            objective,
            x0=np.array([1/n_assets] * n_assets),
            bounds=bounds,
            constraints=constraints,
            method='SLSQP'
        )
        
        weights_arr = result.x
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights_arr, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights_arr))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def maximize_sharpe_ratio(
        self,
        returns: pd.DataFrame,
        bounds: Optional[List[Tuple[float, float]]] = None
    ) -> OptimalAllocation:
        """Find maximum Sharpe ratio portfolio.
        
        Args:
            returns: DataFrame of returns
            bounds: Min/max weights per asset
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov().values * 252
        
        if bounds is None:
            bounds = tuple((0, 1) for _ in range(n_assets))
        
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        def objective(x):
            ret, vol, _ = self.calculate_portfolio_metrics(x, returns, cov_matrix)
            sharpe = (ret - self.risk_free_rate) / vol if vol > 0 else 0
            return -sharpe  # Minimize negative Sharpe
        
        result = minimize(
            objective,
            x0=np.array([1/n_assets] * n_assets),
            bounds=bounds,
            constraints=constraints,
            method='SLSQP'
        )
        
        weights_arr = result.x
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights_arr, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights_arr))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def generate_efficient_frontier(
        self,
        returns: pd.DataFrame,
        num_portfolios: int = 50,
        bounds: Optional[List[Tuple[float, float]]] = None
    ) -> pd.DataFrame:
        """Generate efficient frontier.
        
        Args:
            returns: DataFrame of returns
            num_portfolios: Number of portfolios to generate
            bounds: Min/max weights
            
        Returns:
            DataFrame with return, volatility, Sharpe for each portfolio
        """
        n_assets = len(returns.columns)
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov().values * 252
        
        if bounds is None:
            bounds = tuple((0, 1) for _ in range(n_assets))
        
        results = []
        
        for target_ret in np.linspace(mean_returns.min(), mean_returns.max(), num_portfolios):
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: np.sum(mean_returns * x) - target_ret}
            ]
            
            def objective(x):
                return np.sqrt(np.dot(x, np.dot(cov_matrix, x)))
            
            result = minimize(
                objective,
                x0=np.array([1/n_assets] * n_assets),
                bounds=bounds,
                constraints=constraints,
                method='SLSQP'
            )
            
            if result.success:
                ret, vol, sharpe = self.calculate_portfolio_metrics(
                    result.x, returns, cov_matrix
                )
                results.append({
                    'return': ret,
                    'volatility': vol,
                    'sharpe_ratio': sharpe
                })
        
        return pd.DataFrame(results)
    
    def risk_parity(
        self,
        returns: pd.DataFrame
    ) -> OptimalAllocation:
        """Generate risk parity portfolio (equal risk contribution).
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        cov_matrix = returns.cov().values * 252
        std_devs = np.sqrt(np.diag(cov_matrix))
        
        # Inverse volatility weighting
        weights = (1 / std_devs) / np.sum(1 / std_devs)
        
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def equal_weight(
        self,
        returns: pd.DataFrame
    ) -> OptimalAllocation:
        """Generate equal-weight portfolio.
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        weights = np.array([1/n_assets] * n_assets)
        
        cov_matrix = returns.cov().values * 252
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def get_correlation_matrix(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Get correlation matrix.
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            Correlation matrix
        """
        return returns.corr()
    
    def rebalance_weights(
        self,
        current_prices: Dict[str, float],
        current_holdings: Dict[str, float],
        target_weights: Dict[str, float],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Calculate rebalancing trades needed.
        
        Args:
            current_prices: Current prices
            current_holdings: Current share counts
            target_weights: Target allocation weights
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> shares to trade (positive = buy, negative = sell)
        """
        trades = {}
        
        for symbol, target_weight in target_weights.items():
            price = current_prices.get(symbol, 0)
            current_shares = current_holdings.get(symbol, 0)
            
            if price == 0:
                continue
            
            current_value = current_shares * price
            current_weight = current_value / portfolio_value if portfolio_value > 0 else 0
            
            target_value = target_weight * portfolio_value
            target_shares = target_value / price
            
            shares_to_trade = target_shares - current_shares
            trades[symbol] = float(shares_to_trade)
        
        return trades


# Global instance
_optimizer: Optional[PortfolioOptimizer] = None


def get_portfolio_optimizer() -> PortfolioOptimizer:
    """Get or create global portfolio optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = PortfolioOptimizer()
    return _optimizer
