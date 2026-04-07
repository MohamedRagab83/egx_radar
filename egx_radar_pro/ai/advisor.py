"""
ai/advisor.py — EGX Radar Pro
================================
AI advisory layer — DISPLAY ONLY.

Converts raw probability scores into human-readable confidence labels
and structured advisory context dictionaries.

Nothing in this module affects trade execution.
"""

from __future__ import annotations

from config.settings import Snapshot


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
