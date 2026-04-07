from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import logging
import sys
import yfinance as yf
import hashlib
from typing import Dict, Iterable
import numpy as np
from typing import Dict
from datetime import UTC, datetime
from typing import List
from datetime import datetime
from typing import Tuple
import math
from typing import Dict, List
from typing import Dict, Tuple
from typing import Dict, List, Optional, Tuple
from typing import Dict, List, Tuple
from collections import Counter
import json
from pathlib import Path

# =========================
# FILE: config/__init__.py
# =========================
# EGX Radar Pro — config package

# =========================
# FILE: config/settings.py
# =========================
"""
config/settings.py — EGX Radar Pro
====================================
Central configuration and shared data structures.

All other modules import from here.  This module has NO internal project
imports — it is the lowest layer and must stay that way to prevent circular
dependency chains.

Key exports
-----------
RISK         : RiskConfig singleton
CFG          : EngineConfig singleton
SECTORS      : sector → symbol mapping
SYMBOLS      : sorted list of all tradable symbols
SECTOR_BY_SYMBOL : symbol → sector lookup
Snapshot     : per-symbol market state at a point in time
Trade        : a single executed (or open) trade record
"""





# ──────────────────────────────────────────────────────────────
# EGX Universe
# ──────────────────────────────────────────────────────────────
SECTORS: Dict[str, List[str]] = {
    "BANKS":       ["COMI", "CIEB", "ADIB", "SAUD", "CNFN", "FAIT"],
    "REAL_ESTATE": ["TMGH", "PHDC", "OCDI", "HELI", "DSCW"],
    "INDUSTRIAL":  ["ORAS", "SKPC", "KZPC", "AMOC", "ESRS"],
    "SERVICES":    ["FWRY", "ETEL", "JUFO", "HRHO", "EGTS", "ORWE"],
    "ENERGY":      ["ABUK", "MFPC", "ISPH", "EAST", "SWDY"],
}

SYMBOLS: List[str] = sorted({s for sec in SECTORS.values() for s in sec})

SECTOR_BY_SYMBOL: Dict[str, str] = {
    sym: sec for sec, syms in SECTORS.items() for sym in syms
}


# ──────────────────────────────────────────────────────────────
# Risk Configuration
# ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RiskConfig:
    """
    Immutable risk parameters.  Modify values here ONLY — never hard-code
    them in execution logic.
    """
    account_size:            float = 100_000.0   # Base currency (EGP)
    risk_per_trade:          float = 0.005        # 0.5% of account per trade
    max_open_trades:         int   = 6            # Global position cap
    max_sector_positions:    int   = 2            # Per-sector concentration limit
    max_sector_exposure_pct: float = 0.30         # Max 30% allocated to one sector
    slippage_pct:            float = 0.003        # 0.3% market impact estimate
    fee_pct:                 float = 0.0015       # 0.15% round-trip fee
    max_bars_hold:           int   = 20           # Time-stop: 20 trading days
    partial_exit_fraction:   float = 0.50         # Fraction closed at first target


# ──────────────────────────────────────────────────────────────
# Engine Configuration
# ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class EngineConfig:
    """
    Immutable engine thresholds.  SmartRank is the only execution gate.
    AI / News / Alpha thresholds here are for display logic only.
    """
    warmup_bars:          int   = 80    # Minimum bars required before scoring
    smart_rank_accumulate: float = 70.0  # MAIN entry threshold (legacy mode)
    smart_rank_probe:      float = 55.0  # PROBE entry threshold (legacy mode)

    # Smart Rank 2.0 — filter-first execution parameters
    v2_rsi_min:           float = 45.0
    v2_rsi_max:           float = 65.0
    v2_volume_min:        float = 1.20
    v2_atr_pct_max:       float = 0.035
    v2_breakout_lookback: int   = 20
    v2_breakout_min:      float = 0.97
    v2_score_threshold:   float = 62.0
    v2_stop_atr_mult:     float = 1.20
    v2_min_rr:            float = 2.2
    alpha_min_score:       float = 70.0  # Alpha display threshold (no execution use)
    alpha_sr_cap:          float = 60.0  # Alpha display cap (no execution use)


# ──────────────────────────────────────────────────────────────
# Module-level singletons — import RISK and CFG everywhere
# ──────────────────────────────────────────────────────────────
RISK = RiskConfig()
CFG  = EngineConfig()


# ──────────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────────
@dataclass
class Snapshot:
    """
    Full market snapshot for one symbol at one point in time.

    Fields marked 'display only' are computed for logging and advisory
    purposes.  They must NOT be used in generate_trade_signal() or any
    execution path.
    """
    # Core price / market data
    date:            pd.Timestamp
    symbol:          str
    sector:          str
    close:           float
    open:            float
    high:            float
    low:             float
    volume:          float

    # Derived technical indicators
    rsi:             float
    atr:             float
    atr_pct:         float
    ema20:           float
    ema50:           float
    ema200:          float
    volume_ratio:    float
    trend_strength:  float
    structure_score: float

    # SmartRank — legacy execution score
    smart_rank:      float

    # SmartRank 2.0 score (filter + score model)
    smart_rank_v2:   float = 0.0
    breakout_proximity: float = 0.0

    # ── DISPLAY ONLY fields ─────────────────────────────────────────────
    # These are populated by evaluate_snapshot() after SmartRank is set.
    # They must NEVER gate or trigger trade execution.
    probability:     float = 0.5   # AI probability estimate
    sentiment_score: float = 0.5   # News sentiment [0=bearish, 1=bullish]
    alpha_score:     float = 0.0   # Alpha opportunity score [0, 100]


@dataclass
class Trade:
    """
    A single trade record — covers the full lifecycle from entry to exit.

    The display-only fields (probability, sentiment_score, alpha_score) are
    captured at entry time for post-trade analysis and reporting only.
    """
    symbol:          str
    sector:          str
    entry_date:      pd.Timestamp
    entry:           float
    stop:            float
    target:          float
    size:            int
    risk_used:       float
    signal_type:     str             # "MAIN" | "PROBE"

    # Execution signal
    smart_rank:      float

    # ── DISPLAY ONLY — captured at entry, never used for execution ──────
    probability:     float
    sentiment_score: float
    alpha_score:     float

    # Lifecycle state
    bars_held:       int                    = 0
    status:          str                    = "OPEN"
    exit_date:       Optional[pd.Timestamp] = None
    exit_price:      Optional[float]        = None
    pnl_pct:         float                  = 0.0

# =========================
# FILE: utils/__init__.py
# =========================
# EGX Radar Pro — utils package

# =========================
# FILE: utils/helpers.py
# =========================
"""
utils/helpers.py — EGX Radar Pro
===================================
Pure utility functions with no internal project dependencies.
Safe to import from any module.
"""



def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp a float value to the closed interval [lo, hi]."""
    return max(lo, min(hi, x))


def pct_change(new_val: float, old_val: float) -> float:
    """Percentage change from old_val to new_val, avoiding division by zero."""
    return (new_val - old_val) / max(abs(old_val), 1e-9) * 100.0


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns default when denominator is near zero."""
    return numerator / denominator if abs(denominator) > 1e-9 else default

# =========================
# FILE: utils/logger.py
# =========================
"""
utils/logger.py — EGX Radar Pro
==================================
Centralised logging factory.

Usage
-----
    log = get_logger(__name__)
    log.info("message")
"""




def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return a module-level logger with a consistent, timestamped format.

    Calling this multiple times with the same name is safe — handlers are
    only added once.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger

# =========================
# FILE: data/__init__.py
# =========================
# EGX Radar Pro — data package

# =========================
# FILE: data/loader.py
# =========================
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

# =========================
# FILE: news/__init__.py
# =========================
# EGX Radar Pro — news package

# =========================
# FILE: news/nlp_arabic.py
# =========================
"""
news/nlp_arabic.py — EGX Radar Pro
======================================
Arabic-language NLP for financial news classification and sentiment scoring.

Contains the phrase dictionaries and scoring functions for Egyptian market
news — the primary language of EGX corporate announcements.

All functions are stateless and have no internal project dependencies
(safe to import from any module without circular risk).
"""





# ──────────────────────────────────────────────────────────────
# Phrase Sentiment Dictionaries
# ──────────────────────────────────────────────────────────────
# Weights represent signal strength.  Positive numbers = bullish.
# Negative numbers = bearish.  Range is used with clamp(-3, +3).

POSITIVE_PHRASES: Dict[str, float] = {
    "نمو قوي":          2.0,   # Strong growth
    "زيادة الإيرادات":  2.0,   # Revenue increase
    "تحسن الهوامش":     1.5,   # Margin improvement
    "صفقة استحواذ":     2.5,   # Acquisition deal
    "توزيع أرباح":      1.8,   # Dividend distribution
    "توسع جديد":        1.5,   # New expansion
    "نتائج إيجابية":    1.5,   # Positive results
    "أرباح مرتفعة":     2.0,   # High earnings
}

NEGATIVE_PHRASES: Dict[str, float] = {
    "تراجع الأرباح":    -2.0,  # Profit decline
    "ضغوط تمويلية":    -2.0,  # Financial pressure
    "ارتفاع المديونية": -2.0,  # Rising debt
    "انخفاض الإيرادات": -1.8,  # Revenue decline
    "ضعف الطلب":        -1.5,  # Weak demand
    "خسائر تشغيلية":   -2.0,  # Operating losses
}

CRITICAL_PHRASES: Dict[str, float] = {
    "خسائر كبيرة":    -3.0,   # Major losses
    "إيقاف التداول":  -3.0,   # Trading halt
    "تحقيق رسمي":     -3.0,   # Official investigation
    "إفلاس":          -3.0,   # Bankruptcy
    "تعثر مالي":      -2.8,   # Financial default risk
}


# ──────────────────────────────────────────────────────────────
# Core NLP Functions
# ──────────────────────────────────────────────────────────────

