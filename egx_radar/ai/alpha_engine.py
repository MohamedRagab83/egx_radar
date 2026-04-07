from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, List, Mapping, Optional

from .news_intelligence import evaluate_news_impact, news_decay
from .news_strength import classify_news_type, compute_news_strength
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


def _safe_text(news: Mapping[str, Any]) -> str:
    return f"{news.get('title', '')} {news.get('content', '')}".strip()


def compute_alpha_components(
    news_list: Optional[Iterable[Mapping[str, Any]]],
    snapshot: Any,
    *,
    now: Optional[datetime] = None,
) -> List[dict]:
    now_dt = now or datetime.utcnow()
    components: List[dict] = []
    for news in list(news_list or []):
        sentiment = analyze_arabic_sentiment(_safe_text(news))
        timestamp = _parse_timestamp(news.get("timestamp"), now_dt)
        age_hours = max((now_dt - timestamp).total_seconds() / 3600.0, 0.0)
        strength = compute_news_strength(news)
        decay = news_decay(age_hours)
        reaction = evaluate_news_impact(snapshot, sentiment)
        contribution = sentiment * strength * decay * reaction
        components.append(
            {
                "source": str(news.get("source", "") or "").lower(),
                "news_type": classify_news_type(news),
                "sentiment": round(sentiment, 4),
                "strength": round(strength, 4),
                "decay": round(decay, 4),
                "reaction": round(reaction, 4),
                "contribution": round(contribution, 4),
            }
        )
    return components


def compute_alpha_score(
    news_list: Optional[Iterable[Mapping[str, Any]]],
    snapshot: Any,
    *,
    now: Optional[datetime] = None,
) -> float:
    """Aggregate news alpha into a bounded 0-100 early-opportunity score."""
    components = compute_alpha_components(news_list, snapshot, now=now)
    if not components:
        return 0.0
    raw_score = sum(float(item["contribution"]) for item in components)
    normalized = 50.0 + (raw_score * (50.0 / 3.0))
    return round(max(0.0, min(100.0, normalized)), 2)


__all__ = ["compute_alpha_components", "compute_alpha_score"]
