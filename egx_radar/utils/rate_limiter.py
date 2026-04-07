"""Token Bucket Rate Limiter for EGX Radar (Layer 4 Performance).

This module implements a per-source token bucket algorithm for rate limiting
API requests. Unlike the previous global lock approach, this allows:
  - Concurrent requests to different sources without blocking
  - Burst handling within rate limits
  - Proper 429 response handling with exponential backoff
  - No unnecessary sleep inside global locks

Usage:
    from egx_radar.utils.rate_limiter import RateLimiter, get_rate_limiter
    
    limiter = get_rate_limiter()
    
    # Before making a request
    limiter.acquire("yahoo")  # Blocks until token available
    
    # Or with timeout
    if limiter.try_acquire("twelve_data", timeout=30):
        make_request()
    else:
        handle_timeout()
"""

import logging
import threading
import time
from typing import Dict, Optional

log = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for a single API source.
    
    Implements the token bucket algorithm:
      - Bucket has maximum capacity (burst size)
      - Tokens are added at a fixed rate (refill rate)
      - Each request consumes one token
      - If no tokens available, request must wait
    """
    
    def __init__(self, rate: float, capacity: int = 1):
        """Initialize token bucket.
        
        Args:
            rate: Tokens added per second (e.g., 2.0 = 2 requests/sec)
            capacity: Maximum tokens in bucket (burst size)
        """
        self.rate = rate  # tokens per second
        self.capacity = capacity  # max burst
        self.tokens = float(capacity)  # start full
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire a token from the bucket.
        
        Args:
            blocking: If True, wait for token; if False, return immediately
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if token acquired, False if timeout/non-blocking and no token
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                
                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.rate
            
            if not blocking:
                return False
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False
                wait_time = min(wait_time, timeout - elapsed)
            
            # Sleep outside lock to allow other threads
            time.sleep(min(wait_time, 0.1))  # Cap at 100ms for responsiveness
    
    def try_acquire(self, timeout: Optional[float] = None) -> bool:
        """Try to acquire a token with optional timeout.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if token acquired, False if timeout
        """
        return self.acquire(blocking=True, timeout=timeout)
    
    def get_tokens(self) -> float:
        """Get current token count (for debugging)."""
        with self._lock:
            self._refill()
            return self.tokens
    
    def reset(self) -> None:
        """Reset bucket to full capacity."""
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_update = time.time()


class RateLimiter:
    """Per-source rate limiter using token buckets.
    
    This class manages token buckets for multiple API sources,
    allowing concurrent requests to different sources without
    unnecessary blocking.
    """
    
    def __init__(self):
        """Initialize rate limiter with default configurations."""
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        
        # Default rate limits (requests per second)
        # Source: API documentation and empirical testing
        self._default_rates = {
            "yahoo":           2.0,    # 2 req/sec (500ms interval)
            "stooq":          3.0,    # 3 req/sec (333ms interval)
            "twelve_data":     0.133,  # 8 req/min = 0.133 req/sec
            "alpha_vantage":   0.083,  # 5 req/min = 0.083 req/sec
            "investing":       1.0,    # Conservative estimate
            "trading_designer": 0.133,  # 8 req/min
        }
        
        # Burst capacity (tokens)
        self._default_capacity = {
            "yahoo": 2,
            "stooq": 3,
            "twelve_data": 1,  # No burst for strict limits
            "alpha_vantage": 1,
            "investing": 2,
            "trading_designer": 1,
        }
        
        # Initialize buckets
        for source, rate in self._default_rates.items():
            capacity = self._default_capacity.get(source, 1)
            self._buckets[source] = TokenBucket(rate=rate, capacity=capacity)
    
    def get_bucket(self, source: str) -> Optional[TokenBucket]:
        """Get token bucket for a source.
        
        Args:
            source: Source name (e.g., 'yahoo', 'twelve_data')
            
        Returns:
            TokenBucket for source, or None if not configured
        """
        with self._lock:
            if source not in self._buckets:
                # Create default bucket for unknown source
                self._buckets[source] = TokenBucket(rate=1.0, capacity=1)
            return self._buckets[source]
    
    def acquire(self, source: str, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request to a source.
        
        Args:
            source: Source name
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if permission granted, False if timeout
        """
        bucket = self.get_bucket(source)
        if bucket is None:
            log.warning("RateLimiter: Unknown source '%s', allowing request", source)
            return True
        
        return bucket.acquire(blocking=True, timeout=timeout)
    
    def try_acquire(self, source: str, timeout: float = 5.0) -> bool:
        """Try to acquire permission with default timeout.
        
        Args:
            source: Source name
            timeout: Maximum time to wait (default 5 seconds)
            
        Returns:
            True if permission granted, False if timeout
        """
        return self.acquire(source, timeout=timeout)
    
    def handle_429(self, source: str, retry_after: Optional[float] = None) -> None:
        """Handle HTTP 429 (Too Many Requests) response.
        
        This resets the bucket and applies additional backoff.
        
        Args:
            source: Source that returned 429
            retry_after: Seconds to wait from Retry-After header (if provided)
        """
        bucket = self.get_bucket(source)
        if bucket:
            bucket.reset()  # Reset to prevent immediate retry
            
            if retry_after:
                log.warning(
                    "RateLimiter: %s returned 429, backing off for %.1fs",
                    source, retry_after,
                )
                time.sleep(retry_after)
            else:
                # Exponential backoff: wait 2 seconds
                log.warning(
                    "RateLimiter: %s returned 429, applying backoff",
                    source,
                )
                time.sleep(2.0)
    
    def get_status(self) -> Dict[str, dict]:
        """Get status of all rate limiter buckets (for debugging).
        
        Returns:
            Dictionary mapping source names to status dicts
        """
        status = {}
        for source, bucket in self._buckets.items():
            status[source] = {
                "tokens": bucket.get_tokens(),
                "rate": bucket.rate,
                "capacity": bucket.capacity,
            }
        return status
    
    def reset_all(self) -> None:
        """Reset all buckets to full capacity."""
        for bucket in self._buckets.values():
            bucket.reset()


# Global singleton instance
_rate_limiter: Optional[RateLimiter] = None
_init_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter singleton.
    
    Returns:
        Shared RateLimiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        with _init_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()
    
    return _rate_limiter


# Legacy compatibility function - replaces old _rate_limit
def rate_limit(source: str, timeout: Optional[float] = 60.0) -> bool:
    """Legacy compatibility function for old _rate_limit calls.
    
    Args:
        source: Source name
        timeout: Maximum wait time (default 60 seconds)
        
    Returns:
        True if rate limit acquired, False if timeout
    """
    limiter = get_rate_limiter()
    return limiter.acquire(source, timeout=timeout)
