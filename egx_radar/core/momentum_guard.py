"""Momentum Guard: persistence, loss cluster, and fatigue detection (Module 2).

Thread-safe — the shared MomentumGuard instance uses internal locks for any
mutable state (loss events, breakout tracking). All per-call logic is stateless.
"""

import datetime
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import List

from egx_radar.config.settings import K

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Result type
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MomentumGuardResult:
    """Immutable per-evaluation result from MomentumGuard."""
    symbol: str
    passed: bool
    momentum_persistent: bool
    defensive_mode: bool
    fatigue_mode: bool
    position_scale: float
    effective_rank_threshold_boost: int
    exemption_threshold: float
    flags: list
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# Guard implementation
# ═══════════════════════════════════════════════════════════════════════════

class MomentumGuard:
    """
    Shared, thread-safe momentum quality gate.

    Rules:
      1. Momentum Persistence — both today & yesterday must clear a floor.
      2. Loss Cluster Guard  — if ≥ N stops within recent sessions → defensive.
      3. Market Fatigue      — if > X% of recent breakouts failed → fatigue.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (timestamp, symbol) for each stop-loss event
        self._loss_events: List[tuple] = []
        # (timestamp, symbol, followed_through: bool) for breakout tracking
        self._breakout_events: List[tuple] = []

    # ── External feeds ──────────────────────────────────────────────────
    def record_loss_event(self, symbol: str) -> None:
        """Called by the outcomes engine when a trade is stopped out."""
        with self._lock:
            self._loss_events.append((time.time(), symbol))

    def record_breakout_result(self, symbol: str, followed_through: bool, trade_date=None) -> None:
        """Called during scan to track whether a breakout held or failed."""
        with self._lock:
            ts = time.time()
            if trade_date is not None:
                import datetime
                if isinstance(trade_date, datetime.date) and not isinstance(trade_date, datetime.datetime):
                    ts = datetime.datetime.combine(trade_date, datetime.datetime.min.time()).timestamp()
            self._breakout_events.append((ts, symbol, followed_through))

    # ── Core evaluation ─────────────────────────────────────────────────
    def evaluate(
        self,
        symbol: str,
        momentum_today: float,
        momentum_yesterday: float,
        adx: float,
        vol_ratio: float,
        df=None,      # optional pd.DataFrame — required for trend confirmation
        price=None,   # optional float — required for trend confirmation
    ) -> MomentumGuardResult:
        """
        Evaluate momentum quality for *symbol*.

        Parameters
        ----------
        symbol : str
            Ticker being processed.
        momentum_today : float
            Adaptive momentum value for today (already ×100).
        momentum_yesterday : float
            Adaptive momentum value for previous bar (already ×100).
        adx : float
            Current ADX value.
        vol_ratio : float
            Today volume / 20d avg volume.

        Returns
        -------
        MomentumGuardResult
            Actionable result with scaling, threshold adjustments, and flags.
        """
        flags: List[str] = []
        position_scale = 1.0
        rank_boost = 0
        passed = True

        # ── Rule 1: Momentum Persistence ─────────────────────────────
        persistence = min(momentum_today, momentum_yesterday)
        # min(a, b) >= X already implies both a >= X and b >= X
        persistent = persistence >= K.MG_PERSISTENCE_MIN_EACH
        if not persistent:
            flags.append("MOM_NOT_PERSISTENT")
            # Soft downgrade — do NOT hard-block
            passed = False

        # ── Rule 4: Trend Confirmation ────────────────────────────────
        if (
            getattr(K, "MG_TREND_CONFIRM_ENABLED", True)
            and df is not None
            and price is not None
            and len(df) >= max(K.MG_TREND_CONFIRM_SPANS)
        ):
            close = df["Close"].dropna()
            fast_span, slow_span = K.MG_TREND_CONFIRM_SPANS
            ema_fast = float(close.ewm(span=fast_span, adjust=False).mean().iloc[-1])
            ema_slow = float(close.ewm(span=slow_span, adjust=False).mean().iloc[-1])
            if not (price > ema_fast and price > ema_slow):
                flags.append(f"TREND_NOT_CONFIRMED(price={price:.2f})")
                passed = False

        # ── Rule 2: Loss Cluster Guard ───────────────────────────────
        defensive_mode = False
        with self._lock:
            # Count recent losses within the last N "sessions"
            # Using a time-based window: ~5 sessions ≈ 5 days ≈ 432,000s
            session_window = K.MG_LOSS_CLUSTER_WINDOW * 86400
            cutoff = time.time() - session_window
            recent_losses = [ev for ev in self._loss_events if ev[0] >= cutoff]
            # Prune old events
            self._loss_events = recent_losses

        if len(recent_losses) >= K.MG_LOSS_CLUSTER_TRIGGER:
            defensive_mode = True
            position_scale = min(position_scale, K.MG_DEFENSIVE_POSITION_SCALE)
            rank_boost = K.MG_DEFENSIVE_RANK_BOOST
            flags.append(f"LOSS_CLUSTER({len(recent_losses)}in{K.MG_LOSS_CLUSTER_WINDOW}d)")

        # ── Exemption threshold (defensive raises the bar) ────────────
        exemption_threshold = (
            K.MG_EXEMPTION_THRESHOLD_GUARD if defensive_mode
            else K.MG_EXEMPTION_THRESHOLD_NORMAL
        )

        # ── Rule 3: Market Fatigue Detection ─────────────────────────
        fatigue_mode = False
        with self._lock:
            fatigue_window = K.MG_FATIGUE_WINDOW * 86400
            fatigue_cutoff = time.time() - fatigue_window
            recent_breakouts = [
                ev for ev in self._breakout_events if ev[0] >= fatigue_cutoff
            ]
            # Prune old events
            self._breakout_events = recent_breakouts

        if len(recent_breakouts) >= 3:  # need minimum sample
            fail_count = sum(1 for ev in recent_breakouts if not ev[2])
            fail_rate = fail_count / len(recent_breakouts)
            if fail_rate > K.MG_FATIGUE_FAIL_RATE:
                fatigue_mode = True
                position_scale = min(position_scale, K.MG_FATIGUE_POSITION_SCALE)
                flags.append(f"FATIGUE({fail_rate:.0%}fail)")

        # ── Build message ────────────────────────────────────────────
        parts = []
        if not persistent:
            parts.append(f"MomPersist fail (min={persistence:.1f})")
        if defensive_mode:
            parts.append("Defensive mode active")
        if fatigue_mode:
            parts.append("Market fatigue detected")
        if any("TREND_NOT_CONFIRMED" in f for f in flags):
            parts.append("Trend not confirmed (price below EMA20 or EMA50)")
        message = " | ".join(parts) if parts else "OK"

        return MomentumGuardResult(
            symbol=symbol,
            passed=passed,
            momentum_persistent=persistent,
            defensive_mode=defensive_mode,
            fatigue_mode=fatigue_mode,
            position_scale=position_scale,
            effective_rank_threshold_boost=rank_boost,
            exemption_threshold=exemption_threshold,
            flags=flags,
            message=message,
        )


__all__ = ["MomentumGuard", "MomentumGuardResult"]
