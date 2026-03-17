"""Data fetchers: multi-source OHLCV and supporting helpers (Layer 2)."""

import base64
import csv
import json
import logging
import math
import os
import re
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from egx_radar.config.settings import K, DATA_SOURCE_CFG, _data_cfg_lock, SOURCE_SETTINGS_FILE

log = logging.getLogger(__name__)


def _obfuscate(key: str) -> str:
    return base64.b64encode(key.encode()).decode() if key else ""


def _deobfuscate(enc: str) -> str:
    if not enc:
        return ""
    try:
        return base64.b64decode(enc.encode()).decode()
    except Exception:
        return enc


def load_source_settings() -> None:
    if not os.path.exists(SOURCE_SETTINGS_FILE):
        return
    try:
        with open(SOURCE_SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        saved["alpha_vantage_key"] = _deobfuscate(saved.get("alpha_vantage_key", ""))
        saved["twelve_data_key"]   = _deobfuscate(saved.get("twelve_data_key",   ""))
        with _data_cfg_lock:
            DATA_SOURCE_CFG.update(saved)
    except Exception as e:
        log.warning("load_source_settings: %s", e)


def save_source_settings() -> None:
    try:
        with _data_cfg_lock:
            snap = dict(DATA_SOURCE_CFG)
        snap["alpha_vantage_key"] = _obfuscate(str(snap.get("alpha_vantage_key", "")))
        snap["twelve_data_key"]   = _obfuscate(str(snap.get("twelve_data_key",   "")))
        _atomic_json_write(SOURCE_SETTINGS_FILE, snap)
    except Exception as e:
        log.error("save_source_settings: %s", e)


def _atomic_json_write(filepath: str, data: object) -> None:
    """Write JSON atomically: temp → os.replace()."""
    dirpath = os.path.dirname(os.path.abspath(filepath)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp", prefix=".egx_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, filepath)
    except Exception as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _flatten_df(raw: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Normalise OHLCV column names and strip MultiIndex.

    Handles new yfinance (>=0.2.x) format where MultiIndex is (field, ticker)
    AND old format where it was (ticker, field).
    """
    if raw is None or raw.empty:
        return None
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # Auto-detect format by checking if level 0 contains field names
        lv0_vals = set(str(v).title() for v in df.columns.get_level_values(0))
        ohlcv = {"Close", "Open", "High", "Low", "Volume", "Adj Close"}
        if lv0_vals & ohlcv:
            # New yfinance format: (field, ticker) — collapse level 0
            df.columns = df.columns.get_level_values(0)
        else:
            # Old format: (ticker, field) — take first ticker's slice
            first_ticker = df.columns.get_level_values(0)[0]
            df = df[first_ticker].copy()
    # Guarantee every column is a 1-D Series, not a nested DataFrame
    for col in list(df.columns):
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    df.columns = [str(c).strip().title() for c in df.columns]
    df.rename(columns={
        "Adj Close": "Close", "Adjusted Close": "Close",
        "Adj_Close": "Close", "Turnover": "Volume",
    }, inplace=True)
    seen: dict = {}
    df = df.loc[:, [not (c in seen or seen.update({c: True})) for c in df.columns]]
    return df if "Close" in df.columns else None


def _yfin_extract(raw: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
    """Robustly extract a single ticker from a yfinance MultiIndex DataFrame.

    Handles both old format (ticker, field) and new yfinance (field, ticker).
    """
    if raw is None or raw.empty:
        return None
    if not isinstance(raw.columns, pd.MultiIndex):
        return _flatten_df(raw)

    lv0 = set(raw.columns.get_level_values(0))
    lv1 = set(raw.columns.get_level_values(1))

    # Detect new yfinance format: level 0 = field names, level 1 = tickers
    ohlcv = {"Close", "Open", "High", "Low", "Volume", "Adj Close"}
    lv0_titled = {str(v).title() for v in lv0}
    if lv0_titled & ohlcv:
        # New format: (field, ticker) — look for ticker in level 1
        if ticker in lv1:
            try:
                sub = raw.xs(ticker, axis=1, level=1).copy()
                return _flatten_df(sub)
            except Exception as exc:
                log.debug("_yfin_extract %s: %s", ticker, exc)
        # Case-insensitive fallback on level 1
        for v in lv1:
            if str(v).upper() == ticker.upper():
                try:
                    sub = raw.xs(v, axis=1, level=1).copy()
                    return _flatten_df(sub)
                except Exception as exc:
                    log.debug("_yfin_extract %s: %s", ticker, exc)
                    continue
        return None

    # Old format: (ticker, field) — look for ticker in level 0
    if ticker in lv0:
        try:
            return _flatten_df(raw[ticker].copy())
        except Exception as exc:
            log.debug("_yfin_extract %s: %s", ticker, exc)
            return None
    if ticker in lv1:
        try:
            return _flatten_df(raw.xs(ticker, axis=1, level=1).copy())
        except Exception as exc:
            log.debug("_yfin_extract %s: %s", ticker, exc)
            return None
    # Case-insensitive fallback
    for lv, vals in [(0, lv0), (1, lv1)]:
        for v in vals:
            if str(v).upper() == ticker.upper():
                try:
                    sub = raw[v].copy() if lv == 0 else raw.xs(v, axis=1, level=1).copy()
                    return _flatten_df(sub)
                except Exception as exc:
                    log.debug("_yfin_extract %s: %s", ticker, exc)
                    continue
    return None


def _chunker(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def _fetch_yahoo(yahoo_syms: List[str]) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    for chunk in _chunker(yahoo_syms, K.CHUNK_SIZE):
        for attempt in range(K.MAX_DOWNLOAD_RETRIES + 1):
            try:
                # auto_adjust=False: let _normalise_df() apply Adj Close → Close
                # uniformly across all sources to avoid double-adjustment.
                raw = yf.download(
                    chunk, interval="1d", period="2y",
                    group_by="ticker", auto_adjust=False,
                    progress=False, timeout=K.DOWNLOAD_TIMEOUT,
                )
                if raw is None or raw.empty:
                    break
                for ticker in chunk:
                    if len(chunk) == 1 and not isinstance(raw.columns, pd.MultiIndex):
                        sub = _flatten_df(raw)
                    else:
                        sub = _yfin_extract(raw, ticker)
                    if sub is not None and not sub.empty:
                        result[ticker] = sub
                break
            except Exception as exc:
                if attempt < K.MAX_DOWNLOAD_RETRIES:
                    time.sleep(K.RETRY_BACKOFF_BASE ** attempt)
                else:
                    log.error("Yahoo chunk %s failed: %s", chunk, exc)
    return result


def _fetch_stooq_single(sym: str) -> Optional[pd.DataFrame]:
    url = f"https://stooq.com/q/d/l/?s={sym.lower()}.eg&i=d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        if "No data" in text or len(text.strip()) < 50:
            return None
        df = pd.read_csv(StringIO(text), parse_dates=["Date"], index_col="Date")
        df.columns = [c.strip().title() for c in df.columns]
        df = df.sort_index()
        return df if not df.empty and "Close" in df.columns else None
    except Exception as exc:
        log.debug("Stooq %s: %s", sym, exc)
        return None


def _fetch_stooq(sym_list: List[str]) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    lock   = threading.Lock()

    def _work(sym: str):
        df = _fetch_stooq_single(sym)
        if df is not None:
            with lock:
                result[sym] = df

    with ThreadPoolExecutor(max_workers=K.STOOQ_MAX_WORKERS) as pool:
        futs = [pool.submit(_work, s) for s in sym_list]
        for f in as_completed(futs, timeout=25):
            try:
                f.result()
            except Exception as exc:
                log.debug("Stooq worker: %s", exc)
    return result


def _fetch_av_single(sym: str, api_key: str) -> Optional[pd.DataFrame]:
    url = (
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY_ADJUSTED&symbol={urllib.parse.quote(sym+'.CA')}"
        f"&outputsize=full&apikey={api_key}&datatype=csv"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        if "Invalid API" in text or len(text) < 100:
            return None
        df = pd.read_csv(StringIO(text), parse_dates=["timestamp"], index_col="timestamp")
        df.index.name = "Date"
        df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume", "adjusted_close": "Adj Close"
        }, inplace=True)
        df = df.sort_index()
        if "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        return df if not df.empty and "Close" in df.columns else None
    except Exception as exc:
        log.debug("AlphaVantage %s: %s", sym, exc)
        return None


def _fetch_investing_single(sym: str) -> Optional[float]:
    slug_map: Dict[str, str] = {
        "COMI": "commercial-international-bank-egypt", "CIEB": "cib-egypt",
        "TMGH": "talaat-moustafa-group", "ETEL": "telecom-egypt",
        "ORAS": "orascom-construction", "PHDC": "palm-hills-developments",
        "SKPC": "sidi-kerir-petrochemicals", "AMOC": "alexandria-mineral-oils",
        "EAST": "eastern-company", "ABUK": "abu-kir-fertilizers",
    }
    slug = slug_map.get(sym)
    if not slug:
        return None
    url = f"https://www.investing.com/equities/{slug}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'data-test="instrument-price-last"[^>]*>([\d,.]+)', html)
        if not m:
            m = re.search(r'"price":\s*"([\d.]+)"', html)
        if not m:
            return None
        price = float(m.group(1).replace(",", ""))
        return price if price > 0 else None
    except Exception as exc:
        log.debug("Investing.com %s: %s", sym, exc)
        return None


def _fetch_investing(sym_list: List[str]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    lock   = threading.Lock()

    def _work(sym: str):
        price = _fetch_investing_single(sym)
        if price:
            with lock:
                result[sym] = price

    with ThreadPoolExecutor(max_workers=K.INVESTING_MAX_WORKERS) as pool:
        futs = [pool.submit(_work, s) for s in sym_list]
        for f in as_completed(futs, timeout=30):
            try:
                f.result()
            except Exception as exc:
                log.debug("Investing worker: %s", exc)
    return result


_td_dispatch_lock = threading.Lock()


def _fetch_td_single(sym: str, api_key: str) -> Optional[pd.DataFrame]:
    url = (
        "https://api.twelvedata.com/time_series"
        f"?symbol={urllib.parse.quote(sym)}&exchange=EGX"
        f"&interval=1day&outputsize={K.TD_BARS}&format=JSON"
        f"&apikey={urllib.parse.quote(api_key)}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        if "code" in data and data["code"] != 200:
            return None
        values = data.get("values") or []
        records = []
        for bar in values:
            try:
                records.append({
                    "Date":   pd.Timestamp(bar["datetime"]),
                    "Open":   float(bar["open"]),   "High":   float(bar["high"]),
                    "Low":    float(bar["low"]),    "Close":  float(bar["close"]),
                    "Volume": float(bar.get("volume", 0)),
                })
            except (KeyError, ValueError, TypeError):
                continue
        if not records:
            return None
        df = pd.DataFrame(records).set_index("Date").sort_index()
        return df if len(df) >= K.MIN_BARS_RELAXED else None
    except Exception as exc:
        log.debug("TwelveData %s: %s", sym, exc)
        return None


def _fetch_twelve_data(sym_list: List[str], api_key: str) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    result_lock = threading.Lock()

    def _work(sym: str):
        with _td_dispatch_lock:
            time.sleep(K.TD_REQUEST_DELAY)
            df = _fetch_td_single(sym, api_key)
        if df is not None:
            with result_lock:
                result[sym] = df

    with ThreadPoolExecutor(max_workers=K.TD_MAX_WORKERS) as pool:
        futs = [pool.submit(_work, s) for s in sym_list]
        timeout = len(sym_list) * K.TD_REQUEST_DELAY + 30
        for f in as_completed(futs, timeout=timeout):
            try:
                f.result()
            except Exception as exc:
                log.debug("TD worker: %s", exc)
    return result


__all__ = [
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
]

