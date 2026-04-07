"""
news/sentiment_engine.py — EGX Radar Pro
==========================================
News scoring, decay, and sentiment aggregation.

Converts a list of raw news dicts (from news_fetcher) into a single
normalised sentiment score that is stored on Snapshot.sentiment_score
for display purposes only.

This module does NOT make execution decisions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List

import pandas as pd

from config.settings import Snapshot
from news.nlp_arabic import analyze_arabic_sentiment, classify_news_type
from utils.helpers import clamp


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
