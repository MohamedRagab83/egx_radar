from __future__ import annotations

from typing import Any, Mapping, Tuple


def _snapshot_get(snapshot: Any, key: str, default: float = 0.0) -> float:
    if isinstance(snapshot, Mapping):
        value = snapshot.get(key, default)
    else:
        value = getattr(snapshot, key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def passes_alpha_filter(snapshot: Any, alpha_score: float) -> Tuple[bool, str]:
    atr_pct = _snapshot_get(snapshot, "atr_pct", 0.0)
    volume_ratio = _snapshot_get(snapshot, "volume_ratio", _snapshot_get(snapshot, "vol_ratio", 1.0))
    rsi = _snapshot_get(snapshot, "rsi", 50.0)

    if float(alpha_score) < 60.0:
        return False, "alpha_below_threshold"
    if atr_pct > 0.06:
        return False, "atr_too_high"
    if volume_ratio < 1.3:
        return False, "volume_too_low"
    if rsi < 45.0:
        return False, "rsi_too_weak"
    return True, "alpha_pass"


__all__ = ["passes_alpha_filter"]
