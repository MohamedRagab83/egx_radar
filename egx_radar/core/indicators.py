"""Technical indicator functions for EGX Radar."""

import logging
import pandas as pd
from typing import Optional, Tuple
from egx_radar.config.settings import K


log = logging.getLogger(__name__)


def safe_clamp(val: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, val))


def last_val(s: pd.Series) -> float:
    """Get the last value from a series."""
    s = s.dropna()
    return float(s.iloc[-1]) if not s.empty else 0.0


def compute_atr(df: pd.DataFrame, length: int = 14) -> Optional[float]:
    """Compute ATR (Average True Range)."""
    if length is None:
        length = K.ATR_LENGTH
    if len(df) < 2:
        return None
    try:
        h = df["High"].reset_index(drop=True)
        l = df["Low"].reset_index(drop=True)
        c = df["Close"].reset_index(drop=True)
        tr = pd.concat([
            h - l,
            (h - c.shift()).abs(),
            (l - c.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = float(tr.tail(length).mean())
        return atr if (atr is not None and atr > 0) else None
    except Exception as exc:
        log.debug("compute_atr failed for input: %s", exc)
        return None


def compute_atr_risk(df: pd.DataFrame, price: float) -> Tuple[str, float]:
    """Compute ATR percentile-based risk scoring."""
    if price <= 0 or len(df) < K.ATR_LENGTH + 5:
        return "—", 0.0
    try:
        h = df["High"].reset_index(drop=True)
        l = df["Low"].reset_index(drop=True)
        c = df["Close"].reset_index(drop=True)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr_series = tr.rolling(K.ATR_LENGTH).mean().dropna()
        if len(atr_series) < 5:
            return "—", 0.0
        hist = atr_series.iloc[-K.ATR_HIST_WINDOW:].values
        current = hist[-1]

        # ATR normalization: compare percentage ATR, not raw points.
        # Raw ATR cannot be compared across stocks at different price levels.
        # A 2-point ATR on a 10 EGP stock (20%) is very different from
        # a 2-point ATR on a 100 EGP stock (2%).
        if getattr(K, "ATR_NORMALIZE_BY_PRICE", True) and price > 0:
            hist    = hist / price * 100.0   # convert each historical ATR to % of price
            current = current / price * 100.0

        pct = float((hist <= current).mean()) * 100.0
        if pct >= K.ATR_PCT_HIGH:
            return "⚠️ HIGH", pct
        if pct >= K.ATR_PCT_MED:
            return "🟡 MED", pct
        return "🟢 LOW", pct
    except Exception as exc:
        log.debug("compute_atr_risk failed for input: %s", exc)
        return "—", 0.0


def compute_vwap_dist(df: pd.DataFrame, price: float) -> float:
    """VWAP distance = (price - vwap) / price. Clamped to (-0.5, 0.5)."""
    try:
        close = df["Close"].dropna()
        vol = df["Volume"].dropna()
        if len(close) < 10 or vol.sum() <= 0:
            return 0.0
        n = min(len(close), len(vol), K.VWAP_ROLL_WINDOW)
        close, vol = close.iloc[-n:], vol.iloc[-n:]
        cum_vol = vol.cumsum()
        if cum_vol.iloc[-1] <= 0:
            return 0.0
        vwap = float((close * vol).cumsum().iloc[-1] / cum_vol.iloc[-1])
        return safe_clamp((price - vwap) / price, -0.5, 0.5) if vwap > 0 else 0.0
    except Exception as exc:
        log.debug("compute_vwap_dist failed for input: %s", exc)
        return 0.0


def compute_vol_zscore(df: pd.DataFrame, window: int = None) -> float:
    """Compute volume Z-score with symmetric clamp."""
    if window is None:
        window = K.VOL_ROLL_WINDOW
    try:
        vol = df["Volume"].dropna()
        if vol.sum() <= 0 or len(vol) < window + 2:
            return 0.0
        mu = float(vol.rolling(window).mean().iloc[-1])
        sig = float(vol.rolling(window).std().iloc[-1])
        if sig <= 0:
            return 0.0
        return safe_clamp((float(vol.iloc[-1]) - mu) / sig, K.VOL_ZSCORE_LO, K.VOL_ZSCORE_HI)
    except Exception as exc:
        log.debug("compute_vol_zscore failed for input: %s", exc)
        return 0.0


def detect_ema_cross(close: pd.Series) -> str:
    """Detect EMA10/EMA50 crossover."""
    if len(close) < 55:
        return ""
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    for i in range(-7, 0):
        prev = ema10.iloc[i-1] > ema50.iloc[i-1]
        curr = ema10.iloc[i] > ema50.iloc[i]
        if not prev and curr:
            return "BULL_CROSS"
        if prev and not curr:
            return "BEAR_CROSS"
    return ""


def detect_vol_divergence(close: pd.Series, volume: pd.Series, lookback: int = 5) -> str:
    """Detect volume/price divergence patterns."""
    if len(close) < lookback + 2:
        return ""
    price_chg = float(close.iloc[-1]) - float(close.iloc[-lookback])
    vol_ma = volume.rolling(3).mean()
    if len(vol_ma.dropna()) < lookback:
        return ""
    vol_trend = float(vol_ma.iloc[-1]) - float(vol_ma.iloc[-lookback])
    if price_chg > 0 and vol_trend > 0:
        return "🟢BULL_CONF"
    if price_chg > 0 and vol_trend < 0:
        return "🔀BEAR_DIV"
    if price_chg < 0 and vol_trend < 0:
        return "🔵BASE"
    if price_chg < 0 and vol_trend > 0:
        return "⚠️CLIMAX_SELL"
    return ""


def compute_ud_ratio(close: pd.Series, period: int = 14) -> float:
    """Compute Up/Down ratio (used in RSI-style calculations)."""
    try:
        # Ensure input is a 1-D Series, not a DataFrame
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        # Extract explicit scalars to avoid "truth value of Series" error
        avg_loss_val = float(avg_loss.iloc[-1])
        avg_gain_val = float(avg_gain.iloc[-1])
        if avg_loss_val == 0:
            return 100.0
        rs = avg_gain_val / avg_loss_val
        return 100.0 - (100.0 / (1.0 + rs))
    except Exception as exc:
        log.debug("compute_ud_ratio failed for input: %s", exc)
        return 50.0


def detect_vcp(df: pd.DataFrame, lookback: int = 20) -> bool:
    """Detect Volatility Contraction Pattern (VCP)."""
    try:
        if len(df) < lookback:
            return False
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        
        # Calculate recent volatility
        recent_vol = close.pct_change().rolling(lookback).std()
        
        # Find contraction (lower volatility than average)
        avg_vol = recent_vol.mean()
        current_vol = recent_vol.iloc[-1]
        
        if current_vol < avg_vol * 0.7:  # 30% contraction
            return True
        return False
    except Exception as exc:
        log.debug("detect_vcp failed for input: %s", exc)
        return False


def compute_cmf(df: pd.DataFrame, period: int = None) -> float:
    """Chaikin Money Flow indicator."""
    import numpy as np
    if period is None:
        period = K.CMF_PERIOD
    
    if df is None or len(df) < period:
        return 0.0
    
    try:
        high  = df["High"].values[-period:]
        low   = df["Low"].values[-period:]
        close = df["Close"].values[-period:]
        volume = df["Volume"].values[-period:]
        
        denom = high - low
        denom = np.where(denom == 0, 1e-9, denom)
        
        mfm = ((close - low) - (high - close)) / denom
        mfv = mfm * volume
        
        cmf = mfv.sum() / volume.sum() if volume.sum() > 0 else 0.0
        return round(float(cmf), 4)
    except Exception as exc:
        log.debug("compute_cmf failed for input: %s", exc)
        return 0.0


def sharpe_from_trades(trades: list, risk_free_rate: float = None) -> float:
    """Calculate Sharpe ratio from trade returns."""
    import numpy as np
    try:
        # Handle both list of dicts AND list of floats
        if not trades:
            return 0.0
        
        if isinstance(trades[0], dict):
            returns = [t.get("pnl_pct", 0) for t in trades]
        else:
            returns = [float(t) for t in trades]
        
        arr = np.array(returns) / 100
        if arr.std() == 0:
            return 0.0
        rf_daily = (K.RISK_FREE_ANNUAL_PCT / K.TRADING_DAYS_PER_YEAR / 100) if risk_free_rate is None else risk_free_rate
        return round(float((arr.mean() - rf_daily) / arr.std() * np.sqrt(K.TRADING_DAYS_PER_YEAR)), 2)
    except Exception as exc:
        log.debug("sharpe_from_trades failed for input: %s", exc)
        return 0.0


def pct_change_safe(current: float, previous: float) -> float:
    """Calculate percentage change safely, avoiding division by zero."""
    if previous is None or previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


# ── ATR shrinking check (the function that was causing the bug) ────────────────
def is_atr_shrinking(df: pd.DataFrame, length: int = None, bars: int = 5) -> bool:
    """Check if ATR has been shrinking for the last `bars`.
    length defaults to K.ATR_LENGTH only when the caller does not supply it.
    """
    if length is None:
        length = K.ATR_LENGTH
    try:
        if len(df) < length + bars:
            return False
        h = df["High"].reset_index(drop=True)
        l = df["Low"].reset_index(drop=True)
        c = df["Close"].reset_index(drop=True)
        tr = pd.concat([
            h - l,
            (h - c.shift()).abs(),
            (l - c.shift()).abs(),
        ], axis=1).max(axis=1)
        atr_series = tr.rolling(length).mean().dropna()
        if len(atr_series) < bars:
            return False
        
        # checks if atr[i] - atr[i-1] < 0 for the last `bars-1` diffs
        return (atr_series.tail(bars).diff().dropna() < 0).all()

    except Exception as exc:
        log.debug("is_atr_shrinking failed for input: %s", exc)
        return False


def compute_liquidity_shock(
    df: pd.DataFrame,
    atr: Optional[float],
    avg_volume: float,
) -> float:
    """
    Liquidity Shock indicator.
    Measures the strength of a directional volume event relative to ATR.
    High value = strong institutional move. Low value = retail noise.

    Formula: liq_shock = (vol_today / avg_volume) * (|close - open| / ATR)
    Returns a float clamped to [0.0, 5.0].
    """
    try:
        if df is None or len(df) < 2:
            return 0.0
        if avg_volume <= 0 or atr is None or atr <= 0:
            return 0.0
        vol_today = float(df["Volume"].iloc[-1])
        close     = float(df["Close"].iloc[-1])
        open_     = float(df["Open"].iloc[-1])
        vol_ratio = vol_today / (avg_volume + 1e-9)
        body_size = abs(close - open_) / (atr + 1e-9)
        shock = vol_ratio * body_size
        return safe_clamp(shock, 0.0, 5.0)
    except Exception as exc:
        log.debug("compute_liquidity_shock failed: %s", exc)
        return 0.0


def quantile_norm(value: float, series: pd.Series) -> float:
    """Quantile-based normalization: rank of `value` within `series`, mapped to [0, 1].
    More robust than linear normalization for skewed EGX distributions.
    """
    try:
        s = series.dropna()
        if len(s) < 2:
            return 0.5
        rank = float((s < value).sum()) / len(s)
        return safe_clamp(rank, 0.0, 1.0)
    except Exception as exc:
        log.debug("quantile_norm failed: %s", exc)
        return 0.5