def analyze_arabic_sentiment(text: str) -> float:
    """
    Score Arabic financial text on a [-3.0, +3.0] scale.

    Positive values indicate bullish signals.
    Negative values indicate bearish signals.
    0.0 indicates no detectable sentiment phrases.

    The function uses exact substring matching — suitable for structured
    EGX press release language.  In production, consider augmenting with
    a fine-tuned AraBERT model for unstructured social media text.
    """
    score = 0.0
    for phrase, weight in POSITIVE_PHRASES.items():
        if phrase in text:
            score += weight
    for phrase, weight in NEGATIVE_PHRASES.items():
        if phrase in text:
            score += weight
    for phrase, weight in CRITICAL_PHRASES.items():
        if phrase in text:
            score += weight
    return clamp(score, -3.0, 3.0)


def classify_news_type(text: str) -> str:
    """
    Classify a news item into a category based on keyword presence.

    Categories: "earnings" | "dividend" | "acquisition" | "expansion" | "general"

    Used by sentiment_engine.py to compute importance weights.
    """
    t = text.lower()
    if any(x in t for x in ["نتائج", "أرباح", "earnings", "results"]):
        return "earnings"
    if any(x in t for x in ["توزيع", "dividend", "coupon"]):
        return "dividend"
    if any(x in t for x in ["استحواذ", "merger", "acquisition"]):
        return "acquisition"
    if any(x in t for x in ["توسع", "expansion", "project", "مشروع"]):
        return "expansion"
    return "general"

# =========================
# FILE: news/sentiment_engine.py
# =========================
"""
news/sentiment_engine.py — EGX Radar Pro
==========================================
News scoring, decay, and sentiment aggregation.

Converts a list of raw news dicts (from news_fetcher) into a single
normalised sentiment score that is stored on Snapshot.sentiment_score
for display purposes only.

This module does NOT make execution decisions.
"""






# ──────────────────────────────────────────────────────────────
# Credibility and Importance Weights
# ──────────────────────────────────────────────────────────────

SOURCE_CREDIBILITY: dict = {
    "egx_official":          1.00,
    "company_announcements": 0.95,
    "mubasher":              0.82,
    "investing_egypt":       0.72,
    "daily_news_egypt":      0.60,
}

NEWS_TYPE_IMPORTANCE: dict = {
    "earnings":    1.00,
    "acquisition": 0.94,
    "expansion":   0.88,
    "dividend":    0.82,
    "general":     0.60,
}


# ──────────────────────────────────────────────────────────────
# Component Scoring Functions
# ──────────────────────────────────────────────────────────────

def news_strength(news: dict) -> float:
    """
    Composite reliability weight for one news item.

    Combines source credibility (55%) and news-type importance (45%).
    Returns float in [0.0, 1.0].
    """
    credibility = SOURCE_CREDIBILITY.get(
        str(news.get("source", "")).lower(), 0.55
    )
    news_type = classify_news_type(
        f"{news.get('title', '')} {news.get('content', '')}"
    )
    importance = NEWS_TYPE_IMPORTANCE.get(news_type, 0.60)
    return round(clamp(0.55 * credibility + 0.45 * importance, 0.0, 1.0), 4)


def news_decay(hours_old: float) -> float:
    """
    Exponential-step time-decay weight based on news age.

    Age < 6h    → 1.00  (fresh, full weight)
    Age < 24h   → 0.70  (same-session)
    Age < 48h   → 0.50  (day-old)
    Age >= 48h  → 0.30  (stale)
    """
    if hours_old < 6:
        return 1.00
    if hours_old < 24:
        return 0.70
    if hours_old < 48:
        return 0.50
    return 0.30


def market_reaction_factor(snapshot: Snapshot, raw_sentiment: float) -> float:
    """
    Adjust effective news sentiment based on current price context.

    Rationale
    ---------
    Bullish news on a technically weak (RSI < 50) stock is less credible
    as a catalyst — the market is not yet confirming the news.

    Bearish news on an overbought (RSI > 60) stock is already partially
    priced in — downside is dampened.

    High volume amplifies the reaction (market is paying attention).

    Returns
    -------
    float in [0.4, 1.2]
    """
    impact = 1.0
    if raw_sentiment > 0 and snapshot.rsi < 50:
        impact *= 0.6   # Bullish news on weak stock — dampened
    if raw_sentiment < 0 and snapshot.rsi > 60:
        impact *= 0.6   # Bearish news on strong stock — dampened
    if snapshot.volume_ratio > 1.5:
        impact *= 1.1   # High volume confirms the reaction
    return clamp(impact, 0.4, 1.2)


# ──────────────────────────────────────────────────────────────
# Aggregate Sentiment Score
# ──────────────────────────────────────────────────────────────

def sentiment_score(
    news_list: List[dict],
    snapshot: Snapshot,
    now: datetime,
) -> float:
    """
    Aggregate all news items into a single sentiment score [0.0, 1.0].

    0.5 = neutral (no news or balanced)
    > 0.5 = net bullish
    < 0.5 = net bearish

    For each news item:
      contribution = raw_sentiment × time_decay × market_reaction × strength

    The sum is normalised from [-5, +5] to [0, 1] linearly.
    """
    if not news_list:
        return 0.5

    total = 0.0
    for n in news_list:
        txt = f"{n.get('title', '')} {n.get('content', '')}"
        raw = analyze_arabic_sentiment(txt)

        ts = n.get("timestamp", now)
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()
        if ts.tzinfo is not None:
            ts = ts.astimezone(UTC).replace(tzinfo=None)

        age_hours = max((now - ts).total_seconds() / 3600.0, 0.0)
        total += (
            raw
            * news_decay(age_hours)
            * market_reaction_factor(snapshot, raw)
            * news_strength(n)
        )

    normalised = (total + 5.0) / 10.0
    return round(clamp(normalised, 0.0, 1.0), 4)

# =========================
# FILE: news/news_fetcher.py
# =========================
"""
news/news_fetcher.py — EGX Radar Pro
========================================
News data acquisition layer.

In development/backtest mode: returns deterministic synthetic news.
In production: replace fetch_news() with live feed integrations.

Supported production sources
-----------------------------
  - EGX official announcements feed (primary)
  - Mubasher financial news API
  - Company investor relations RSS feeds
  - Egypt Stock Exchange regulatory filings scraper

The function signature and return format must remain stable so that
all downstream modules (sentiment_engine, alpha_engine) work without
modification when switching from synthetic to live data.
"""





log = get_logger(__name__)


def fetch_news(symbol: str, date: pd.Timestamp) -> List[dict]:
    """
    Retrieve news articles for a symbol on or before a given date.

    Current implementation: deterministic synthetic generator.
    Approximately 10% of dates return a news item for a given symbol,
    using a stable hash so backtest results are fully reproducible.

    Parameters
    ----------
    symbol : EGX ticker symbol (e.g. "COMI", "TMGH")
    date   : The trading date to fetch news for

    Returns
    -------
    List of news dicts, each containing:
      title     : str   — Arabic headline
      content   : str   — Article body (may duplicate title in stub)
      source    : str   — "egx_official" | "mubasher" | ...
      timestamp : datetime — Publication datetime

    Production replacement
    ----------------------
    Replace the body below with your live feed call, preserving the
    return format.  Example:

        response = requests.get(f"{FEED_URL}/news?symbol={symbol}&date={date.date()}")
        return response.json().get("articles", [])
    """
    seed = abs(hash((symbol, str(date.date())))) % 100

    if seed < 90:
        return []   # ~90% of days have no material news

    if seed % 2 == 0:
        title  = "نمو قوي وزيادة الإيرادات"
        source = "egx_official" if seed % 3 == 0 else "mubasher"
    else:
        title  = "تراجع الأرباح وضغوط تمويلية"
        source = "mubasher"

    log.debug("Synthetic news — %s on %s: %s", symbol, date.date(), title)

    return [{
        "title":     title,
        "content":   title,
        "source":    source,
        "timestamp": date.to_pydatetime(),
    }]

# =========================
# FILE: news/news_intelligence.py
# =========================
"""
news/news_intelligence.py — EGX Radar Pro
===========================================
High-level news intelligence aggregator — DISPLAY ONLY.

NewsIntelligence wraps fetch_news + sentiment scoring into a single
reporting interface used by the dashboard / logging layer.

Output is never used in execution decisions.
"""




log = get_logger(__name__)


class NewsIntelligence:
    """
    Fetch, score, and summarise news for a market snapshot.

    Methods
    -------
    analyse(snapshot, now) → dict
        Full intelligence report for one symbol.
    """

    def analyse(self, snapshot: Snapshot, now: datetime) -> dict:
        """
        Full news intelligence report.

        Parameters
        ----------
        snapshot : Evaluated market Snapshot
        now      : Current datetime (timezone-naive UTC)

        Returns
        -------
        dict with keys:
          raw_news     : list[dict]  — raw news items from fetcher
          sentiment    : float       — aggregate sentiment score [0, 1]
          top_items    : list[dict]  — up to 3 highest-impact items
          has_critical : bool        — True if major negative news detected
          item_count   : int         — number of news items found
        """
        news_list = fetch_news(snapshot.symbol, snapshot.date)
        sent      = sentiment_score(news_list, snapshot, now)

        scored: List[dict] = []
        for n in news_list:
            txt    = f"{n.get('title', '')} {n.get('content', '')}"
            raw    = analyze_arabic_sentiment(txt)
            weight = news_strength(n)
            scored.append({
                "title":    n.get("title", ""),
                "source":   n.get("source", ""),
                "raw_sent": raw,
                "strength": weight,
                "impact":   round(raw * weight, 4),
            })

        scored.sort(key=lambda x: abs(x["impact"]), reverse=True)

        has_critical = any(item["raw_sent"] <= -2.5 for item in scored)
        if has_critical:
            log.warning(
                "Critical negative news detected for %s on %s — review before trading.",
                snapshot.symbol,
                snapshot.date.date(),
            )

        return {
            "raw_news":    news_list,
            "sentiment":   sent,
            "top_items":   scored[:3],
            "has_critical": has_critical,
            "item_count":  len(news_list),
        }

    def format_report(self, snapshot: Snapshot, now: datetime) -> str:
        """
        Human-readable news intelligence report for console / log output.
        """
        report = self.analyse(snapshot, now)
        lines  = [
            f"News Intelligence: {snapshot.symbol} @ {snapshot.date.date()}",
            f"  Sentiment : {report['sentiment']:.4f}",
            f"  Items     : {report['item_count']}",
            f"  Critical  : {report['has_critical']}",
        ]
        for i, item in enumerate(report["top_items"], 1):
            lines.append(
                f"  [{i}] {item['title']}  "
                f"(src={item['source']} sent={item['raw_sent']:.2f} str={item['strength']:.2f})"
            )
        return "\n".join(lines)

