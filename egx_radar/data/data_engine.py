"""Unified data entry point for EGX Radar (Layer 2).

DataEngine wraps both the live multi-source pipeline (download_all)
and the backtest Yahoo-only pipeline (load_backtest_data) behind a
single interface.

OUTPUT CONTRACT (unchanged):
    Dict[str, pd.DataFrame]
    Keys   = Yahoo tickers (e.g. "COMI.CA")
    Values = OHLCV DataFrames with DatetimeIndex
    Columns guaranteed: Open, High, Low, Close, Volume

This module does NOT add new features, APIs, or data sources.
It only unifies existing paths and adds consistency logging.
"""

import hashlib
import logging
import pathlib
import pickle
import tempfile
import time
from typing import Dict, Optional

import pandas as pd

log = logging.getLogger(__name__)

# ── Disk cache for OHLCV data ────────────────────────────────────────────
_CACHE_DIR = pathlib.Path(tempfile.gettempdir()) / "egx_radar_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key() -> str:
    """Generate cache key from enabled data sources."""
    from egx_radar.config.settings import DATA_SOURCE_CFG
    key_data = str(sorted(DATA_SOURCE_CFG.items()))
    return hashlib.md5(key_data.encode()).hexdigest()


def _cache_path() -> pathlib.Path:
    key = _cache_key()
    return _CACHE_DIR / f"{key}.pkl"


def _cache_load() -> Optional[Dict[str, pd.DataFrame]]:
    """Return cached data if fresh (within CACHE_TTL_SECONDS), else None."""
    try:
        p = _cache_path()
        if not p.exists():
            return None
        age = time.time() - p.stat().st_mtime
        if age > K.CACHE_TTL_SECONDS:
            return None
        with open(p, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _cache_save(data: Dict[str, pd.DataFrame]) -> None:
    """Save OHLCV data to disk cache."""
    try:
        with open(_cache_path(), "wb") as f:
            pickle.dump(data, f)
    except Exception:
        pass

# ── Required OHLCV columns ────────────────────────────────────────────────
_REQUIRED_COLS = {"Open", "High", "Low", "Close", "Volume"}


def _normalise_ohlcv(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Ensure every DataFrame in the result has a consistent schema.

    Guarantees:
      - All 5 OHLCV columns present (Volume defaults to 0.0)
      - DatetimeIndex (not RangeIndex or string index)
      - Sorted ascending by date
      - No duplicate index entries
    """
    clean: Dict[str, pd.DataFrame] = {}
    for sym, df in data.items():
        if df is None or df.empty:
            continue
        df = df.copy()

        # Ensure Volume exists
        if "Volume" not in df.columns:
            df["Volume"] = 0.0

        # Verify required columns
        missing = _REQUIRED_COLS - set(df.columns)
        if missing:
            log.warning("DataEngine: %s missing columns %s — skipping", sym, missing)
            continue

        # Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                log.warning("DataEngine: %s has non-datetime index — skipping", sym)
                continue

        # Sort and deduplicate
        df = df.sort_index()
        if df.index.duplicated().any():
            df = df[~df.index.duplicated(keep="last")]

        clean[sym] = df

    return clean


class DataEngine:
    """Unified data access for live scan and backtest paths.

    Usage:
        engine = DataEngine()
        data = engine.fetch_live()              # live multi-source
        data = engine.fetch_backtest("2024-01-01", "2025-12-31")  # backtest
    """

    def fetch_live(self) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV from all enabled live sources (Yahoo, Stooq, AV, TD, INV).

        This wraps ``download_all()`` from ``data.merge`` and adds
        post-fetch normalisation to guarantee a consistent schema.

        Returns:
            Dict[yahoo_ticker, DataFrame] with OHLCV + DatetimeIndex.
        """
        from egx_radar.config.settings import K
        from egx_radar.data.merge import download_all, _source_labels, _source_labels_lock

        # Check disk cache first
        cached = _cache_load()
        if cached is not None:
            log.debug("cache hit: %d symbols", len(cached))
            return cached

        log.info("DataEngine.fetch_live: starting multi-source download")
        raw = download_all()

        result = _normalise_ohlcv(raw)

        # Log source summary
        with _source_labels_lock:
            labels = dict(_source_labels)
        fallback_count = sum(1 for v in labels.values() if "Yahoo" not in v)
        if fallback_count:
            log.info(
                "DataEngine.fetch_live: %d symbols loaded, %d used fallback sources",
                len(result), fallback_count,
            )
        else:
            log.info("DataEngine.fetch_live: %d symbols loaded (all from Yahoo)", len(result))

        # Save to disk cache
        if result:
            _cache_save(result)

        return result

    def fetch_backtest(
        self,
        date_from: str,
        date_to: str,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV for backtest date range (Yahoo only, auto_adjust=False).

        This wraps ``load_backtest_data()`` from ``backtest.data_loader``
        and adds the same post-fetch normalisation as the live path,
        ensuring column parity.

        Returns:
            Dict[yahoo_ticker, DataFrame] with OHLCV + DatetimeIndex.
        """
        from egx_radar.backtest.data_loader import load_backtest_data

        log.info(
            "DataEngine.fetch_backtest: %s to %s",
            date_from, date_to,
        )
        raw = load_backtest_data(date_from, date_to)

        result = _normalise_ohlcv(raw)

        log.info("DataEngine.fetch_backtest: %d symbols loaded", len(result))
        return result

    def get_source_labels(self) -> Dict[str, str]:
        """Return a snapshot of the per-symbol source labels from the last fetch."""
        from egx_radar.data.merge import _source_labels, _source_labels_lock

        with _source_labels_lock:
            return dict(_source_labels)


# ── Module-level singleton ────────────────────────────────────────────────
_engine: Optional[DataEngine] = None


def get_data_engine() -> DataEngine:
    """Get or create the global DataEngine singleton."""
    global _engine
    if _engine is None:
        _engine = DataEngine()
    return _engine
