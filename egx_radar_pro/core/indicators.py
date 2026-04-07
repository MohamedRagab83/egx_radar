"""
core/indicators.py — EGX Radar Pro
======================================
Low-level technical indicator calculations.

All functions are stateless and take slices of OHLCV data as input.
They return scalar floats — no side-effects.

Dependencies: numpy, pandas, utils.helpers  (no other internal imports)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from utils.helpers import clamp


def rsi_wilder(close: pd.Series, period: int = 14) -> float:
    """
    Wilder-smoothed Relative Strength Index.

    Uses a simplified Wilder smoothing approximation over the last
    (period + 16) bars for computational efficiency.

    Returns 50.0 when insufficient data is available.
    """
    arr = close.to_numpy(dtype=float)
    if len(arr) < period + 2:
        return 50.0

    delta = np.diff(arr[-(period + 16):])
    gain  = np.maximum(delta, 0.0)
    loss  = np.maximum(-delta, 0.0)

    avg_gain = float(np.mean(gain[-period:]))
    avg_loss = float(np.mean(loss[-period:]))

    if avg_loss <= 1e-9:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def atr_wilder(df: pd.DataFrame, period: int = 14) -> float:
    """
    Wilder Average True Range.

    Computes True Range = max(H-L, |H-Cprev|, |L-Cprev|) then
    takes a simple mean over the last `period` bars as an approximation.

    Returns 0.0 when insufficient data is available.
    """
    if len(df) < period + 2:
        return 0.0

    hi = df["High"].to_numpy(dtype=float)
    lo = df["Low"].to_numpy(dtype=float)
    cl = df["Close"].to_numpy(dtype=float)

    n  = min(len(df), period + 24)
    hi, lo, cl = hi[-n:], lo[-n:], cl[-n:]

    prev_close    = np.roll(cl, 1)
    prev_close[0] = cl[0]

    tr = np.maximum(
        hi - lo,
        np.maximum(np.abs(hi - prev_close), np.abs(lo - prev_close)),
    )
    atr = float(np.mean(tr[-period:]))
    return atr if math.isfinite(atr) else 0.0


def ema_last(series: pd.Series, span: int) -> float:
    """
    Exponential moving average — returns the last value only.

    Uses pandas ewm with adjust=False (Wilder-style recursive formula).
    """
    return float(series.astype(float).ewm(span=span, adjust=False).mean().iloc[-1])


def volume_ratio(volume: pd.Series, window: int = 20) -> float:
    """
    Current bar volume divided by the rolling average volume.

    Returns 1.0 (neutral) when insufficient data is available.
    """
    v   = volume.astype(float)
    avg = float(v.rolling(window).mean().iloc[-1]) if len(v) >= window else float(v.mean())
    return float(v.iloc[-1]) / max(avg, 1e-9)
