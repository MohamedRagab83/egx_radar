"""Orchestration Service for EGX Radar - Coordinates scan services (Layer 3 Architecture).

This service is responsible for:
  - Coordinating DataService and ScoringService
  - Managing parallel symbol processing
  - Aggregating results and computing sector metrics
  - Applying portfolio-level filters
  - Emitting results to UI and downstream systems

This provides a clean separation between orchestration logic and
the individual data/scoring services.
"""

import json
import logging
import math
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from egx_radar.config.settings import K, SECTORS, SYMBOLS, get_sector
from egx_radar.scan.data_service import DataService, get_data_service
from egx_radar.scan.scoring_service import ScoringService, get_scoring_service
from egx_radar.core.signal_engine import detect_conservative_market_regime
from egx_radar.outcomes.engine import (
    oe_process_open_trades,
    oe_save_rejections,
    oe_save_daily_scan,
)

log = logging.getLogger(__name__)


class OrchestrationService:
    """Service for orchestrating the scan pipeline."""
    
    def __init__(self):
        """Initialize the orchestration service."""
        self._data_service = get_data_service()
        self._scoring_service = get_scoring_service()
        self._results: List[dict] = []
        self._rejections: List[dict] = []
        self._lock = threading.Lock()
        
    def run_scan(
        self,
        force_refresh: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[List[dict], List[dict]]:
        """Execute a complete scan of all symbols.
        
        Args:
            force_refresh: If True, bypass cache and re-fetch all data
            progress_callback: Optional callback for progress updates (0-100)
            
        Returns:
            Tuple of (results, rejections) lists
        """
        scan_start = time.time()
        log.info("OrchestrationService: Starting scan (force_refresh=%s)", force_refresh)
        
        # Phase 1: Fetch data
        if progress_callback:
            progress_callback(5, "Loading data from multiple sources...")
        
        all_data = self._data_service.fetch_all_data(force_refresh=force_refresh)
        
        if not all_data and not self._data_service._cache:
            log.error("OrchestrationService: No data fetched from any source")
            return [], []
        
        # Phase 2: Calculate market breadth
        if progress_callback:
            progress_callback(10, "Calculating market breadth...")
        
        market_healthy = self._data_service.calculate_market_breadth(all_data)
        market_regime = "BULL" if market_healthy else "NEUTRAL"
        log.info("OrchestrationService: Market regime=%s (healthy=%s)", market_regime, market_healthy)
        
        # Phase 3: Update alpha status
        alpha_status = self._scoring_service.update_alpha_status()
        
        # Phase 4: Process symbols in parallel
        if progress_callback:
            progress_callback(15, "Processing symbols...")
        
        results, rejections = self._process_symbols_parallel(
            all_data=all_data,
            market_regime=market_regime,
            market_healthy=market_healthy,
            alpha_status=alpha_status,
            progress_callback=progress_callback,
        )
        
        # Phase 5: Compute sector metrics
        if progress_callback:
            progress_callback(90, "Computing sector metrics...")
        
        sector_strength = self._compute_sector_strength(results)
        
        # Identify weak sectors
        weak_sectors = [s for s, _ in sorted(sector_strength.items(), key=lambda x: x[1])[:2] if sector_strength.get(s, 0.0) > 0.0]
        
        # Phase 6: Apply post-scoring filters
        if progress_callback:
            progress_callback(95, "Applying final filters...")
        
        for result in results:
            self._scoring_service.apply_post_scoring_filters(
                result=result,
                market_regime=market_regime,
                market_healthy=market_healthy,
                sector_strength=sector_strength,
                weak_sectors=weak_sectors,
            )
        
        # Phase 7: Save rejections and daily scan
        if rejections:
            oe_save_rejections(rejections)
        
        oe_save_daily_scan(results)
        
        # Phase 8: Write scan snapshot for API consumption
        self._write_scan_snapshot(results)
        
        scan_duration = time.time() - scan_start
        log.info(
            "OrchestrationService: Scan complete in %.2fs - %d results, %d rejections",
            scan_duration, len(results), len(rejections),
        )
        
        return results, rejections
    
    def _process_symbols_parallel(
        self,
        all_data: Dict[str, any],
        market_regime: str,
        market_healthy: bool,
        alpha_status: any,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[List[dict], List[dict]]:
        """Process all symbols in parallel using thread pool.
        
        Args:
            all_data: Raw data from DataService
            market_regime: Market regime string
            market_healthy: Market breadth health boolean
            alpha_status: Current AlphaStatus
            progress_callback: Optional progress callback
            
        Returns:
            Tuple of (results, rejections)
        """
        results = []
        rejections = []
        results_lock = threading.Lock()
        rejections_lock = threading.Lock()
        
        total = len(SYMBOLS)
        completed_count = 0
        
        def _process_single(sym: str, yahoo: str) -> Optional[dict]:
            """Process a single symbol."""
            # Check cache first
            cached = self._data_service.get_cached_indicator(sym)
            if cached:
                return cached
            
            # Check if data available
            if yahoo not in all_data:
                with rejections_lock:
                    rejections.append({"sym": sym, "reason": "No data downloaded"})
                return None
            
            df = all_data[yahoo]
            
            # Process through scoring service
            try:
                scoring_result = self._scoring_service.process_symbol(
                    symbol=sym,
                    yahoo_symbol=yahoo,
                    df=df,
                    market_regime=market_regime,
                    alpha_status=alpha_status,
                )
                
                if scoring_result is None:
                    with rejections_lock:
                        rejections.append({"sym": sym, "reason": "Failed scoring filters"})
                    return None
                
                # Cache the result
                self._data_service.cache_indicator_result(
                    symbol=sym,
                    result=scoring_result["result"],
                    slope=scoring_result["slope"],
                    quantum_n=scoring_result["quantum_n"],
                )
                
                return scoring_result
                
            except Exception as e:
                log.error("Error processing %s: %s", sym, e)
                with rejections_lock:
                    rejections.append({"sym": sym, "reason": f"Processing error: {e}"})
                return None
        
        # Execute in thread pool
        try:
            with ThreadPoolExecutor(max_workers=K.SCAN_MAX_WORKERS) as executor:
                future_to_sym = {
                    executor.submit(_process_single, k, v): k
                    for k, v in SYMBOLS.items()
                }
                
                for future in as_completed(future_to_sym):
                    sym = future_to_sym[future]
                    completed_count += 1
                    
                    # Progress update
                    if progress_callback and completed_count % 4 == 0:
                        progress_callback(
                            int(15 + (completed_count / max(1, total)) * 75),
                            f"Processing: {completed_count}/{total}",
                        )
                    
                    try:
                        scoring_result = future.result()
                        if scoring_result is not None:
                            with results_lock:
                                results.append(scoring_result)
                    except Exception as exc:
                        log.error("Error processing %s: %s", sym, exc)
                        
        except (RuntimeError, KeyboardInterrupt) as exc:
            log.warning("Scan interrupted during executor phase: %s", exc)
        
        return results, rejections
    
    def _compute_sector_strength(self, results: List[dict]) -> Dict[str, float]:
        """Compute sector strength scores from results.
        
        Args:
            results: List of scoring results
            
        Returns:
            Dictionary mapping sector names to strength scores
        """
        sec_quant: Dict[str, List[float]] = {k: [] for k in SECTORS}
        
        for result in results:
            r = result["result"]
            sec = r["sector"]
            if sec in sec_quant:
                sec_quant[sec].append(result["quantum_n"])
        
        sector_strength = {}
        for sec, vals in sec_quant.items():
            if vals:
                sector_strength[sec] = sum(vals) / len(vals)
            else:
                sector_strength[sec] = 0.0
        
        return sector_strength
    
    def _write_scan_snapshot(self, results: List[dict]) -> None:
        """Write scan results to snapshot file for API consumption.
        
        Args:
            results: List of scoring results
        """
        try:
            snapshot = []
            for result in results:
                r = result["result"]
                plan = r.get("plan", {})
                
                snapshot.append({
                    "sym": r.get("sym"),
                    "sector": r.get("sector"),
                    "price": r.get("price"),
                    "signal": r.get("signal"),
                    "tag": r.get("tag"),
                    "smart_rank": r.get("smart_rank", 0.0),
                    "confidence": r.get("confidence", 0.0),
                    "direction": r.get("signal_dir", ""),
                    "phase": r.get("phase", ""),
                    "zone": r.get("zone", ""),
                    "action": plan.get("action", "WAIT") if plan else "WAIT",
                    "entry": plan.get("entry", 0.0) if plan else 0.0,
                    "stop": plan.get("stop", 0.0) if plan else 0.0,
                    "target": plan.get("target", 0.0) if plan else 0.0,
                    "winrate": plan.get("winrate", 0.0) if plan else 0.0,
                    "scan_time": datetime.utcnow().isoformat(),
                })
            
            # Write snapshot file
            from egx_radar.config.settings import K
            snapshot_path = os.path.join(
                os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
            )
            
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(snapshot_path), suffix='.tmp')
            with os.fdopen(fd, 'w') as f:
                json.dump(snapshot, f, default=str)
            os.replace(tmp, snapshot_path)
            
            log.debug("OrchestrationService: Wrote scan snapshot to %s", snapshot_path)
            
        except Exception as e:
            log.error("OrchestrationService: Failed to write scan snapshot: %s", e)


# Global singleton instance
_orchestration_service: Optional[OrchestrationService] = None
_init_lock = threading.Lock()


def get_orchestration_service() -> OrchestrationService:
    """Get the global orchestration service singleton.
    
    Returns:
        Shared OrchestrationService instance
    """
    global _orchestration_service
    
    if _orchestration_service is None:
        with _init_lock:
            if _orchestration_service is None:
                _orchestration_service = OrchestrationService()
    
    return _orchestration_service
