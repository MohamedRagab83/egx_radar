"""Market data and real-time data management."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import threading
import time
from collections import deque


class MarketDataManager:
    """Manages real-time and historical market data."""
    
    def __init__(self, cache_size: int = 5000):
        """Initialize market data manager.
        
        Args:
            cache_size: Maximum number of price points to keep in memory
        """
        self.cache_size = cache_size
        self._price_cache: Dict[str, deque] = {}  # symbol -> deque of (timestamp, price)
        self._last_update: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
        self._subscribers: Dict[str, List[callable]] = {}  # callbacks for price updates
    
    def get_historical_data(self, symbol: str, days: int = 365, interval: str = '1d') -> pd.DataFrame:
        """Fetch historical OHLCV data.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            days: Number of days of history to fetch
            interval: Candle interval ('1m', '5m', '1h', '1d', etc.)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Adj Close
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )
            
            return data if isinstance(data, pd.DataFrame) else data.to_frame()
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None if unable to fetch
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d')
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            print(f"Error fetching current price for {symbol}: {e}")
        return None
    
    def get_multi_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """Get current prices for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to prices
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
            time.sleep(0.1)  # Rate limiting
        return prices
    
    def cache_price(self, symbol: str, price: float, timestamp: Optional[datetime] = None) -> None:
        """Cache price data for a symbol.
        
        Args:
            symbol: Stock symbol
            price: Current price
            timestamp: Timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        with self._lock:
            if symbol not in self._price_cache:
                self._price_cache[symbol] = deque(maxlen=self.cache_size)
            
            self._price_cache[symbol].append((timestamp, price))
            self._last_update[symbol] = timestamp
            
            # Notify subscribers
            if symbol in self._subscribers:
                for callback in self._subscribers[symbol]:
                    try:
                        callback(symbol, price, timestamp)
                    except Exception as e:
                        print(f"Error in price callback: {e}")
    
    def get_cached_prices(self, symbol: str, limit: int = 100) -> List[Tuple[datetime, float]]:
        """Get cached price history for a symbol.
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of cached prices to return
            
        Returns:
            List of (timestamp, price) tuples
        """
        with self._lock:
            if symbol not in self._price_cache:
                return []
            return list(self._price_cache[symbol])[-limit:]
    
    def get_price_stats(self, symbol: str) -> Dict[str, float]:
        """Get statistics on cached prices.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with min, max, avg, latest price
        """
        prices = self.get_cached_prices(symbol)
        if not prices:
            return {}
        
        price_values = [p[1] for p in prices]
        return {
            'min': min(price_values),
            'max': max(price_values),
            'avg': sum(price_values) / len(price_values),
            'latest': price_values[-1],
            'count': len(price_values),
            'last_update': prices[-1][0].isoformat() if prices else None
        }
    
    def subscribe(self, symbol: str, callback: callable) -> None:
        """Subscribe to price updates for a symbol.
        
        Args:
            symbol: Stock symbol
            callback: Function to call on price updates (symbol, price, timestamp)
        """
        if symbol not in self._subscribers:
            self._subscribers[symbol] = []
        self._subscribers[symbol].append(callback)
    
    def unsubscribe(self, symbol: str, callback: callable) -> None:
        """Unsubscribe from price updates.
        
        Args:
            symbol: Stock symbol
            callback: Callback function to remove
        """
        if symbol in self._subscribers:
            self._subscribers[symbol] = [
                cb for cb in self._subscribers[symbol] if cb != callback
            ]
    
    def get_intraday_volatility(self, symbol: str, minutes: int = 60) -> Optional[float]:
        """Calculate intraday volatility over recent period.
        
        Args:
            symbol: Stock symbol
            minutes: Period in minutes
            
        Returns:
            Volatility percentage or None
        """
        try:
            data = yf.download(symbol, period='5d', interval='1m', progress=False)
            if data.empty or len(data) < 2:
                return None
            
            returns = data['Close'].pct_change().dropna()
            if len(returns) > 0:
                volatility = float(returns.std() * 100)
                return volatility if not pd.isna(volatility) else None
        except Exception as e:
            print(f"Error calculating volatility for {symbol}: {e}")
        return None
    
    def get_sentiment_indicators(self, symbol: str) -> Dict[str, float]:
        """Get general market sentiment indicators.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with momentum, trend, strength indicators
        """
        try:
            data = self.get_historical_data(symbol, days=30, interval='1d')
            if data.empty or len(data) < 5:
                return {}
            
            # Simple momentum calculation
            close_prices = data['Close'].values
            momentum = (close_prices[-1] - close_prices[-5]) / close_prices[-5] * 100
            
            # Trend (5-day vs 20-day average)
            avg_5 = close_prices[-5:].mean()
            avg_20 = close_prices[-20:].mean() if len(close_prices) >= 20 else close_prices.mean()
            trend = 'bullish' if avg_5 > avg_20 else 'bearish'
            
            # Simple RSI approximation
            deltas = pd.Series(close_prices).diff().dropna().values
            seed = deltas[:1]
            up = seed[seed >= 0].sum()
            down = -seed[seed < 0].sum()
            rs = up / down if down != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            return {
                'momentum': float(momentum),
                'trend': trend,
                'rsi': float(rsi),
                'strength': float(abs(momentum))
            }
        except Exception as e:
            print(f"Error calculating sentiment for {symbol}: {e}")
            return {}
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear cached price data.
        
        Args:
            symbol: Specific symbol to clear, or None for all
        """
        with self._lock:
            if symbol:
                if symbol in self._price_cache:
                    self._price_cache[symbol].clear()
            else:
                self._price_cache.clear()
                self._last_update.clear()


# Global market data manager instance
_market_data_manager: Optional[MarketDataManager] = None


def get_market_data_manager() -> MarketDataManager:
    """Get or create global market data manager."""
    global _market_data_manager
    if _market_data_manager is None:
        _market_data_manager = MarketDataManager()
    return _market_data_manager
