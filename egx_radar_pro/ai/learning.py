"""
ai/learning.py — EGX Radar Pro
==================================
Adaptive learning state — tracks win/loss history and derives a mild
probability bias used ONLY for the AI display layer.

This module has NO effect on execution decisions.  The learning bias is
fed exclusively into probability_engine() which is a display-only metric.

Persistence: JSON file on disk (default: learning_state.json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class LearningState:
    """Rolling trade statistics persisted between runs."""
    wins:    int   = 0
    losses:  int   = 0
    avg_pnl: float = 0.0


class LearningModule:
    """
    Record closed trade outcomes and expose an adaptive probability bias.

    Usage
    -----
        learning = LearningModule()
        ...
        learning.record(trade.pnl_pct)   # after each trade closes
        bias = learning.bias             # pass to probability_engine()

    The bias is bounded to [-0.10, +0.10] and only activates after 10 trades.
    """

    def __init__(self, path: str = "learning_state.json") -> None:
        self.path  = Path(path)
        self.state = LearningState()
        self._load()

    # ── Persistence ────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.state = LearningState(
                wins    = int(raw.get("wins", 0)),
                losses  = int(raw.get("losses", 0)),
                avg_pnl = float(raw.get("avg_pnl", 0.0)),
            )
            log.debug(
                "Learning state loaded — wins=%d losses=%d avg_pnl=%.4f",
                self.state.wins, self.state.losses, self.state.avg_pnl,
            )
        except Exception as exc:
            log.warning("Could not load learning state (%s) — starting fresh.", exc)
            self.state = LearningState()

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "wins":    self.state.wins,
                    "losses":  self.state.losses,
                    "avg_pnl": round(self.state.avg_pnl, 4),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── Public interface ────────────────────────────────────────────────

    def record(self, pnl_pct: float) -> None:
        """Record the PnL of a closed trade and persist updated state."""
        if pnl_pct >= 0:
            self.state.wins += 1
        else:
            self.state.losses += 1
        n = self.state.wins + self.state.losses
        self.state.avg_pnl = ((self.state.avg_pnl * (n - 1)) + pnl_pct) / max(n, 1)
        self._save()

    @property
    def bias(self) -> float:
        """
        Adaptive learning bias in (-0.10, +0.10).

        Positive when win rate is above 50%, negative below.
        Returns 0.0 until at least 10 trades have been recorded.
        Consumed only by probability_engine() — never by execution logic.
        """
        n = self.total_trades
        if n < 10:
            return 0.0
        win_rate = self.state.wins / n
        return (win_rate - 0.5) * 0.2

    @property
    def total_trades(self) -> int:
        return self.state.wins + self.state.losses

    @property
    def win_rate(self) -> float:
        n = self.total_trades
        return self.state.wins / n if n > 0 else 0.0

    def summary(self) -> dict:
        return {
            "wins":        self.state.wins,
            "losses":      self.state.losses,
            "total":       self.total_trades,
            "win_rate":    round(self.win_rate, 4),
            "avg_pnl":     round(self.state.avg_pnl, 4),
            "bias":        round(self.bias, 5),
        }