# =========================
# FILE: alpha/__init__.py
# =========================
# EGX Radar Pro — alpha package

# =========================
# FILE: alpha/alpha_filter.py
# =========================
"""
alpha/alpha_filter.py — EGX Radar Pro
=========================================
Alpha opportunity filter — DISPLAY / RESEARCH ONLY.

Evaluates whether alpha conditions are technically sound.
The result is used for research, logging, and advisory display.

It must NEVER be used as an execution gate in generate_trade_signal().

Filter criteria
---------------
  alpha_score >= 60     : Minimum alpha signal strength
  atr_pct <= 6%         : Volatility not excessive
  volume_ratio >= 1.3   : Volume confirmation present
  rsi >= 45             : Not technically oversold
"""





def alpha_filter(snapshot: Snapshot, alpha_score: float) -> Tuple[bool, str]:
    """
    Evaluate alpha quality conditions.

    Parameters
    ----------
    snapshot    : Market snapshot for the symbol
    alpha_score : Computed alpha score from compute_alpha_score()

    Returns
    -------
    Tuple (passed: bool, reason: str)
      passed=True  → "alpha_pass"
      passed=False → reason code describing the failing condition
    """
    if alpha_score < 60:
        return False, "alpha_below_60"
    if snapshot.atr_pct > 0.06:
        return False, "atr_too_high"
    if snapshot.volume_ratio < 1.3:
        return False, "volume_too_low"
    if snapshot.rsi < 45:
        return False, "rsi_too_low"
    return True, "alpha_pass"


def alpha_quality_score(snapshot: Snapshot, alpha_score: float) -> float:
    """
    Quantify overall alpha signal quality on a [0, 1] scale.

    Used for ranking / display in a scanner UI.
    Does not affect execution.
    """
    passed, _ = alpha_filter(snapshot, alpha_score)
    if not passed:
        return 0.0

    quality = 0.0
    quality += min((alpha_score - 60.0) / 40.0, 1.0) * 0.40
    quality += min(snapshot.volume_ratio / 3.0, 1.0)  * 0.30
    quality += min((snapshot.rsi - 45.0) / 30.0, 1.0) * 0.30
    return round(quality, 4)

# =========================
# FILE: alpha/alpha_engine.py
# =========================
"""
alpha/alpha_engine.py — EGX Radar Pro
=========================================
Alpha score computation — DISPLAY ONLY.

Computes a news-and-context-driven alpha opportunity score [0, 100]
that is stored on Snapshot.alpha_score for display purposes.

This score is NEVER used to gate or trigger position entry.
Execution is exclusively driven by SmartRank in signal_engine.py.

Methodology
-----------
For each news item attached to the snapshot:
  contribution = sentiment × news_strength × time_decay × market_reaction

The aggregated contribution is scaled from a [-3, +3] raw range to a
[0, 100] score, with 50 as the neutral (no-news) baseline.

Dependencies
------------
  config.settings (Snapshot)
  news.nlp_arabic  (analyze_arabic_sentiment)
  news.sentiment_engine (news_strength, news_decay, market_reaction_factor)
  utils.helpers (clamp)
"""






def compute_alpha_score(
    news_list: List[dict],
    snapshot: Snapshot,
    now: datetime,
) -> float:
    """
    Compute alpha opportunity score for a snapshot.

    Parameters
    ----------
    news_list : Raw news items from news_fetcher.fetch_news()
    snapshot  : The market snapshot (used for market_reaction_factor)
    now       : Current datetime (timezone-naive UTC) for age calculation

    Returns
    -------
    float in [0.0, 100.0], rounded to 2 decimal places.
    50.0 is returned when no news is present (neutral baseline).
    """
    if not news_list:
        return 0.0

    raw_total = 0.0
    for n in news_list:
        txt  = f"{n.get('title', '')} {n.get('content', '')}"
        sent = analyze_arabic_sentiment(txt)

        ts = n.get("timestamp", now)
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()
        if ts.tzinfo is not None:
            ts = ts.astimezone(UTC).replace(tzinfo=None)

        age_hours = max((now - ts).total_seconds() / 3600.0, 0.0)

        raw_total += (
            sent
            * news_strength(n)
            * news_decay(age_hours)
            * market_reaction_factor(snapshot, sent)
        )

    # Scale from approximate [-3, +3] range to [0, 100]
    score = 50.0 + raw_total * (50.0 / 3.0)
    return round(clamp(score, 0.0, 100.0), 2)

# =========================
# FILE: alpha/alpha_execution.py
# =========================
"""
alpha/alpha_execution.py — EGX Radar Pro
==========================================
Alpha trade parameter builder — CALCULATION ONLY, NOT EXECUTED.

Computes what an alpha-driven trade WOULD look like: entry, stop, target,
and position scale.  These parameters are returned for display, research,
and reporter logging.

IMPORTANT: The output of this module is NEVER passed to the backtest
engine or used to open a real position.  Trade execution is exclusively
driven by SmartRank via core/signal_engine.py.
"""




def build_alpha_trade(snapshot: Snapshot, alpha_score: float) -> dict:
    """
    Compute alpha-driven trade parameters for display / research.

    Entry logic
    -----------
    - Pullback entry below close (ATR-scaled pullback, capped at 1.5%)
    - Stop defined by recent low with a small buffer
    - Target set at 2.2× the risk
    - Position scale proportional to alpha score (8–20% of base risk)

    Parameters
    ----------
    snapshot    : Market snapshot at evaluation time
    alpha_score : Alpha score from compute_alpha_score() — must be >= 60

    Returns
    -------
    dict with keys:
      entry          : float — suggested entry price
      stop           : float — suggested stop-loss price
      target         : float — suggested profit target
      risk_pct       : float — estimated risk as fraction of entry
      target_pct     : float — estimated gain potential as fraction of entry
      position_scale : float — fraction of base risk to allocate (8–20%)
      alpha_score    : float — the alpha score used in this calculation
      display_only   : bool  — always True; documents intended use
    """
    pullback   = min(
        max(snapshot.atr * 0.35, snapshot.close * 0.003),
        snapshot.close * 0.015,
    )
    entry      = max(snapshot.low, snapshot.close - pullback)
    risk_pct   = clamp(
        (entry - snapshot.low * 0.995) / max(entry, 1e-9),
        0.008, 0.025,
    )
    target_pct = max(0.04, risk_pct * 2.2)
    scale      = clamp((alpha_score - 60.0) / 200.0, 0.08, 0.20)

    return {
        "entry":          round(entry, 3),
        "stop":           round(entry * (1.0 - risk_pct), 3),
        "target":         round(entry * (1.0 + target_pct), 3),
        "risk_pct":       round(risk_pct, 4),
        "target_pct":     round(target_pct, 4),
        "position_scale": round(scale, 4),
        "alpha_score":    round(alpha_score, 2),
        "display_only":   True,
    }

# =========================
# FILE: core/__init__.py
# =========================
# EGX Radar Pro — core package

# =========================
# FILE: core/indicators.py
# =========================
"""
core/indicators.py — EGX Radar Pro
======================================
Low-level technical indicator calculations.

All functions are stateless and take slices of OHLCV data as input.
They return scalar floats — no side-effects.

Dependencies: numpy, pandas, utils.helpers  (no other internal imports)
"""






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

# =========================
# FILE: core/market_regime.py
# =========================
"""
core/market_regime.py — EGX Radar Pro
==========================================
Market-wide and sector-level regime detection.

Regime classification is used as an execution gate in signal_engine.py:
  - BEAR  → no new entries allowed
  - NEUTRAL / BULL → entries allowed per SmartRank threshold

Regime detection uses breadth metrics across the full universe snapshot,
not individual symbol data.
"""






def detect_market_regime(universe_snaps: List[Snapshot]) -> str:
    """
    Classify the current broad market as BULL, BEAR, or NEUTRAL.

    Methodology
    -----------
    - Breadth above EMA50  : fraction of symbols trading above their 50-day EMA
    - Breadth above EMA200 : fraction of symbols trading above their 200-day EMA
    - Average SmartRank    : mean SmartRank across the universe

    BULL  : breadth_ema50 >= 60%, breadth_ema200 >= 55%, avg_rank >= 52
    BEAR  : breadth_ema50 <= 35%  OR  avg_rank < 42
    NEUTRAL : everything in between

    Parameters
    ----------
    universe_snaps : all Snapshot objects computed for the current bar

    Returns
    -------
    "BULL" | "BEAR" | "NEUTRAL"
    """
    if not universe_snaps:
        return "NEUTRAL"

    n = len(universe_snaps)
    breadth_ema50  = sum(1 for s in universe_snaps if s.close > s.ema50)  / n
    breadth_ema200 = sum(1 for s in universe_snaps if s.close > s.ema200) / n
    avg_rank       = sum(s.smart_rank for s in universe_snaps) / n

    if breadth_ema50 >= 0.60 and breadth_ema200 >= 0.55 and avg_rank >= 52:
        return "BULL"
    if breadth_ema50 <= 0.35 or avg_rank < 42:
        return "BEAR"
    return "NEUTRAL"


