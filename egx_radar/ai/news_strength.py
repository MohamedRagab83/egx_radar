from __future__ import annotations

from typing import Any, Mapping, Tuple


_SOURCE_CREDIBILITY = {
    "egx_official": 1.00,
    "company_announcements": 0.95,
    "mubasher": 0.82,
    "investing_egypt": 0.72,
}

_NEWS_TYPE_WEIGHTS = {
    "earnings": 1.00,
    "dividend": 0.82,
    "acquisition": 0.94,
    "expansion": 0.88,
    "general": 0.60,
}

_TYPE_KEYWORDS = {
    "earnings": (
        "earnings",
        "profit",
        "results",
        "quarter",
        "annual",
        "ارباح",
        "الارباح",
        "نتائج",
        "القوائم الماليه",
    ),
    "dividend": (
        "dividend",
        "cash distribution",
        "coupon",
        "توزيع",
        "توزيعات",
        "كوبون",
        "ارباح نقديه",
    ),
    "acquisition": (
        "acquisition",
        "merger",
        "stake purchase",
        "استحواذ",
        "اندماج",
        "حصه",
        "صفقه",
    ),
    "expansion": (
        "expansion",
        "new plant",
        "capacity",
        "contract win",
        "توسع",
        "طاقه انتاجيه",
        "مصنع جديد",
        "عقد",
        "مشروع",
    ),
}


def _combined_text(news: Mapping[str, Any]) -> str:
    title = str(news.get("title", "") or "")
    content = str(news.get("content", "") or "")
    return f"{title} {content}".lower()


def classify_news_type(news: Mapping[str, Any]) -> str:
    text = _combined_text(news)
    for news_type, keywords in _TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return news_type
    return "general"


def compute_news_strength(news: Mapping[str, Any]) -> float:
    """Score one item by source credibility and event importance in [0, 1]."""
    source = str(news.get("source", "") or "").lower()
    news_type = classify_news_type(news)
    credibility = float(_SOURCE_CREDIBILITY.get(source, 0.55))
    importance = float(_NEWS_TYPE_WEIGHTS.get(news_type, 0.60))
    strength = (credibility * 0.55) + (importance * 0.45)
    return round(max(0.0, min(1.0, strength)), 4)


def describe_news_strength(news: Mapping[str, Any]) -> Tuple[str, float]:
    news_type = classify_news_type(news)
    return news_type, compute_news_strength(news)


__all__ = ["classify_news_type", "compute_news_strength", "describe_news_strength"]
