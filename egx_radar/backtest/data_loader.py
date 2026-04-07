from __future__ import annotations

"""Load historical OHLCV for backtest date range.

PARITY FIX: Uses auto_adjust=False + _flatten_df() from fetchers,
identical to the live-scan Yahoo path.  This ensures OHLCV values
are the same in both live and backtest for the same symbol/date.
"""

import logging
from typing import Dict

import pandas as pd
import yfinance as yf

from egx_radar.config.settings import K, SYMBOLS
from egx_radar.data.fetchers import _flatten_df, _yfin_extract

log = logging.getLogger(__name__)


def load_backtest_data(
    date_from: str,
    date_to: str,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical OHLCV for all watchlist symbols over [date_from, date_to].
    Returns Dict[key=yahoo_ticker e.g. "COMI.CA", value=DataFrame with DatetimeIndex].
    Uses only past data; no look-ahead.

    PARITY: auto_adjust=False + _flatten_df() — same as live-scan path.
    """
    sym_list = list(SYMBOLS.values())
    result: Dict[str, pd.DataFrame] = {}
    for chunk_start in range(0, len(sym_list), K.CHUNK_SIZE):
        chunk = sym_list[chunk_start : chunk_start + K.CHUNK_SIZE]
        try:
            raw = yf.download(
                chunk,
                start=date_from,
                end=date_to,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                timeout=K.DOWNLOAD_TIMEOUT,
                threads=True,
            )
        except Exception as exc:
            log.warning("Backtest yfinance chunk %s failed: %s", chunk, exc)
            continue
        if raw is None or raw.empty:
            continue
        if len(chunk) == 1 and not isinstance(raw.columns, pd.MultiIndex):
            sub = _flatten_df(raw)
            if sub is not None and len(sub) >= K.MIN_BARS:
                result[chunk[0]] = sub
            continue
        for ticker in chunk:
            sub = _yfin_extract(raw, ticker)
            if sub is not None and len(sub) >= K.MIN_BARS:
                result[ticker] = sub
    return result