def sector_strength(snaps: List[Snapshot]) -> Dict[str, float]:
    """
    Compute average SmartRank per sector.

    This is a display / monitoring metric — it does not affect execution.

    Returns
    -------
    dict mapping sector name → average SmartRank (rounded to 2 dp)
    """
    bucket: Dict[str, List[float]] = {}
    for s in snaps:
        bucket.setdefault(s.sector, []).append(s.smart_rank)
    return {k: round(float(np.mean(v)), 2) for k, v in bucket.items() if v}

# =========================
# FILE: core/smart_rank.py
# =========================
"""
core/smart_rank.py — EGX Radar Pro
======================================
Legacy and Smart Rank 2.0 scoring logic.

Smart Rank 2.0 uses a filter-first model:
1) Hard filters must pass (trend, momentum zone, volume, ATR control, breakout quality)
2) Only then compute a clean weighted score
"""





def smart_rank_legacy(snapshot: Snapshot) -> float:
    """Legacy score retained for old-vs-new baseline comparison."""
    flow      = clamp(snapshot.volume_ratio / 2.2,      0.0, 1.0)
    structure = clamp(snapshot.structure_score / 100.0, 0.0, 1.0)
    timing    = clamp((snapshot.rsi - 35.0) / 40.0,     0.0, 1.0)
    momentum  = clamp(snapshot.trend_strength,           0.0, 1.0)
    regime    = 1.0 if snapshot.close > snapshot.ema200 else 0.4

    raw_score = (
        0.30 * flow
        + 0.25 * structure
        + 0.20 * timing
        + 0.10 * momentum
        + 0.10 * regime
        + 0.05 * 0.5
    ) * 100.0
    return round(clamp(raw_score, 0.0, 100.0), 2)


def _v2_params(overrides: Dict | None = None) -> Dict[str, float]:
    params = {
        "rsi_min": CFG.v2_rsi_min,
        "rsi_max": CFG.v2_rsi_max,
        "volume_min": CFG.v2_volume_min,
        "atr_pct_max": CFG.v2_atr_pct_max,
        "breakout_min": CFG.v2_breakout_min,
        "score_threshold": CFG.v2_score_threshold,
    }
    if overrides:
        params.update(overrides)
    return params


def smart_rank_v2_filters(snapshot: Snapshot, params: Dict | None = None) -> Tuple[bool, Dict[str, bool]]:
    """Hard filters for Smart Rank 2.0: all must pass."""
    p = _v2_params(params)
    checks = {
        "trend_ok": bool(snapshot.close > snapshot.ema50 and snapshot.close > snapshot.ema200),
        "rsi_ok": bool(p["rsi_min"] <= snapshot.rsi <= p["rsi_max"]),
        "volume_ok": bool(snapshot.volume_ratio > p["volume_min"]),
        "atr_ok": bool(snapshot.atr_pct <= p["atr_pct_max"]),
        "breakout_ok": bool(snapshot.breakout_proximity >= p["breakout_min"]),
    }
    return all(checks.values()), checks


def smart_rank_v2(snapshot: Snapshot, params: Dict | None = None) -> float:
    """
    Smart Rank 2.0 clean score.

    Assumes filters have already passed; still bounded to [0,100].
    """
    p = _v2_params(params)

    trend_score = clamp((snapshot.close / max(snapshot.ema50, 1e-9) - 1.0) / 0.08, 0.0, 1.0)

    mid = (p["rsi_min"] + p["rsi_max"]) / 2.0
    half_range = max((p["rsi_max"] - p["rsi_min"]) / 2.0, 1e-9)
    momentum_score = clamp(1.0 - abs(snapshot.rsi - mid) / half_range, 0.0, 1.0)

    volume_score = clamp((snapshot.volume_ratio - p["volume_min"]) / 1.8, 0.0, 1.0)
    volatility_score = clamp(1.0 - (snapshot.atr_pct / max(p["atr_pct_max"], 1e-9)), 0.0, 1.0)
    breakout_score = clamp(
        (snapshot.breakout_proximity - p["breakout_min"]) / max(1.0 - p["breakout_min"], 1e-9),
        0.0,
        1.0,
    )

    raw_score = (
        0.30 * trend_score
        + 0.20 * momentum_score
        + 0.20 * volume_score
        + 0.15 * volatility_score
        + 0.15 * breakout_score
    ) * 100.0

    return round(clamp(raw_score, 0.0, 100.0), 2)

# =========================
# FILE: core/signal_engine.py
# =========================
"""
core/signal_engine.py — EGX Radar Pro
==========================================
Signal evaluation and trade entry generation.

Two strategy modes:
- legacy: original SmartRank thresholds (for baseline comparison only)
- v2: strict filter-first engine (production edge rebuild)
"""





log = get_logger(__name__)


def evaluate_snapshot(
    df_slice: pd.DataFrame,
    symbol: str,
    learning_bias: float = 0.0,
) -> Optional[Snapshot]:
    """Build and enrich one market snapshot from an OHLCV slice."""
    if len(df_slice) < CFG.warmup_bars:
        return None

    c = df_slice["Close"].astype(float)
    v = df_slice["Volume"].astype(float)

    e20 = ema_last(c, 20)
    e50 = ema_last(c, 50)
    e200 = ema_last(c, 200)
    rsi = rsi_wilder(c)
    atr = atr_wilder(df_slice)
    close = float(c.iloc[-1])

    atr_pct = atr / max(close, 1e-9)
    vol_ratio = clamp(volume_ratio(v), 0.0, 4.0)
    trend = clamp((close - e50) / max(e50, 1e-9) * 5.0, 0.0, 1.0)
    structure = clamp((0.5 * float(close > e20) + 0.5 * float(close > e50)) * 100.0, 0.0, 100.0)

    recent_high = float(df_slice["High"].astype(float).tail(CFG.v2_breakout_lookback).max())
    breakout_proximity = close / max(recent_high, 1e-9)

    snap = Snapshot(
        date=df_slice.index[-1],
        symbol=symbol,
        sector=SECTOR_BY_SYMBOL.get(symbol, "OTHER"),
        close=close,
        open=float(df_slice["Open"].iloc[-1]),
        high=float(df_slice["High"].iloc[-1]),
        low=float(df_slice["Low"].iloc[-1]),
        volume=float(v.iloc[-1]),
        rsi=round(rsi, 2),
        atr=round(atr, 4),
        atr_pct=round(atr_pct, 6),
        ema20=round(e20, 3),
        ema50=round(e50, 3),
        ema200=round(e200, 3),
        volume_ratio=round(vol_ratio, 3),
        trend_strength=round(trend, 4),
        structure_score=round(structure, 2),
        smart_rank=0.0,
        smart_rank_v2=0.0,
        breakout_proximity=round(breakout_proximity, 5),
    )

    snap.smart_rank = smart_rank_legacy(snap)
    snap.smart_rank_v2 = smart_rank_v2(snap)

    # Display-only enrichment
    now = snap.date.to_pydatetime().replace(tzinfo=None)
    news = fetch_news(symbol, snap.date)
    snap.sentiment_score = sentiment_score(news, snap, now)
    snap.alpha_score = compute_alpha_score(news, snap, now)
    snap.probability = probability_engine(snap, learning_bias)

    return snap


def _legacy_plan(snapshot: Snapshot) -> Optional[Tuple[str, dict]]:
    if snapshot.smart_rank >= CFG.smart_rank_accumulate:
        entry = snapshot.close
        stop = entry * (1.0 - min(max(snapshot.atr_pct * 1.4, 0.01), 0.03))
        target = entry * 1.08
        return "MAIN", {"entry": entry, "stop": stop, "target": target, "risk_used": RISK.risk_per_trade}

    if snapshot.smart_rank >= CFG.smart_rank_probe:
        entry = snapshot.close
        stop = entry * (1.0 - min(max(snapshot.atr_pct * 1.2, 0.01), 0.025))
        target = entry * 1.06
        return "PROBE", {
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_used": RISK.risk_per_trade * 0.65,
        }
    return None


def _v2_plan(snapshot: Snapshot, params: Optional[Dict] = None) -> Optional[Tuple[str, dict]]:
    passed, _ = smart_rank_v2_filters(snapshot, params)
    if not passed:
        return None

    p = {
        "score_threshold": CFG.v2_score_threshold,
        "stop_atr_mult": CFG.v2_stop_atr_mult,
        "min_rr": CFG.v2_min_rr,
    }
    if params:
        p.update(params)

    score = smart_rank_v2(snapshot, params)
    if score < p["score_threshold"]:
        return None

    entry = snapshot.close
    stop = entry - (snapshot.atr * p["stop_atr_mult"])
    if stop <= 0.0 or stop >= entry:
        return None

    risk_per_share = entry - stop
    target = entry + (max(p["min_rr"], 2.0) * risk_per_share)

    rr = (target - entry) / max(entry - stop, 1e-9)
    if rr < 2.0:
        return None

    return "MAIN", {
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_used": RISK.risk_per_trade,
        "smart_rank_v2": score,
    }


def generate_trade_signal(
    snapshot: Snapshot,
    regime: str,
    open_trades: List[Trade],
    use_ai: bool = True,
    use_alpha: bool = True,
    strategy: str = "legacy",
    strategy_params: Optional[Dict] = None,
) -> Optional[Tuple[str, dict]]:
    """
    Entry decision engine.

    strategy="legacy" for baseline comparison.
    strategy="v2" for strict filter-first execution.
    """
    _ = (use_ai, use_alpha)

    if regime == "BEAR":
        return None

    if sum(1 for t in open_trades if t.status == "OPEN") >= RISK.max_open_trades:
        return None

    if sector_positions(open_trades).get(snapshot.sector, 0) >= RISK.max_sector_positions:
        return None

    if strategy == "v2":
        return _v2_plan(snapshot, strategy_params)

    return _legacy_plan(snapshot)


