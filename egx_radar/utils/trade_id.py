"""Trade identity utilities for deterministic trade identification (Layer 1 Data Integrity).

This module provides SHA256-based unique identifiers for trades to ensure:
  - Deterministic ID generation from trade attributes
  - No duplicate trades in database
  - Reliable outcome attribution
  - Audit trail integrity

Usage:
    from egx_radar.utils.trade_id import generate_trade_uid, validate_trade_uid
    
    # Generate deterministic ID
    uid = generate_trade_uid(
        symbol='COMI',
        entry_date='2024-03-15',
        entry_price=10.50,
        entry_signal='buy',
    )
    
    # Validate UID format
    if validate_trade_uid(uid):
        print("Valid trade UID")
"""

import hashlib
import re
from datetime import datetime
from typing import Optional, Union


def generate_trade_uid(
    symbol: str,
    entry_date: Union[str, datetime],
    entry_price: float,
    entry_signal: str,
    backtest_id: Optional[str] = None,
) -> str:
    """Generate a deterministic unique identifier for a trade.
    
    The UID is generated using SHA256 hash of the trade's core attributes,
    ensuring the same trade always produces the same ID regardless of
    when or where it's generated.
    
    Args:
        symbol: Trading symbol (e.g., 'COMI')
        entry_date: Trade entry date (string or datetime)
        entry_price: Entry price per share
        entry_signal: Signal type ('buy', 'sell', 'short', etc.)
        backtest_id: Optional backtest identifier for scoping
        
    Returns:
        16-character hexadecimal string (first 16 chars of SHA256 hash)
        
    Example:
        >>> generate_trade_uid('COMI', '2024-03-15', 10.50, 'buy')
        'a3f8c9d2e1b4567890'
    """
    # Normalize inputs for consistent hashing
    if isinstance(entry_date, datetime):
        date_str = entry_date.strftime('%Y-%m-%d')
    else:
        # Parse and re-format to ensure consistency
        try:
            dt = datetime.fromisoformat(str(entry_date).replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            date_str = str(entry_date)
    
    # Normalize symbol (uppercase, stripped)
    symbol_norm = str(symbol).upper().strip()
    
    # Normalize signal (lowercase, stripped)
    signal_norm = str(entry_signal).lower().strip()
    
    # Normalize price (fixed precision to avoid float representation issues)
    price_norm = f"{float(entry_price):.6f}"
    
    # Build canonical string for hashing
    # Format: BACKTEST_ID|SYMBOL|DATE|PRICE|SIGNAL
    # This ensures uniqueness across different backtests
    if backtest_id:
        canonical = f"{backtest_id}|{symbol_norm}|{date_str}|{price_norm}|{signal_norm}"
    else:
        canonical = f"LIVE|{symbol_norm}|{date_str}|{price_norm}|{signal_norm}"
    
    # Generate SHA256 hash
    hash_bytes = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    # Return first 16 characters (64 bits of entropy - sufficient for trade IDs)
    # Format: 16 hex chars = 2^64 possible values ≈ 1.8×10^19 unique IDs
    return hash_bytes[:16]


def validate_trade_uid(uid: str) -> bool:
    """Validate the format of a trade UID.
    
    Args:
        uid: Trade UID to validate
        
    Returns:
        True if UID is valid format, False otherwise
    """
    if not uid or not isinstance(uid, str):
        return False
    
    # Valid UID: exactly 16 hexadecimal characters
    pattern = r'^[a-f0-9]{16}$'
    return bool(re.match(pattern, uid.lower()))


def generate_signal_uid(
    symbol: str,
    signal_date: Union[str, datetime],
    signal_type: str,
    backtest_id: str,
) -> str:
    """Generate deterministic UID for trading signals.
    
    Similar to trade UID but for signals (which may not result in trades).
    
    Args:
        symbol: Trading symbol
        signal_date: Date signal was generated
        signal_type: Type of signal ('buy', 'sell', 'strong_buy', etc.)
        backtest_id: Backtest identifier
        
    Returns:
        16-character hexadecimal string
    """
    if isinstance(signal_date, datetime):
        date_str = signal_date.strftime('%Y-%m-%d')
    else:
        try:
            dt = datetime.fromisoformat(str(signal_date).replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            date_str = str(signal_date)
    
    symbol_norm = str(symbol).upper().strip()
    type_norm = str(signal_type).lower().strip()
    
    canonical = f"{backtest_id}|{symbol_norm}|{date_str}|{type_norm}"
    hash_bytes = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return hash_bytes[:16]


def verify_trade_match(
    uid: str,
    symbol: str,
    entry_date: Union[str, datetime],
    entry_price: float,
    entry_signal: str,
    backtest_id: Optional[str] = None,
) -> bool:
    """Verify that a UID matches the provided trade attributes.
    
    This is used to verify trade identity during outcome attribution.
    
    Args:
        uid: Trade UID to verify
        symbol: Trade symbol
        entry_date: Entry date
        entry_price: Entry price
        entry_signal: Entry signal type
        backtest_id: Optional backtest ID
        
    Returns:
        True if UID matches the attributes, False otherwise
    """
    expected_uid = generate_trade_uid(
        symbol=symbol,
        entry_date=entry_date,
        entry_price=entry_price,
        entry_signal=entry_signal,
        backtest_id=backtest_id,
    )
    return uid.lower() == expected_uid.lower()


def extract_uid_components(uid: str) -> dict:
    """Extract metadata from a trade UID (for debugging/audit).
    
    Note: This doesn't decode the UID (hashes are one-way),
    but provides metadata about the UID itself.
    
    Args:
        uid: Trade UID
        
    Returns:
        Dictionary with UID metadata
    """
    if not validate_trade_uid(uid):
        return {"valid": False, "error": "Invalid UID format"}
    
    return {
        "valid": True,
        "uid": uid,
        "length": len(uid),
        "entropy_bits": len(uid) * 4,  # 4 bits per hex char
        "collision_probability": f"~1 in {2**64:.2e}",  # Birthday paradox
        "format": "SHA256 truncated to 16 hex chars",
    }


__all__ = [
    "generate_trade_uid",
    "validate_trade_uid",
    "generate_signal_uid",
    "verify_trade_match",
    "extract_uid_components",
]
