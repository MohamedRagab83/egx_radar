"""
data/loader.py — EGX Radar Pro
==================================
Market data loading layer.

Current implementation: deterministic synthetic OHLCV generator for
development, backtesting, and CI validation.

Production migration
--------------------
Replace synthetic_ohlcv() with a real market data feed. Options:

  Option A — yfinance (free, easy, EGX tickers ending in .CA)
  ─────────────────────────────────────────────────────────────
      import yfinance as yf

      def load_market_data(symbols, start="2020-01-01", end=None):
          data = {}
          for sym in symbols:
              df = yf.download(f"{sym}.CA", start=start, end=end, auto_adjust=True)
              df = df.rename(columns={"Open":"Open","High":"High",
                                      "Low":"Low","Close":"Close","Volume":"Volume"})
              if not df.empty:
                  data[sym] = df
          return data

  Option B — Refinitiv / Bloomberg API
  ──────────────────────────────────────
      Contact your data provider for the Python SDK.

  Option C — EGX direct download (CSV)
  ──────────────────────────────────────
      Download the daily EOD CSV from https://www.egx.com.eg/,
      parse it with pandas, and load into the same {symbol: DataFrame} format.

Required DataFrame format
-------------------------
  Index : pd.DatetimeIndex (business days, UTC or timezone-naive)
  Columns required:
    Open   : float  (opening price)
    High   : float  (daily high)
    Low    : float  (daily low)
    Close  : float  (closing price)
    Volume : float or int (shares traded)
"""

from __future__ import annotations

import hashlib
from typing import Dict, Iterable

import numpy as np
import pandas as pd


def _stable_int(symbol: str) -> int:
    digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def synthetic_ohlcv(
    symbol: str,
    start:  str = "2023-01-01",
    bars:   int = 320,
) -> pd.DataFrame:
    """
    Generate deterministic, reproducible synthetic OHLCV data.

    Properties
    ----------
    - Same symbol always produces identical series (hash-seeded RNG)
    - Positive drift + EGX-realistic daily volatility (~1.2–1.9%)
    - Intraday ranges (High/Low spread ~0.6–1.0% of Close)
    - Volume follows a uniform random distribution with per-symbol scaling

    Parameters
    ----------
    symbol : EGX ticker (e.g. "COMI", "TMGH")
    start  : ISO date string for the first trading day
    bars   : Number of business day bars to generate

    Returns
    -------
    pd.DataFrame with columns [Open, High, Low, Close, Volume]
    and a pd.DatetimeIndex of business days.
    """
    base_int = _stable_int(symbol)
    seed  = base_int % (2 ** 32 - 1)
    rng   = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=bars)

    # Per-symbol drift and volatility parameters (deterministic)
    drift = 0.0006 + (base_int % 5) * 0.0001   # 0.06–0.10% daily
    vol   = 0.012  + (base_int % 7) * 0.001    # 1.2–1.9% daily

    # Price series — geometric random walk with positive drift
    base = 20.0 + (base_int % 80)
    prices = [float(base)]
    for _ in range(1, bars):
        ret = rng.normal(drift, vol)
        prices.append(max(1.0, prices[-1] * (1.0 + ret)))

    close_arr = np.array(prices, dtype=float)

    # OHLCV construction
    open_arr   = close_arr * (1.0 + rng.normal(0.0, 0.002, bars))
    spread_hi  = np.abs(rng.normal(0.004, 0.003, bars))
    spread_lo  = np.abs(rng.normal(0.004, 0.003, bars))
    high_arr   = np.maximum(open_arr, close_arr) * (1.0 + spread_hi)
    low_arr    = np.minimum(open_arr, close_arr) * (1.0 - spread_lo)
    volume_arr = rng.integers(150_000, 2_200_000, bars).astype(float)

    return pd.DataFrame(
        {
            "Open":   open_arr,
            "High":   high_arr,
            "Low":    low_arr,
            "Close":  close_arr,
            "Volume": volume_arr,
        },
        index=dates,
    )


def load_market_data(
    symbols: Iterable[str],
    start:   str = "2023-01-01",
    bars:    int = 320,
) -> Dict[str, pd.DataFrame]:
    """
    Load OHLCV data for a list of symbols.

    Currently delegates to synthetic data.
    Swap the body of this function for a real data provider in production.

    Parameters
    ----------
    symbols : Iterable of EGX tickers
    start   : Data start date (used only by synthetic generator)
    bars    : Number of bars per symbol (used only by synthetic generator)

    Returns
    -------
    {symbol: OHLCV DataFrame}
    """
    return {sym: synthetic_ohlcv(sym, start=start, bars=bars) for sym in symbols}