def format_signal_log(snapshot: Snapshot, decision: str) -> str:
    """Human-readable signal formatting."""
    if snapshot.sentiment_score >= 0.55:
        sentiment_label = "Positive"
    elif snapshot.sentiment_score <= 0.45:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"

    action = "BUY" if decision in {"MAIN", "PROBE"} else "WAIT"
    signal_tag = f" [{decision}]" if action == "BUY" else ""

    return (
        f"SYMBOL: {snapshot.symbol}\n"
        f"SmartRank(legacy): {snapshot.smart_rank:.2f}\n"
        f"SmartRank(2.0):    {snapshot.smart_rank_v2:.2f} -> {action}{signal_tag}\n"
        f"\n"
        f"AI Probability : {snapshot.probability:.4f}\n"
        f"Sentiment      : {snapshot.sentiment_score:.4f} ({sentiment_label})\n"
        f"Alpha Score    : {snapshot.alpha_score:.2f}\n"
        f"\n"
        f"Decision: {action} (strategy-controlled, AI/News/Alpha display only)"
    )

# =========================
# FILE: risk/__init__.py
# =========================
# EGX Radar Pro — risk package

# =========================
# FILE: risk/position_sizing.py
# =========================
"""
risk/position_sizing.py — EGX Radar Pro
==========================================
Fixed-fractional position sizing calculator.

Sizing Rule
-----------
  risk_amount    = account_size × risk_used_fraction
  risk_per_share = max(entry - stop, entry × 0.5%)
  size           = risk_amount / risk_per_share  (integer, minimum 1)

This produces dollar-risk-based sizing: the position size is set so that
a stop-loss hit costs exactly risk_amount in base currency.

The function is deterministic and has no side-effects.
"""



def compute_position_size(
    entry:        float,
    stop:         float,
    risk_used:    float,
    account_size: float,
) -> int:
    """
    Calculate the number of shares to purchase for a new position.

    Parameters
    ----------
    entry        : Actual entry price (post-slippage)
    stop         : Stop-loss price
    risk_used    : Fraction of account to risk on this trade
                   (e.g. 0.005 = 0.5%, typical for SmartRank MAIN entries)
    account_size : Current account equity in base currency

    Returns
    -------
    int — number of shares, floored to whole units.
    Returns 0 only if risk_amount <= 0 (should not occur in normal usage).
    Returns at least 1 share when risk_amount > 0.

    Notes
    -----
    The minimum risk_per_share floor (entry × 0.5%) prevents absurdly
    large position sizes when stop is very close to entry.
    """
    risk_amount    = account_size * risk_used
    risk_per_share = max(entry - stop, entry * 0.005)

    if risk_amount <= 0:
        return 0

    return max(1, int(risk_amount / max(risk_per_share, 1e-9)))

# =========================
# FILE: risk/portfolio.py
# =========================
"""
risk/portfolio.py — EGX Radar Pro
=====================================
Portfolio-level position tracking and concentration rules.

Functions here enforce the outer risk shell that wraps every entry
decision — regardless of which signal triggered it.

Limits
------
  max_open_trades      : Global cap on concurrent positions
  max_sector_positions : Per-sector concentration limit
  max_sector_exposure  : Max capital fraction in one sector

All limits are read from RISK (RiskConfig singleton in config.settings).
"""





def sector_positions(open_trades: List[Trade]) -> Dict[str, int]:
    """
    Count currently open positions per sector.

    Parameters
    ----------
    open_trades : Full list of Trade objects (open and closed mixed)

    Returns
    -------
    dict mapping sector name → count of OPEN positions in that sector
    """
    counts: Dict[str, int] = {}
    for t in open_trades:
        if t.status == "OPEN":
            counts[t.sector] = counts.get(t.sector, 0) + 1
    return counts


def can_open_position(sector: str, open_trades: List[Trade]) -> bool:
    """
    Check all portfolio-level constraints before opening a new position.

    Checks
    ------
    1. Global open trade cap (RISK.max_open_trades)
    2. Per-sector concentration limit (RISK.max_sector_positions)

    Returns
    -------
    True if a new position is within all limits, False otherwise.
    """
    open_count = sum(1 for t in open_trades if t.status == "OPEN")
    if open_count >= RISK.max_open_trades:
        return False

    if sector_positions(open_trades).get(sector, 0) >= RISK.max_sector_positions:
        return False

    return True


def portfolio_exposure(open_trades: List[Trade]) -> float:
    """
    Total allocated capital as a fraction of account size.

    Used for monitoring and dashboard display — not for execution gating.

    Returns
    -------
    float in [0, ∞)  — typically < 1.0 in a healthy portfolio.
    Values above 1.0 indicate leverage (should not occur in this system).
    """
    total = sum(
        t.entry * t.size
        for t in open_trades
        if t.status == "OPEN"
    )
    return total / max(RISK.account_size, 1e-9)


def portfolio_summary(open_trades: List[Trade]) -> dict:
    """
    Summary statistics for the current open portfolio.

    Returns
    -------
    dict with keys:
      open_positions   : int
      exposure_pct     : float  (fraction of account allocated)
      sector_breakdown : dict[sector → count]
    """
    open_count    = sum(1 for t in open_trades if t.status == "OPEN")
    exposure      = portfolio_exposure(open_trades)
    sectors       = sector_positions(open_trades)
    return {
        "open_positions":   open_count,
        "exposure_pct":     round(exposure * 100.0, 2),
        "sector_breakdown": sectors,
    }

# =========================
# FILE: backtest/__init__.py
# =========================
# EGX Radar Pro — backtest package

# =========================
# FILE: backtest/engine.py
# =========================
"""
backtest/engine.py — EGX Radar Pro
======================================
Walk-forward backtest simulation engine.

Design
------
  - Date-sequential simulation over all dates in market_data
  - For each date: close qualifying positions, then open new entries
  - Entries are filled at next-day open price (realistic simulation)
  - Equity curve tracks compounding portfolio returns
  - All execution decisions delegate to generate_trade_signal()
    which is SmartRank-only — AI and Alpha parameters are for
    display logging only

Trade lifecycle
---------------
  OPEN  → STOP    : Stop-loss hit (priority: gap-down open first)
  OPEN  → TARGET  : Profit target hit
  OPEN  → TIME    : Max holding period reached (time-stop)
  OPEN  → FINAL   : Force-closed at backtest end date

PnL calculation
---------------
  gross_pnl_pct  = (exit_price - entry_price) / entry_price × 100
  net_pnl_pct    = gross_pnl_pct − fee_pct × 100
  equity_update  = equity × (1 + alloc_pct × net_pnl_pct / 100)
  alloc_pct      = min(entry × size / account_size, max_sector_exposure)
"""





log = get_logger(__name__)


def _close_trade(t: Trade, px: float, date: pd.Timestamp, reason: str) -> None:
    """
    Finalise a trade: record exit details and compute net PnL.

    Parameters
    ----------
    t      : Open Trade object (mutated in place)
    px     : Exit price (post-slippage)
    date   : Exit date
    reason : "STOP" | "TARGET" | "TIME" | "FINAL"
    """
    gross    = (px - t.entry) / max(t.entry, 1e-9) * 100.0
    net      = gross - (RISK.fee_pct * 100.0)
    t.exit_price = float(px)
    t.exit_date  = date
    t.status     = reason
    t.pnl_pct    = float(net)


