"""Scoring Service for EGX Radar - Handles symbol analysis and scoring (Layer 3 Architecture).

This service is responsible for:
  - Processing individual symbols through the scoring pipeline
  - Applying guards (DataGuard, MomentumGuard, AlphaMonitor)
  - Computing SmartRank scores and trade plans
  - Applying post-scoring filters and gates

This decouples symbol scoring from the scan orchestration logic.
"""

import logging
import threading
from typing import Dict, List, Optional, Tuple

import pandas as pd

from egx_radar.config.settings import K, get_sector
from egx_radar.core.data_guard import DataGuard
from egx_radar.core.momentum_guard import MomentumGuard
from egx_radar.core.alpha_monitor import AlphaMonitor, AlphaStatus
from egx_radar.core.signals import get_signal_direction
from egx_radar.core.signal_engine import evaluate_symbol_snapshot

log = logging.getLogger(__name__)


class ScoringService:
    """Service for symbol scoring and guard evaluation."""
    
    def __init__(self):
        """Initialize the scoring service with guard instances."""
        self._data_guard = DataGuard()
        self._momentum_guard = MomentumGuard()
        self._alpha_monitor = AlphaMonitor()
        self._alpha_status: AlphaStatus = AlphaStatus()
        
    def update_alpha_status(self) -> AlphaStatus:
        """Update and get current alpha monitor status.
        
        Returns:
            Current AlphaStatus object
        """
        self._alpha_status = self._alpha_monitor.evaluate()
        
        if self._alpha_status.warning_level >= 1:
            log.warning(
                "[AlphaMonitor] Level %d - %s",
                self._alpha_status.warning_level,
                self._alpha_status.message,
            )
        
        if self._alpha_status.pause_new_entries:
            log.warning(
                "[AlphaMonitor] Level 3 - new entries paused this session. %s",
                self._alpha_status.message,
            )
        
        return self._alpha_status
    
    def process_symbol(
        self,
        symbol: str,
        yahoo_symbol: str,
        df: pd.DataFrame,
        market_regime: str,
        alpha_status: Optional[AlphaStatus] = None,
    ) -> Optional[Dict]:
        """Process a single symbol through the scoring pipeline.
        
        Args:
            symbol: EGX symbol (e.g., 'COMI')
            yahoo_symbol: Yahoo Finance symbol (e.g., 'COMI.CA')
            df: OHLCV DataFrame with required columns
            market_regime: Current market regime ('BULL', 'NEUTRAL', 'BEAR')
            alpha_status: Optional pre-computed AlphaStatus (will compute if not provided)
            
        Returns:
            Result dictionary with scores, signals, and trade plan, or None if rejected
        """
        if alpha_status is None:
            alpha_status = self._alpha_status
        
        # Validate DataFrame
        required = {"Close", "High", "Low", "Open"}
        if not required.issubset(set(df.columns)):
            log.debug("ScoringService: %s missing OHLC columns", symbol)
            return None
        
        # Ensure Volume column exists
        if "Volume" not in df.columns:
            df["Volume"] = 0.0
        
        # Safety net: flatten any MultiIndex columns
        for col in ["Close", "High", "Low", "Open", "Volume"]:
            if col in df.columns and isinstance(df[col], pd.DataFrame):
                df[col] = df[col].iloc[:, 0]
        
        # Check minimum bars
        close = df["Close"].dropna()
        if len(close) < K.MIN_BARS:
            log.debug("ScoringService: %s has insufficient bars (%d < %d)", symbol, len(close), K.MIN_BARS)
            return None
        
        # Check price floor
        price = float(close.iloc[-1])
        if price < K.PRICE_FLOOR:
            log.debug("ScoringService: %s price below floor (%.2f < %.2f)", symbol, price, K.PRICE_FLOOR)
            return None
        
        # Check for stale/frozen data
        df_ta = df.tail(250).copy()
        last10 = df_ta["Close"].iloc[-10:]
        if len(last10) >= 10 and last10.nunique() <= 1 and df_ta["Volume"].iloc[-5:].sum() == 0:
            log.warning("ScoringService: Stale/frozen OHLC for %s — skipping", symbol)
            return None
        
        # DataGuard evaluation (Module 1)
        dg_result = self._data_guard.evaluate(df_ta, symbol)
        if not dg_result.passed:
            log.debug(
                "ScoringService: DataGuard REJECTED %s (conf=%.1f): %s",
                symbol, dg_result.confidence, dg_result.reason,
            )
            return None
        
        # Core signal evaluation
        result = evaluate_symbol_snapshot(
            df_ta=df_ta,
            sym=symbol,
            sector=get_sector(symbol),
            regime=market_regime,
        )
        
        if result is None:
            log.debug("ScoringService: %s failed conservative EGX filters", symbol)
            return None
        
        # Calculate momentum series
        mom_series = close.pct_change(5).rolling(3).mean()
        raw_mom_prev = mom_series.iloc[-2] if len(mom_series) >= 2 else float("nan")
        momentum_prev = float(raw_mom_prev) * 100 if pd.notna(raw_mom_prev) else 0.0
        
        # MomentumGuard evaluation (Module 2)
        mg_result = self._momentum_guard.evaluate(
            symbol=symbol,
            momentum_today=result["momentum"],
            momentum_yesterday=momentum_prev,
            adx=result["adx"],
            vol_ratio=result["vol_ratio"],
            df=df_ta,
            price=result["price"],
        )
        
        # Enrich result with guard outputs
        result["dg_confidence"] = dg_result.confidence
        result["dg_tier"] = dg_result.confidence_tier  # "FULL" or "DEGRADED"
        result["mg_passed"] = mg_result.passed
        result["mg_position_scale"] = mg_result.position_scale
        result["mg_rank_boost"] = mg_result.effective_rank_threshold_boost
        result["mg_defensive"] = mg_result.defensive_mode
        result["mg_fatigue"] = mg_result.fatigue_mode
        result["mg_exemption_threshold"] = mg_result.exemption_threshold
        result["mg_flags"] = mg_result.flags
        result["mg_message"] = mg_result.message
        result["alpha_warning_level"] = alpha_status.warning_level
        result["size_multiplier"] = mg_result.position_scale * alpha_status.position_scale
        result["combined_position_scale"] = mg_result.position_scale * alpha_status.position_scale
        result["combined_rank_boost"] = mg_result.effective_rank_threshold_boost + alpha_status.rank_threshold_boost
        result["signal_dir"] = get_signal_direction(result["tag"])
        
        # EMA200 slope for sector analysis
        slope = float(result.get("ema200_slope_pct", 0.0)) / 100.0
        quantum_n = float(result.get("quantum", 0.0))
        
        return {
            "result": result,
            "slope": slope,
            "quantum_n": quantum_n,
            "dg_result": dg_result,
            "mg_result": mg_result,
        }
    
    def apply_post_scoring_filters(
        self,
        result: Dict,
        market_regime: str,
        market_healthy: bool,
        sector_strength: Dict[str, float],
        weak_sectors: List[str],
    ) -> Dict:
        """Apply post-scoring filters and gates to a result.
        
        This includes:
          - SmartRank threshold checks
          - Market regime gates
          - Sector strength filters
          - RSI/ATR filters
          - DataGuard tier adjustments
        
        Args:
            result: Scoring result from process_symbol
            market_regime: Current market regime
            market_healthy: Market breadth health indicator
            sector_strength: Sector strength scores
            weak_sectors: List of weakest sectors
            
        Returns:
            Modified result with applied filters
        """
        r = result["result"]
        
        # Leader flag
        sector_rank_map = {sec: (val * 100.0) for sec, val in sector_strength.items()}
        r["leader"] = r["smart_rank"] >= sector_rank_map.get(r["sector"], 0.0) + 8.0
        
        # SmartRank minimum actionable threshold
        if r["smart_rank"] < K.SMARTRANK_MIN_ACTIONABLE:
            self._set_wait(r, f"rank-below-{K.SMARTRANK_MIN_ACTIONABLE:.0f}")
        
        # Market regime gate
        if market_regime != "BULL":
            from egx_radar.core.signal_engine import apply_regime_gate
            r.update(apply_regime_gate(r, market_regime))
        elif not market_healthy and r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
            self._set_wait(r, "market-breadth-weak")
        
        # Late zone filter
        if r.get("zone") == "🔴 LATE" and r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
            self._set_wait(r, "late-zone")
        
        # RSI filters
        if r.get("rsi", 0.0) > 65.0 and r.get("plan", {}).get("action") == "ACCUMULATE":
            self._downgrade_to_probe(r, "rsi-high")
        if r.get("rsi", 0.0) >= K.RSI_OB_HARD_LIMIT:
            self._set_wait(r, f"rsi-overbought-{r['rsi']:.0f}")
        
        # ATR filters
        atr_pct = (r["atr"] / r["price"] * 100.0) if r.get("atr") and r.get("price") else 0.0
        if atr_pct >= K.ATR_PCT_HARD_LIMIT:
            self._set_wait(r, f"atr-too-high-{atr_pct:.1f}%")
        elif atr_pct >= K.ATR_PCT_SOFT_LIMIT and r.get("plan", {}).get("action") == "ACCUMULATE":
            self._downgrade_to_probe(r, f"atr-elevated-{atr_pct:.1f}%")
        
        # Sector weakness filter
        if r.get("sector") in weak_sectors and r.get("plan", {}).get("action") == "ACCUMULATE":
            self._downgrade_to_probe(r, "weak-sector")
        
        # DataGuard tier adjustment
        if r.get("dg_tier") == "DEGRADED":
            if r.get("plan", {}).get("action") == "ACCUMULATE":
                self._downgrade_to_probe(r, f"dataguard-{r['dg_confidence']:.0f}")
            elif r.get("plan", {}).get("action") == "PROBE":
                self._set_wait(r, f"dataguard-{r['dg_confidence']:.0f}")
            r["confidence"] = round(r.get("confidence", 0.0) * 0.70, 1)
        
        # MomentumGuard filter
        if not r.get("mg_passed", True):
            mg_flags = " ".join(r.get("mg_flags", []))
            if r.get("accumulation_detected"):
                if "LOSS_CLUSTER" in mg_flags or "FATIGUE" in mg_flags:
                    if r.get("smart_rank", 0.0) < K.SMARTRANK_ENTRY_THRESHOLD + r.get("mg_rank_boost", 0.0):
                        self._set_wait(r, "momentum-guard-hard")
        
        return result
    
    def _set_wait(self, r: dict, reason: str) -> None:
        """Set signal to WAIT state."""
        plan = dict(r.get("plan") or {})
        plan["action"] = "WAIT"
        plan["size"] = 0
        plan["force_wait"] = True
        plan["winrate"] = 0.0
        plan["winrate_na"] = True
        r["plan"] = plan
        r["tag"] = "watch"
        r["signal"] = "WAIT"
        r["signal_reason"] = (r.get("signal_reason", "") + f" | {reason}").strip(" |")
    
    def _downgrade_to_probe(self, r: dict, reason: str) -> None:
        """Downgrade ACCUMULATE to PROBE."""
        plan = dict(r.get("plan") or {})
        if plan.get("action") == "ACCUMULATE":
            plan["action"] = "PROBE"
        if plan.get("size", 0) > 0:
            plan["size"] = max(1, int(plan["size"] * 0.75))
        r["plan"] = plan
        if r.get("tag") == "buy":
            r["tag"] = "early"
            r["signal"] = "PROBE"
        r["signal_reason"] = (r.get("signal_reason", "") + f" | {reason}").strip(" |")


# Global singleton instance
_scoring_service: Optional[ScoringService] = None
_init_lock = threading.Lock()


def get_scoring_service() -> ScoringService:
    """Get the global scoring service singleton.
    
    Returns:
        Shared ScoringService instance
    """
    global _scoring_service
    
    if _scoring_service is None:
        with _init_lock:
            if _scoring_service is None:
                _scoring_service = ScoringService()
    
    return _scoring_service
