from __future__ import annotations

from typing import Any, Mapping


def _snapshot_get(snapshot: Any, key: str, default: float = 0.0) -> float:
    if isinstance(snapshot, Mapping):
        value = snapshot.get(key, default)
    else:
        value = getattr(snapshot, key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def evaluate_news_impact(snapshot: Any, sentiment: float) -> float:
    """Compute whether market conditions confirm or fade the news signal."""
    impact = 1.0

    rsi = _snapshot_get(snapshot, "rsi", 50.0)
    volume_ratio = _snapshot_get(snapshot, "volume_ratio", _snapshot_get(snapshot, "vol_ratio", 1.0))

    if sentiment > 0 and rsi < 50.0:
        impact *= 0.6
    if sentiment < 0 and rsi > 60.0:
        impact *= 0.6
    if volume_ratio > 1.5:
        impact *= 1.1

    if impact < 0.4:
        return 0.4
    if impact > 1.2:
        return 1.2
    return round(impact, 4)


def news_decay(hours: float) -> float:
    h = float(max(hours, 0.0))
    if h < 6:
        return 1.0
    if h < 24:
        return 0.7
    if h < 48:
        return 0.5
    return 0.3


__all__ = ["evaluate_news_impact", "news_decay"]
