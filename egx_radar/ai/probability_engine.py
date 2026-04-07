from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping


def _clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))


def _snapshot_get(snapshot: Any, key: str, default: Any = 0.0) -> Any:
    if isinstance(snapshot, Mapping):
        return snapshot.get(key, default)
    return getattr(snapshot, key, default)


def _snapshot_float(snapshot: Any, key: str, default: float = 0.0) -> float:
    value = _snapshot_get(snapshot, key, default)
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _snapshot_bool(snapshot: Any, key: str, default: bool = False) -> bool:
    return bool(_snapshot_get(snapshot, key, default))


def _resolve_sentiment_score(snapshot: Any, sentiment_score: float | None) -> float:
    if sentiment_score is not None:
        try:
            return _clamp(float(sentiment_score), 0.0, 1.0)
        except (TypeError, ValueError):
            return 0.5
    try:
        return _clamp(float(_snapshot_get(snapshot, "sentiment_score", 0.5)), 0.0, 1.0)
    except (TypeError, ValueError):
        return 0.5


@dataclass(frozen=True)
class ProbabilityFeatures:
    smart_rank: float
    structure_score: float
    anticipation_pct: float
    volume_ratio: float
    atr_pct: float
    adx: float
    rsi: float
    spread_pct: float
    fake_move: bool
    erratic_volume: bool
    entry_ready: bool
    volume_confirmed: bool


def extract_probability_features(snapshot: Any) -> ProbabilityFeatures:
    anticipation = _snapshot_float(snapshot, "anticipation", 0.0)
    if anticipation <= 1.0:
        anticipation *= 100.0

    volume_ratio = _snapshot_float(
        snapshot,
        "volume_ratio",
        _snapshot_float(snapshot, "vol_ratio", 1.0),
    )

    return ProbabilityFeatures(
        smart_rank=_clamp(_snapshot_float(snapshot, "smart_rank", 0.0), 0.0, 100.0),
        structure_score=_clamp(_snapshot_float(snapshot, "structure_score", 50.0), 0.0, 100.0),
        anticipation_pct=_clamp(anticipation, 0.0, 100.0),
        volume_ratio=_clamp(volume_ratio, 0.0, 4.0),
        atr_pct=_clamp(_snapshot_float(snapshot, "atr_pct", 0.0), 0.0, 1.0),
        adx=_clamp(_snapshot_float(snapshot, "adx", 0.0), 0.0, 60.0),
        rsi=_clamp(_snapshot_float(snapshot, "rsi", 50.0), 0.0, 100.0),
        spread_pct=_clamp(_snapshot_float(snapshot, "spread_pct", 0.0), 0.0, 10.0),
        fake_move=_snapshot_bool(snapshot, "fake_move", False),
        erratic_volume=_snapshot_bool(snapshot, "erratic_volume", False),
        entry_ready=_snapshot_bool(snapshot, "entry_ready", False),
        volume_confirmed=_snapshot_bool(snapshot, "volume_confirmed", False),
    )


def compute_probability(snapshot: Any, *, bias: float = 0.0, sentiment_score: float | None = None) -> float:
    features = extract_probability_features(snapshot)

    smart_rank_score = features.smart_rank / 100.0
    structure_score = features.structure_score / 100.0
    anticipation_score = features.anticipation_pct / 100.0
    adx_score = features.adx / 60.0
    volume_score = _clamp(features.volume_ratio / 2.0, 0.0, 1.0)
    rsi_balance = 1.0 - min(abs(features.rsi - 55.0), 35.0) / 35.0
    atr_penalty = _clamp(features.atr_pct / 0.12, 0.0, 1.0)
    spread_penalty = _clamp(features.spread_pct / 3.0, 0.0, 1.0)

    raw_score = (
        smart_rank_score * 0.34
        + structure_score * 0.20
        + anticipation_score * 0.16
        + volume_score * 0.08
        + adx_score * 0.08
        + rsi_balance * 0.06
        + (0.04 if features.entry_ready else 0.0)
        + (0.04 if features.volume_confirmed else 0.0)
        - atr_penalty * 0.08
        - spread_penalty * 0.05
        - (0.18 if features.fake_move else 0.0)
        - (0.12 if features.erratic_volume else 0.0)
    )

    centered = ((raw_score - 0.50) * 6.0) + float(bias)
    probability = 1.0 / (1.0 + math.exp(-centered))
    sentiment = _resolve_sentiment_score(snapshot, sentiment_score)
    probability *= 0.95 + (0.1 * sentiment)
    return round(_clamp(probability, 0.05, 0.95), 4)


__all__ = ["ProbabilityFeatures", "compute_probability", "extract_probability_features"]