"""Data layer: source fetchers, OHLCV merge/orchestration, and DataEngine (Layer 2).

SECURITY NOTE (Phase 1 - Security Hardening):
  API keys are now managed via egx_radar.utils.secrets.SecretManager.
  Legacy _obfuscate/_deobfuscate functions removed (insecure base64 encoding).
"""

import logging

log = logging.getLogger(__name__)

# SECURITY FIX (Phase 1): Removed _obfuscate/_deobfuscate imports
# API keys now managed via SecureManager in egx_radar.utils.secrets
from egx_radar.data.fetchers import (
    # _obfuscate,       # REMOVED - insecure base64 obfuscation
    # _deobfuscate,     # REMOVED - insecure base64 deobfuscation
    load_source_settings,
    save_source_settings,
    _atomic_json_write,
    _flatten_df,
    _yfin_extract,
    _chunker,
    _fetch_yahoo,
    _fetch_stooq_single,
    _fetch_stooq,
    _fetch_av_single,
    _fetch_investing_single,
    _fetch_investing,
    _td_dispatch_lock,
    _fetch_td_single,
    _fetch_twelve_data,
)

from egx_radar.data.merge import (
    _merge_ohlcv,
    download_all,
    _source_labels,
    _source_labels_lock,
)

from egx_radar.data.source_scoring import (
    score_source,
    rank_sources,
    get_cache_snapshot,
    QUALITY_THRESHOLD,
    FALLBACK_THRESHOLD,
)

# DataEngine uses lazy imports to avoid circular dependency with backtest.data_loader.
# Import it last, and access via get_data_engine() at call time.
from egx_radar.data.data_engine import (
    DataEngine,
    get_data_engine,
)

__all__ = [
    # fetchers - SECURITY FIX: removed _obfuscate/_deobfuscate
    # "_obfuscate",    # REMOVED - insecure base64 obfuscation
    # "_deobfuscate",  # REMOVED - insecure base64 deobfuscation
    "load_source_settings",
    "save_source_settings",
    "_atomic_json_write",
    "_flatten_df",
    "_yfin_extract",
    "_chunker",
    "_fetch_yahoo",
    "_fetch_stooq_single",
    "_fetch_stooq",
    "_fetch_av_single",
    "_fetch_investing_single",
    "_fetch_investing",
    "_td_dispatch_lock",
    "_fetch_td_single",
    "_fetch_twelve_data",
    # merge
    "_merge_ohlcv",
    "download_all",
    "_source_labels",
    "_source_labels_lock",
    # source scoring
    "score_source",
    "rank_sources",
    "get_cache_snapshot",
    "QUALITY_THRESHOLD",
    "FALLBACK_THRESHOLD",
    # data engine
    "DataEngine",
    "get_data_engine",
]
