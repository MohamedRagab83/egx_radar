from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _default_state() -> Dict[str, Any]:
    return {
        "summary": {
            "total_records": 0,
            "wins": 0,
            "avg_pnl_pct": 0.0,
        },
        "by_trade_class": {
            "STRONG": {"count": 0, "wins": 0, "avg_pnl_pct": 0.0},
            "MEDIUM": {"count": 0, "wins": 0, "avg_pnl_pct": 0.0},
            "WEAK": {"count": 0, "wins": 0, "avg_pnl_pct": 0.0},
        },
        "recent_outcomes": [],
    }


class LearningEngine:
    def __init__(self, storage_path: Optional[str] = None, max_records: int = 250) -> None:
        self.storage_path = Path(storage_path or "ai_learning_state.json")
        self.max_records = max_records

    def load_state(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return _default_state()
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _default_state()

    def save_state(self, state: Dict[str, Any]) -> None:
        self.storage_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def record_outcome(
        self,
        *,
        symbol: str,
        probability: float,
        trade_class: str,
        pnl_pct: float,
        outcome: str,
        smart_rank: float,
        signal_date: str,
    ) -> Dict[str, Any]:
        state = self.load_state()
        trade_class = str(trade_class).upper()
        entry = {
            "symbol": symbol,
            "probability": round(float(probability), 4),
            "trade_class": trade_class,
            "pnl_pct": round(float(pnl_pct), 2),
            "outcome": outcome,
            "smart_rank": round(float(smart_rank), 2),
            "signal_date": signal_date,
        }

        recent = state.setdefault("recent_outcomes", [])
        recent.append(entry)
        if len(recent) > self.max_records:
            del recent[:-self.max_records]

        by_trade_class = state.setdefault("by_trade_class", _default_state()["by_trade_class"])
        bucket = by_trade_class.setdefault(trade_class, {"count": 0, "wins": 0, "avg_pnl_pct": 0.0})
        bucket["count"] += 1
        if float(pnl_pct) > 0:
            bucket["wins"] += 1
        prev_count = max(bucket["count"] - 1, 0)
        bucket["avg_pnl_pct"] = round(
            ((bucket["avg_pnl_pct"] * prev_count) + float(pnl_pct)) / max(bucket["count"], 1),
            2,
        )

        summary = state.setdefault("summary", _default_state()["summary"])
        summary["total_records"] += 1
        if float(pnl_pct) > 0:
            summary["wins"] += 1
        prev_total = max(summary["total_records"] - 1, 0)
        summary["avg_pnl_pct"] = round(
            ((summary["avg_pnl_pct"] * prev_total) + float(pnl_pct)) / max(summary["total_records"], 1),
            2,
        )

        self.save_state(state)
        return state

    def calibration_bias(self, trade_class: Optional[str] = None) -> float:
        state = self.load_state()
        if trade_class:
            bucket = state.get("by_trade_class", {}).get(str(trade_class).upper(), {})
            count = int(bucket.get("count", 0))
            wins = int(bucket.get("wins", 0))
        else:
            summary = state.get("summary", {})
            count = int(summary.get("total_records", 0))
            wins = int(summary.get("wins", 0))

        if count < 10:
            return 0.0

        empirical = (wins + 1.0) / (count + 2.0)
        bias = (empirical - 0.5) * 0.5
        return max(-0.15, min(0.15, round(bias, 4)))


__all__ = ["LearningEngine"]