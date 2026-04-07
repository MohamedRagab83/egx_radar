"""
news/news_intelligence.py — EGX Radar Pro
===========================================
High-level news intelligence aggregator — DISPLAY ONLY.

NewsIntelligence wraps fetch_news + sentiment scoring into a single
reporting interface used by the dashboard / logging layer.

Output is never used in execution decisions.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from config.settings import Snapshot
from news.news_fetcher import fetch_news
from news.nlp_arabic import analyze_arabic_sentiment
from news.sentiment_engine import market_reaction_factor, news_strength, sentiment_score
from utils.logger import get_logger

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
