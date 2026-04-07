from __future__ import annotations

from typing import Dict


_SIZE_MULTIPLIERS = {
    "STRONG": 1.00,
    "MEDIUM": 0.65,
    "WEAK": 0.35,
}


def size_multiplier_for_trade_class(trade_class: str) -> float:
    return float(_SIZE_MULTIPLIERS.get(str(trade_class).upper(), 0.35))


def apply_execution_scaling(plan: Dict[str, object], probability: float, trade_class: str) -> Dict[str, object]:
    scaled = dict(plan)
    multiplier = size_multiplier_for_trade_class(trade_class)
    size = int(scaled.get("size", 0) or 0)
    scaled_size = max(1, int(round(size * multiplier))) if size > 0 else 0

    scaled["probability"] = round(float(probability), 4)
    scaled["trade_class"] = str(trade_class).upper()
    scaled["ai_size_multiplier"] = round(multiplier, 2)
    scaled["ai_scaled_size"] = scaled_size
    scaled["ai_scaled_risk_used"] = round(float(scaled.get("risk_used", 0.0) or 0.0) * multiplier, 4)
    return scaled


__all__ = ["apply_execution_scaling", "size_multiplier_for_trade_class"]