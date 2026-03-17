"""Data Guard — pre-scoring data quality layer (Module 1).

Validates each symbol's OHLCV DataFrame *before* it enters the indicator /
scoring pipeline.  Catches broken candles, volume anomalies, and
insufficient bar counts, then computes a composite **data confidence**
score (0–100) with three tiers:

    FULL      (≥ 65)  → full signal allowed
    DEGRADED  (40–64) → signal capped at WATCH maximum
    REJECTED  (< 40)  → symbol skipped entirely
"""

import datetime as _dt
import logging
import math
from typing import NamedTuple

import pandas as pd

from egx_radar.config.settings import K

log = logging.getLogger(__name__)


# ── Trading day calculations (Phase 3) ────────────────────────────────────────

def _egx_trading_days_since(last_date: _dt.date) -> int:
    """Count EGX trading days (Sunday–Thursday) elapsed since last_date.

    Uses Python weekday(): Mon=0 Tue=1 Wed=2 Thu=3 Fri=4 Sat=5 Sun=6.
    EGX does not trade on Friday (4) or Saturday (5).

    A one-day-per-week holiday buffer is subtracted to absorb Egyptian
    public holidays without requiring a full holiday calendar lookup.
    This allows up to one public holiday per week before triggering a
    staleness rejection.
    """
    today = _dt.date.today()
    if last_date >= today:
        return 0

    trading_count = 0
    weeks_elapsed = 0
    cursor = last_date + _dt.timedelta(days=1)

    while cursor <= today:
        weekday = cursor.weekday()
        if weekday not in (4, 5):     # skip Friday and Saturday
            trading_count += 1
        if weekday == 6:              # Sunday = start of new EGX week
            weeks_elapsed += 1
        cursor += _dt.timedelta(days=1)

    # Subtract one buffer day per elapsed week to absorb public holidays
    return max(0, trading_count - weeks_elapsed)


# ── Result container ─────────────────────────────────────────────────────────

class DataGuardResult(NamedTuple):
    """Immutable result of a DataGuard evaluation."""
    passed: bool             # False only when tier == "REJECTED"
    confidence: float        # 0–100
    confidence_tier: str     # "FULL" | "DEGRADED" | "REJECTED"
    reason: str              # human-readable summary


# ── Main class ───────────────────────────────────────────────────────────────

