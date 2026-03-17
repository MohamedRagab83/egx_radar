"""Thread-safe application state container (Layer 8)."""

import json
import logging
import os
import sqlite3
import threading
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from egx_radar.config.settings import K, SECTORS
from egx_radar.core.indicators import safe_clamp

log = logging.getLogger(__name__)


class AppState:
    """
    Thread-safe application state container.
    FIX-H: All shared state mutations go through this class.
    No direct global state writes outside this class.
    """

    def __init__(self) -> None:
        self._lock           = threading.Lock()
        self._momentum_lock  = threading.Lock()
        
        self.momentum_guard: Optional[Any] = None
        self.position_manager: Optional[Any] = None

        # ── Neural adaptive weights ────────────────────────────────────────
        self.neural_weights: Dict[str, float] = {
            "flow": 1.0, "structure": 1.0, "timing": 1.0
        }
        self.neural_memory      = deque(maxlen=K.NEURAL_MEM_SIZE)

        # ── Win/loss memory ────────────────────────────────────────────────
        self.neural_win_memory  = deque(maxlen=80)
        self.neural_loss_memory = deque(maxlen=80)
        self.neural_bias_memory = deque(maxlen=80)

        # ── FIX-5: Per-sector win/loss tracking for smarter WinRate ───────────
        # Each entry: (rank, anticipation)
        self.sector_win_memory:  Dict[str, deque] = {s: deque(maxlen=30) for s in SECTORS}
        self.sector_loss_memory: Dict[str, deque] = {s: deque(maxlen=30) for s in SECTORS}
        # Per-tag win/loss (ultra/early/buy/watch)
        self.tag_win_memory:  Dict[str, deque] = defaultdict(lambda: deque(maxlen=30))
        self.tag_loss_memory: Dict[str, deque] = defaultdict(lambda: deque(maxlen=30))

        # ── Signal history ──────────────────────────────────────────────────
        self.signal_history: Dict[str, deque]  = defaultdict(lambda: deque(maxlen=5))
        self.prev_ranks:     Dict[str, float]  = {}

        # ── Momentum ─────────────────────────────────────────────────────────
        self.momentum_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=4))

        # ── Sector memory ─────────────────────────────────────────────────────
        self.sector_flow_memory     = {k: deque(maxlen=15) for k in SECTORS}
        self.sector_rotation_memory = {k: deque(maxlen=20) for k in SECTORS}

        # ── Brain mode ─────────────────────────────────────────────────────────
        self.brain_mode      = "neutral"
        self.brain_vol_req   = 1.0
        self.brain_score_req = K.BRAIN_SCORE_NEUTRAL

        self.scan_count = 0

        # ── Backtest results (persist in memory while app is open) ─────────────
        self.backtest_results: dict = {}

    # ── Neural weights ──────────────────────────────────────────────────────
    def update_neural_weights(self, results: List[dict]) -> None:
        """
        Feature 1: ML & Neural Adaptive Weights
        Uses recent win/loss tracking memory to adjust weights dynamically.
        """
        if len(results) < 6:
            return
            
        with self._lock:
            win_mem  = list(self.neural_win_memory)
            loss_mem = list(self.neural_loss_memory)
            nw = self.neural_weights
            
            # Require at least some history to make intelligent decisions
            sample_size = len(win_mem) + len(loss_mem)
            if sample_size > 10:
                win_rate = len(win_mem) / sample_size
                
                # If win rate is terrible recently, we penalize structure heavily to demand better setups
                if win_rate < 0.40:
                    nw["structure"] = safe_clamp(nw["structure"] - K.NEURAL_STEP * 2, K.NEURAL_WEIGHT_MIN, K.NEURAL_WEIGHT_MAX)
                    nw["flow"] = safe_clamp(nw["flow"] + K.NEURAL_STEP, K.NEURAL_WEIGHT_MIN, K.NEURAL_WEIGHT_MAX)
                elif win_rate > 0.60:
                    nw["structure"] = safe_clamp(nw["structure"] + K.NEURAL_STEP, K.NEURAL_WEIGHT_MIN, K.NEURAL_WEIGHT_MAX)
                
            # Current environment evaluation (Mean-reversion component)
            avg_q = sum(r["quantum"] for r in results) / len(results)
            avg_v = sum(r["vol_ratio"] for r in results) / len(results)
            self.neural_memory.append((avg_q, avg_v, 0)) # simplified memory
            
            if len(self.neural_memory) >= 5:
                q_avg = sum(x[0] for x in self.neural_memory) / len(self.neural_memory)
                v_avg = sum(x[1] for x in self.neural_memory) / len(self.neural_memory)
                
                for key, cond in [("timing", q_avg > 2.0), ("flow", v_avg > 1.4)]:
                    step  = K.NEURAL_STEP if cond else -K.NEURAL_STEP
                    decay = K.NEURAL_DECAY * (nw[key] - 1.0)
                    nw[key] = safe_clamp(nw[key] + step - decay, K.NEURAL_WEIGHT_MIN, K.NEURAL_WEIGHT_MAX)


    def get_neural_weights(self) -> Dict[str, float]:
        with self._lock:
            return dict(self.neural_weights)

    # ── Win rate ────────────────────────────────────────────────────────────
    def estimate_winrate(
        self,
        smart_rank: float,
        anticipation: float,
        sector: str = "",
        tag: str = "",
        regime: str = "NEUTRAL",
    ) -> float:
        """
        FIX-5: Added sector-specific win rate adjustment, tag-type bonus,
        and regime multiplier.

        sector_adj:     based on historical win rate for this sector vs global
        tag_adj:        ultra/early signals get +5/+3 bonus (historically better)
        regime_mult:    MOMENTUM × 1.1 boosts confidence; DISTRIBUTION × 0.9 dampens
        """
        with self._lock:
            win_mem  = list(self.neural_win_memory)
            loss_mem = list(self.neural_loss_memory)
            bias_mem = list(self.neural_bias_memory)
            # FIX-5: sector-specific memories
            s_win  = list(self.sector_win_memory.get(sector, deque()))
            s_loss = list(self.sector_loss_memory.get(sector, deque()))
            t_win  = list(self.tag_win_memory.get(tag, deque()))
            t_loss = list(self.tag_loss_memory.get(tag, deque()))

        all_outcomes  = win_mem + loss_mem
        sample_size   = len(all_outcomes)
        win_count     = len(win_mem)

        # FIX-3: return sentinel when sample too small
        if sample_size < K.WINRATE_MIN_SAMPLE:
            return -1.0

        if sample_size == 0:
            base = 45.0
        else:
            empirical_wr = (win_count / sample_size) * 100.0
            avg_rank = sum(x[0] for x in all_outcomes) / sample_size
            avg_ant  = sum(x[1] for x in all_outcomes) / sample_size
            base     = empirical_wr + (smart_rank - avg_rank) * 3 + (anticipation - avg_ant) * 2

            if sample_size < K.WINRATE_MIN_SAMPLE:
                sparsity_ratio = 1.0 - (sample_size / K.WINRATE_MIN_SAMPLE)
                base -= K.WINRATE_SPARSE_PENALTY * sparsity_ratio

        if bias_mem:
            weights = [0.85 ** (len(bias_mem) - i - 1) for i in range(len(bias_mem))]
            w_sum   = sum(weights)
            bias    = sum(b * w for b, w in zip(bias_mem, weights)) / (w_sum + 1e-9)
            base   += bias * 5

        # FIX-5a: sector adjustment
        sector_total = len(s_win) + len(s_loss)
        if sector_total >= 5:
            sector_wr  = len(s_win) / sector_total * 100.0
            global_wr  = (win_count / sample_size * 100.0) if sample_size > 0 else 45.0
            sector_adj = (sector_wr - global_wr) * 0.3   # partial weight
            base      += sector_adj

        # FIX-5b: tag-type adjustment
        tag_total = len(t_win) + len(t_loss)
        if tag_total >= 3:
            tag_wr  = len(t_win) / tag_total * 100.0
            global_wr = (win_count / sample_size * 100.0) if sample_size > 0 else 45.0
            base   += (tag_wr - global_wr) * 0.2
        else:
            # Prior bonus for historically better signal types
            if tag == "ultra":  base += 5.0
            elif tag == "early": base += 3.0

        # FIX-5c: regime multiplier
        regime_mult = {"MOMENTUM": 1.10, "ACCUMULATION": 1.05,
                       "DISTRIBUTION": 0.90, "NEUTRAL": 1.0}.get(regime, 1.0)
        base *= regime_mult

        dynamic_floor = safe_clamp(K.WINRATE_FLOOR + smart_rank * (15.0 / K.SMART_RANK_SCALE), 20.0, 35.0)
        return safe_clamp(round(base, 1), dynamic_floor, K.WINRATE_CEIL)

    # ── Win/loss recording ───────────────────────────────────────────────────
    def record_win(self, rank: float, ant: float, sector: str = "", tag: str = "") -> None:
        with self._lock:
            self.neural_win_memory.append((rank, ant))
            self.neural_bias_memory.append(0.5)
            if sector and sector in self.sector_win_memory:   # FIX-5
                self.sector_win_memory[sector].append((rank, ant))
            if tag:
                self.tag_win_memory[tag].append((rank, ant))

    def record_loss(self, rank: float, ant: float, sector: str = "", tag: str = "") -> None:
        with self._lock:
            self.neural_loss_memory.append((rank, ant))
            self.neural_bias_memory.append(-0.4)
            if sector and sector in self.sector_loss_memory:  # FIX-5
                self.sector_loss_memory[sector].append((rank, ant))
            if tag:
                self.tag_loss_memory[tag].append((rank, ant))

    def record_signal_bias(self, top_results: List[dict]) -> None:
        """Consolidate current scan bias to prevent flooding memory."""
        entries = [r for r in top_results if (r.get("plan") or {}).get("action") in ("ACCUMULATE", "PROBE")]
        if not entries:
            return
        
        # Calculate mean bias of this scan
        total_bias = 0.0
        for r in entries:
            total_bias += 0.2 if r["plan"]["action"] == "ACCUMULATE" else 0.05
        
        avg_bias = total_bias / len(entries)
        
        with self._lock:
            self.neural_bias_memory.append(safe_clamp(avg_bias, -0.5, 0.5))

    # ── Signal & momentum history ────────────────────────────────────────────
    def append_signal_history(self, sym: str, tag: str) -> List[str]:
        with self._lock:
            if sym not in self.signal_history:
                self.signal_history[sym] = deque(maxlen=5)
            self.signal_history[sym].append(tag)
            return list(self.signal_history[sym])

    def momentum_arrow(self, sym: str, current_mom: float) -> str:
        with self._momentum_lock:
            hist = self.momentum_history[sym]
            hist.append(current_mom)
            hist_copy = list(hist)
        if len(hist_copy) < 2:
            return "→"
        avg  = sum(hist_copy[:-1]) / (len(hist_copy) - 1)
        diff = hist_copy[-1] - avg
        if diff > 0.3:  return "↑"
        if diff < -0.3: return "↓"
        return "→"

    # ── Prev rank ────────────────────────────────────────────────────────────
    def get_prev_rank(self, sym: str, default: float) -> float:
        with self._lock:
            return self.prev_ranks.get(sym, default)

    def set_prev_rank(self, sym: str, val: float) -> None:
        with self._lock:
            self.prev_ranks[sym] = val

    # ── Brain mode ────────────────────────────────────────────────────────────
    def set_brain(self, mode: str) -> None:
        with self._lock:
            if mode == "aggressive":
                self.brain_mode, self.brain_vol_req = "aggressive", 0.8
                self.brain_score_req = K.BRAIN_SCORE_AGGRESSIVE
            elif mode == "defensive":
                self.brain_mode, self.brain_vol_req = "defensive", 1.2
                self.brain_score_req = K.BRAIN_SCORE_DEFENSIVE
            else:
                self.brain_mode, self.brain_vol_req = "neutral", 1.0
                self.brain_score_req = K.BRAIN_SCORE_NEUTRAL

    def snapshot_brain(self) -> Tuple[str, float, int]:
        with self._lock:
            return self.brain_mode, self.brain_vol_req, self.brain_score_req

    # ── Sector flow ───────────────────────────────────────────────────────────
    def update_sector_flow(self, sec: str, cpi_val: float) -> None:
        with self._lock:
            self.sector_flow_memory[sec].append(cpi_val)

    def update_sector_rotation(self, sec: str, val: float) -> None:
        """FIX: thread-safe access to sector_rotation_memory."""
        with self._lock:
            self.sector_rotation_memory[sec].append(val)

    def get_sector_flow_avg(self, sec: str) -> float:
        with self._lock:
            mem = self.sector_flow_memory[sec]
            return sum(mem) / len(mem) if mem else 0.0

    # ── Persist / restore ─────────────────────────────────────────────────────
    def save(self, filename: str = "brain_state.db") -> None:
        """Persist neural state to SQLite (atomic, crash-safe)."""
        try:
            with self._lock:
                data = {
                    "neural_weights": self.neural_weights,
                    "prev_ranks":     self.prev_ranks,
                    "neural_win":     list(self.neural_win_memory),
                    "neural_loss":    list(self.neural_loss_memory),
                    "neural_bias":    list(self.neural_bias_memory),
                    "sector_flow":    {k: list(v) for k, v in self.sector_flow_memory.items()},
                    "sector_win":     {k: list(v) for k, v in self.sector_win_memory.items()},
                    "sector_loss":    {k: list(v) for k, v in self.sector_loss_memory.items()},
                    "tag_win":        {k: list(v) for k, v in self.tag_win_memory.items()},
                    "tag_loss":       {k: list(v) for k, v in self.tag_loss_memory.items()},
                }
            con = sqlite3.connect(filename, timeout=10)
            with con:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS brain_state
                    (key TEXT PRIMARY KEY, value TEXT)
                """)
                con.execute(
                    "INSERT OR REPLACE INTO brain_state VALUES (?, ?)",
                    ("state", json.dumps(data, default=str))
                )
            con.close()
        except Exception as e:
            log.error("AppState.save (sqlite): %s", e)

    def load(self, filename: str = "brain_state.db") -> None:
        """Load neural state from SQLite. Falls back to JSON if .db missing."""
        # Fallback: load from old JSON file if SQLite db doesn't exist yet
        json_path = filename.replace(".db", ".json")
        if not os.path.exists(filename) and os.path.exists(json_path):
            log.info("AppState: migrating from JSON to SQLite")
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._apply_state(data)
                self.save(filename)  # migrate to SQLite immediately
                return
            except Exception as e:
                log.warning("AppState: JSON migration failed: %s", e)
                return

        if not os.path.exists(filename):
            return
        try:
            con = sqlite3.connect(filename, timeout=10)
            row = con.execute(
                "SELECT value FROM brain_state WHERE key = 'state'"
            ).fetchone()
            con.close()
            if row:
                data = json.loads(row[0])
                self._apply_state(data)
        except Exception as e:
            log.error("AppState.load (sqlite): %s", e)

    def _apply_state(self, data: dict) -> None:
        """Apply a state dict to this AppState instance."""
        with self._lock:
            self.neural_weights = data.get("neural_weights", self.neural_weights)
            self.prev_ranks     = data.get("prev_ranks", {})
            if "neural_win"  in data:
                self.neural_win_memory  = deque(data["neural_win"],  maxlen=80)
            if "neural_loss" in data:
                self.neural_loss_memory = deque(data["neural_loss"], maxlen=80)
            if "neural_bias" in data:
                self.neural_bias_memory = deque(data["neural_bias"], maxlen=80)
            for sec, vals in data.get("sector_flow", {}).items():
                if sec in self.sector_flow_memory:
                    self.sector_flow_memory[sec] = deque(vals, maxlen=15)
            for sec, vals in data.get("sector_win", {}).items():
                if sec in self.sector_win_memory:
                    self.sector_win_memory[sec] = deque(vals, maxlen=50)
            for sec, vals in data.get("sector_loss", {}).items():
                if sec in self.sector_loss_memory:
                    self.sector_loss_memory[sec] = deque(vals, maxlen=50)
            for tag, vals in data.get("tag_win", {}).items():
                self.tag_win_memory[tag] = deque(vals, maxlen=30)
            for tag, vals in data.get("tag_loss", {}).items():
                self.tag_loss_memory[tag] = deque(vals, maxlen=30)


STATE = AppState()


__all__ = ["AppState", "STATE"]
