from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .execution_layer import size_multiplier_for_trade_class
from .probability_engine import compute_probability


@dataclass(frozen=True)
class TradeDecision:
    probability: float
    trade_class: str
    size_multiplier: float
    rationale: str


def classify_trade(probability: float) -> str:
    prob = float(probability)
    if prob >= 0.68:
        return "STRONG"
    if prob >= 0.55:
        return "MEDIUM"
    return "WEAK"


def build_trade_decision(snapshot: Any, probability: Optional[float] = None) -> TradeDecision:
    prob = float(probability) if probability is not None else compute_probability(snapshot)
    trade_class = classify_trade(prob)
    multiplier = size_multiplier_for_trade_class(trade_class)
    rationale = f"prob={prob:.2f} class={trade_class} scale={multiplier:.2f}"
    return TradeDecision(
        probability=round(prob, 4),
        trade_class=trade_class,
        size_multiplier=multiplier,
        rationale=rationale,
    )


__all__ = ["TradeDecision", "build_trade_decision", "classify_trade"]