def run_backtest(
    market_data:  Dict[str, pd.DataFrame],
    use_ai:       bool                   = True,
    use_alpha:    bool                   = True,
    learning=None,
    strategy: str = "legacy",
    strategy_params: Optional[Dict] = None,
) -> Tuple[List[Trade], List[Tuple[str, float]]]:
    """
    Full walk-forward backtest simulation.

    Parameters
    ----------
    market_data : {symbol: OHLCV DataFrame}
                  All DataFrames must share compatible date ranges.
    use_ai      : Passed through to generate_trade_signal() — no execution
                  effect (kept for API compatibility and logging).
    use_alpha   : Passed through to generate_trade_signal() — no execution
                  effect (kept for API compatibility and logging).
    learning    : Optional LearningModule.
                  If provided, records each closed trade and supplies an
                  adaptive bias to probability_engine() (display only).
    strategy    : "legacy" or "v2".
    strategy_params : Optional parameter overrides for strategy.

    Returns
    -------
    (closed_trades, equity_curve)
      closed_trades : list of all completed Trade objects
      equity_curve  : list of (date_str, cumulative_return_pct)
                      e.g. [("2023-01-03", 0.0), ("2023-01-04", 0.24), ...]
    """
    all_dates: List[pd.Timestamp] = sorted(
        {d for df in market_data.values() for d in df.index}
    )

    open_trades: List[Trade] = []
    closed:      List[Trade] = []
    equity       = 100.0
    curve:       List[Tuple[str, float]] = []

    for i, date in enumerate(all_dates):

        # ── Build snapshots for every symbol available on this date ────
        snaps: List[Snapshot] = []
        for sym, df in market_data.items():
            if date not in df.index:
                continue
            df_slice = df[df.index <= date].tail(260)
            bias = learning.bias if learning is not None else 0.0
            snap = evaluate_snapshot(df_slice, sym, learning_bias=bias)
            if snap is not None:
                snaps.append(snap)

        regime = detect_market_regime(snaps)

        # ── Manage existing positions ───────────────────────────────────
        for t in list(open_trades):
            sym_df = market_data.get(t.symbol)
            if sym_df is None or date not in sym_df.index:
                continue

            row     = sym_df.loc[date]
            t.bars_held += 1
            open_px = float(row["Open"])
            high    = float(row["High"])
            low     = float(row["Low"])
            close   = float(row["Close"])

            # Stop-loss checks (gap-open priority)
            if open_px <= t.stop:
                _close_trade(t, open_px * (1.0 - RISK.slippage_pct), date, "STOP")
            elif low <= t.stop:
                _close_trade(t, t.stop  * (1.0 - RISK.slippage_pct), date, "STOP")
            elif high >= t.target:
                _close_trade(t, t.target * (1.0 - RISK.slippage_pct), date, "TARGET")
            elif t.bars_held >= RISK.max_bars_hold:
                _close_trade(t, close   * (1.0 - RISK.slippage_pct), date, "TIME")
            else:
                continue   # position still open

            # Update equity for the closed trade
            alloc_pct = min(
                (t.entry * t.size) / max(RISK.account_size, 1e-9),
                RISK.max_sector_exposure_pct,
            )
            equity *= 1.0 + alloc_pct * (t.pnl_pct / 100.0)
            closed.append(t)

            if learning is not None:
                learning.record(t.pnl_pct)

            open_trades.remove(t)

            log.debug(
                "Closed %-6s @ %.3f  PnL=%+.2f%%  [%s]  bars=%d",
                t.symbol, t.exit_price, t.pnl_pct, t.status, t.bars_held,
            )

        # ── Generate new entries (filled at next open) ──────────────────
        if i + 1 < len(all_dates):
            next_date   = all_dates[i + 1]
            taken_today = {t.symbol for t in open_trades if t.status == "OPEN"}

            if strategy == "v2":
                ranked_snaps = sorted(snaps, key=lambda x: x.smart_rank_v2, reverse=True)
            else:
                ranked_snaps = sorted(snaps, key=lambda x: x.smart_rank, reverse=True)

            for s in ranked_snaps:
                if s.symbol in taken_today:
                    continue

                sig = generate_trade_signal(
                    s, regime, open_trades,
                    use_ai=use_ai, use_alpha=use_alpha,
                    strategy=strategy,
                    strategy_params=strategy_params,
                )
                if sig is None:
                    continue

                signal_type, plan = sig
                next_df = market_data.get(s.symbol)
                if next_df is None or next_date not in next_df.index:
                    continue

                next_open = float(next_df.loc[next_date]["Open"])
                entry     = float(plan["entry"])
                stop      = float(plan["stop"])
                target    = float(plan["target"])
                risk_used = float(plan["risk_used"])

                size = compute_position_size(entry, stop, risk_used, RISK.account_size)
                if size <= 0:
                    continue

                trade = Trade(
                    symbol          = s.symbol,
                    sector          = s.sector,
                    entry_date      = next_date,
                    entry           = next_open * (1.0 + RISK.slippage_pct),
                    stop            = stop,
                    target          = target,
                    size            = size,
                    risk_used       = risk_used,
                    signal_type     = signal_type,
                    smart_rank      = s.smart_rank_v2 if strategy == "v2" else s.smart_rank,
                    probability     = s.probability,      # display only
                    sentiment_score = s.sentiment_score,  # display only
                    alpha_score     = s.alpha_score,       # display only
                )
                open_trades.append(trade)
                taken_today.add(s.symbol)

                log.debug(
                    "Entry  %-6s @ %.3f  SR=%.1f  type=%s  P=%.3f  "
                    "Sent=%.3f  Alpha=%.1f",
                    s.symbol, next_open, s.smart_rank, signal_type,
                    s.probability, s.sentiment_score, s.alpha_score,
                )

                if len([t for t in open_trades if t.status == "OPEN"]) >= RISK.max_open_trades:
                    break

        curve.append((date.strftime("%Y-%m-%d"), round(equity - 100.0, 3)))

    # ── Force-close remaining positions at end of data ─────────────────
    if all_dates:
        last = all_dates[-1]
        for t in list(open_trades):
            sym_df = market_data.get(t.symbol)
            if sym_df is not None and last in sym_df.index:
                exit_px = float(sym_df.loc[last]["Close"]) * (1.0 - RISK.slippage_pct)
                _close_trade(t, exit_px, last, "FINAL")
                alloc_pct = min(
                    (t.entry * t.size) / max(RISK.account_size, 1e-9),
                    RISK.max_sector_exposure_pct,
                )
                equity *= 1.0 + alloc_pct * (t.pnl_pct / 100.0)
                closed.append(t)
                if learning is not None:
                    learning.record(t.pnl_pct)

        if curve:
            curve[-1] = (curve[-1][0], round(equity - 100.0, 3))

    log.info(
        "Backtest finished — %d trades closed  |  final equity: %+.2f%%",
        len(closed), equity - 100.0,
    )
    return closed, curve

# =========================
# FILE: backtest/metrics.py
# =========================
"""
backtest/metrics.py — EGX Radar Pro
=======================================
Performance metric computation from completed backtest results.

All functions operate on closed Trade lists and equity curves
produced by backtest/engine.py.

Metrics
-------
  trades          : Total number of closed trades
  return_pct      : Cumulative portfolio return (%)
  winrate_pct     : Percentage of trades closed with positive PnL
  drawdown_pct    : Maximum peak-to-trough drawdown (%)
  sharpe          : Annualised Sharpe ratio (assuming 252 trading days)
  expectancy_pct  : Mean PnL per trade (%)
"""






def performance_metrics(
    trades: List[Trade],
    curve:  List[Tuple[str, float]],
) -> Dict[str, float]:
    """
    Compute standard performance metrics from a completed backtest.

    Parameters
    ----------
    trades : List of closed Trade objects
    curve  : Equity curve as [(date_str, cumulative_return_pct), ...]

    Returns
    -------
    dict with keys:
      trades, return_pct, winrate_pct, drawdown_pct, sharpe, expectancy_pct
    """
    if not trades:
        return {
            "trades":          0,
            "return_pct":      0.0,
            "winrate_pct":     0.0,
            "drawdown_pct":    0.0,
            "sharpe":          0.0,
            "expectancy_pct":  0.0,
        }

    pnl_arr    = np.array([t.pnl_pct for t in trades], dtype=float)
    winrate    = float(np.mean(pnl_arr > 0) * 100.0)
    expectancy = float(np.mean(pnl_arr))

    # Equity curve (base = 100)
    eq   = np.array([v for _, v in curve], dtype=float) + 100.0
    peak = np.maximum.accumulate(eq)
    dd   = (eq - peak) / np.maximum(peak, 1e-9)
    drawdown = float(abs(dd.min()) * 100.0)

    # Annualised Sharpe ratio
    rets   = np.diff(eq) / np.maximum(eq[:-1], 1e-9)
    sharpe = 0.0
    if len(rets) > 5 and float(np.std(rets)) > 1e-9:
        sharpe = float((np.mean(rets) / np.std(rets)) * math.sqrt(252))

    return {
        "trades":          int(len(trades)),
        "return_pct":      float(round(eq[-1] - 100.0, 2)),
        "winrate_pct":     float(round(winrate, 2)),
        "drawdown_pct":    float(round(drawdown, 2)),
        "sharpe":          float(round(sharpe, 2)),
        "expectancy_pct":  float(round(expectancy, 2)),
    }


def breakdown_by_signal_type(trades: List[Trade]) -> Dict[str, Dict[str, float]]:
    """
    Split performance metrics by signal type (MAIN vs PROBE).

    Returns
    -------
    dict mapping signal_type → {winrate, count, avg_pnl}
    """
    buckets: Dict[str, List[float]] = {}
    for t in trades:
        buckets.setdefault(t.signal_type, []).append(t.pnl_pct)

    result = {}
    for sig_type, pnls in buckets.items():
        arr = np.array(pnls, dtype=float)
        result[sig_type] = {
            "count":    len(pnls),
            "winrate":  round(float(np.mean(arr > 0) * 100.0), 2),
            "avg_pnl":  round(float(np.mean(arr)), 4),
        }
    return result


def breakdown_by_sector(trades: List[Trade]) -> Dict[str, Dict[str, float]]:
    """
    Split performance metrics by sector.

    Returns
    -------
    dict mapping sector → {count, winrate, avg_pnl}
    """
    buckets: Dict[str, List[float]] = {}
    for t in trades:
        buckets.setdefault(t.sector, []).append(t.pnl_pct)

    result = {}
    for sector, pnls in buckets.items():
        arr = np.array(pnls, dtype=float)
        result[sector] = {
            "count":    len(pnls),
            "winrate":  round(float(np.mean(arr > 0) * 100.0), 2),
            "avg_pnl":  round(float(np.mean(arr)), 4),
        }
    return result


def print_metrics(label: str, metrics: Dict[str, float]) -> None:
    """Pretty-print a metrics dict with a section header."""
    print(f"\n{'─' * 44}")
    print(f"  {label.upper()}")
    print(f"{'─' * 44}")
    for key, val in metrics.items():
        print(f"  {key:16} : {val}")

# =========================
# FILE: backtest/optimizer.py
# =========================
"""
backtest/optimizer.py — EGX Radar Pro
========================================
Grid-search optimizer for Smart Rank 2.0 strategy parameters.
"""






def _candidate_grid() -> List[Dict[str, float]]:
    return [
        {"rsi_min": 44.0, "rsi_max": 64.0, "volume_min": 1.10, "atr_pct_max": 0.030, "score_threshold": 58.0},
        {"rsi_min": 44.0, "rsi_max": 64.0, "volume_min": 1.20, "atr_pct_max": 0.030, "score_threshold": 60.0},
        {"rsi_min": 45.0, "rsi_max": 65.0, "volume_min": 1.20, "atr_pct_max": 0.035, "score_threshold": 62.0},
        {"rsi_min": 46.0, "rsi_max": 66.0, "volume_min": 1.10, "atr_pct_max": 0.035, "score_threshold": 60.0},
        {"rsi_min": 47.0, "rsi_max": 65.0, "volume_min": 1.15, "atr_pct_max": 0.035, "score_threshold": 58.0},
        {"rsi_min": 45.0, "rsi_max": 63.0, "volume_min": 1.25, "atr_pct_max": 0.030, "score_threshold": 62.0},
        {"rsi_min": 43.0, "rsi_max": 67.0, "volume_min": 1.10, "atr_pct_max": 0.035, "score_threshold": 56.0},
        {"rsi_min": 45.0, "rsi_max": 65.0, "volume_min": 1.05, "atr_pct_max": 0.040, "score_threshold": 55.0},
    ]


