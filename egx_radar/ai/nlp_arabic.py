from __future__ import annotations

import re
from typing import Dict


_POSITIVE_PHRASES: Dict[str, float] = {
    "نمو قوي": 2.0,
    "زيادة الإيرادات": 2.0,
    "تحسن الهوامش": 1.5,
    "صفقة استحواذ": 2.5,
    "ارتفاع الأرباح": 2.0,
    "تحسن السيولة": 1.0,
}

_NEGATIVE_PHRASES: Dict[str, float] = {
    "تراجع الأرباح": -2.0,
    "ضغوط تمويلية": -2.0,
    "ارتفاع المديونية": -2.0,
    "تراجع الإيرادات": -2.0,
    "انخفاض الهوامش": -1.5,
}

_CRITICAL_PHRASES: Dict[str, float] = {
    "خسائر كبيرة": -3.0,
    "إيقاف التداول": -3.0,
    "تحقيق رسمي": -3.0,
    "تعثر السداد": -3.0,
}

_FINANCIAL_CONTEXT = {
    "أرباح": 1.10,
    "الإيرادات": 1.10,
    "الهوامش": 1.10,
    "مديونية": 1.20,
    "تمويل": 1.10,
    "سيولة": 1.05,
}

_TASHKEEL_RE = re.compile(r"[\u0617-\u061A\u064B-\u0652]")


def _normalize_arabic_text(text: str) -> str:
    cleaned = _TASHKEEL_RE.sub("", str(text or ""))
    cleaned = cleaned.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    cleaned = cleaned.replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def analyze_arabic_sentiment(text: str) -> float:
    """Return bounded sentiment score in [-3, 3] using phrase-first scoring."""
    normalized = _normalize_arabic_text(text)
    if not normalized:
        return 0.0

    score = 0.0

    for phrase, weight in _POSITIVE_PHRASES.items():
        if _normalize_arabic_text(phrase) in normalized:
            score += weight

    for phrase, weight in _NEGATIVE_PHRASES.items():
        if _normalize_arabic_text(phrase) in normalized:
            score += weight

    for phrase, weight in _CRITICAL_PHRASES.items():
        if _normalize_arabic_text(phrase) in normalized:
            score += weight

    context_multiplier = 1.0
    for token, weight in _FINANCIAL_CONTEXT.items():
        if _normalize_arabic_text(token) in normalized:
            context_multiplier = max(context_multiplier, weight)

    score *= context_multiplier
    if score > 3.0:
        return 3.0
    if score < -3.0:
        return -3.0
    return round(score, 3)


__all__ = ["analyze_arabic_sentiment"]
