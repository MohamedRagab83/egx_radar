"""Options trading strategies and Greeks calculation."""

import numpy as np
from scipy.stats import norm
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum


class OptionType(str, Enum):
    """Option types."""
    CALL = "call"
    PUT = "put"


class OptionStrategy(str, Enum):
    """Predefined strategies."""
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    STRADDLE = "straddle"
    STRANGLE = "strangle"


@dataclass
class GreeksData:
    """Option Greeks data."""
    delta: float  # Price sensitivity
    gamma: float  # Delta sensitivity  
    vega: float   # Volatility sensitivity
    theta: float  # Time decay
    rho: float    # Interest rate sensitivity


class BlackScholesCalculator:
    """Black-Scholes option pricing calculator."""
    
    @staticmethod
    def calculate_price(
        S: float,  # Current  stock price
        K: float,  # Strike price
        T: float,  # Time to expiration (years)
        r: float,  # Risk-free rate
        sigma: float,  # Volatility
        option_type: OptionType = OptionType.CALL
    ) -> float:
        """Calculate option price using Black-Scholes.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration
            r: Risk-free rate
            sigma: Volatility
            option_type: Call or Put
            
        Returns:
            Option price
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == OptionType.CALL:
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # PUT
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return float(price)
    
    @staticmethod
    def calculate_greeks(
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: OptionType = OptionType.CALL
    ) -> GreeksData:
        """Calculate option Greeks.
        
        Args:
            S, K, T, r, sigma: See calculate_price
            option_type: Call or Put
            
        Returns:
            GreeksData with all Greeks
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if option_type == OptionType.CALL:
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        # Gamma (same for both)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Vega (same for both)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% change in volatility
        
        # Theta  
        sqrt_T = np.sqrt(T)
        if option_type == OptionType.CALL:
            theta = (-S * norm.pdf(d1) * sigma / (2 * sqrt_T) -
                     r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (-S * norm.pdf(d1) * sigma / (2 * sqrt_T) +
                     r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        # Rho
        if option_type == OptionType.CALL:
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100  # Per 1% change
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        return GreeksData(
            delta=float(delta),
            gamma=float(gamma),
            vega=float(vega),
            theta=float(theta),
            rho=float(rho)
        )


class OptionsPortfolio:
    """Portfolio of options positions."""
    
    @dataclass
    class Position:
        """Single option position."""
        symbol: str
        option_type: OptionType
        strike: float
        expiration: datetime
        quantity: int  # Positive for long, negative for short
        entry_price: float
    
    def __init__(self):
        """Initialize empty portfolio."""
        self.positions: List['OptionsPortfolio.Position'] = []
    
    def add_position(
        self,
        symbol: str,
        option_type: OptionType,
        strike: float,
        expiration: datetime,
        quantity: int,
        entry_price: float
    ) -> None:
        """Add position to portfolio.
        
        Args:
            symbol: Stock symbol
            option_type: Call or Put
            strike: Strike price
            expiration: Expiration date
            quantity: Position size (positive=long, negative=short)
            entry_price: Entry price
        """
        position = self.Position(
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiration=expiration,
            quantity=quantity,
            entry_price=entry_price
        )
        self.positions.append(position)
    
    def calculate_portfolio_greeks(
        self,
        stock_prices: Dict[str, float],
        vol: Dict[str, float],
        r: float = 0.05
    ) -> Dict[str, float]:
        """Calculate aggregate Greeks for portfolio.
        
        Args:
            stock_prices: Current prices by symbol
            vol: Volatilities by symbol
            r: Risk-free rate
            
        Returns:
            Aggregate Greeks
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_vega = 0.0
        total_theta = 0.0
        total_rho = 0.0
        
        calculator = BlackScholesCalculator()
        
        for pos in self.positions:
            S = stock_prices.get(pos.symbol)
            sigma = vol.get(pos.symbol, 0.25)
            
            if S is None:
                continue
            
            T = (pos.expiration - datetime.now()).days / 365
            if T <= 0:
                continue
            
            greeks = calculator.calculate_greeks(S, pos.strike, T, r, sigma, pos.option_type)
            
            total_delta += greeks.delta * pos.quantity
            total_gamma += greeks.gamma * pos.quantity
            total_vega += greeks.vega * pos.quantity
            total_theta += greeks.theta * pos.quantity
            total_rho += greeks.rho * pos.quantity
        
        return {
            'delta': float(total_delta),
            'gamma': float(total_gamma),
            'vega': float(total_vega),
            'theta': float(total_theta),
            'rho': float(total_rho)
        }
    
    def calculate_portfolio_value(
        self,
        stock_prices: Dict[str, float],
        vol: Dict[str, float],
        r: float = 0.05
    ) -> float:
        """Calculate total portfolio value.
        
        Args:
            stock_prices: Current prices by symbol
            vol: Volatilities by symbol
            r: Risk-free rate
            
        Returns:
            Total portfolio price
        """
        total_value = 0.0
        calculator = BlackScholesCalculator()
        
        for pos in self.positions:
            S = stock_prices.get(pos.symbol)
            sigma = vol.get(pos.symbol, 0.25)
            
            if S is None:
                continue
            
            T = (pos.expiration - datetime.now()).days / 365
            if T <= 0:
                continue
            
            option_price = calculator.calculate_price(
                S, pos.strike, T, r, sigma, pos.option_type
            )
            
            # Add to total (negative quantity = short, subtracts)
            total_value += option_price * pos.quantity
        
        return float(total_value)
    
    def max_profit(self, stock_prices: Dict[str, float]) -> float:
        """Calculate maximum profit from strategy.
        
        Args:
            stock_prices: Current stock prices
            
        Returns:
            Max profit
        """
        # Simplified: assume positions expire at strike
        max_profit = 0.0
        
        for pos in self.positions:
            S = stock_prices.get(pos.symbol, 0)
            
            if pos.option_type == OptionType.CALL:
                if pos.quantity > 0:  # Long call
                    intrinsic = max(0, S - pos.strike)
                else:  # Short call
                    intrinsic = max(0, pos.strike - S)
            else:  # PUT
                if pos.quantity > 0:  # Long put
                    intrinsic = max(0, pos.strike - S)
                else:  # Short put
                    intrinsic = max(0, S - pos.strike)
            
            max_profit += (intrinsic - pos.entry_price) * abs(pos.quantity)
        
        return float(max_profit)
    
    def max_loss(self, stock_prices: Dict[str, float]) -> float:
        """Calculate maximum loss from strategy.
        
        Args:
            stock_prices: Current stock prices
            
        Returns:
            Max loss (negative value)
        """
        max_loss = 0.0
        
        for pos in self.positions:
            if pos.quantity > 0:  # Long position
                # Max loss is the entry price
                max_loss -= pos.entry_price * abs(pos.quantity)
            else:  # Short position
                # Max loss is unlimited for short calls, limited for short puts
                if pos.option_type == OptionType.PUT:
                    max_loss -= pos.strike * abs(pos.quantity)
        
        return float(max_loss)
    
    def break_even_points(self) -> List[Tuple[str, float]]:
        """ Calculate break-even points for positions.
        
        Returns:
            List of (symbol, break_even_price) tuples
        """
        break_even_points = []
        
        for pos in self.positions:
            if pos.option_type == OptionType.CALL:
                be = pos.strike + pos.entry_price
            else:  # PUT
                be = pos.strike - pos.entry_price
            
            break_even_points.append((pos.symbol, be))
        
        return break_even_points


# Global instance
_options_calculator: Optional[BlackScholesCalculator] = None


def get_options_calculator() -> BlackScholesCalculator:
    """Get options calculator instance."""
    global _options_calculator
    if _options_calculator is None:
        _options_calculator = BlackScholesCalculator()
    return _options_calculator