class DataGuard:
    """Stateless data-quality gate.  One instance per call is fine."""

    # ── 1. Candle Integrity ──────────────────────────────────────────────

    @staticmethod
    def check_candle_integrity(df: pd.DataFrame) -> tuple:
        """Return (score_0_to_1, bad_bar_pct, details_str).

        Checks per bar:
          • High < Low                         (inverted bar)
          • Open > High or Open < Low          (open outside range)
          • Close > High or Close < Low        (close outside range)
          • body==0 AND range==0 AND volume==0 (null candle)
        """
        n = len(df)
        if n == 0:
            return 0.0, 1.0, "empty DataFrame"

        missing = []
        for col in ["High", "Low", "Open", "Close"]:
            if col not in df.columns:
                missing.append(col)
        
        if missing:
            return 0.0, 1.0, f"missing required columns: {', '.join(missing)}"

        h, l = df["High"], df["Low"]
        o, c = df["Open"], df["Close"]
        v = df["Volume"] if "Volume" in df.columns else pd.Series(0.0, index=df.index)

        # Handle potential duplicates if caller didn't clean
        if isinstance(h, pd.DataFrame): h = h.iloc[:, 0]
        if isinstance(l, pd.DataFrame): l = l.iloc[:, 0]
        if isinstance(o, pd.DataFrame): o = o.iloc[:, 0]
        if isinstance(c, pd.DataFrame): c = c.iloc[:, 0]
        if isinstance(v, pd.DataFrame): v = v.iloc[:, 0]

        inverted    = (h < l).sum()
        open_oob    = ((o > h) | (o < l)).sum()
        close_oob   = ((c > h) | (c < l)).sum()
        null_candle = (((c - o).abs() < 1e-9) & ((h - l).abs() < 1e-9) & (v <= 0)).sum()

        # Each bar can have multiple issues — count unique bad bars
        bad = (
            (h < l)
            | (o > h) | (o < l)
            | (c > h) | (c < l)
            | (((c - o).abs() < 1e-9) & ((h - l).abs() < 1e-9) & (v <= 0))
        ).sum()

        bad_pct = bad / n
        # Score: 1.0 when 0% bad, 0.0 when ≥ limit
        score = max(0.0, 1.0 - bad_pct / K.DG_CANDLE_BAD_PCT_LIMIT)

        details = (
            f"{bad}/{n} bad bars ({bad_pct:.1%}) — "
            f"inverted={inverted}, open_oob={open_oob}, "
            f"close_oob={close_oob}, null={null_candle}"
        )
        return score, bad_pct, details

    # ── 2. Volume Anomaly ────────────────────────────────────────────────

    @staticmethod
    def check_volume_anomaly(df: pd.DataFrame) -> tuple:
        """Return (score_0_to_1, anomaly_pct, details_str).

        Uses a rolling Z-score (same window as ``K.VOL_ROLL_WINDOW``).
        A bar is "anomalous" when  |z| > DG_VOL_ANOMALY_ZSCORE.
        Also flags all-zeros volume.
        """
        vol = df["Volume"] if "Volume" in df.columns else None
        if vol is None or vol.sum() <= 0:
            return 0.0, 1.0, "no volume data (all zeros)"

        n = len(vol)
        window = K.VOL_ROLL_WINDOW

        if n < window + 2:
            return 0.5, 0.0, f"too few bars for Z-score ({n} < {window + 2})"

        mu = vol.rolling(window).mean()
        sigma = vol.rolling(window).std()

        # Avoid division by zero
        valid = sigma > 0
        z = pd.Series(0.0, index=vol.index)
        z[valid] = (vol[valid] - mu[valid]) / sigma[valid]

        anomalous = (z.abs() > K.DG_VOL_ANOMALY_ZSCORE).sum()
        # Only consider the bars where Z was computable
        computable = valid.sum()
        anom_pct = anomalous / computable if computable > 0 else 0.0

        score = max(0.0, 1.0 - anom_pct / K.DG_VOL_ANOMALY_PCT_LIMIT)

        details = f"{anomalous}/{computable} anomalous bars ({anom_pct:.1%})"
        return score, anom_pct, details

    # ── 3. Bar-count Sufficiency ─────────────────────────────────────────

    @staticmethod
    def _bar_sufficiency_score(df: pd.DataFrame) -> float:
        """0–1 score: 1.0 when bar count ≥ DG_IDEAL_BARS, linearly down."""
        n = len(df)
        if n <= 0:
            return 0.0
        return min(1.0, n / K.DG_IDEAL_BARS)

    # ── 4. Consecutive Zero-Volume Days ───────────────────────────────────

    @staticmethod
    def check_consecutive_zero_volume(df: pd.DataFrame, max_allowed: int = None) -> tuple:
        """Return (score_0_to_1, max_consecutive_zeros, details_str).

        Counts the maximum consecutive run of Volume == 0 in the last 20 bars.
        EGX context: 1-2 zero-volume days can happen on thin trading.
        3+ consecutive zero-volume days = data problem, not thin trading.
        """
        if max_allowed is None:
            max_allowed = K.DG_MAX_CONSECUTIVE_ZERO_VOL

        vol = df["Volume"].iloc[-20:] if len(df) >= 20 else df["Volume"]
        if isinstance(vol, pd.DataFrame):
            vol = vol.iloc[:, 0]

        # Count max consecutive zeros
        max_run = 0
        current_run = 0
        for v in vol:
            if pd.isna(v) or v == 0:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0

        if max_run == 0:
            return 1.0, 0, "no zero-volume runs"

        # Score: 1.0 if max_run=0, 0.0 if max_run >= max_allowed
        score = max(0.0, 1.0 - (max_run / max_allowed))
        details = f"max consecutive zero-volume days = {max_run} (limit={max_allowed})"
        return score, max_run, details

    # ── 5. Data Staleness (Last Bar Date vs Today) ───────────────────────

    @staticmethod
    def check_data_staleness(df: pd.DataFrame, max_lag_days: int = None) -> tuple:
        """Return (score_0_to_1, lag_days, details_str).

        Computes the number of TRADING days (Sun–Thu) between the last bar's 
        date and today. Accounts for EGX holidays using a one-day-per-week buffer.

        EGX trades Sun–Thu. A one-week holiday buffer allows for one public
        holiday per week before triggering a staleness penalty.
        Default max_lag_days = 3 covers typical weekend gaps.
        """
        from datetime import datetime, timezone

        if max_lag_days is None:
            max_lag_days = K.DG_MAX_DATA_LAG_DAYS

        try:
            last_date = pd.Timestamp(df.index[-1])
            # Make timezone-naive for comparison
            if last_date.tzinfo is not None:
                last_date = last_date.tz_localize(None)
            # Convert to Python date for trading day calculation
            last_date_py = last_date.date()
        except Exception:
            return 0.5, -1, "could not determine last bar date"

        # Use trading-day aware function
        lag = _egx_trading_days_since(last_date_py)

        if lag < 0:
            # This should not happen with the new function
            return 0.0, lag, f"internal error in trading day calculation"

        if lag <= max_lag_days:
            score = 1.0
            details = f"last bar {lag} trading day(s) ago — OK"
        else:
            # Linear penalty: score=0.5 at 2x lag, score=0.0 at 4x lag
            score = max(0.0, 1.0 - (lag - max_lag_days) / (max_lag_days * 2))
            details = f"last bar {lag} trading day(s) ago — STALE (limit={max_lag_days})"

        return score, lag, details

    # ── 6. Composite Confidence ──────────────────────────────────────────

    def compute_confidence(self, df: pd.DataFrame) -> tuple:
        """Return (confidence_0_100, candle_details, volume_details)."""
        candle_score, _, c_detail = self.check_candle_integrity(df)
        volume_score, _, v_detail = self.check_volume_anomaly(df)
        bar_score = self._bar_sufficiency_score(df)
        zvol_score, zvol_run, zvol_detail = self.check_consecutive_zero_volume(df)

        confidence = (
            K.DG_WEIGHT_CANDLE * candle_score
            + K.DG_WEIGHT_VOLUME * volume_score
            + K.DG_WEIGHT_BARS  * bar_score
            + K.DG_WEIGHT_ZVOL  * zvol_score
        ) * 100.0

        # Clamp to [0, 100]
        confidence = max(0.0, min(100.0, confidence))
        return confidence, c_detail, v_detail

    # ── 7. Top-level Evaluator ───────────────────────────────────────────

    def evaluate(self, df: pd.DataFrame, sym: str) -> DataGuardResult:
        """Run all checks and return a :class:`DataGuardResult`.

        Tier logic:
            confidence ≥ 65  → FULL      (all signals allowed)
            confidence 40–64 → DEGRADED  (cap signal at WATCH)
            confidence < 40  → REJECTED  (skip symbol)
        """
        confidence, c_detail, v_detail = self.compute_confidence(df)

        # Staleness: integrate into confidence score (not just post-hoc override)
        stale_score, lag_days, stale_detail = self.check_data_staleness(df)
        if stale_score < 1.0:
            confidence *= stale_score
        if lag_days > K.DG_MAX_DATA_LAG_DAYS:
            log.warning("DataGuard %s: stale data — %s", sym, stale_detail)
            # Also enforce DEGRADED ceiling for stale data
            if confidence >= K.DG_CONFIDENCE_FULL:
                confidence = K.DG_CONFIDENCE_FULL - 1  # push to DEGRADED

        if confidence >= K.DG_CONFIDENCE_FULL:
            tier = "FULL"
        elif confidence >= K.DG_CONFIDENCE_DEGRADED:
            tier = "DEGRADED"
        else:
            tier = "REJECTED"

        passed = tier != "REJECTED"

        reason_parts = []
        if ("bad bars" in c_detail and not c_detail.startswith("0/")) or "missing" in c_detail:
            reason_parts.append(f"candle: {c_detail}")
        if "anomalous" in v_detail or "no volume" in v_detail:
            reason_parts.append(f"volume: {v_detail}")
        if lag_days > K.DG_MAX_DATA_LAG_DAYS:
            reason_parts.append(f"stale: {stale_detail}")
        reason = "; ".join(reason_parts) if reason_parts else "OK"

        log.debug(
            "DataGuard %s → conf=%.1f tier=%s | %s | %s",
            sym, confidence, tier, c_detail, v_detail,
        )

        return DataGuardResult(
            passed=passed,
            confidence=confidence,
            confidence_tier=tier,
            reason=reason,
        )


__all__ = ["DataGuard", "DataGuardResult"]
