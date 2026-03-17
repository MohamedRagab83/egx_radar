from __future__ import annotations

"""Load historical OHLCV for backtest date range (2020-01-01 to today)."""

import logging
from typing import Dict

import pandas as pd
import yfinance as yf

from egx_radar.config.settings import K, SYMBOLS

log = logging.getLogger(__name__)


def load_backtest_data(
    date_from: str,
    date_to: str,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical OHLCV for all watchlist symbols over [date_from, date_to].
    Returns Dict[key=yahoo_ticker e.g. "COMI.CA", value=DataFrame with DatetimeIndex].
    Uses only past data; no look-ahead.
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
                auto_adjust=True,
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
            sub = _flatten(raw)
            if sub is not None and len(sub) >= K.MIN_BARS:
                result[chunk[0]] = sub
            continue
        for ticker in chunk:
            sub = _extract_ticker(raw, ticker)
            if sub is not None and len(sub) >= K.MIN_BARS:
                result[ticker] = sub
    return result


def _flatten(raw: pd.DataFrame) -> pd.DataFrame | None:
    if raw is None or raw.empty:
        return None
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip().title() for c in df.columns]
    df.rename(columns={
        "Adj Close": "Close",
        "Adjusted Close": "Close",
        "Adj_Close": "Close",
        "Turnover": "Volume",
    }, inplace=True)
    # Deduplicate columns if any (keep first)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # FIX-3D: OHLCV sanity check — verify Close is between Low and High on last bar.
    # If this fails, yfinance likely changed its column mapping in a new version.
    if len(df) > 0 and {"Close", "High", "Low"}.issubset(df.columns):
        last = df.iloc[-1]
        try:
            c = float(last["Close"])
            h = float(last["High"])
            l = float(last["Low"])
            if h > 0 and l > 0 and not (l <= c <= h):
                log.warning(
                    "_flatten: OHLCV sanity check failed on last bar "
                    "(Close=%.4f High=%.4f Low=%.4f). "
                    "Possible yfinance column inversion after API update. "
                    "Pin yfinance version in requirements.txt.",
                    c, h, l,
                )
                return None   # reject silently-corrupt data rather than pass it on
        except (TypeError, ValueError):
            pass   # NaN values — downstream layers will handle these
    
    return df if "Close" in df.columns else None


def _extract_ticker(raw: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    if raw is None or raw.empty:
        return None
    if not isinstance(raw.columns, pd.MultiIndex):
        return _flatten(raw)
    if ticker in raw.columns.get_level_values(0):
        try:
            return _flatten(raw[ticker].copy())
        except Exception:
            pass
    if ticker in raw.columns.get_level_values(1):
        try:
            return _flatten(raw.xs(ticker, axis=1, level=1).copy())
        except Exception:
            pass
    return None
