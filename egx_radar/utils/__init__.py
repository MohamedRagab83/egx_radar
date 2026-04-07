"""EGX Radar utilities package.

Provides secure secret management, trade identity utilities, rate limiting, logging helpers, and other utilities.
"""

from egx_radar.utils.secrets import (
    SecretManager,
    get_secrets_manager,
    secure_get_key,
    secure_set_key,
)

from egx_radar.utils.trade_id import (
    generate_trade_uid,
    validate_trade_uid,
    generate_signal_uid,
    verify_trade_match,
    extract_uid_components,
)

from egx_radar.utils.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    rate_limit,
    TokenBucket,
)

__all__ = [
    # Security
    "SecretManager",
    "get_secrets_manager",
    "secure_get_key",
    "secure_set_key",
    # Trade identity
    "generate_trade_uid",
    "validate_trade_uid",
    "generate_signal_uid",
    "verify_trade_match",
    "extract_uid_components",
    # Rate limiting
    "RateLimiter",
    "get_rate_limiter",
    "rate_limit",
    "TokenBucket",
]
