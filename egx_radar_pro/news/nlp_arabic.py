"""
news/nlp_arabic.py — EGX Radar Pro
======================================
Arabic-language NLP for financial news classification and sentiment scoring.

Contains the phrase dictionaries and scoring functions for Egyptian market
news — the primary language of EGX corporate announcements.

All functions are stateless and have no internal project dependencies
(safe to import from any module without circular risk).
"""

from __future__ import annotations

from typing import Dict

from utils.helpers import clamp


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
