"""Data layer: source fetchers and OHLCV merge/orchestration (Layer 2)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.data.fetchers import (
    _obfuscate,
    _deobfuscate,
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

__all__ = [
    # fetchers
    "_obfuscate",
    "_deobfuscate",
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
]