def _objective(metrics: Dict[str, float]) -> float:
    """Favor expectancy and drawdown stability, then winrate."""
    return (
        2.4 * metrics["expectancy_pct"]
        + 0.8 * metrics["winrate_pct"]
        - 1.6 * metrics["drawdown_pct"]
    )


def optimize_v2(market_data: Dict[str, pd.DataFrame]) -> Dict:
    """
    Run grid search and return best Smart Rank 2.0 parameter set.

    Returns
    -------
    dict with:
      best_params, best_metrics, top_results
    """
    results: List[Dict] = []

    for params in _candidate_grid():
        trades, curve = run_backtest(
            market_data,
            use_ai=False,
            use_alpha=False,
            learning=None,
            strategy="v2",
            strategy_params=params,
        )
        metrics = performance_metrics(trades, curve)

        # Avoid overfitting to tiny sample sizes
        if metrics["trades"] < 5:
            continue

        results.append(
            {
                "params": params,
                "metrics": metrics,
                "objective": round(_objective(metrics), 4),
            }
        )

    if not results:
        raise RuntimeError("Optimizer found no valid parameter sets (all had too few trades).")

    results.sort(key=lambda x: x["objective"], reverse=True)
    return {
        "best_params": results[0]["params"],
        "best_metrics": results[0]["metrics"],
        "all_results": results,
        "top_results": results[:10],
    }

# =========================
# FILE: backtest/validator.py
# =========================
"""
backtest/validator.py — EGX Radar Pro
=========================================
Validation and diagnosis toolkit.
"""





log = get_logger(__name__)


def validate_system(
    market_data: Dict[str, pd.DataFrame],
    strategy: str = "legacy",
    strategy_params: Dict | None = None,
) -> Dict[str, Dict[str, float]]:
    """
    Run three-mode parity validation for a given strategy.

    Execution must be identical across baseline/ai/alpha modes because
    AI/News/Alpha remain display-only.
    """
    baseline_trades, baseline_curve = run_backtest(
        market_data,
        use_ai=False,
        use_alpha=False,
        learning=None,
        strategy=strategy,
        strategy_params=strategy_params,
    )

    learning = LearningModule()
    ai_trades, ai_curve = run_backtest(
        market_data,
        use_ai=True,
        use_alpha=False,
        learning=learning,
        strategy=strategy,
        strategy_params=strategy_params,
    )

    alpha_trades, alpha_curve = run_backtest(
        market_data,
        use_ai=True,
        use_alpha=True,
        learning=learning,
        strategy=strategy,
        strategy_params=strategy_params,
    )

    counts = (len(baseline_trades), len(ai_trades), len(alpha_trades))
    if not (counts[0] == counts[1] == counts[2]):
        raise RuntimeError(
            f"EXECUTION PARITY FAILED for strategy='{strategy}'.\n"
            f"  baseline={counts[0]} ai={counts[1]} alpha={counts[2]}"
        )

    return {
        "baseline": performance_metrics(baseline_trades, baseline_curve),
        "ai": performance_metrics(ai_trades, ai_curve),
        "alpha": performance_metrics(alpha_trades, alpha_curve),
    }


def diagnose_failure(market_data: Dict[str, pd.DataFrame]) -> Dict:
    """Return a data-driven diagnosis for why legacy mode loses edge."""
    trades, curve = run_backtest(market_data, strategy="legacy", use_ai=False, use_alpha=False)
    metrics = performance_metrics(trades, curve)

    pnls = np.array([t.pnl_pct for t in trades], dtype=float) if trades else np.array([], dtype=float)
    sr = np.array([t.smart_rank for t in trades], dtype=float) if trades else np.array([], dtype=float)
    exits = dict(Counter([t.status for t in trades]))

    # Reconstruct filter quality at signal time to expose weak entries
    sampled = 0
    trend_fail = 0
    rsi_outside = 0
    vol_low = 0
    atr_high = 0

    for t in trades:
        df = market_data[t.symbol]
        pos = df.index.get_loc(t.entry_date)
        if isinstance(pos, slice) or pos <= 0:
            continue
        signal_date = df.index[pos - 1]
        snap = evaluate_snapshot(df[df.index <= signal_date].tail(260), t.symbol, learning_bias=0.0)
        if snap is None:
            continue

        sampled += 1
        if not (snap.close > snap.ema50 and snap.close > snap.ema200):
            trend_fail += 1
        if not (45.0 <= snap.rsi <= 65.0):
            rsi_outside += 1
        if not (snap.volume_ratio > 1.2):
            vol_low += 1
        if not (snap.atr_pct <= 0.03):
            atr_high += 1

    sr_buckets = []
    for a, b in [(55, 60), (60, 65), (65, 70), (70, 75), (75, 100)]:
        if len(sr) == 0:
            continue
        idx = (sr >= a) & (sr < b)
        c = int(idx.sum())
        if c == 0:
            continue
        sr_buckets.append(
            {
                "bucket": f"{a}-{b}",
                "count": c,
                "winrate_pct": round(float((pnls[idx] > 0).mean() * 100.0), 2),
                "expectancy_pct": round(float(pnls[idx].mean()), 4),
            }
        )

    return {
        "legacy_metrics": metrics,
        "legacy_exit_mix": exits,
        "entry_quality": {
            "sampled_entries": sampled,
            "trend_fail_pct": round(100.0 * trend_fail / max(sampled, 1), 2),
            "rsi_outside_45_65_pct": round(100.0 * rsi_outside / max(sampled, 1), 2),
            "volume_ratio_le_1_2_pct": round(100.0 * vol_low / max(sampled, 1), 2),
            "atr_pct_gt_3_pct": round(100.0 * atr_high / max(sampled, 1), 2),
        },
        "legacy_smart_rank_buckets": sr_buckets,
    }


def validate_old_vs_new(market_data: Dict[str, pd.DataFrame]) -> Dict:
    """
    Compare legacy strategy vs Smart Rank 2.0 with optimizer-selected params.

    Raises RuntimeError if the new strategy fails to improve all required metrics.
    """
    old_trades, old_curve = run_backtest(
        market_data,
        use_ai=False,
        use_alpha=False,
        learning=None,
        strategy="legacy",
    )
    old_metrics = performance_metrics(old_trades, old_curve)

    opt = optimize_v2(market_data)
    viable = [
        r for r in opt["all_results"]
        if r["metrics"]["expectancy_pct"] > old_metrics["expectancy_pct"]
        and r["metrics"]["drawdown_pct"] < old_metrics["drawdown_pct"]
        and r["metrics"]["winrate_pct"] > old_metrics["winrate_pct"]
    ]
    if not viable:
        raise RuntimeError("No Smart Rank 2.0 parameter set improved expectancy, drawdown, and winrate together.")

    viable.sort(key=lambda x: x["objective"], reverse=True)
    new_params = viable[0]["params"]

    new_trades, new_curve = run_backtest(
        market_data,
        use_ai=False,
        use_alpha=False,
        learning=None,
        strategy="v2",
        strategy_params=new_params,
    )
    new_metrics = performance_metrics(new_trades, new_curve)

    improved = {
        "expectancy": new_metrics["expectancy_pct"] > old_metrics["expectancy_pct"],
        "drawdown": new_metrics["drawdown_pct"] < old_metrics["drawdown_pct"],
        "winrate": new_metrics["winrate_pct"] > old_metrics["winrate_pct"],
    }

    if not all(improved.values()):
        raise RuntimeError(
            "Smart Rank 2.0 did not satisfy mandatory improvement gates. "
            f"Improvements={improved}"
        )

    parity = validate_system(market_data, strategy="v2", strategy_params=new_params)

    return {
        "old": old_metrics,
        "new": new_metrics,
        "new_params": new_params,
        "optimizer_top": opt["top_results"],
        "improved": improved,
        "parity_v2": parity,
    }

# =========================
# FILE: ai/__init__.py
# =========================
# EGX Radar Pro — ai package

# =========================
# FILE: ai/probability_engine.py
# =========================
"""
ai/probability_engine.py — EGX Radar Pro
==========================================
AI probability estimator — DISPLAY ONLY.

Computes the estimated probability that a trade will be profitable,
using a logistic function over a weighted combination of technical
factors.  The output is used exclusively for display/advisory purposes.

CRITICAL: This value must NEVER appear in generate_trade_signal() or
any other execution path.

Architecture
------------
  Input weights
    34%   SmartRank (primary driver)
    20%   Market structure (EMA alignment score)
    16%   RSI timing (ideal accumulation zone)
    10%   Volume confirmation
     8%   Trend momentum
    10%   ATR risk penalty (negative weight)
    +/-   Learning bias (adaptive, bounded ±0.10)

  Activation: logistic sigmoid applied to the weighted sum
  Sentiment:  mild modulation factor applied post-sigmoid
  Output:     clamped to [0.05, 0.95]
"""





