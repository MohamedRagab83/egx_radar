"""Alpha Monitor: session-level edge quality tracker (Module 3).

Reads resolved trade history and computes rolling performance metrics
to detect strategy degradation. Stateless per call — no locks needed.
"""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from egx_radar.config.settings import K
from egx_radar.core.indicators import sharpe_from_trades
from egx_radar.outcomes.engine import oe_load_history

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Result type
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AlphaStatus:
    """Session-level edge quality assessment."""
    warning_level: int                # 0–3
    position_scale: float             # 1.0 | 0.75 | 0.50 | 0.0
    rank_threshold_boost: int         # 0 | 5 | 10
    pause_new_entries: bool
    metrics_20: dict                  # computed metrics for last 20 trades
    metrics_50: dict                  # computed metrics for last 50 trades
    stability_score: float            # 0–1
    setup_breakdown: dict             # {setup_type: {win_rate, n, expectancy}}
    message: str
    flags: list


# ═══════════════════════════════════════════════════════════════════════════
# Monitor implementation
# ═══════════════════════════════════════════════════════════════════════════

class AlphaMonitor:
    """
    Stateless session-level edge quality tracker.

    Reads from resolved trade history (K.OUTCOME_HISTORY_FILE) via
    oe_load_history(), computes rolling performance metrics, and returns
    an AlphaStatus with warning levels, scaling factors, and diagnostics.
    """

    def load_history(self) -> List[dict]:
        """
        Load resolved trades from history, filtering out invalid entries.

        Returns
        -------
        list[dict]
            Valid resolved trades with finite pnl_pct.
        """
        try:
            raw = oe_load_history()
        except FileNotFoundError:
            log.info("[AlphaMonitor] History file not found (first session?) — returning empty.")
            return []
        except Exception as exc:
            log.warning("[AlphaMonitor] Unexpected error loading history: %s", exc)
            return []

        valid = [
            t for t in raw
            if t.get("pnl_pct") is not None
            and isinstance(t.get("pnl_pct"), (int, float))
            and math.isfinite(t["pnl_pct"])
        ]
        log.info("[AlphaMonitor] Loaded %d valid trades from %d total", len(valid), len(raw))
        return valid

    def evaluate(self) -> AlphaStatus:
        """
        Compute rolling metrics and return session-level warning status.

        Returns
        -------
        AlphaStatus
            Warning level (0–3), scaling, and diagnostics.
        """
        trades = self.load_history()

        # ── Insufficient data guard ──────────────────────────────────
        if len(trades) < K.AM_MIN_TRADES:
            flag = "NO_HISTORY_FILE" if len(trades) == 0 else "INSUFFICIENT_TRADES"
            return AlphaStatus(
                warning_level=0,
                position_scale=1.0,
                rank_threshold_boost=0,
                pause_new_entries=False,
                metrics_20={},
                metrics_50={},
                stability_score=1.0,
                setup_breakdown={},
                message=f"Only {len(trades)} resolved trades — need {K.AM_MIN_TRADES}",
                flags=[flag],
            )

        # ── Compute windowed metrics ─────────────────────────────────
        last_20 = trades[-20:] if len(trades) >= 20 else trades
        last_50 = trades[-50:] if len(trades) >= 50 else trades

        m20 = self._compute_metrics(last_20)
        m50 = self._compute_metrics(last_50)

        # ── Warning levels (based on 20-window) ─────────────────────
        flags: List[str] = []
        warning_level = 0
        position_scale = 1.0
        rank_boost = 0
        pause = False

        sharpe_20 = m20["sharpe"]
        wr_20 = m20["win_rate"]
        exp_20 = m20["expectancy"]

        # Level 3 (most severe — checked first to allow override)
        if sharpe_20 <= K.AM_LEVEL3_SHARPE or exp_20 < K.AM_LEVEL3_EXPECTANCY:
            warning_level = 3
            position_scale = 0.0
            rank_boost = 10
            pause = True
            if sharpe_20 <= K.AM_LEVEL3_SHARPE:
                flags.append(f"SHARPE_CRITICAL({sharpe_20:.2f})")
            if exp_20 < K.AM_LEVEL3_EXPECTANCY:
                flags.append(f"EXPECTANCY_CRITICAL({exp_20:.4f})")

        # Level 2
        elif sharpe_20 < K.AM_LEVEL2_SHARPE or wr_20 < K.AM_LEVEL2_WINRATE:
            warning_level = 2
            position_scale = 0.50
            rank_boost = 5
            if sharpe_20 < K.AM_LEVEL2_SHARPE:
                flags.append(f"SHARPE_LOW({sharpe_20:.2f})")
            if wr_20 < K.AM_LEVEL2_WINRATE:
                flags.append(f"WINRATE_CRITICAL({wr_20:.2f})")

        # Level 1
        elif (sharpe_20 < K.AM_LEVEL1_SHARPE or
              exp_20 < K.AM_LEVEL1_EXPECTANCY or
              wr_20 < K.AM_LEVEL1_WINRATE):
            warning_level = 1
            position_scale = 0.75
            if sharpe_20 < K.AM_LEVEL1_SHARPE:
                flags.append(f"SHARPE_WEAK({sharpe_20:.2f})")
            if exp_20 < K.AM_LEVEL1_EXPECTANCY:
                flags.append(f"EXPECTANCY_NEGATIVE({exp_20:.4f})")
            if wr_20 < K.AM_LEVEL1_WINRATE:
                flags.append(f"WINRATE_LOW({wr_20:.2f})")

        # ── Stability score ──────────────────────────────────────────
        sharpe_50 = m50["sharpe"]
        wr_50 = m50["win_rate"]
        sharpe_drift = abs(sharpe_20 - sharpe_50)
        wr_drift = abs(wr_20 - wr_50)
        stability = max(0.0, 1.0 - (sharpe_drift * 0.2) - (wr_drift * 1.0))

        if stability < 0.5:
            flags.append(f"UNSTABLE({stability:.2f})")

        # ── Setup breakdown ──────────────────────────────────────────
        setup_breakdown = self._compute_setup_breakdown(trades)

        # ── Build message ────────────────────────────────────────────
        parts = [f"Level {warning_level}"]
        if warning_level >= 2:
            parts.append(f"WR={wr_20:.0%} Sharpe={sharpe_20:.2f} Exp={exp_20:.4f}")
        if pause:
            parts.append("NEW ENTRIES PAUSED")
        if stability < 0.5:
            parts.append(f"stability={stability:.2f}")
        message = " | ".join(parts)

        return AlphaStatus(
            warning_level=warning_level,
            position_scale=position_scale,
            rank_threshold_boost=rank_boost,
            pause_new_entries=pause,
            metrics_20=m20,
            metrics_50=m50,
            stability_score=round(stability, 3),
            setup_breakdown=setup_breakdown,
            message=message,
            flags=flags,
        )

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _compute_metrics(trades: List[dict]) -> Dict[str, Any]:
        """Compute performance metrics for a list of resolved trades."""
        if not trades:
            return {
                "n": 0, "win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "loss_rate": 1.0, "expectancy": 0.0, "sharpe": 0.0,
                "mean_return": 0.0, "std_return": 0.0,
            }

        n = len(trades)
        returns = [t["pnl_pct"] for t in trades]

        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]

        win_rate = len(wins) / n
        loss_rate = 1.0 - win_rate
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

        mean_return = sum(returns) / n
        if n >= 2:
            variance = sum((r - mean_return) ** 2 for r in returns) / (n - 1)
            std_return = math.sqrt(variance) if variance > 0 else 1e-9
        else:
            std_return = 1e-9

        # Trade-based Sharpe (no annualisation)
        sharpe = sharpe_from_trades(returns)

        return {
            "n": n,
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "loss_rate": round(loss_rate, 4),
            "expectancy": round(expectancy, 4),
            "sharpe": round(sharpe, 4),
            "mean_return": round(mean_return, 4),
            "std_return": round(std_return, 4),
        }

    @staticmethod
    def _compute_setup_breakdown(trades: List[dict]) -> Dict[str, dict]:
        """Group trades by setup_type and compute per-group metrics."""
        groups: Dict[str, List[float]] = defaultdict(list)
        for t in trades:
            setup = t.get("setup_type") or t.get("action", "UNKNOWN")
            pnl = t.get("pnl_pct", 0.0)
            groups[setup].append(pnl)

        breakdown = {}
        for setup, pnls in groups.items():
            n = len(pnls)
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            wr = len(wins) / n if n > 0 else 0.0
            avg_w = (sum(wins) / len(wins)) if wins else 0.0
            avg_l = abs(sum(losses) / len(losses)) if losses else 0.0
            exp = (wr * avg_w) - ((1 - wr) * avg_l)
            breakdown[setup] = {
                "win_rate": round(wr, 4),
                "n": n,
                "expectancy": round(exp, 4),
            }

        return breakdown

    def evaluate_from_trades(self, trades: List[dict]) -> AlphaStatus:
        """Evaluate alpha from a provided trades list instead of reading from file."""
        if not trades:
            return AlphaStatus(
                warning_level=0,
                position_scale=1.0,
                rank_threshold_boost=0,
                pause_new_entries=False,
                metrics_20={},
                metrics_50={},
                stability_score=1.0,
                setup_breakdown={},
                message="No trades provided",
                flags=["NO_TRADES"],
            )
            
        # Filter valid trades (similar to load_history)
        valid = [
            t for t in trades
            if t.get("pnl_pct") is not None
            and isinstance(t.get("pnl_pct"), (int, float))
            and math.isfinite(t["pnl_pct"])
        ]
        
        # Now replicate the logic from evaluate()
        if len(valid) < K.AM_MIN_TRADES:
            return AlphaStatus(
                warning_level=0,
                position_scale=1.0,
                rank_threshold_boost=0,
                pause_new_entries=False,
                metrics_20={},
                metrics_50={},
                stability_score=1.0,
                setup_breakdown={},
                message=f"Only {len(valid)} valid trades — need {K.AM_MIN_TRADES}",
                flags=["INSUFFICIENT_TRADES"],
            )

        last_20 = valid[-20:] if len(valid) >= 20 else valid
        last_50 = valid[-50:] if len(valid) >= 50 else valid

        m20 = self._compute_metrics(last_20)
        m50 = self._compute_metrics(last_50)

        flags: List[str] = []
        warning_level = 0
        position_scale = 1.0
        rank_boost = 0
        pause = False

        sharpe_20 = m20["sharpe"]
        wr_20 = m20["win_rate"]
        exp_20 = m20["expectancy"]

        if sharpe_20 <= K.AM_LEVEL3_SHARPE or exp_20 < K.AM_LEVEL3_EXPECTANCY:
            warning_level = 3
            position_scale = 0.0
            rank_boost = 10
            pause = True
            if sharpe_20 <= K.AM_LEVEL3_SHARPE:
                flags.append(f"SHARPE_CRITICAL({sharpe_20:.2f})")
            if exp_20 < K.AM_LEVEL3_EXPECTANCY:
                flags.append(f"EXPECTANCY_CRITICAL({exp_20:.4f})")
        elif sharpe_20 < K.AM_LEVEL2_SHARPE or wr_20 < K.AM_LEVEL2_WINRATE:
            warning_level = 2
            position_scale = 0.50
            rank_boost = 5
            if sharpe_20 < K.AM_LEVEL2_SHARPE:
                flags.append(f"SHARPE_LOW({sharpe_20:.2f})")
            if wr_20 < K.AM_LEVEL2_WINRATE:
                flags.append(f"WINRATE_CRITICAL({wr_20:.2f})")
        elif (sharpe_20 < K.AM_LEVEL1_SHARPE or
              exp_20 < K.AM_LEVEL1_EXPECTANCY or
              wr_20 < K.AM_LEVEL1_WINRATE):
            warning_level = 1
            position_scale = 0.75
            if sharpe_20 < K.AM_LEVEL1_SHARPE:
                flags.append(f"SHARPE_WEAK({sharpe_20:.2f})")
            if exp_20 < K.AM_LEVEL1_EXPECTANCY:
                flags.append(f"EXPECTANCY_NEGATIVE({exp_20:.4f})")
            if wr_20 < K.AM_LEVEL1_WINRATE:
                flags.append(f"WINRATE_LOW({wr_20:.2f})")

        sharpe_50 = m50["sharpe"]
        wr_50 = m50["win_rate"]
        sharpe_drift = abs(sharpe_20 - sharpe_50)
        wr_drift = abs(wr_20 - wr_50)
        stability = max(0.0, 1.0 - (sharpe_drift * 0.2) - (wr_drift * 1.0))

        if stability < 0.5:
            flags.append(f"UNSTABLE({stability:.2f})")

        setup_breakdown = self._compute_setup_breakdown(valid)

        parts = [f"Level {warning_level}"]
        if warning_level >= 2:
            parts.append(f"WR={wr_20:.0%} Sharpe={sharpe_20:.2f} Exp={exp_20:.4f}")
        if pause:
            parts.append("NEW ENTRIES PAUSED")
        if stability < 0.5:
            parts.append(f"stability={stability:.2f}")
        message = " | ".join(parts)

        return AlphaStatus(
            warning_level=warning_level,
            position_scale=position_scale,
            rank_threshold_boost=rank_boost,
            pause_new_entries=pause,
            metrics_20=m20,
            metrics_50=m50,
            stability_score=round(stability, 3),
            setup_breakdown=setup_breakdown,
            message=message,
            flags=flags,
        )


__all__ = ["AlphaMonitor", "AlphaStatus"]
