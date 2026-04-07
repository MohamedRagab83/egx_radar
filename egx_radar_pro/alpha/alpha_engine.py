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

from __future__ import annotations

from datetime import UTC, datetime
from typing import List

import pandas as pd

from config.settings import Snapshot
from news.nlp_arabic import analyze_arabic_sentiment
from news.sentiment_engine import market_reaction_factor, news_decay, news_strength
from utils.helpers import clamp


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
