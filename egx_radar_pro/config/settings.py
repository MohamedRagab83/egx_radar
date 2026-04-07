"""
config/settings.py — EGX Radar Pro
====================================
Central configuration and shared data structures.

All other modules import from here.  This module has NO internal project
imports — it is the lowest layer and must stay that way to prevent circular
dependency chains.

Key exports
-----------
RISK         : RiskConfig singleton
CFG          : EngineConfig singleton
SECTORS      : sector → symbol mapping
SYMBOLS      : sorted list of all tradable symbols
SECTOR_BY_SYMBOL : symbol → sector lookup
Snapshot     : per-symbol market state at a point in time
Trade        : a single executed (or open) trade record
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# ──────────────────────────────────────────────────────────────
# EGX Universe
# ──────────────────────────────────────────────────────────────
SECTORS: Dict[str, List[str]] = {
    "BANKS":       ["COMI", "CIEB", "ADIB", "SAUD", "CNFN", "FAIT"],
    "REAL_ESTATE": ["TMGH", "PHDC", "OCDI", "HELI", "DSCW"],
    "INDUSTRIAL":  ["ORAS", "SKPC", "KZPC", "AMOC", "ESRS"],
    "SERVICES":    ["FWRY", "ETEL", "JUFO", "HRHO", "EGTS", "ORWE"],
    "ENERGY":      ["ABUK", "MFPC", "ISPH", "EAST", "SWDY"],
}

SYMBOLS: List[str] = sorted({s for sec in SECTORS.values() for s in sec})

SECTOR_BY_SYMBOL: Dict[str, str] = {
    sym: sec for sec, syms in SECTORS.items() for sym in syms
}


# ──────────────────────────────────────────────────────────────
# Risk Configuration
# ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RiskConfig:
    """
    Immutable risk parameters.  Modify values here ONLY — never hard-code
    them in execution logic.
    """
    account_size:            float = 100_000.0   # Base currency (EGP)
    risk_per_trade:          float = 0.005        # 0.5% of account per trade
    max_open_trades:         int   = 6            # Global position cap
    max_sector_positions:    int   = 2            # Per-sector concentration limit
    max_sector_exposure_pct: float = 0.30         # Max 30% allocated to one sector
    slippage_pct:            float = 0.003        # 0.3% market impact estimate
    fee_pct:                 float = 0.0015       # 0.15% round-trip fee
    max_bars_hold:           int   = 20           # Time-stop: 20 trading days
    partial_exit_fraction:   float = 0.50         # Fraction closed at first target


# ──────────────────────────────────────────────────────────────
# Engine Configuration
# ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class EngineConfig:
    """
    Immutable engine thresholds.  SmartRank is the only execution gate.
    AI / News / Alpha thresholds here are for display logic only.
    """
    warmup_bars:          int   = 80    # Minimum bars required before scoring
    smart_rank_accumulate: float = 70.0  # MAIN entry threshold (legacy mode)
    smart_rank_probe:      float = 55.0  # PROBE entry threshold (legacy mode)

    # Smart Rank 2.0 — filter-first execution parameters
    v2_rsi_min:           float = 45.0
    v2_rsi_max:           float = 65.0
    v2_volume_min:        float = 1.20
    v2_atr_pct_max:       float = 0.035
    v2_breakout_lookback: int   = 20
    v2_breakout_min:      float = 0.97
    v2_score_threshold:   float = 62.0
    v2_stop_atr_mult:     float = 1.20
    v2_min_rr:            float = 2.2
    alpha_min_score:       float = 70.0  # Alpha display threshold (no execution use)
    alpha_sr_cap:          float = 60.0  # Alpha display cap (no execution use)


# ──────────────────────────────────────────────────────────────
# Module-level singletons — import RISK and CFG everywhere
# ──────────────────────────────────────────────────────────────
RISK = RiskConfig()
CFG  = EngineConfig()


# ──────────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────────
@dataclass
class Snapshot:
    """
    Full market snapshot for one symbol at one point in time.

    Fields marked 'display only' are computed for logging and advisory
    purposes.  They must NOT be used in generate_trade_signal() or any
    execution path.
    """
    # Core price / market data
    date:            pd.Timestamp
    symbol:          str
    sector:          str
    close:           float
    open:            float
    high:            float
    low:             float
    volume:          float

    # Derived technical indicators
    rsi:             float
    atr:             float
    atr_pct:         float
    ema20:           float
    ema50:           float
    ema200:          float
    volume_ratio:    float
    trend_strength:  float
    structure_score: float

    # SmartRank — legacy execution score
    smart_rank:      float

    # SmartRank 2.0 score (filter + score model)
    smart_rank_v2:   float = 0.0
    breakout_proximity: float = 0.0

    # ── DISPLAY ONLY fields ─────────────────────────────────────────────
    # These are populated by evaluate_snapshot() after SmartRank is set.
    # They must NEVER gate or trigger trade execution.
    probability:     float = 0.5   # AI probability estimate
    sentiment_score: float = 0.5   # News sentiment [0=bearish, 1=bullish]
    alpha_score:     float = 0.0   # Alpha opportunity score [0, 100]


@dataclass
class Trade:
    """
    A single trade record — covers the full lifecycle from entry to exit.

    The display-only fields (probability, sentiment_score, alpha_score) are
    captured at entry time for post-trade analysis and reporting only.
    """
    symbol:          str
    sector:          str
    entry_date:      pd.Timestamp
    entry:           float
    stop:            float
    target:          float
    size:            int
    risk_used:       float
    signal_type:     str             # "MAIN" | "PROBE"

    # Execution signal
    smart_rank:      float

    # ── DISPLAY ONLY — captured at entry, never used for execution ──────
    probability:     float
    sentiment_score: float
    alpha_score:     float

    # Lifecycle state
    bars_held:       int                    = 0
    status:          str                    = "OPEN"
    exit_date:       Optional[pd.Timestamp] = None
    exit_price:      Optional[float]        = None
    pnl_pct:         float                  = 0.0
