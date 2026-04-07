"""Data Service for EGX Radar - Handles data fetching and caching (Layer 3 Architecture).

This service is responsible for:
  - Fetching OHLCV data from multiple sources
  - Managing indicator cache
  - Market breadth health calculation
  - Data validation and preprocessing

This decouples data fetching from the scan orchestration logic.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from egx_radar.config.settings import K, SYMBOLS
from egx_radar.data.data_engine import get_data_engine

log = logging.getLogger(__name__)


class DataService:
    """Service for data fetching, caching, and market health assessment."""
    
    def __init__(self):
        """Initialize the data service."""
        self._cache: Dict[str, dict] = {}
        self._cache_lock = threading.Lock()
        self._market_healthy: bool = True
        self._data_engine = get_data_engine()
        
    def fetch_all_data(self, force_refresh: bool = False) -> Dict[str, any]:
        """Fetch all symbol data from configured sources.
        
        Args:
            force_refresh: If True, bypass cache and re-fetch all data
            
        Returns:
            Dictionary mapping Yahoo symbols to DataFrames
        """
        current_time = time.time()
        
        # Check if all data is cached and fresh
        if not force_refresh and self._cache:
            all_cached = True
            for sym in SYMBOLS.keys():
                c = self._cache.get(sym)
                if not c or (current_time - c.get("timestamp", 0)) > K.CACHE_TTL_SECONDS:
                    all_cached = False
                    break
            
            if all_cached:
                log.debug("DataService: Using cached data (all symbols fresh)")
                return {}  # Return empty - use cache
        
        # Fetch fresh data
        log.debug("DataService: Fetching fresh data from sources...")
        all_data = self._data_engine.fetch_live()
        
        if not all_data:
            log.error("DataService: No data fetched from any source")
            return {}
        
        # Update cache metadata
        for sym in all_data.keys():
            with self._cache_lock:
                self._cache[sym] = {
                    "timestamp": current_time,
                    "loaded": True,
                }
        
        log.info(f"DataService: Loaded {len(all_data)} symbols")
        return all_data
    
    def calculate_market_breadth(self, all_data: Dict[str, any]) -> bool:
        """Calculate market breadth health indicator.
        
        Strategy: Count how many scanned symbols have price > EMA50.
        If >50% of stocks are above their EMA50, market is healthy.
        
        Args:
            all_data: Raw data dictionary from fetch_all_data
            
        Returns:
            True if market is healthy (>50% above EMA50), False otherwise
        """
        # Check cache first
        if not all_data and "_MARKET_HEALTHY" in self._cache:
            return self._cache.get("_MARKET_HEALTHY", True)
        
        if not all_data:
            # No data and not cached - default to healthy
            return True
        
        above_ema50 = 0
        total_checked = 0
        
        for yahoo_sym, df_raw in all_data.items():
            if df_raw is None or (hasattr(df_raw, 'empty') and df_raw.empty):
                continue
            
            close = df_raw["Close"].dropna() if "Close" in df_raw.columns else None
            if close is None or len(close) < 52:
                continue
            
            try:
                ema50_val = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
                price_val = float(close.iloc[-1])
                total_checked += 1
                if price_val > ema50_val:
                    above_ema50 += 1
            except (IndexError, ValueError, TypeError) as e:
                log.warning("Error calculating EMA50 for %s: %s", yahoo_sym, e)
                continue
        
        if total_checked == 0:
            self._market_healthy = True
            log.warning("Market breadth: 0 symbols had sufficient bars — defaulting healthy=True")
        else:
            breadth_ratio = above_ema50 / total_checked
            self._market_healthy = breadth_ratio > K.MARKET_BREADTH_THRESHOLD
            log.info(
                "Market breadth: %d/%d symbols above EMA50 (%.0f%%) → healthy=%s",
                above_ema50, total_checked, breadth_ratio * 100, self._market_healthy,
            )
        
        # Cache the result
        with self._cache_lock:
            self._cache["_MARKET_HEALTHY"] = self._market_healthy
        
        return self._market_healthy
    
    def get_cached_indicator(self, symbol: str) -> Optional[dict]:
        """Get cached indicator result for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Cached result dictionary or None if not cached/expired
        """
        current_time = time.time()
        with self._cache_lock:
            c_data = self._cache.get(symbol)
            if c_data and (current_time - c_data.get("timestamp", 0)) <= 3600:
                return c_data.get("res_dict")
        return None
    
    def cache_indicator_result(
        self,
        symbol: str,
        result: dict,
        slope: float,
        quantum_n: float,
    ) -> None:
        """Cache indicator calculation result for a symbol.
        
        Args:
            symbol: Stock symbol
            result: Indicator result dictionary
            slope: EMA200 slope value
            quantum_n: Quantum score
        """
        current_time = time.time()
        with self._cache_lock:
            self._cache[symbol] = {
                "timestamp": current_time,
                "res_dict": result,
                "slope": slope,
                "quantum_n": quantum_n,
            }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self._cache_lock:
            self._cache.clear()
        log.info("DataService: Cache cleared")
    
    def get_market_regime(self) -> str:
        """Get current market regime based on breadth health.
        
        Returns:
            "BULL" if market healthy, "NEUTRAL" otherwise
        """
        return "BULL" if self._market_healthy else "NEUTRAL"


# Global singleton instance
_data_service: Optional[DataService] = None
_init_lock = threading.Lock()


def get_data_service() -> DataService:
    """Get the global data service singleton.
    
    Returns:
        Shared DataService instance
    """
    global _data_service
    
    if _data_service is None:
        with _init_lock:
            if _data_service is None:
                _data_service = DataService()
    
    return _data_service
