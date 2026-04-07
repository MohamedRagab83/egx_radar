from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping, Optional

from .news_intelligence import evaluate_news_impact, news_decay
from .nlp_arabic import analyze_arabic_sentiment


def _parse_timestamp(value: Any, now: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return now
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return now


def _safe_news_text(news: Mapping[str, Any]) -> str:
    return f"{news.get('title', '')} {news.get('content', '')}".strip()


def compute_sentiment(news_list: Optional[Iterable[Mapping[str, Any]]], snapshot: Any, *, now: Optional[datetime] = None) -> float:
    """Compute normalized news sentiment score in [0, 1], neutral defaults to 0.5."""
    now_dt = now or datetime.utcnow()
    items = list(news_list or [])
    if not items:
        return 0.5

    total_score = 0.0
    for news in items:
        raw_text = _safe_news_text(news)
        sentiment = analyze_arabic_sentiment(raw_text)
        timestamp = _parse_timestamp(news.get("timestamp"), now_dt)
        age_hours = max((now_dt - timestamp).total_seconds() / 3600.0, 0.0)
        decay = news_decay(age_hours)
        reaction = evaluate_news_impact(snapshot, sentiment)
        total_score += sentiment * decay * reaction

    normalized = (total_score + 5.0) / 10.0
    if normalized < 0.0:
        return 0.0
    if normalized > 1.0:
        return 1.0
    return round(normalized, 4)


__all__ = ["compute_sentiment"]