def probability_engine(snapshot: Snapshot, learning_bias: float = 0.0) -> float:
    """
    Estimate trade success probability for a given market snapshot.

    Parameters
    ----------
    snapshot      : Fully-evaluated market Snapshot (all fields populated).
    learning_bias : Adaptive bias from LearningModule.bias.
                    Bounded to [-0.10, +0.10].
                    Has NO effect on SmartRank or execution decisions.

    Returns
    -------
    float in [0.05, 0.95]
    """
    raw = (
        0.34 * (snapshot.smart_rank / 100.0)
        + 0.20 * (snapshot.structure_score / 100.0)
        + 0.16 * clamp((snapshot.rsi - 35.0) / 40.0, 0.0, 1.0)
        + 0.10 * clamp(snapshot.volume_ratio / 2.5,  0.0, 1.0)
        + 0.08 * clamp(snapshot.trend_strength,       0.0, 1.0)
        - 0.10 * clamp(snapshot.atr_pct / 0.08,      0.0, 1.0)
        + learning_bias
    )

    # Logistic activation centred at 0.50
    centered = (raw - 0.50) * 6.0
    p = 1.0 / (1.0 + math.exp(-centered))

    # Mild sentiment modulation (keeps range well within [0.05, 0.95])
    p = p * (0.95 + 0.10 * snapshot.sentiment_score)

    return round(clamp(p, 0.05, 0.95), 4)

# =========================
# FILE: ai/learning.py
# =========================
"""
ai/learning.py — EGX Radar Pro
==================================
Adaptive learning state — tracks win/loss history and derives a mild
probability bias used ONLY for the AI display layer.

This module has NO effect on execution decisions.  The learning bias is
fed exclusively into probability_engine() which is a display-only metric.

Persistence: JSON file on disk (default: learning_state.json).
"""




log = get_logger(__name__)


@dataclass
class LearningState:
    """Rolling trade statistics persisted between runs."""
    wins:    int   = 0
    losses:  int   = 0
    avg_pnl: float = 0.0


class LearningModule:
    """
    Record closed trade outcomes and expose an adaptive probability bias.

    Usage
    -----
        learning = LearningModule()
        ...
        learning.record(trade.pnl_pct)   # after each trade closes
        bias = learning.bias             # pass to probability_engine()

    The bias is bounded to [-0.10, +0.10] and only activates after 10 trades.
    """

    def __init__(self, path: str = "learning_state.json") -> None:
        self.path  = Path(path)
        self.state = LearningState()
        self._load()

    # ── Persistence ────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.state = LearningState(
                wins    = int(raw.get("wins", 0)),
                losses  = int(raw.get("losses", 0)),
                avg_pnl = float(raw.get("avg_pnl", 0.0)),
            )
            log.debug(
                "Learning state loaded — wins=%d losses=%d avg_pnl=%.4f",
                self.state.wins, self.state.losses, self.state.avg_pnl,
            )
        except Exception as exc:
            log.warning("Could not load learning state (%s) — starting fresh.", exc)
            self.state = LearningState()

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "wins":    self.state.wins,
                    "losses":  self.state.losses,
                    "avg_pnl": round(self.state.avg_pnl, 4),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── Public interface ────────────────────────────────────────────────

    def record(self, pnl_pct: float) -> None:
        """Record the PnL of a closed trade and persist updated state."""
        if pnl_pct >= 0:
            self.state.wins += 1
        else:
            self.state.losses += 1
        n = self.state.wins + self.state.losses
        self.state.avg_pnl = ((self.state.avg_pnl * (n - 1)) + pnl_pct) / max(n, 1)
        self._save()

    @property
    def bias(self) -> float:
        """
        Adaptive learning bias in (-0.10, +0.10).

        Positive when win rate is above 50%, negative below.
        Returns 0.0 until at least 10 trades have been recorded.
        Consumed only by probability_engine() — never by execution logic.
        """
        n = self.total_trades
        if n < 10:
            return 0.0
        win_rate = self.state.wins / n
        return (win_rate - 0.5) * 0.2

    @property
    def total_trades(self) -> int:
        return self.state.wins + self.state.losses

    @property
    def win_rate(self) -> float:
        n = self.total_trades
        return self.state.wins / n if n > 0 else 0.0

    def summary(self) -> dict:
        return {
            "wins":        self.state.wins,
            "losses":      self.state.losses,
            "total":       self.total_trades,
            "win_rate":    round(self.win_rate, 4),
            "avg_pnl":     round(self.state.avg_pnl, 4),
            "bias":        round(self.bias, 5),
        }

# =========================
# FILE: ai/advisor.py
# =========================
"""
ai/advisor.py — EGX Radar Pro
================================
AI advisory layer — DISPLAY ONLY.

Converts raw probability scores into human-readable confidence labels
and structured advisory context dictionaries.

Nothing in this module affects trade execution.
"""




def classify_decision(probability: float) -> str:
    """
    Convert AI probability to a qualitative confidence label.

    Thresholds
    ----------
    >= 0.68  → STRONG
    >= 0.55  → MEDIUM
     < 0.55  → WEAK

    Returns
    -------
    "STRONG" | "MEDIUM" | "WEAK"
    """
    if probability >= 0.68:
        return "STRONG"
    if probability >= 0.55:
        return "MEDIUM"
    return "WEAK"


def get_ai_context(snapshot: Snapshot) -> dict:
    """
    Build a structured AI advisory context for display and logging.

    This dictionary can be shown in a dashboard, written to a log, or
    stored alongside a trade record.  It must never be used to gate
    execution decisions.

    Returns
    -------
    dict with keys:
      probability   float    : AI probability estimate
      confidence    str      : "STRONG" | "MEDIUM" | "WEAK"
      sentiment     float    : news sentiment [0=bearish, 1=bullish]
      alpha_score   float    : alpha opportunity score [0, 100]
      display_only  bool     : always True — documents the intended use
    """
    return {
        "probability":  snapshot.probability,
        "confidence":   classify_decision(snapshot.probability),
        "sentiment":    snapshot.sentiment_score,
        "alpha_score":  snapshot.alpha_score,
        "display_only": True,
    }


def format_ai_summary(snapshot: Snapshot) -> str:
    """
    One-line AI summary string for console display.

    Example: 'AI: STRONG (p=0.7214) | Sentiment: 0.72 | Alpha: 65.4'
    """
    ctx = get_ai_context(snapshot)
    return (
        f"AI: {ctx['confidence']} (p={ctx['probability']:.4f}) | "
        f"Sentiment: {ctx['sentiment']:.4f} | "
        f"Alpha: {ctx['alpha_score']:.2f}"
    )

# =========================
# FILE: main.py
# =========================
"""
main.py — EGX Radar Pro
=========================
Rebuild-edge pipeline:
1) Diagnose why legacy loses
2) Build and optimize Smart Rank 2.0
3) Validate old vs new with strict improvement gates
"""




sys.path.insert(0, str(Path(__file__).parent))


log = get_logger("egx_radar_pro")


def signal_preview(market_data: Dict[str, pd.DataFrame], top_n: int = 5) -> None:
    latest = min(df.index.max() for df in market_data.values() if not df.empty)
    snaps = []
    for sym, df in market_data.items():
        if latest not in df.index:
            continue
        snap = evaluate_snapshot(df[df.index <= latest].tail(260), sym)
        if snap is not None:
            snaps.append(snap)

    regime = detect_market_regime(snaps)
    print(f"\n{'═' * 60}")
    print("  SMART RANK 2.0 PREVIEW")
    print(f"  Date: {latest.strftime('%Y-%m-%d')}   Regime: {regime}")
    print(f"{'═' * 60}")

    shown = 0
    for snap in sorted(snaps, key=lambda s: s.smart_rank_v2, reverse=True):
        sig = generate_trade_signal(snap, regime, [], strategy="v2")
        decision = sig[0] if sig else "WAIT"
        print(format_signal_log(snap, decision))
        print()
        shown += 1
        if shown >= top_n:
            break


def _print_diagnosis(diag: Dict) -> None:
    print(f"\n{'═' * 60}")
    print("  PHASE 1 — DIAGNOSIS")
    print(f"{'═' * 60}")
    print_metrics("legacy metrics", diag["legacy_metrics"])
    print("\n  Exit mix:", diag["legacy_exit_mix"])
    eq = diag["entry_quality"]
    print("\n  Entry quality leakage:")
    print(f"    trend fail %              : {eq['trend_fail_pct']}")
    print(f"    RSI outside 45-65 %       : {eq['rsi_outside_45_65_pct']}")
    print(f"    volume <= 1.2 %           : {eq['volume_ratio_le_1_2_pct']}")
    print(f"    ATR% > 3% %               : {eq['atr_pct_gt_3_pct']}")
    print("\n  SmartRank bucket quality:")
    for row in diag["legacy_smart_rank_buckets"]:
        print(f"    SR {row['bucket']}: n={row['count']} WR={row['winrate_pct']} Exp={row['expectancy_pct']}")


def _print_comparison(comp: Dict) -> None:
    print(f"\n{'═' * 60}")
    print("  PHASE 6 — OLD VS NEW VALIDATION")
    print(f"{'═' * 60}")
    print_metrics("old system", comp["old"])
    print_metrics("new system (smart rank 2.0)", comp["new"])

    print("\n  Optimized parameters:")
    for k, v in comp["new_params"].items():
        print(f"    {k:16}: {v}")

    print("\n  Mandatory improvements:")
    print(f"    expectancy improved : {comp['improved']['expectancy']}")
    print(f"    drawdown improved   : {comp['improved']['drawdown']}")
    print(f"    winrate improved    : {comp['improved']['winrate']}")


def main() -> None:
    log.info("EGX Radar Pro — rebuild edge")

    universe = SYMBOLS[:14]
    market_data = load_market_data(universe, bars=280)

    signal_preview(market_data, top_n=5)

    diag = diagnose_failure(market_data)
    _print_diagnosis(diag)

    comp = validate_old_vs_new(market_data)
    _print_comparison(comp)

    out = {
        "diagnosis": diag,
        "comparison": comp,
    }
    out_path = Path(__file__).parent / "egx_radar_pro_rebuild_results.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    log.info("Saved rebuild report: %s", out_path)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        log.error("VALIDATION FAILED: %s", exc)
        sys.exit(1)

