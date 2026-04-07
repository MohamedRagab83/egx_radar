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

from __future__ import annotations

from typing import List

import pandas as pd

from utils.logger import get_logger

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
