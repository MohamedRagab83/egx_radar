"""Adaptive source quality scoring for EGX Radar data layer.

Scores each data source on four quality dimensions:
  - Missing values  (Close NaN ratio)
  - Volume validity (rows with volume > 0)
  - Data completeness (row count vs ideal length)
  - Recency         (days since last data point)

Used by merge.py to dynamically select the best source per symbol
instead of relying on a fixed priority order.
"""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

log = logging.getLogger(__name__)

# ── Quality thresholds ─────────────────────────────────────────────────
QUALITY_THRESHOLD = 0.4    # below this → reject source entirely
FALLBACK_THRESHOLD = 0.6   # below this → log fallback warning

# ── Scoring weights (sum = 1.0) ───────────────────────────────────────
_W_MISSING = 0.30
_W_VOLUME = 0.20
_W_LENGTH = 0.25
_W_RECENCY = 0.25

# Ideal bar count for full length score
_IDEAL_BARS = 120


def score_source(
    df: Optional[pd.DataFrame],
    label: str,
    sym: str,
    ideal_bars: int = _IDEAL_BARS,
) -> Dict[str, float]:
    """Score a single data source on quality dimensions.

    Returns dict with keys:
        missing_pct    float 0–1  (lower = better quality)
        volume_score   float 0–1  (higher = better)
        length_score   float 0–1  (higher = better)
        recency_score  float 0–1  (higher = better)
        total          float 0–1  weighted composite
        label          str        source name
    """
    empty: Dict[str, float] = {
        "missing_pct": 1.0,
        "volume_score": 0.0,
        "length_score": 0.0,
        "recency_score": 0.0,
        "total": 0.0,
        "label": label,
    }
    if df is None or df.empty or "Close" not in df.columns:
        return empty

    n = len(df)

    # 1. Missing values — fraction of NaN in Close
    close_nan = int(df["Close"].isna().sum())
    missing_pct = close_nan / max(n, 1)
    missing_score = 1.0 - missing_pct

    # 2. Volume validity — fraction of rows with volume > 0
    if "Volume" in df.columns:
        vol_valid = int((df["Volume"].fillna(0) > 0).sum())
        volume_score = vol_valid / max(n, 1)
    else:
        volume_score = 0.0

    # 3. Data length — how complete vs ideal
    length_score = min(1.0, n / max(ideal_bars, 1))

    # 4. Recency — days since last data point
    try:
        idx = (
            df.index
            if isinstance(df.index, pd.DatetimeIndex)
            else pd.to_datetime(df.index)
        )
        last_date = idx.max()
        days_old = max(0, (pd.Timestamp.now() - last_date).days)
        # Full score if ≤1 day old, degrades linearly to 0 at 30 days
        recency_score = max(0.0, 1.0 - days_old / 30.0)
    except Exception:
        recency_score = 0.0

    total = (
        _W_MISSING * missing_score
        + _W_VOLUME * volume_score
        + _W_LENGTH * length_score
        + _W_RECENCY * recency_score
    )

    return {
        "missing_pct": round(missing_pct, 4),
        "volume_score": round(volume_score, 4),
        "length_score": round(length_score, 4),
        "recency_score": round(recency_score, 4),
        "total": round(total, 4),
        "label": label,
    }


def rank_sources(
    candidates: List[Tuple[pd.DataFrame, str]],
    sym: str,
) -> List[Tuple[pd.DataFrame, str, Dict[str, float]]]:
    """Score and rank candidates by quality (highest first).

    Args:
        candidates: list of (DataFrame, source_label) already filtered
                    for minimum bar count / staleness.
        sym: symbol name for logging.

    Returns:
        Sorted list of (DataFrame, label, score_dict) — best first.
    """
    scored = []
    for df, label in candidates:
        sc = score_source(df, label, sym)
        scored.append((df, label, sc))

    scored.sort(key=lambda x: x[2]["total"], reverse=True)
    return scored


# ── Best-source cache ──────────────────────────────────────────────────
_best_source_cache: Dict[str, str] = {}


def cache_best_source(sym: str, label: str) -> None:
    """Remember the best source selected for a symbol."""
    _best_source_cache[sym] = label


def get_cached_source(sym: str) -> Optional[str]:
    """Return the cached best source for a symbol, or None."""
    return _best_source_cache.get(sym)


def get_cache_snapshot() -> Dict[str, str]:
    """Return a copy of the full best-source cache."""
    return dict(_best_source_cache)
