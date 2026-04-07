EGX RADAR CODEBASE EXPORT

TOTAL FILES: 69
INCLUDED MODULES:
- egx_radar/config/__init__.py
- egx_radar/config/settings.py
- egx_radar/core/__init__.py
- egx_radar/core/accumulation.py
- egx_radar/core/alpha_monitor.py
- egx_radar/core/data_guard.py
- egx_radar/core/indicators.py
- egx_radar/core/momentum_guard.py
- egx_radar/core/position_manager.py
- egx_radar/core/scoring.py
- egx_radar/core/signal_engine.py
- egx_radar/core/signals.py
- egx_radar/market_data/__init__.py
- egx_radar/market_data/manager.py
- egx_radar/market_data/notifications.py
- egx_radar/market_data/signals.py
- egx_radar/advanced/risk_management.py
- egx_radar/core/portfolio.py
- egx_radar/core/risk.py
- egx_radar/backtest/__init__.py
- egx_radar/backtest/dashboard.py
- egx_radar/backtest/data_loader.py
- egx_radar/backtest/engine.py
- egx_radar/backtest/engine_with_guards.py
- egx_radar/backtest/metrics.py
- egx_radar/backtest/missed_trades.py
- egx_radar/backtest/report.py
- egx_radar/backtest/tracking_dashboard.py
- egx_radar/data/__init__.py
- egx_radar/data/fetchers.py
- egx_radar/data/merge.py
- egx_radar/database/__init__.py
- egx_radar/database/alembic_env.py
- egx_radar/database/config.py
- egx_radar/database/manager.py
- egx_radar/database/models.py
- egx_radar/database/utils.py
- egx_radar/outcomes/__init__.py
- egx_radar/outcomes/engine.py
- egx_radar/scan/__init__.py
- egx_radar/scan/runner.py
- egx_radar/state/__init__.py
- egx_radar/state/app_state.py
- egx_radar/tools/__init__.py
- egx_radar/tools/__main__.py
- egx_radar/tools/paper_trading_tracker.py
- egx_radar/dashboard/__init__.py
- egx_radar/dashboard/app.py
- egx_radar/dashboard/routes.py
- egx_radar/dashboard/run.py
- egx_radar/dashboard/websocket.py
- egx_radar/ui/__init__.py
- egx_radar/ui/components.py
- egx_radar/ui/main_window.py
- egx_radar/advanced/__init__.py
- egx_radar/advanced/ml_predictor.py
- egx_radar/advanced/options.py
- egx_radar/advanced/portfolio_optimization.py
- egx_radar/backup.py
- egx_radar/data_validator.py
- egx_radar/error_handler.py
- egx_radar/__init__.py
- egx_radar/__main__.py
- egx_radar/main.py
- source_settings.json
- brain_state.json
- scan_snapshot.json
- egx_radar/source_settings.json
- egx_radar/brain_state.json
DETECTED ENTRY POINTS:
- egx_radar/main.py
- egx_radar/__main__.py
- egx_radar/dashboard/run.py

==================================================
FILE: egx_radar/config/__init__.py
==================================

```python
"""Config package: colours, fonts, constants, sectors, symbols, and data config."""

from egx_radar.config.settings import (
    C,
    K,
    F_TITLE,
    F_HEADER,
    F_BODY,
    F_SMALL,
    F_MICRO,
    SECTORS,
    SYMBOLS,
    DECISION_PRIORITY,
    DATA_SOURCE_CFG,
    _data_cfg_lock,
    SOURCE_SETTINGS_FILE,
    get_sector,
    get_account_size,
    get_risk_per_trade,
    get_atr_exposure,
    get_max_per_sector,
)

__all__ = [
    "C",
    "K",
    "F_TITLE",
    "F_HEADER",
    "F_BODY",
    "F_SMALL",
    "F_MICRO",
    "SECTORS",
    "SYMBOLS",
    "DECISION_PRIORITY",
    "DATA_SOURCE_CFG",
    "_data_cfg_lock",
    "SOURCE_SETTINGS_FILE",
    "get_sector",
    "get_account_size",
    "get_risk_per_trade",
    "get_atr_exposure",
    "get_max_per_sector",
]
```

==================================================
FILE: egx_radar/config/settings.py
==================================

```python
"""Global configuration and constants for EGX Radar (Layer 1)."""

import base64
import json
import os
import tempfile
import threading
from typing import Dict, List


class C:
    """UI colour palette."""
    BG      = "#0a0e14";  BG2     = "#131920";  BG3     = "#1a2230"
    ACCENT  = "#4d9cf0";  ACCENT2 = "#9ad1ff";  GREEN   = "#4cdd7a"
    RED     = "#ff6b6b";  RED_DIM = "#7f1d1d";  YELLOW  = "#f0c040"
    CYAN    = "#79c0ff";  PURPLE  = "#c792ea";  GOLD    = "#ffd700"
    TEXT    = "#dde6f0";  MUTED   = "#7a8a9a";  WHITE   = "#f8fafc"
    ROW_SEL = "#1e3a5f"


F_TITLE  = ("Consolas", 14, "bold")
F_HEADER = ("Consolas", 11, "bold")
F_BODY   = ("Consolas", 11)
F_SMALL  = ("Consolas",  9)
F_MICRO  = ("Consolas",  8)


class K:
    """
    All system constants.
    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    NAMING CONVENTION:
      ADX_*        â†’ ADX indicator thresholds
      MIN_*        â†’ minimum data-quality requirements
      VOL_*        â†’ volume-related parameters
      PRICE_*      â†’ price filter floors
      SCORE_*      â†’ signal score thresholds
      ATR_*        â†’ ATR risk engine constants
      NEURAL_*     â†’ adaptive weight parameters
      WINRATE_*    â†’ win-rate engine constants
      SMART_*      â†’ SmartRank composite parameters
      PORTFOLIO_*  â†’ portfolio guard limits
      OUTCOME_*    â†’ trade log parameters
      PLAN_*       â†’ trade plan geometry
      BRAIN_*      â†’ market mode thresholds
      REGIME_*     â†’ market regime detection
      UI_*         â†’ UI refresh timing
    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    """
    # â”€â”€ Data quality â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    MIN_BARS            = 60       # hard minimum for Yahoo path
    MIN_BARS_RELAXED    = 30       # relaxed minimum for Stooq/TD fallback
    LOW_LIQ_FILTER      = 150_000.0   # legacy share-volume floor (turnover filter is primary)
    PRICE_FLOOR         = 2.0      # minimum price in EGP
    LIQUIDITY_GATE_MIN_VOLUME = 100_000.0   # legacy share-volume gate
    MIN_TURNOVER_EGP    = 3_000_000.0  # â† lowered from 7M for hybrid (wider EGX coverage)
    MAX_SPREAD_PCT      = 4.5          # daily-range proxy ceiling; not a true bid/ask spread

    # â”€â”€ ADX â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ADX_LENGTH          = 14
    ADX_STRONG          = 25.0
    ADX_MID             = 18.0
    # EGX-calibrated: allow slightly lower ADX threshold for accumulation
    ADX_SOFT_LO         = 14.0     # below this â†’ WAIT regardless of score
    ADX_SOFT_HI         = 22.0     # below this â†’ PROBE only if rank meets bar

    # â”€â”€ Volume Z-score â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    VOL_ROLL_WINDOW     = 20
    # FIX-D: Symmetric clamp.  v77 used asymmetric (-5, +10) which rewarded
    # abnormal upside spikes while ignoring downside. Now (-4, +4).
    VOL_ZSCORE_LO       = -4.0
    VOL_ZSCORE_HI       =  4.0

    # [P3-G5] Volume Surge
    VOL_SURGE_ENABLED   = True
    VOL_SURGE_THRESHOLD = 2.5

    # Logarithmic volume scaling â€” suppresses retail spikes, highlights institutional volume
    VOL_LOG_SCALE_ENABLED  = True
    VOL_LOG_SCALE_DIVISOR  = 1.3    # log1p(vol_ratio) / divisor maps to [0, ~1]

    # Liquidity Shock Detector â€” distinguishes institutional from retail volume events
    LIQ_SHOCK_ENABLED      = True
    LIQ_SHOCK_THRESHOLD    = 1.5    # minimum shock value required to apply the boost
    LIQ_SHOCK_BOOST        = 0.08   # additive boost applied to final_n (scale 0â€“1)

    # â”€â”€ VWAP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    VWAP_ROLL_WINDOW    = 20

    # â”€â”€ ATR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ATR_LENGTH          = 14
    # FIX-F: Percentile thresholds instead of hardcoded pct values
    ATR_HIST_WINDOW     = 60       # bars used to compute percentile
    # EGX-calibrated: raise ATR percentile thresholds so only extreme moves flag
    ATR_PCT_HIGH        = 85       # â‰¥85th percentile â†’ HIGH risk (EGX-calibrated)
    ATR_PCT_MED         = 65       # â‰¥65th percentile â†’ MED risk (EGX-calibrated)

    # [P3-G3] ATR% Filter (Hard/Soft Limits)
    ATR_PCT_FILTER_ENABLED = True
    # EGX-calibrated: loosen hard/soft ATR% limits (EGX stocks run larger ATRs)
    ATR_PCT_HARD_LIMIT      = 10.0   # â‰¥10% ATR â†’ WAIT (was 8.0)
    ATR_PCT_SOFT_LIMIT      = 7.0    # â‰¥7% ATR + BUY â†’ PROBE (was 5.0)
    ATR_NORMALIZE_BY_PRICE  = True   # always use atr/price (%), never raw ATR points

    # â”€â”€ Whale detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    WHALE_ZSCORE_THRESH = 1.5
    WHALE_CLV_THRESH    = 0.5
    WHALE_VOL_THRESH    = 1.3
    WHALE_CLV_SIGNAL    = 0.6

    # â”€â”€ CMF (Chaikin Money Flow) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    CMF_DAMPING_ENABLED = True
    CMF_DAMPING_FACTOR  = 0.70
    CMF_PERIOD          = 20

    # [P3-G6] CMF Size Boost
    CMF_SIZE_BOOST_ENABLED   = True
    CMF_SIZE_BOOST_THRESHOLD = 0.15
    CMF_SIZE_BOOST_MULT      = 1.10

    # â”€â”€ VCP (Volatility Contraction Pattern) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    VCP_MULTIPLIER_ENABLED = True
    VCP_SCORE_MULTIPLIER   = 1.15

    # â”€â”€ Signal score â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    SCORE_BUY           = 7
    SCORE_WATCH         = 4
    FAKE_BREAK_BODY     = 0.45
    RSI_OVERBOUGHT      = 72.0

    # â”€â”€ Gating â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    LATE_ZONE_FILTER_ENABLED = True
    RSI_OB_GATE_ENABLED      = True
    RSI_OB_HARD_LIMIT        = 78.0
    RSI_OB_SOFT_LIMIT        = 72.0
    EMA50_GUARD_ENABLED      = True

    # â”€â”€ SmartRank weights (EXPLICIT â€” all components normalised 0-1) â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FIX-B: Each weight is applied to a 0-1 normalised sub-score.
    # Total weight budget = 1.0.  Adjust weights here, not in the formula.
    # Formula (documented in smart_rank_score()):
    #   smart_rank = Î£(weight_i Ã— normalised_component_i) Ã— SMART_RANK_SCALE
    #   where each normalised_component_i âˆˆ [0, 1]
    # Rebalanced: more weight on capital flow and structure, less on momentum.
    # EGX signals driven by institutional flows, not momentum spikes.
    # New sum: 0.30+0.25+0.20+0.10+0.10+0.05 = 1.00 â€” assert still passes.
    SR_W_FLOW        = 0.30   # increased â€” EGX is driven by institutional capital flows
    SR_W_STRUCTURE   = 0.25   # increased â€” technical structure is a more reliable signal
    SR_W_TIMING      = 0.20   # unchanged
    SR_W_MOMENTUM    = 0.10   # decreased â€” was over-promoting volatile low-quality stocks
    SR_W_REGIME      = 0.10   # decreased
    SR_W_NEURAL      = 0.05   # decreased
    # (weights must sum to 1.0 â€” enforced at startup)
    SMART_RANK_SCALE    = 100.0  # position score output range: [0, 100]
    SMART_RANK_SMOOTHING = 0.5  # EWM alpha: higher = faster response
    SMART_RANK_ADX_CAP  = 70.0  # cap accumulation setups when trend quality is weak
    SMARTRANK_ENTRY_THRESHOLD = 75  # STRONG trade threshold
    SMARTRANK_MIN_ACTIONABLE = 65.0  # MEDIUM trade threshold

    # â”€â”€ Sector configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Remove hard-block blacklist for EGX â€” use soft downgrade instead
    BLACKLISTED_SECTORS = set()

    # EGX-calibrated: sectors historically weak that should be downgraded
    WEAK_SECTOR_DOWNGRADE = set()
    BLACKLISTED_SECTORS_BT = set()
    PRIORITY_SECTORS = []
    SECTOR_FILTER_ENABLED = False
    SIZE_MULTIPLIER_FLOOR = 0.25   # global floor â€” never reduce below 25%

    # â”€â”€ Neural adaptive weights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FIX-E: Weight update now uses mean-reversion to 1.0 (neutral).
    # Old code accumulated drift; new code decays toward 1.0 each update.
    NEURAL_WEIGHT_MIN   = 0.8
    NEURAL_WEIGHT_MAX   = 1.4
    NEURAL_STEP         = 0.05
    NEURAL_DECAY        = 0.02   # decay toward 1.0 per update cycle
    NEURAL_MEM_SIZE     = 50     # rolling window for market context

    # â”€â”€ Win-rate engine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FIX-A: True empirical win rate from balanced win/loss sample.
    WINRATE_MIN_SAMPLE  = 10     # below this â†’ show "âŒ› Building"
    WINRATE_FLOOR       = 20.0
    WINRATE_CEIL        = 60.0
    WINRATE_SPARSE_PENALTY = 5.0 # per-missing-trade confidence discount

    # â”€â”€ Market regime detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FIX-C: Regime now requires BOTH ADX > threshold AND EMA200 slope direction.
    # Prevents "Accumulation" false-positives in downtrending markets.
    REGIME_ADX_BULL       = 25.0
    REGIME_ADX_DIST       = 18.0
    REGIME_SLOPE_BARS     = 20   # bars used to compute EMA200 slope

    # Bear market score damping â€” reduces signal count in weak or bear markets
    REGIME_BEAR_DAMPING_ENABLED = True
    REGIME_BEAR_SCORE_MULT      = 0.60   # multiply raw_n by 0.60 in BEAR / DISTRIBUTION
    REGIME_NEUTRAL_SCORE_MULT   = 0.85   # multiply raw_n by 0.85 in NEUTRAL market

    REGIME_RSI_DIST_MIN   = 65.0
    REGIME_BEAR_SLOPE_THRESH = -0.002   # EMA200 slope below this â†’ BEAR candidate
    REGIME_BEAR_RSI_MAX      = 45.0     # RSI below this confirms BEAR (not just cooling)
    
    # â”€â”€ General Market Proxy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # NOTE: ^EGX30 is dead on Yahoo Finance (returns HTTP 404 for all variants).
    # Best working proxy is COMI.CA (Commercial International Bank of Egypt),
    # the most liquid and institutionally tracked EGX blue chip (124 bars on YF).
    EGX30_SYMBOL          = "COMI.CA"  # Proxy for broad EGX market health
    EGX30_HEALTH_BARS     = 50        # Bars required to evaluate broad market health (EMA50)
    MARKET_REGIME_STRONG_ADX = 20.0
    MARKET_REGIME_WEAK_ADX   = 18.0
    MARKET_REGIME_EMA_NEAR_PCT = 0.03
    MARKET_REGIME_VOL_LOOKBACK = 20
    MARKET_REGIME_RECENT_WINDOW = 5
    MARKET_REGIME_HIGHER_HIGHS_LOOKBACK = 20
    MARKET_REGIME_ATR_PCT_MAX_STRONG = 0.06
    MARKET_REGIME_STD_MAX_STRONG = 0.03
    MARKET_REGIME_WEAK_RISK_MULT = 0.50
    MARKET_REGIME_WEAK_SMARTRANK_BONUS = 5.0

    # â”€â”€ Trade plan geometry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PLAN_ENTRY_DISCOUNT  = 1.0
    PLAN_STOP_ADX_LOW    = 0.965
    PLAN_STOP_CLV_HIGH   = 0.970
    PLAN_STOP_DEFAULT    = 0.955
    PLAN_TARGET_HIGH     = 1.10
    PLAN_TARGET_DEFAULT  = 1.08
    PLAN_ANTICIPATION_HI = 0.60
    MAX_STOP_LOSS_PCT    = 0.05      # â† widened: let natural support work (position trading)
    PARTIAL_TP_PCT       = 0.07      # â† raised: take partial profits at +7% not +4%
    TRAILING_TRIGGER_PCT = 0.05      # â† raised: activate trail at +5% not +3%
    TRAILING_STOP_PCT    = 0.03      # â† widened: give winners room to breathe (3% trail)
    PULLBACK_MA20_MAX_DIST_PCT = 0.02
    PULLBACK_MA50_MAX_DIST_PCT = 0.03
    MAX_3DAY_GAIN_PCT    = 5.0       # â† tightened from 10.0 (reject recent surges)
    MAX_GAP_UP_PCT       = 2.0       # â† tightened from 3.0 (reject gap-ups)
    MAX_VERTICAL_EXTENSION_PCT = 0.08
    ANTI_FAKE_ABNORMAL_VOL_RATIO = 2.5

    # Position accumulation thresholds
    ACCUM_COMPRESSION_MIN_DAYS      = 5
    ACCUM_COMPRESSION_MAX_DAYS      = 15
    ACCUM_COMPRESSION_RANGE_MAX_PCT = 8.5
    ACCUM_PREBREAK_BUFFER_PCT       = 1.5
    ACCUM_MAX_MINOR_BREAK_PCT       = 2.5
    ACCUM_MAX_2DAY_SPIKE_PCT        = 8.0
    ACCUM_ABNORMAL_CANDLE_RANGE_PCT = 6.0
    ACCUM_ABNORMAL_BODY_PCT         = 3.5
    ACCUM_VOL_CONFIRM_MIN           = 0.95
    ACCUM_VOL_CONFIRM_MAX           = 1.80
    ACCUM_ERRATIC_VOLUME_CV         = 0.95
    ACCUM_SCORE_MIN                 = 65.0
    ACCUM_SCORE_ENTRY               = 75.0
    POSITION_MAIN_TP_PCT            = 0.10

    # Trade classification and trigger execution
    # HYBRID SYSTEM: two-tier classification with different risk budgets
    TRADE_TYPE_STRONG_MIN           = 70.0    # â† SR >= 70 = STRONG (full conviction)
    TRADE_TYPE_MEDIUM_MIN           = 45.0    # â† SR >= 45 = MEDIUM (reduced risk)
    RISK_PER_TRADE_STRONG           = 0.005   # 0.5% risk per STRONG trade
    RISK_PER_TRADE_MEDIUM           = 0.0020  # 0.20% risk per MEDIUM trade
    TRIGGER_FILL_TOLERANCE_PCT      = 0.001   # 0.1% trigger touch tolerance

    # â”€â”€ Trade sizing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ACCOUNT_SIZE         = 10_000.0
    RISK_PER_TRADE       = 0.005     # â† halved from 0.01 (0.5% risk per trade)

    # â”€â”€ Portfolio guard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FIX-G: Guard is now a pure function returning a new annotated list.
    PORTFOLIO_MAX_PER_SECTOR    = 2
    PORTFOLIO_MAX_ATR_EXPOSURE  = 0.04  # 4% of account in ATR units
    PORTFOLIO_MAX_OPEN_TRADES   = 3        # â† HYBRID: allow 3 concurrent trades
    PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT = 0.30

    # â”€â”€ Trade outcome engine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    OUTCOME_LOG_FILE         = "trades_log.json"
    OUTCOME_HISTORY_FILE     = "trades_history.json"
    OUTCOME_LOOKFORWARD_DAYS = 20
    OUTCOME_MIN_BARS_NEEDED  = 3
    MAX_BARS_HELD            = 20

    # â”€â”€ Backtest costs & limits â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    BT_SLIPPAGE_PCT  = 0.005        # minimum slippage per round-trip
    BT_FEES_PCT      = 0.002        # broker + EGX fees per round-trip
    BT_TOTAL_COST_PCT = BT_SLIPPAGE_PCT + BT_FEES_PCT
    BT_MAX_BARS      = 20           # default max holding period
    BT_DAILY_TOP_N   = 2            # â† HYBRID: allow top 2 signals per day
                                     # Set to 0 to disable (all allowed signals enter)
    # Phase 2b: minimum action quality for backtest entry
    # "ACCUMULATE" = SmartRank >= 40% of scale (>=24) â€” high conviction only
    # "PROBE"      = SmartRank >= 28% of scale (>=16.8) â€” includes weaker signals
    # Set to "ACCUMULATE" to filter out low-SmartRank entries
    BT_MIN_ACTION    = "PROBE"       # â† quality gate handles filtering, allow wider entry
    BT_MIN_SMARTRANK = 45.0          # â† HYBRID: lowered to 45 (MEDIUM tier threshold)
    BT_OOS_START     = "2025-01-01"     # Phase 4: recommended out-of-sample start date
                                         # Results before this date may be optimistically biased
    MIN_BARS_HELD            = 3
    OPTIMAL_BARS_LOW         = 7
    OPTIMAL_BARS_HIGH        = 20

    # â”€â”€ Scan history & paper trading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    SCAN_HISTORY_ENABLED   = True    # auto-save daily scan CSV
    SCAN_HISTORY_KEEP_DAYS = 90      # delete scans older than 90 days

    # â”€â”€ Brain mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    BRAIN_SCORE_AGGRESSIVE = 6
    BRAIN_SCORE_NEUTRAL    = 7
    BRAIN_SCORE_DEFENSIVE  = 8

    # â”€â”€ Signal accumulation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ACCUM_SCORE_THRESH   = 2.0
    LEADER_QUANTUM_DELTA = 1.2

    # â”€â”€ Download â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    CHUNK_SIZE           = 6
    DOWNLOAD_TIMEOUT     = 30
    MAX_DOWNLOAD_RETRIES = 2
    RETRY_BACKOFF_BASE   = 1.5
    STOOQ_MAX_WORKERS    = 8
    INVESTING_MAX_WORKERS = 8
    TD_MAX_WORKERS       = 6
    TD_REQUEST_DELAY     = 7.5   # 8 req/min = 7.5s gap
    TD_BARS              = 500

    # â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    UI_POLL_MS     = 40
    UI_PULSE_MS    = 420

    # â”€â”€ Misc â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    CONF_SIGMOID_SCALE = 0.25
    CONF_SIGMOID_SHIFT = 15.0

    # Unified trading days â€” was 250 in indicators.py vs 252 in metrics.py
    TRADING_DAYS_PER_YEAR = 252

    # EGP risk-free rate (Egyptian T-bills ~12%)
    RISK_FREE_ANNUAL_PCT = 12.0

    # â”€â”€ Data Guard (Module 1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    DG_CANDLE_BAD_PCT_LIMIT  = 0.10   # reject if >10% bars have broken candles
    DG_VOL_ANOMALY_ZSCORE    = 3.0    # |Z| threshold per bar
    DG_VOLUME_ZSCORE_THRESHOLD = DG_VOL_ANOMALY_ZSCORE  # legacy alias for backtest overrides
    DG_CANDLE_SIZE_ATR_MULTIPLIER = 4.0                 # legacy backtest knob (unused by current DataGuard)
    DG_VOL_ANOMALY_PCT_LIMIT = 0.20   # reject if >20% of bars anomalous
    DG_CONFIDENCE_FULL       = 65.0   # â‰¥65 â†’ full signal
    DG_CONFIDENCE_DEGRADED   = 40.0   # 40-64 â†’ WATCH cap; <40 â†’ rejected
    DG_IDEAL_BARS            = 200    # bar count for 100% sufficiency
    
    # â”€â”€ Data Guard: Consecutive Zero Volume â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    DG_MAX_CONSECUTIVE_ZERO_VOL = 3   # flag if 3+ consecutive zero-volume days
    
    # â”€â”€ Data Guard: Data Staleness â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Phase 3: Changed from calendar days to trading days (Sun-Thu only).
    # Accounts for Egyptian public holidays with 1-day/week buffer.
    DG_MAX_DATA_LAG_DAYS      = 3    # EGX trading days (was 4 calendar days)
    
    # â”€â”€ Data Guard: Cross-Source Agreement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    DG_CROSS_SOURCE_SPREAD_LIMIT = 0.05  # flag if sources disagree by more than 5%
    
    # â”€â”€ Data Guard: Weights (must sum to 1.0) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    DG_WEIGHT_CANDLE         = 0.35   # was 0.40
    DG_WEIGHT_VOLUME         = 0.25   # was 0.30
    DG_WEIGHT_BARS           = 0.25   # was 0.30
    DG_WEIGHT_ZVOL           = 0.15   # weight for consecutive-zero-volume check

    # â”€â”€ Momentum Guard (Module 2) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    MG_PERSISTENCE_MIN_EACH       = 2.0    # each day's momentum must clear this
    MG_LOSS_CLUSTER_WINDOW        = 5      # sessions to look back for stop-losses
    MG_LOSS_CLUSTER_TRIGGER       = 2      # stop-losses within window to trigger guard
    MG_DEFENSIVE_RANK_BOOST       = 5      # SmartRank threshold boost in defensive mode
    MG_DEFENSIVE_POSITION_SCALE   = 0.65   # position scale in defensive mode
    MG_EXEMPTION_THRESHOLD_NORMAL = 2.5    # momentum exemption in normal mode
    MG_EXEMPTION_THRESHOLD_GUARD  = 3.5    # momentum exemption in defensive mode
    MG_FATIGUE_WINDOW             = 10     # sessions to look back for breakout failures
    MG_FATIGUE_FAIL_RATE          = 0.6    # >60% failure â†’ fatigue mode
    MG_FATIGUE_POSITION_SCALE     = 0.75   # position scale cap in fatigue mode
    # Trend structure confirmation â€” signal only passes when price > EMA20 AND price > EMA50
    MG_TREND_CONFIRM_ENABLED = True
    MG_TREND_CONFIRM_SPANS   = (20, 50)   # (fast_ema_span, slow_ema_span)
    # â”€â”€ Alpha Monitor (Module 3) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    AM_MIN_TRADES          = 10     # minimum resolved trades before warnings
    AM_LEVEL1_SHARPE       = 0.5    # Sharpe below this â†’ Level 1
    AM_LEVEL2_SHARPE       = 0.2    # Sharpe below this â†’ Level 2
    AM_LEVEL3_SHARPE       = 0.0    # Sharpe at/below this â†’ Level 3
    AM_LEVEL1_EXPECTANCY   = 0.0    # expectancy below this â†’ Level 1
    AM_LEVEL1_WINRATE      = 0.35   # win rate below this â†’ Level 1
    AM_LEVEL2_WINRATE      = 0.25   # win rate below this â†’ Level 2
    AM_LEVEL3_EXPECTANCY   = -0.02  # expectancy below this â†’ Level 3

    # â”€â”€ Position Manager (Module 4) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PM_MAX_ADDONS_PER_POSITION = 1      # max add-ons per trade
    PM_ADDON_R                 = 0.5    # add-on size in R units
    PM_MAX_EXPOSURE_R          = 2.0    # hard ceiling: initial(1R) + addon(0.5R) = 1.5R max
    PM_ADD_MIN_PROFIT_PCT      = 3.0    # minimum open profit % to qualify
    PM_ADD_MIN_ADX             = 30.0   # minimum ADX
    PM_ADD_MIN_MOMENTUM        = 2.0    # minimum momentum score
    PM_ADDON_STOP_ATR_MULT     = 0.5    # add-on stop = current_price - (ATR Ã— this)

    # â”€â”€ Scan / Runner
    CACHE_TTL_SECONDS        = 3600
    MARKET_BREADTH_THRESHOLD = 0.45
    SCAN_MAX_WORKERS         = 8
    MARKET_BULL_STACKED_MIN  = 0.35
    MARKET_BEAR_BREADTH_MAX  = 0.45
    INDICATOR_CACHE_ENABLED  = True  # Can be disabled for debugging

    # â”€â”€ Scoring
    CPI_FLOOR   = 0.1
    MOM_NORM_LO = -3.0
    MOM_NORM_HI =  6.0
    QUANTILE_NORM_ENABLED = False

    # â”€â”€ [P3-G2] RR Bonus â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    RR_BONUS_ENABLED     = False
    RR_BONUS_THRESHOLD   = 3.0
    RR_BONUS_AMOUNT      = 0.0

    # â”€â”€ Risk
    ATR_INTRADAY_THRESH = 1.5

    # â”€â”€ Outcomes
    OUTCOME_STALE_MULTIPLIER = 2


_SR_WEIGHT_SUM = (
    K.SR_W_FLOW + K.SR_W_STRUCTURE + K.SR_W_TIMING +
    K.SR_W_MOMENTUM + K.SR_W_REGIME + K.SR_W_NEURAL
)
assert abs(_SR_WEIGHT_SUM - 1.0) < 1e-9, (
    f"SmartRank weights must sum to 1.0, got {_SR_WEIGHT_SUM}"
)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SECTORS & SYMBOLS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

SECTORS: Dict[str, List[str]] = {
    "BANKS":       ["COMI", "CIEB", "ADIB", "SAUD", "CNFN", "FAIT"],
    "REAL_ESTATE": ["TMGH", "PHDC", "OCDI", "HELI", "DSCW"],
    "INDUSTRIAL":  ["ORAS", "SKPC", "KZPC", "AMOC", "ESRS"],
    "SERVICES":    ["FWRY", "ETEL", "JUFO", "HRHO", "EGTS", "ORWE"],
    "ENERGY":      ["ABUK", "MFPC", "ISPH", "EAST", "SWDY"],
}
ALL_SYMS = sorted({s for lst in SECTORS.values() for s in lst})
SYMBOLS  = {s: f"{s}.CA" for s in ALL_SYMS}   # EGX Yahoo suffix

_SECTOR_LOOKUP: Dict[str, str] = {
    sym: sec for sec, syms in SECTORS.items() for sym in syms
}
DECISION_PRIORITY = {"ultra": 0, "early": 1, "buy": 2, "watch": 3, "sell": 4}


def get_sector(sym: str) -> str:
    return _SECTOR_LOOKUP.get(sym, "OTHER")


# â”€â”€ Live account/risk setting accessors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DATA_SOURCE_CFG: Dict[str, object] = {
    "alpha_vantage_key":  "",
    "use_yahoo":          True,
    "use_stooq":          True,
    "use_alpha_vantage":  False,
    "use_investing":      True,
    "use_twelve_data":    False,
    "twelve_data_key":    "",
    # â”€â”€ Account / Risk settings (editable from UI) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "account_size":       10_000.0,
    "risk_per_trade":     0.01,
    "portfolio_max_atr_exposure": 0.04,
    "portfolio_max_per_sector":   2,
}
_data_cfg_lock        = threading.Lock()

SOURCE_SETTINGS_FILE = "source_settings.json"


def get_account_size() -> float:
    with _data_cfg_lock:
        return float(DATA_SOURCE_CFG.get("account_size", K.ACCOUNT_SIZE))


def get_risk_per_trade() -> float:
    with _data_cfg_lock:
        return float(DATA_SOURCE_CFG.get("risk_per_trade", K.RISK_PER_TRADE))


def get_atr_exposure() -> float:
    with _data_cfg_lock:
        return float(DATA_SOURCE_CFG.get("portfolio_max_atr_exposure", K.PORTFOLIO_MAX_ATR_EXPOSURE))


def get_max_per_sector() -> int:
    with _data_cfg_lock:
        return int(DATA_SOURCE_CFG.get("portfolio_max_per_sector", K.PORTFOLIO_MAX_PER_SECTOR))


__all__ = [
    "C",
    "K",
    "F_TITLE",
    "F_HEADER",
    "F_BODY",
    "F_SMALL",
    "F_MICRO",
    "SECTORS",
    "SYMBOLS",
    "DECISION_PRIORITY",
    "DATA_SOURCE_CFG",
    "_data_cfg_lock",
    "SOURCE_SETTINGS_FILE",
    "get_sector",
    "get_account_size",
    "get_risk_per_trade",
    "get_atr_exposure",
    "get_max_per_sector",
]
```

==================================================
FILE: egx_radar/core/__init__.py
================================

```python
"""Core computation layer: indicators, scoring, signals, risk, portfolio."""

import logging

log = logging.getLogger(__name__)

from egx_radar.core.indicators import (
    safe_clamp,
    last_val,
    compute_atr,
    compute_atr_risk,
    compute_vwap_dist,
    compute_vol_zscore,
    detect_ema_cross,
    detect_vol_divergence,
    compute_ud_ratio,
    detect_vcp,
    sharpe_from_trades,
)

from egx_radar.core.scoring import (
    _norm,
    score_capital_pressure,
    score_institutional_entry,
    score_whale_footprint,
    score_flow_anticipation,
    score_quantum,
    score_gravity,
    score_tech_signal,
    smart_rank_score,
)

from egx_radar.core.signals import (
    detect_market_regime,
    detect_phase,
    detect_predictive_zone,
    build_signal,
    build_signal_reason,
    get_signal_direction,
)

from egx_radar.core.risk import (
    build_trade_plan,
    institutional_confidence,
    compute_dynamic_stop,
)

from egx_radar.core.portfolio import (
    GuardedResult,
    compute_portfolio_guard,
)

from egx_radar.core.signal_engine import (
    apply_regime_gate,
    compute_adx_value,
    compute_rsi_value,
    detect_conservative_market_regime,
    evaluate_symbol_snapshot,
)
from egx_radar.core.accumulation import evaluate_accumulation_context

from egx_radar.core.data_guard import DataGuard, DataGuardResult

__all__ = [
    # indicators
    "safe_clamp",
    "last_val",
    "compute_atr",
    "compute_atr_risk",
    "compute_vwap_dist",
    "compute_vol_zscore",
    "compute_ud_ratio",
    "detect_vcp",
    "detect_ema_cross",
    "detect_vol_divergence",
    "sharpe_from_trades",
    # scoring
    "_norm",
    "score_capital_pressure",
    "score_institutional_entry",
    "score_whale_footprint",
    "score_flow_anticipation",
    "score_quantum",
    "score_gravity",
    "score_tech_signal",
    "smart_rank_score",
    # signals
    "detect_market_regime",
    "detect_phase",
    "detect_predictive_zone",
    "build_signal",
    "build_signal_reason",
    "get_signal_direction",
    # risk
    "build_trade_plan",
    "institutional_confidence",
    # portfolio
    "GuardedResult",
    "compute_portfolio_guard",
    "compute_adx_value",
    "compute_rsi_value",
    "evaluate_symbol_snapshot",
    "detect_conservative_market_regime",
    "apply_regime_gate",
    "evaluate_accumulation_context",
    # data guard
    "DataGuard",
    "DataGuardResult",
]
```

==================================================
FILE: egx_radar/core/accumulation.py
====================================

```python
from __future__ import annotations

"""Accumulation detection primitives for EGX position trading."""

from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

from egx_radar.config.settings import K
from egx_radar.core.indicators import safe_clamp


def _last(series: pd.Series, default: float = 0.0) -> float:
    data = pd.Series(series).dropna()
    return float(data.iloc[-1]) if not data.empty else default


def _norm_score(value: float, low: float, high: float, inverse: bool = False) -> float:
    if high <= low:
        return 0.0
    clipped = safe_clamp((value - low) / (high - low), 0.0, 1.0)
    return round((1.0 - clipped if inverse else clipped) * 100.0, 2)


def _slope_pct(series: pd.Series, bars: int) -> float:
    window = pd.Series(series).dropna().tail(bars)
    if len(window) < max(3, bars):
        return 0.0
    x = np.arange(len(window), dtype=float)
    slope = float(np.polyfit(x, window.astype(float).values, 1)[0])
    base = max(float(window.mean()), 1e-9)
    return (slope / base) * 100.0


def _support_slope_pct(low: pd.Series, window: int) -> float:
    supports = low.tail(window).rolling(3, min_periods=3).min().dropna()
    if len(supports) < 3:
        return 0.0
    return _slope_pct(supports, len(supports))


def _compression_profile(df: pd.DataFrame, price: float) -> Dict[str, float]:
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    candidates: List[Dict[str, float]] = []

    for window in range(K.ACCUM_COMPRESSION_MIN_DAYS, K.ACCUM_COMPRESSION_MAX_DAYS + 1):
        if len(df) < window + 5:
            continue
        w_high = float(high.tail(window).max())
        w_low = float(low.tail(window).min())
        range_pct = ((w_high - w_low) / max(price, 1e-9)) * 100.0

        recent_span = max(3, window // 2)
        recent_vol = float(close.tail(recent_span).pct_change(fill_method=None).std() or 0.0)
        prior_slice = close.tail(window).iloc[:-recent_span]
        prior_vol = float(prior_slice.pct_change(fill_method=None).std() or 0.0)
        contraction_ratio = recent_vol / max(prior_vol, 1e-6)

        range_score = _norm_score(range_pct, K.ACCUM_COMPRESSION_RANGE_MAX_PCT, 14.0, inverse=True)
        contraction_score = _norm_score(contraction_ratio, 0.70, 1.25, inverse=True)
        position_in_range = safe_clamp((price - w_low) / max(w_high - w_low, 1e-9), 0.0, 1.0)
        location_score = _norm_score(abs(position_in_range - 0.72), 0.0, 0.42, inverse=True)

        total = range_score * 0.50 + contraction_score * 0.35 + location_score * 0.15
        candidates.append(
            {
                "window": float(window),
                "range_pct": round(range_pct, 2),
                "contraction_ratio": round(contraction_ratio, 3),
                "position_in_range": round(position_in_range, 3),
                "compression_score": round(total, 2),
                "base_low": round(w_low, 3),
                "base_high": round(w_high, 3),
            }
        )

    if not candidates:
        return {
            "window": float(K.ACCUM_COMPRESSION_MIN_DAYS),
            "range_pct": 99.0,
            "contraction_ratio": 2.0,
            "position_in_range": 0.0,
            "compression_score": 0.0,
            "base_low": price,
            "base_high": price,
        }
    return max(candidates, key=lambda item: item["compression_score"])


def _up_down_volume_ratio(close: pd.Series, volume: pd.Series, window: int) -> float:
    close_tail = close.tail(window)
    vol_tail = volume.tail(window)
    delta = close_tail.diff().fillna(0.0)
    up_vol = float(vol_tail[delta >= 0].mean() or 0.0)
    down_vol = float(vol_tail[delta < 0].mean() or 0.0)
    if down_vol <= 1e-6:
        return 2.0 if up_vol > 0 else 1.0
    return up_vol / down_vol


def _volume_variation_ratio(volume: pd.Series, window: int) -> float:
    vol_tail = volume.tail(window)
    mean = float(vol_tail.mean() or 0.0)
    std = float(vol_tail.std() or 0.0)
    return std / max(mean, 1e-6)


def _count_large_gain_days(close: pd.Series, threshold_pct: float, lookback: int) -> int:
    gains = close.pct_change(fill_method=None).tail(lookback).fillna(0.0) * 100.0
    return int((gains >= threshold_pct).sum())


def evaluate_accumulation_context(
    df_ta: pd.DataFrame,
    *,
    price: float,
    ema20: float,
    ema50: float,
    ema200: float,
    ema20_slope_pct: float,
    ema50_slope_pct: float,
    ema200_slope_pct: float,
    rsi: float,
    adx: float,
    avg_turnover: float,
    spread_pct: float,
    avg_vol: float,
    vol_ratio: float,
    vol_zscore: float,
) -> Dict[str, float]:
    close = df_ta["Close"].astype(float)
    open_ = df_ta["Open"].astype(float)
    high = df_ta["High"].astype(float)
    low = df_ta["Low"].astype(float)
    volume = df_ta["Volume"].fillna(0.0).astype(float)

    compression = _compression_profile(df_ta, price)
    window = int(compression["window"])
    window_high = float(compression["base_high"])
    window_low = float(compression["base_low"])
    prior_highs = high.tail(window).iloc[:-1]
    prior_closes = close.tail(window).iloc[:-1]
    if len(prior_highs) > 0:
        cluster_high = float(prior_highs.quantile(0.75))
        close_ceiling = float(prior_closes.max()) if not prior_closes.empty else cluster_high
        wick_high = float(prior_highs.max())
        minor_resistance = max(close_ceiling, min(wick_high, cluster_high * 1.01))
    else:
        minor_resistance = window_high
    minor_break_pct = ((price / max(minor_resistance, 1e-9)) - 1.0) * 100.0

    rolling_supports = low.tail(window).rolling(3, min_periods=3).min().dropna()
    support_floor = float(rolling_supports.quantile(0.35)) if not rolling_supports.empty else window_low
    support_floor = max(window_low, min(support_floor, price))
    support_slope_pct = _support_slope_pct(low, window)
    higher_lows = support_slope_pct > 0.02 and float(low.tail(3).min()) >= window_low * 1.01
    structure_slope_score = _norm_score(support_slope_pct, 0.0, 0.20)
    ma50_score = 100.0 if price >= ema50 * 0.998 else _norm_score((price / max(ema50, 1e-9)) - 1.0, -0.03, 0.03)
    ema20_score = _norm_score(ema20_slope_pct, -0.10, 0.18)
    ema50_trend_score = _norm_score(ema50_slope_pct, -0.08, 0.15)
    resistance_tightness = _norm_score(abs(minor_break_pct - 0.9), 0.0, K.ACCUM_MAX_MINOR_BREAK_PCT)
    structure_strength = round(
        safe_clamp(
            structure_slope_score * 0.40
            + ma50_score * 0.25
            + ema20_score * 0.20
            + resistance_tightness * 0.15,
            0.0,
            100.0,
        ),
        2,
    )

    volume_5 = float(volume.tail(5).mean() or 0.0)
    volume_20 = float(volume.tail(20).mean() or 0.0)
    volume_10 = float(volume.tail(10).mean() or 0.0)
    gradual_volume_ratio = volume_5 / max(volume_20, 1e-6)
    up_down_ratio = _up_down_volume_ratio(close, volume, window)
    turnover_multiple = avg_turnover / max(K.MIN_TURNOVER_EGP, 1.0)
    volume_variation = _volume_variation_ratio(volume, window)
    erratic_volume = (
        vol_ratio > K.ACCUM_VOL_CONFIRM_MAX
        or volume_variation > K.ACCUM_ERRATIC_VOLUME_CV
        or float(volume.tail(window).max()) > max(volume_20, 1e-6) * K.ANTI_FAKE_ABNORMAL_VOL_RATIO
    )

    turnover_score = _norm_score(turnover_multiple, 1.0, 3.0)
    gradual_volume_score = _norm_score(abs(gradual_volume_ratio - 1.18), 0.0, 0.85, inverse=True)
    up_down_score = _norm_score(up_down_ratio, 0.95, 1.45)
    smooth_volume_score = _norm_score(volume_variation, 0.20, K.ACCUM_ERRATIC_VOLUME_CV, inverse=True)
    volume_quality = round(
        safe_clamp(
            turnover_score * 0.35
            + gradual_volume_score * 0.25
            + up_down_score * 0.25
            + smooth_volume_score * 0.15
            - (20.0 if erratic_volume else 0.0),
            0.0,
            100.0,
        ),
        2,
    )

    range_today_pct = ((float(high.iloc[-1]) - float(low.iloc[-1])) / max(price, 1e-9)) * 100.0
    body_today_pct = abs(float(close.iloc[-1]) - float(open_.iloc[-1])) / max(price, 1e-9) * 100.0
    one_day_gain_pct = close.pct_change(fill_method=None).iloc[-1] * 100.0 if len(close) >= 2 else 0.0
    two_day_gain_pct = ((price / max(float(close.iloc[-3]), 1e-9)) - 1.0) * 100.0 if len(close) >= 3 else one_day_gain_pct
    last_3_days_gain_pct = ((price / max(float(close.iloc[-4]), 1e-9)) - 1.0) * 100.0 if len(close) >= 4 else two_day_gain_pct
    gap_up_pct = ((float(open_.iloc[-1]) / max(float(close.iloc[-2]), 1e-9)) - 1.0) * 100.0 if len(close) >= 2 else 0.0

    sudden_spike = max(one_day_gain_pct, two_day_gain_pct) > K.ACCUM_MAX_2DAY_SPIKE_PCT
    abnormal_candle = range_today_pct > K.ACCUM_ABNORMAL_CANDLE_RANGE_PCT and body_today_pct > K.ACCUM_ABNORMAL_BODY_PCT
    too_many_shock_days = _count_large_gain_days(close, K.ACCUM_MAX_2DAY_SPIKE_PCT, window) >= 2
    fake_move = sudden_spike or abnormal_candle or too_many_shock_days or gap_up_pct > K.MAX_GAP_UP_PCT

    rsi_score = _norm_score(abs(rsi - 52.0), 0.0, 12.0, inverse=True)
    compression_score = float(compression["compression_score"])
    base_position_score = _norm_score(abs(compression["position_in_range"] - 0.72), 0.0, 0.40, inverse=True)
    volatility_score = _norm_score(vol_zscore, 0.2, 2.4, inverse=True)
    accumulation_quality = round(
        safe_clamp(
            compression_score * 0.45
            + rsi_score * 0.20
            + base_position_score * 0.15
            + volatility_score * 0.20
            - (20.0 if fake_move else 0.0),
            0.0,
            100.0,
        ),
        2,
    )

    adx_score = 100.0 - _norm_score(abs(adx - 20.0), 0.0, 15.0)
    ema200_score = _norm_score(ema200_slope_pct, -0.10, 0.18)
    stack_score = 100.0 if price > ema50 > ema200 else 60.0 if price > ema50 and ema50 >= ema200 * 0.99 else 10.0
    stability_score = _norm_score(spread_pct, 0.4, K.MAX_SPREAD_PCT, inverse=True)
    trend_alignment = round(
        safe_clamp(
            stack_score * 0.35
            + ema20_score * 0.20
            + ema50_trend_score * 0.15
            + ema200_score * 0.15
            + adx_score * 0.10
            + stability_score * 0.05,
            0.0,
            100.0,
        ),
        2,
    )

    volume_confirmed = (
        not erratic_volume
        and vol_ratio <= K.ACCUM_VOL_CONFIRM_MAX
        and up_down_ratio >= 0.95
        and (
            vol_ratio >= K.ACCUM_VOL_CONFIRM_MIN
            or (gradual_volume_ratio >= 0.98 and up_down_ratio >= 1.05 and volume_quality >= 58.0)
        )
    )
    risk_anchor = support_floor * 0.995
    base_risk_pct = ((price - risk_anchor) / max(price, 1e-9)) if risk_anchor > 0 else 1.0
    stop_capped = base_risk_pct > K.MAX_STOP_LOSS_PCT
    risk_viable = 0.0 < base_risk_pct <= 0.10

    accumulation_detected = bool(
        not fake_move
        and sum([
            accumulation_quality >= 58.0,
            structure_strength >= 55.0,
            volume_quality >= 52.0,
            trend_alignment >= 52.0,
            higher_lows,
            price >= ema50 * 0.995,
            ema20_slope_pct >= -0.15,
            38.0 <= rsi <= 65.0,
        ]) >= 6
    )
    break_confirmed = minor_break_pct > 0.0
    trigger_price = minor_resistance * 1.001
    entry_ready = bool(
        accumulation_detected
        and -K.ACCUM_PREBREAK_BUFFER_PCT <= minor_break_pct <= K.ACCUM_MAX_MINOR_BREAK_PCT
        and volume_confirmed
        and risk_viable
    )

    return {
        "accumulation_quality_score": accumulation_quality,
        "structure_strength_score": structure_strength,
        "volume_quality_score": volume_quality,
        "trend_alignment_score": trend_alignment,
        "compression_window": window,
        "compression_range_pct": float(compression["range_pct"]),
        "compression_score": compression_score,
        "contraction_ratio": float(compression["contraction_ratio"]),
        "position_in_range": float(compression["position_in_range"]),
        "support_slope_pct": round(support_slope_pct, 4),
        "higher_lows": bool(higher_lows),
        "gradual_volume_ratio": round(gradual_volume_ratio, 3),
        "up_down_volume_ratio": round(up_down_ratio, 3),
        "volume_variation_ratio": round(volume_variation, 3),
        "turnover_multiple": round(turnover_multiple, 3),
        "minor_resistance": round(minor_resistance, 3),
        "trigger_price": round(trigger_price, 3),
        "minor_break_pct": round(minor_break_pct, 2),
        "base_low": round(support_floor, 3),
        "base_wick_low": round(window_low, 3),
        "base_high": round(window_high, 3),
        "volume_confirmed": bool(volume_confirmed),
        "erratic_volume": bool(erratic_volume),
        "abnormal_candle": bool(abnormal_candle),
        "sudden_spike": bool(sudden_spike),
        "fake_move": bool(fake_move),
        "one_day_gain_pct": round(one_day_gain_pct, 2),
        "two_day_gain_pct": round(two_day_gain_pct, 2),
        "last_3_days_gain_pct": round(last_3_days_gain_pct, 2),
        "gap_up_pct": round(gap_up_pct, 2),
        "range_today_pct": round(range_today_pct, 2),
        "body_today_pct": round(body_today_pct, 2),
        "avg_vol_5": round(volume_5, 2),
        "avg_vol_10": round(volume_10, 2),
        "avg_vol_20": round(volume_20, 2),
        "base_risk_pct": round(base_risk_pct, 4),
        "risk_viable": bool(risk_viable),
        "stop_capped": bool(stop_capped),
        "accumulation_detected": accumulation_detected,
        "break_confirmed": bool(break_confirmed),
        "entry_ready": entry_ready,
    }


__all__ = ["evaluate_accumulation_context"]
```

==================================================
FILE: egx_radar/core/alpha_monitor.py
=====================================

```python
"""Alpha Monitor: session-level edge quality tracker (Module 3).

Reads resolved trade history and computes rolling performance metrics
to detect strategy degradation. Stateless per call â€” no locks needed.
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Result type
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class AlphaStatus:
    """Session-level edge quality assessment."""
    warning_level: int                # 0â€“3
    position_scale: float             # 1.0 | 0.75 | 0.50 | 0.0
    rank_threshold_boost: int         # 0 | 5 | 10
    pause_new_entries: bool
    metrics_20: dict                  # computed metrics for last 20 trades
    metrics_50: dict                  # computed metrics for last 50 trades
    stability_score: float            # 0â€“1
    setup_breakdown: dict             # {setup_type: {win_rate, n, expectancy}}
    message: str
    flags: list


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Monitor implementation
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
            log.info("[AlphaMonitor] History file not found (first session?) â€” returning empty.")
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
            Warning level (0â€“3), scaling, and diagnostics.
        """
        trades = self.load_history()

        # â”€â”€ Insufficient data guard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                message=f"Only {len(trades)} resolved trades â€” need {K.AM_MIN_TRADES}",
                flags=[flag],
            )

        # â”€â”€ Compute windowed metrics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        last_20 = trades[-20:] if len(trades) >= 20 else trades
        last_50 = trades[-50:] if len(trades) >= 50 else trades

        m20 = self._compute_metrics(last_20)
        m50 = self._compute_metrics(last_50)

        # â”€â”€ Warning levels (based on 20-window) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        flags: List[str] = []
        warning_level = 0
        position_scale = 1.0
        rank_boost = 0
        pause = False

        sharpe_20 = m20["sharpe"]
        wr_20 = m20["win_rate"]
        exp_20 = m20["expectancy"]

        # Level 3 (most severe â€” checked first to allow override)
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

        # â”€â”€ Stability score â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sharpe_50 = m50["sharpe"]
        wr_50 = m50["win_rate"]
        sharpe_drift = abs(sharpe_20 - sharpe_50)
        wr_drift = abs(wr_20 - wr_50)
        stability = max(0.0, 1.0 - (sharpe_drift * 0.2) - (wr_drift * 1.0))

        if stability < 0.5:
            flags.append(f"UNSTABLE({stability:.2f})")

        # â”€â”€ Setup breakdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        setup_breakdown = self._compute_setup_breakdown(trades)

        # â”€â”€ Build message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
                message=f"Only {len(valid)} valid trades â€” need {K.AM_MIN_TRADES}",
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
```

==================================================
FILE: egx_radar/core/data_guard.py
==================================

```python
"""Data Guard â€” pre-scoring data quality layer (Module 1).

Validates each symbol's OHLCV DataFrame *before* it enters the indicator /
scoring pipeline.  Catches broken candles, volume anomalies, and
insufficient bar counts, then computes a composite **data confidence**
score (0â€“100) with three tiers:

    FULL      (â‰¥ 65)  â†’ full signal allowed
    DEGRADED  (40â€“64) â†’ signal capped at WATCH maximum
    REJECTED  (< 40)  â†’ symbol skipped entirely
"""

import datetime as _dt
import logging
import math
from typing import NamedTuple

import pandas as pd

from egx_radar.config.settings import K

log = logging.getLogger(__name__)


# â”€â”€ Trading day calculations (Phase 3) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _egx_trading_days_since(last_date: _dt.date) -> int:
    """Count EGX trading days (Sundayâ€“Thursday) elapsed since last_date.

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


# â”€â”€ Result container â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class DataGuardResult(NamedTuple):
    """Immutable result of a DataGuard evaluation."""
    passed: bool             # False only when tier == "REJECTED"
    confidence: float        # 0â€“100
    confidence_tier: str     # "FULL" | "DEGRADED" | "REJECTED"
    reason: str              # human-readable summary


# â”€â”€ Main class â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class DataGuard:
    """Stateless data-quality gate.  One instance per call is fine."""

    # â”€â”€ 1. Candle Integrity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @staticmethod
    def check_candle_integrity(df: pd.DataFrame) -> tuple:
        """Return (score_0_to_1, bad_bar_pct, details_str).

        Checks per bar:
          â€¢ High < Low                         (inverted bar)
          â€¢ Open > High or Open < Low          (open outside range)
          â€¢ Close > High or Close < Low        (close outside range)
          â€¢ body==0 AND range==0 AND volume==0 (null candle)
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

        # Each bar can have multiple issues â€” count unique bad bars
        bad = (
            (h < l)
            | (o > h) | (o < l)
            | (c > h) | (c < l)
            | (((c - o).abs() < 1e-9) & ((h - l).abs() < 1e-9) & (v <= 0))
        ).sum()

        bad_pct = bad / n
        # Score: 1.0 when 0% bad, 0.0 when â‰¥ limit
        score = max(0.0, 1.0 - bad_pct / K.DG_CANDLE_BAD_PCT_LIMIT)

        details = (
            f"{bad}/{n} bad bars ({bad_pct:.1%}) â€” "
            f"inverted={inverted}, open_oob={open_oob}, "
            f"close_oob={close_oob}, null={null_candle}"
        )
        return score, bad_pct, details

    # â”€â”€ 2. Volume Anomaly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ 3. Bar-count Sufficiency â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @staticmethod
    def _bar_sufficiency_score(df: pd.DataFrame) -> float:
        """0â€“1 score: 1.0 when bar count â‰¥ DG_IDEAL_BARS, linearly down."""
        n = len(df)
        if n <= 0:
            return 0.0
        return min(1.0, n / K.DG_IDEAL_BARS)

    # â”€â”€ 4. Consecutive Zero-Volume Days â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ 5. Data Staleness (Last Bar Date vs Today) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @staticmethod
    def check_data_staleness(df: pd.DataFrame, max_lag_days: int = None) -> tuple:
        """Return (score_0_to_1, lag_days, details_str).

        Computes the number of TRADING days (Sunâ€“Thu) between the last bar's 
        date and today. Accounts for EGX holidays using a one-day-per-week buffer.

        EGX trades Sunâ€“Thu. A one-week holiday buffer allows for one public
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
            details = f"last bar {lag} trading day(s) ago â€” OK"
        else:
            # Linear penalty: score=0.5 at 2x lag, score=0.0 at 4x lag
            score = max(0.0, 1.0 - (lag - max_lag_days) / (max_lag_days * 2))
            details = f"last bar {lag} trading day(s) ago â€” STALE (limit={max_lag_days})"

        return score, lag, details

    # â”€â”€ 6. Composite Confidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ 7. Top-level Evaluator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def evaluate(self, df: pd.DataFrame, sym: str) -> DataGuardResult:
        """Run all checks and return a :class:`DataGuardResult`.

        Tier logic:
            confidence â‰¥ 65  â†’ FULL      (all signals allowed)
            confidence 40â€“64 â†’ DEGRADED  (cap signal at WATCH)
            confidence < 40  â†’ REJECTED  (skip symbol)
        """
        confidence, c_detail, v_detail = self.compute_confidence(df)

        # Staleness: integrate into confidence score (not just post-hoc override)
        stale_score, lag_days, stale_detail = self.check_data_staleness(df)
        if stale_score < 1.0:
            confidence *= stale_score
        if lag_days > K.DG_MAX_DATA_LAG_DAYS:
            log.warning("DataGuard %s: stale data â€” %s", sym, stale_detail)
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
            "DataGuard %s â†’ conf=%.1f tier=%s | %s | %s",
            sym, confidence, tier, c_detail, v_detail,
        )

        return DataGuardResult(
            passed=passed,
            confidence=confidence,
            confidence_tier=tier,
            reason=reason,
        )


__all__ = ["DataGuard", "DataGuardResult"]
```

==================================================
FILE: egx_radar/core/indicators.py
==================================

```python
"""Technical indicator functions for EGX Radar."""

import logging
import pandas as pd
from typing import Optional, Tuple
from egx_radar.config.settings import K


log = logging.getLogger(__name__)


def safe_clamp(val: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, val))


def last_val(s: pd.Series) -> float:
    """Get the last value from a series."""
    s = s.dropna()
    return float(s.iloc[-1]) if not s.empty else 0.0


def compute_atr(df: pd.DataFrame, length: int = 14) -> Optional[float]:
    """Compute ATR (Average True Range)."""
    if length is None:
        length = K.ATR_LENGTH
    if len(df) < 2:
        return None
    try:
        h = df["High"].reset_index(drop=True)
        l = df["Low"].reset_index(drop=True)
        c = df["Close"].reset_index(drop=True)
        tr = pd.concat([
            h - l,
            (h - c.shift()).abs(),
            (l - c.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = float(tr.tail(length).mean())
        return atr if (atr is not None and atr > 0) else None
    except Exception as exc:
        log.debug("compute_atr failed for input: %s", exc)
        return None


def compute_atr_risk(df: pd.DataFrame, price: float) -> Tuple[str, float]:
    """Compute ATR percentile-based risk scoring."""
    if price <= 0 or len(df) < K.ATR_LENGTH + 5:
        return "â€”", 0.0
    try:
        h = df["High"].reset_index(drop=True)
        l = df["Low"].reset_index(drop=True)
        c = df["Close"].reset_index(drop=True)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr_series = tr.rolling(K.ATR_LENGTH).mean().dropna()
        if len(atr_series) < 5:
            return "â€”", 0.0
        hist = atr_series.iloc[-K.ATR_HIST_WINDOW:].values
        current = hist[-1]

        # ATR normalization: compare percentage ATR, not raw points.
        # Raw ATR cannot be compared across stocks at different price levels.
        # A 2-point ATR on a 10 EGP stock (20%) is very different from
        # a 2-point ATR on a 100 EGP stock (2%).
        if getattr(K, "ATR_NORMALIZE_BY_PRICE", True) and price > 0:
            hist    = hist / price * 100.0   # convert each historical ATR to % of price
            current = current / price * 100.0

        pct = float((hist <= current).mean()) * 100.0
        if pct >= K.ATR_PCT_HIGH:
            return "âš ï¸ HIGH", pct
        if pct >= K.ATR_PCT_MED:
            return "ðŸŸ¡ MED", pct
        return "ðŸŸ¢ LOW", pct
    except Exception as exc:
        log.debug("compute_atr_risk failed for input: %s", exc)
        return "â€”", 0.0


def compute_vwap_dist(df: pd.DataFrame, price: float) -> float:
    """VWAP distance = (price - vwap) / price. Clamped to (-0.5, 0.5)."""
    try:
        close = df["Close"].dropna()
        vol = df["Volume"].dropna()
        if len(close) < 10 or vol.sum() <= 0:
            return 0.0
        n = min(len(close), len(vol), K.VWAP_ROLL_WINDOW)
        close, vol = close.iloc[-n:], vol.iloc[-n:]
        cum_vol = vol.cumsum()
        if cum_vol.iloc[-1] <= 0:
            return 0.0
        vwap = float((close * vol).cumsum().iloc[-1] / cum_vol.iloc[-1])
        return safe_clamp((price - vwap) / price, -0.5, 0.5) if vwap > 0 else 0.0
    except Exception as exc:
        log.debug("compute_vwap_dist failed for input: %s", exc)
        return 0.0


def compute_vol_zscore(df: pd.DataFrame, window: int = None) -> float:
    """Compute volume Z-score with symmetric clamp."""
    if window is None:
        window = K.VOL_ROLL_WINDOW
    try:
        vol = df["Volume"].dropna()
        if vol.sum() <= 0 or len(vol) < window + 2:
            return 0.0
        mu = float(vol.rolling(window).mean().iloc[-1])
        sig = float(vol.rolling(window).std().iloc[-1])
        if sig <= 0:
            return 0.0
        return safe_clamp((float(vol.iloc[-1]) - mu) / sig, K.VOL_ZSCORE_LO, K.VOL_ZSCORE_HI)
    except Exception as exc:
        log.debug("compute_vol_zscore failed for input: %s", exc)
        return 0.0


def detect_ema_cross(close: pd.Series) -> str:
    """Detect EMA10/EMA50 crossover."""
    if len(close) < 55:
        return ""
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    for i in range(-7, 0):
        prev = ema10.iloc[i-1] > ema50.iloc[i-1]
        curr = ema10.iloc[i] > ema50.iloc[i]
        if not prev and curr:
            return "BULL_CROSS"
        if prev and not curr:
            return "BEAR_CROSS"
    return ""


def detect_vol_divergence(close: pd.Series, volume: pd.Series, lookback: int = 5) -> str:
    """Detect volume/price divergence patterns."""
    if len(close) < lookback + 2:
        return ""
    price_chg = float(close.iloc[-1]) - float(close.iloc[-lookback])
    vol_ma = volume.rolling(3).mean()
    if len(vol_ma.dropna()) < lookback:
        return ""
    vol_trend = float(vol_ma.iloc[-1]) - float(vol_ma.iloc[-lookback])
    if price_chg > 0 and vol_trend > 0:
        return "ðŸŸ¢BULL_CONF"
    if price_chg > 0 and vol_trend < 0:
        return "ðŸ”€BEAR_DIV"
    if price_chg < 0 and vol_trend < 0:
        return "ðŸ”µBASE"
    if price_chg < 0 and vol_trend > 0:
        return "âš ï¸CLIMAX_SELL"
    return ""


def compute_ud_ratio(close: pd.Series, period: int = 14) -> float:
    """Compute a true up/down ratio around 1.0, not an RSI value."""
    try:
        if isinstance(close, pd.DataFrame):
            if "Close" in close.columns:
                close = close["Close"]
            else:
                close = close.iloc[:, 0]
        close = pd.Series(close).astype(float).dropna()
        if len(close) < period + 1:
            return 1.0
        delta = close.diff()
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        avg_gain_val = float(avg_gain.iloc[-1])
        avg_loss_val = float(avg_loss.iloc[-1])
        if avg_gain_val <= 1e-9 and avg_loss_val <= 1e-9:
            return 1.0
        if avg_loss_val <= 1e-9:
            return 3.0
        return safe_clamp(avg_gain_val / avg_loss_val, 0.0, 3.0)
    except Exception as exc:
        log.debug("compute_ud_ratio failed for input: %s", exc)
        return 1.0


def detect_vcp(df: pd.DataFrame, lookback: int = 20) -> bool:
    """Detect Volatility Contraction Pattern (VCP)."""
    try:
        if len(df) < lookback:
            return False
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        
        # Calculate recent volatility
        recent_vol = close.pct_change().rolling(lookback).std()
        
        # Find contraction (lower volatility than average)
        avg_vol = recent_vol.mean()
        current_vol = recent_vol.iloc[-1]
        
        if current_vol < avg_vol * 0.7:  # 30% contraction
            return True
        return False
    except Exception as exc:
        log.debug("detect_vcp failed for input: %s", exc)
        return False


def compute_cmf(df: pd.DataFrame, period: int = None) -> float:
    """Chaikin Money Flow indicator."""
    import numpy as np
    if period is None:
        period = K.CMF_PERIOD
    
    if df is None or len(df) < period:
        return 0.0
    
    try:
        high  = df["High"].values[-period:]
        low   = df["Low"].values[-period:]
        close = df["Close"].values[-period:]
        volume = df["Volume"].values[-period:]
        
        denom = high - low
        denom = np.where(denom == 0, 1e-9, denom)
        
        mfm = ((close - low) - (high - close)) / denom
        mfv = mfm * volume
        
        cmf = mfv.sum() / volume.sum() if volume.sum() > 0 else 0.0
        return round(float(cmf), 4)
    except Exception as exc:
        log.debug("compute_cmf failed for input: %s", exc)
        return 0.0


def sharpe_from_trades(trades: list, risk_free_rate: float = None) -> float:
    """Calculate Sharpe ratio from trade returns."""
    import numpy as np
    try:
        # Handle both list of dicts AND list of floats
        if not trades:
            return 0.0
        
        if isinstance(trades[0], dict):
            returns = [t.get("pnl_pct", 0) for t in trades]
        else:
            returns = [float(t) for t in trades]
        
        arr = np.array(returns) / 100
        if arr.std() == 0:
            return 0.0
        rf_daily = (K.RISK_FREE_ANNUAL_PCT / K.TRADING_DAYS_PER_YEAR / 100) if risk_free_rate is None else risk_free_rate
        return round(float((arr.mean() - rf_daily) / arr.std() * np.sqrt(K.TRADING_DAYS_PER_YEAR)), 2)
    except Exception as exc:
        log.debug("sharpe_from_trades failed for input: %s", exc)
        return 0.0


def pct_change_safe(current: float, previous: float) -> float:
    """Calculate percentage change safely, avoiding division by zero."""
    if previous is None or previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


# â”€â”€ ATR shrinking check (the function that was causing the bug) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def is_atr_shrinking(df: pd.DataFrame, length: int = None, bars: int = 5) -> bool:
    """Check if ATR has been shrinking for the last `bars`.
    length defaults to K.ATR_LENGTH only when the caller does not supply it.
    """
    if length is None:
        length = K.ATR_LENGTH
    try:
        if len(df) < length + bars:
            return False
        h = df["High"].reset_index(drop=True)
        l = df["Low"].reset_index(drop=True)
        c = df["Close"].reset_index(drop=True)
        tr = pd.concat([
            h - l,
            (h - c.shift()).abs(),
            (l - c.shift()).abs(),
        ], axis=1).max(axis=1)
        atr_series = tr.rolling(length).mean().dropna()
        if len(atr_series) < bars:
            return False
        
        # checks if atr[i] - atr[i-1] < 0 for the last `bars-1` diffs
        return (atr_series.tail(bars).diff().dropna() < 0).all()

    except Exception as exc:
        log.debug("is_atr_shrinking failed for input: %s", exc)
        return False


def compute_liquidity_shock(
    df: pd.DataFrame,
    atr: Optional[float],
    avg_volume: float,
) -> float:
    """
    Liquidity Shock indicator.
    Measures the strength of a directional volume event relative to ATR.
    High value = strong institutional move. Low value = retail noise.

    Formula: liq_shock = (vol_today / avg_volume) * (|close - open| / ATR)
    Returns a float clamped to [0.0, 5.0].
    """
    try:
        if df is None or len(df) < 2:
            return 0.0
        if avg_volume <= 0 or atr is None or atr <= 0:
            return 0.0
        vol_today = float(df["Volume"].iloc[-1])
        close     = float(df["Close"].iloc[-1])
        open_     = float(df["Open"].iloc[-1])
        vol_ratio = vol_today / (avg_volume + 1e-9)
        body_size = abs(close - open_) / (atr + 1e-9)
        shock = vol_ratio * body_size
        return safe_clamp(shock, 0.0, 5.0)
    except Exception as exc:
        log.debug("compute_liquidity_shock failed: %s", exc)
        return 0.0


def quantile_norm(value: float, series: pd.Series) -> float:
    """Quantile-based normalization: rank of `value` within `series`, mapped to [0, 1].
    More robust than linear normalization for skewed EGX distributions.
    """
    try:
        s = series.dropna()
        if len(s) < 2:
            return 0.5
        rank = float((s < value).sum()) / len(s)
        return safe_clamp(rank, 0.0, 1.0)
    except Exception as exc:
        log.debug("quantile_norm failed: %s", exc)
        return 0.5
```

==================================================
FILE: egx_radar/core/momentum_guard.py
======================================

```python
"""Momentum Guard: persistence, loss cluster, and fatigue detection (Module 2).

Thread-safe â€” the shared MomentumGuard instance uses internal locks for any
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Result type
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Guard implementation
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MomentumGuard:
    """
    Shared, thread-safe momentum quality gate.

    Rules:
      1. Momentum Persistence â€” both today & yesterday must clear a floor.
      2. Loss Cluster Guard  â€” if â‰¥ N stops within recent sessions â†’ defensive.
      3. Market Fatigue      â€” if > X% of recent breakouts failed â†’ fatigue.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (timestamp, symbol) for each stop-loss event
        self._loss_events: List[tuple] = []
        # (timestamp, symbol, followed_through: bool) for breakout tracking
        self._breakout_events: List[tuple] = []

    # â”€â”€ External feeds â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Core evaluation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def evaluate(
        self,
        symbol: str,
        momentum_today: float,
        momentum_yesterday: float,
        adx: float,
        vol_ratio: float,
        df=None,      # optional pd.DataFrame â€” required for trend confirmation
        price=None,   # optional float â€” required for trend confirmation
    ) -> MomentumGuardResult:
        """
        Evaluate momentum quality for *symbol*.

        Parameters
        ----------
        symbol : str
            Ticker being processed.
        momentum_today : float
            Adaptive momentum value for today (already Ã—100).
        momentum_yesterday : float
            Adaptive momentum value for previous bar (already Ã—100).
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

        # â”€â”€ Rule 1: Momentum Persistence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        persistence = min(momentum_today, momentum_yesterday)
        # min(a, b) >= X already implies both a >= X and b >= X
        persistent = persistence >= K.MG_PERSISTENCE_MIN_EACH
        if not persistent:
            flags.append("MOM_NOT_PERSISTENT")
            # Soft downgrade â€” do NOT hard-block
            passed = False

        # â”€â”€ Rule 4: Trend Confirmation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ Rule 2: Loss Cluster Guard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        defensive_mode = False
        with self._lock:
            # Count recent losses within the last N "sessions"
            # Using a time-based window: ~5 sessions â‰ˆ 5 days â‰ˆ 432,000s
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

        # â”€â”€ Exemption threshold (defensive raises the bar) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        exemption_threshold = (
            K.MG_EXEMPTION_THRESHOLD_GUARD if defensive_mode
            else K.MG_EXEMPTION_THRESHOLD_NORMAL
        )

        # â”€â”€ Rule 3: Market Fatigue Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ Build message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
```

==================================================
FILE: egx_radar/core/position_manager.py
========================================

```python
"""Position Manager: open position and add-on logic (Module 4).

Stateless evaluator that reads from the trades log to determine if
an open position exists and if it qualifies for an add-on.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from egx_radar.config.settings import K
from egx_radar.outcomes.engine import oe_load_log, oe_save_log

log = logging.getLogger(__name__)


@dataclass
class AddOnResult:
    """Result of an add-on evaluation for an open position."""
    approved: bool
    symbol: str
    reason: str
    flags: List[str]
    # If approved:
    add_on_r: float = 0.0          # PM_ADDON_R or 0.0
    new_stop_initial: float = 0.0  # Break-even stop for the original position
    new_stop_addon: float = 0.0    # Tighter stop for the add-on
    total_exposure_r: float = 0.0  # Total R after add-on
    profit_pct: float = 0.0        # Open profit % at evaluation time


class PositionManager:
    """
    Stateless evaluator for open positions and add-ons.
    Always reads live data from the trades log file via engine.py.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def get_all_open_positions(self) -> List[dict]:
        """Returns a list of all currently open trades."""
        try:
            trades = oe_load_log()
            return [t for t in trades if t.get("status") == "OPEN"]
        except Exception as e:
            log.error("[PositionManager] Failed to load open positions: %s", e)
            return []

    def get_open_position(self, symbol: str) -> Optional[dict]:
        """Returns the open trade dict for symbol, or None if not open."""
        try:
            trades = oe_load_log()
            for t in trades:
                if t.get("sym") == symbol and t.get("status") == "OPEN":
                    return t
        except Exception as e:
            log.error("[PositionManager] Error getting position for %s: %s", symbol, e)
        return None

    def evaluate_addon(
        self,
        symbol: str,
        current_price: float,
        adx: float,
        momentum: float,
        smart_rank: float,
        smart_rank_threshold: float,
        bearish_divergence: bool,
    ) -> AddOnResult:
        """
        Evaluate whether an add-on is justified for an existing open position.
        Fail-fast condition checks before approval.
        """
        flags = []

        # 1. Position exists?
        trade = self.get_open_position(symbol)
        if trade is None:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="NO_OPEN_POSITION", flags=["NO_OPEN_POSITION"]
            )

        # 2. Already has add-on?
        addon_count = trade.get("addon_count", 0)
        if addon_count >= K.PM_MAX_ADDONS_PER_POSITION:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="MAX_ADDONS_REACHED", flags=["MAX_ADDONS_REACHED"]
            )

        # 3. Exposure limit? (Initial is 1.0R, each addon is PM_ADDON_R)
        current_total_r = 1.0 + (K.PM_ADDON_R * addon_count)
        if current_total_r + K.PM_ADDON_R > K.PM_MAX_EXPOSURE_R:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="MAX_EXPOSURE_EXCEEDED", flags=["MAX_EXPOSURE_EXCEEDED"]
            )

        # 4. Profit threshold?
        entry_price = trade.get("entry", 0.0)
        if entry_price <= 0:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="INVALID_ENTRY_PRICE", flags=["INVALID_ENTRY_PRICE"]
            )
            
        profit_pct = (current_price - entry_price) / entry_price * 100
        if profit_pct < K.PM_ADD_MIN_PROFIT_PCT:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="INSUFFICIENT_PROFIT", flags=["INSUFFICIENT_PROFIT"]
            )

        # 5. ADX strong enough?
        if adx < K.PM_ADD_MIN_ADX:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="WEAK_ADX", flags=["WEAK_ADX"]
            )

        # 6. Momentum strong enough?
        if momentum < K.PM_ADD_MIN_MOMENTUM:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="WEAK_MOMENTUM", flags=["WEAK_MOMENTUM"]
            )

        # 7. No bearish divergence?
        if bearish_divergence:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="BEARISH_DIVERGENCE", flags=["BEARISH_DIVERGENCE"]
            )

        # 8. SmartRank still valid?
        if smart_rank < smart_rank_threshold:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="RANK_BELOW_THRESHOLD", flags=["RANK_BELOW_THRESHOLD"]
            )

        # All conditions pass â†’ approve
        atr = trade.get("atr", 0.0)
        new_stop_initial = entry_price
        new_stop_addon = current_price - (atr * K.PM_ADDON_STOP_ATR_MULT)
        new_total_r = current_total_r + K.PM_ADDON_R

        return AddOnResult(
            approved=True,
            symbol=symbol,
            reason="ADDON_APPROVED",
            flags=["ADDON_APPROVED"],
            add_on_r=K.PM_ADDON_R,
            new_stop_initial=new_stop_initial,
            new_stop_addon=new_stop_addon,
            total_exposure_r=new_total_r,
            profit_pct=profit_pct,
        )

    def confirm_addon(self, symbol: str) -> bool:
        """
        Called after the broker order for the add-on is confirmed.
        Updates the trade in the log.
        """
        with self._lock:
            try:
                trades = oe_load_log()
                for t in trades:
                    if t.get("sym") == symbol and t.get("status") == "OPEN":
                        t["addon_count"] = t.get("addon_count", 0) + 1
                        t["addon_date"] = datetime.now().strftime("%Y-%m-%d")
                        oe_save_log(trades)
                        return True
            except Exception as e:
                log.error("[PositionManager] Failed to confirm addon for %s: %s", symbol, e)
            return False

    def get_open_position_from_list(self, symbol: str, open_trades: List[dict]) -> Optional[dict]:
        """Backtest version â€” reads from provided list instead of oe_load_log()."""
        for t in open_trades:
            if t.get("sym") == symbol and t.get("status") == "OPEN":
                return t
        return None


__all__ = ["PositionManager", "AddOnResult"]
```

==================================================
FILE: egx_radar/core/scoring.py
===============================

```python
"""Scoring engine: component and SmartRank scores (Layer 4)."""

import logging
import math
from typing import Dict, List, Tuple

from egx_radar.config.settings import K
from egx_radar.core.indicators import safe_clamp, quantile_norm

log = logging.getLogger(__name__)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LAYER 4: SCORING ENGINE â€” All component scores normalised 0-1
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


def _norm(val: float, lo: float, hi: float) -> float:
    """Linearly normalise val âˆˆ [lo, hi] â†’ [0, 1]. Clamps outside range."""
    if hi <= lo:
        return 0.0
    return safe_clamp((val - lo) / (hi - lo), 0.0, 1.0)


def score_capital_pressure(
    clv: float, trend_acc: float, vol_ratio: float,
    price: float, ema50: float, vwap_dist: float,
    ud_ratio: float = 1.0, is_vcp: bool = False
) -> float:
    """
    Capital Pressure Index, normalised 0-1.
    Raw CPI components:
      - volume contribution: min(2.0, vol_ratio * 0.9)
      - CLV contribution (if positive): clv * 2.2
      - trend acceleration (if positive): min(1.5, trend_acc * 6.0)
      - EMA50 proximity bonus: 1.2 if within 3%
      - VWAP discount bonus: min(1.0, |vwap_dist| * 4.0) if below VWAP
    Raw range: [0, ~8].  Normalised to [0, 1].
    """
    if getattr(K, "VOL_LOG_SCALE_ENABLED", True):
        # Logarithmic scaling: dampens minor retail spikes, rewards sustained volume
        vol_contrib = min(1.0, math.log1p(max(0.0, vol_ratio)) / K.VOL_LOG_SCALE_DIVISOR)
    else:
        vol_contrib = min(2.0, vol_ratio * 0.9)  # legacy linear fallback
    raw = vol_contrib
    if clv > 0:
        raw += clv * 2.2
    if trend_acc > 0:
        raw += min(1.5, trend_acc * 6.0)
    if ema50 > 0 and abs(price - ema50) / (ema50 + 1e-9) < 0.03:
        raw += 1.2
    if vwap_dist < -0.01:
        raw += min(1.0, abs(vwap_dist) * 4.0)
        
    # Feature 3: Micro-Structure Volume Analysis
    if is_vcp:
        raw += 1.5  # Bonus for volatility contraction
        
    if ud_ratio < 0.7:
        raw -= 1.0  # Softened penalty for down-volume dominance in EGX
    elif ud_ratio > 1.5:
        raw += 1.0  # Bonus for strong up-volume dominance
        
    final_score = _norm(safe_clamp(raw, 0.0, 10.0), 0.0, 10.0)
    # Floor at config minimum so structurally sound stocks don't lose the entire 20% FLOW weight
    return max(K.CPI_FLOOR, final_score)


def score_institutional_entry(
    rsi: float, adx: float, clv: float,
    trend_acc: float, vol_ratio: float, pct_ema200: float
) -> float:
    """
    Institutional Entry Timing score, normalised 0-1.
    Raw components (max 10.0):
      2.0 if RSI 45-60 | 1.5 if ADX < 22 | 2.0 if CLV > 0.45
      2.0 if trend_acc > 0 | 1.5 if vol_ratio 1.0-1.4 | 1.0 if pct_ema200 < 18
    """
    s = 0.0
    if 45 <= rsi <= 60:          s += 2.0
    if adx < 22:                 s += 1.5
    if clv > 0.45:               s += 2.0
    if trend_acc > 0:            s += 2.0
    if 1.0 <= vol_ratio <= 1.4:  s += 1.5
    if pct_ema200 < 18:          s += 1.0
    return _norm(safe_clamp(s, 0.0, 10.0), 0.0, 10.0)


def score_whale_footprint(
    adx: float, clv: float, trend_acc: float, vol_ratio: float, rsi: float
) -> float:
    """
    Whale Footprint score, normalised 0-1.
    Raw max: 9.0.
    """
    s = 0.0
    if adx < 25:                 s += 1.5
    if clv > 0.55:               s += 2.5
    if trend_acc > 0:            s += 2.0
    if vol_ratio > 0.9:          s += 2.0  # Calibrated for lower EGX liquidity
    if rsi < 68:                 s += 1.0
    return _norm(safe_clamp(s, 0.0, 9.0), 0.0, 9.0)


def score_flow_anticipation(
    rsi: float, adx: float, clv: float,
    trend_acc: float, vol_ratio: float, pct_ema200: float
) -> float:
    """
    Flow Anticipation score (forward-looking), normalised 0-1.
    Raw max: 10.5.
    """
    s = 0.0
    if 47 <= rsi <= 60:          s += 2.0
    if adx < 22:                 s += 1.5
    if clv > 0.45:               s += 2.5
    if trend_acc > 0:            s += 2.0
    if 0.9 <= vol_ratio <= 1.3:  s += 1.5
    if pct_ema200 < 18:          s += 1.0
    return _norm(safe_clamp(s, 0.0, 10.5), 0.0, 10.5)


def score_quantum(rsi: float, momentum: float, trend_acc: float, clv: float, vol_ratio: float) -> float:
    """
    Quantum flow convergence score, normalised 0-1.
    Raw max: 5.5.
    """
    q = 0.0
    if 48 <= rsi <= 60:       q += 1.5
    if 0.3 < momentum < 2.0:  q += 1.5
    if trend_acc > 0:         q += 1.0
    if clv > 0.4:             q += 1.0
    if vol_ratio < 1.3:       q += 0.5
    return _norm(safe_clamp(q, 0.0, 5.5), 0.0, 5.5)


def score_gravity(clv: float, trend_acc: float, vol_ratio: float, rsi: float, adaptive_mom: float) -> Tuple[str, float]:
    """Money Flow Gravity. Returns (label, normalised_score 0-1)."""
    g = vol_ratio * 1.2 + clv * 2.5 + trend_acc * 4.0
    if 48 <= rsi <= 62:   g += 2.0
    if adaptive_mom > 0:  g += 1.5
    raw = safe_clamp(g, 0.0, 12.0)
    label = "ðŸ§² HEAVY" if raw >= 8 else ("ðŸ§² BUILDING" if raw >= 5 else "â–«ï¸ LIGHT")
    return label, _norm(raw, 0.0, 12.0)


def score_tech_signal(
    price: float, ema200: float, ema50: float, adx: float, rsi: float,
    adaptive_mom: float, vol_ratio: float, breakout: bool, pct_ema200: float,
) -> int:
    """Raw integer signal score for build_signal(). Not normalised â€” used directly in signal classification."""
    score = 0
    if price > ema200:           score += 3
    elif price > ema200 * 0.97:  score += 1
    if price > ema50:            score += 1
    if adx > K.ADX_STRONG:       score += 2
    elif adx > K.ADX_MID:        score += 1
    if 55 < rsi < 70:            score += 3
    elif 48 <= rsi <= 55:        score += 1
    if adaptive_mom > 2:         score += 3
    elif adaptive_mom > 0:       score += 2
    elif adaptive_mom > -1:      score += 1
    if vol_ratio > 1.5:          score += 2
    elif vol_ratio > 1.2:        score += 1
    if breakout:                 score += 2
    if pct_ema200 > 35:          score -= 2
    return max(0, score)


def smart_rank_score(
    cpi_n: float, iet_n: float, whale_n: float, gravity_n: float,
    quantum_n: float, tech_score: int, trend_acc: float, hidden_score: float,
    adaptive_mom: float, phase: str, zone: str, tag: str,
    silent: bool, hunter: bool, expansion: bool, fake_expansion: bool,
    leader: bool, ema_cross: str, vol_div: str,
    rsi: float, adx: float, pct_ema200: float, vol_ratio: float,
    brain_mode: str, brain_vol_req: float,
    sig_hist: List[str], market_soft: bool,
    nw: Dict[str, float],
    sector_bias: float,
    anticipation_n: float,
    regime: str,
    cmf: float,
    vwap_dist: float,
    vcp_detected: bool,
    price: float,
    clv: float,
    liq_shock: float = 0.0,
    momentum_series=None,   # optional pd.Series of recent cross-sectional momentum values
) -> float:
    """
    FIX-B: Documented SmartRank formula with explicit normalised components.

    SmartRank = Î£(weight_i Ã— component_i) Ã— SMART_RANK_SCALE

    where each component_i âˆˆ [0, 1] and Î£ weights_i = 1.0:

      FLOW (20%):
        flow_component = normalised(vol_ratio^1.3 Ã— max(clv_from_cpi, 0)) Ã— neural_flow
        â†’ captured via cpi_n which already embeds vol + CLV + VWAP

      STRUCTURE (20%):
        structure_component = normalised(tech_score / 14 + trend_acc_n + hidden_n)
        â†’ tech_score max = 14, trend_acc normalised, hidden normalised

      TIMING (20%):
        timing_component = phase/zone/pattern bonuses, normalised to [0,1]

      MOMENTUM (15%):
        momentum_component = normalised(adaptive_mom, -5, +10)

      REGIME (15%):
        regime_component = (iet_n + whale_n + gravity_n) / 3

      NEURAL (10%):
        neural_component = weighted blend of nw values, normalised

    Late-entry penalties are applied as multiplicative dampers (â‰¤ 1.0).
    """
    # â”€â”€ FLOW component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FIX-2.3: Apply neural flow weight and sector bias as real multipliers.
    # Previous code divided out the same factors it multiplied in, yielding
    # flow_n == cpi_n regardless of neural weight or sector bias.
    flow_n = safe_clamp(cpi_n * nw.get("flow", 1.0) * sector_bias, 0.0, 1.0)

    # â”€â”€ STRUCTURE component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tech_n      = _norm(tech_score, 0, 14)
    trend_acc_n = _norm(trend_acc, -0.05, 0.05)
    hidden_n    = _norm(hidden_score, 0.0, 4.0)
    structure_n = safe_clamp(
        (tech_n * 0.5 + trend_acc_n * 0.3 + hidden_n * 0.2) * nw.get("structure", 1.0),
        0.0, 1.0,
    )

    # â”€â”€ TIMING component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    timing_raw = 0.0
    if tag == "ultra":          timing_raw += 0.35
    if silent:                  timing_raw += 0.25
    if hunter:                  timing_raw += 0.15
    if expansion:               timing_raw += 0.10
    if quantum_n > 0.5:         timing_raw += 0.20
    if gravity_n > 0.6:         timing_raw += 0.15
    if zone == "ðŸŸ¢ EARLY":      timing_raw += 0.15
    elif zone == "ðŸ”´ LATE":     timing_raw -= 0.10
    if phase == "Accumulation": timing_raw += 0.10
    if leader:                  timing_raw += 0.20 * nw.get("timing", 1.0)
    if tag == "early" and pct_ema200 < 20: timing_raw += 0.10
    if ema_cross == "BULL_CROSS": timing_raw += 0.15
    elif ema_cross == "BEAR_CROSS": timing_raw -= 0.15
    timing_n = safe_clamp(timing_raw, 0.0, 1.0)

    # â”€â”€ MOMENTUM component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Use quantile normalization when a cross-sectional series is available.
    # This handles EGX's skewed momentum distribution better than linear norm.
    if (
        getattr(K, "QUANTILE_NORM_ENABLED", True)
        and momentum_series is not None
        and len(momentum_series.dropna()) >= 5
    ):
        momentum_n = quantile_norm(adaptive_mom, momentum_series)
    else:
        momentum_n = _norm(adaptive_mom, K.MOM_NORM_LO, K.MOM_NORM_HI)

    # â”€â”€ REGIME component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    regime_n = (iet_n + whale_n + gravity_n) / 3.0

    # â”€â”€ NEURAL component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    nw_avg  = (nw.get("flow", 1.0) + nw.get("structure", 1.0) + nw.get("timing", 1.0)) / 3.0
    neural_n = _norm(nw_avg, K.NEURAL_WEIGHT_MIN, K.NEURAL_WEIGHT_MAX)

    # â”€â”€ Weighted sum â†’ raw rank [0, 1] â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    raw_n = (
        K.SR_W_FLOW      * flow_n      +
        K.SR_W_STRUCTURE * structure_n +
        K.SR_W_TIMING    * timing_n    +
        K.SR_W_MOMENTUM  * momentum_n  +
        K.SR_W_REGIME    * regime_n    +
        K.SR_W_NEURAL    * neural_n
    )

    # Market regime damping â€” generate fewer signals in bear or neutral markets
    if getattr(K, "REGIME_BEAR_DAMPING_ENABLED", True):
        if regime in ("DISTRIBUTION", "BEAR"):
            raw_n *= K.REGIME_BEAR_SCORE_MULT
        elif regime == "NEUTRAL":
            raw_n *= K.REGIME_NEUTRAL_SCORE_MULT

    # [P3-E3] CMF Damping
    if K.CMF_DAMPING_ENABLED and cmf < 0 and vol_ratio < 1.0 and vwap_dist < 0:
        raw_n *= K.CMF_DAMPING_FACTOR

    # [P3-E2] VCP Score Multiplier
    if vcp_detected:
        raw_n *= K.VCP_SCORE_MULTIPLIER

    # â”€â”€ Late-entry penalty damper (multiplicative) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Kept multiplicative so we never go below 0 unnaturally
    
    # Feature: Momentum Acceleration Exemption
    # If a stock demonstrates extreme confirmed momentum, ignore certain late-entry dampers.
    acceleration_condition = (
        adaptive_mom > 2.5 and
        adx > 30 and
        vol_ratio > 1.8 and
        vol_div != "ðŸ”€BEAR_DIV" and
        tag != "sell"
    )

    damper = 1.0
    
    if not acceleration_condition:
        if rsi > 70:                            damper *= 0.85
        if pct_ema200 > 35:                     damper *= 0.85
        if market_soft and tag == "buy":        damper *= 0.88
        if len(sig_hist) >= 3 and all(h == "buy" for h in sig_hist[-3:]):
            damper *= 0.85
            
    # Always apply these structural/distribution penalties
    if fake_expansion:                      damper *= 0.70
    if vol_div == "ðŸ”€BEAR_DIV":             damper *= 0.88
    if vol_div == "âš ï¸CLIMAX_SELL":          damper *= 0.80   # FIX-4: strong distribution signal
    if brain_mode == "defensive" and vol_ratio < brain_vol_req:
        damper *= 0.90

    # Cap the total damping if acceleration is true
    if acceleration_condition:
        damper = max(0.90, damper)

    # â”€â”€ Brain-mode bonus (additive boost on top of penalised raw) â”€â”€â”€â”€â”€â”€â”€â”€â”€
    brain_boost = 0.0
    if brain_mode == "aggressive" and vol_ratio >= brain_vol_req:
        brain_boost = 0.02

    # â”€â”€ FIX-4: BULL_CONF additive boost (price up + volume up = confirmed) â”€
    bull_conf_boost = 0.04 if vol_div == "ðŸŸ¢BULL_CONF" else 0.0

    # â”€â”€ Anticipation contribution (already normalised) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    anticipation_contrib = anticipation_n * 0.05   # minor forward-looking nudge

    final_n = safe_clamp(raw_n * damper + brain_boost + bull_conf_boost + anticipation_contrib, 0.0, 1.0)

    # Liquidity Shock boost â€” reward genuine institutional directional moves
    if getattr(K, "LIQ_SHOCK_ENABLED", True) and liq_shock >= K.LIQ_SHOCK_THRESHOLD:
        final_n = min(1.0, final_n + K.LIQ_SHOCK_BOOST)

    # [P3-G2] RR Bonus - apply AFTER weighted sum, BEFORE Ã—60 scaling
    # Compute estimated RR from available parameters (before build_trade_plan)
    estimated_rr = 0.0
    if 45 <= rsi <= 60:                              # Sweet spot RSI
        estimated_rr += 1.0
    if adx >= 25:                                    # Strong trend
        estimated_rr += 1.0
    if adaptive_mom > 0:                             # Positive momentum
        estimated_rr += 0.5
    if pct_ema200 < 15:                              # Room to run
        estimated_rr += 0.5
    if vol_ratio >= 1.2:                             # Volume confirmation
        estimated_rr += 0.5

    if K.RR_BONUS_ENABLED and estimated_rr >= K.RR_BONUS_THRESHOLD:
        final_n += K.RR_BONUS_AMOUNT

    # FIX-2.1: Clamp to [0, 1] so SmartRank never exceeds SMART_RANK_SCALE.
    final_n = min(1.0, final_n)

    return round(final_n * K.SMART_RANK_SCALE, 3)
```

==================================================
FILE: egx_radar/core/signal_engine.py
=====================================

```python
from __future__ import annotations

"""Unified EGX accumulation signal engine for live scan and backtest."""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from egx_radar.config.settings import K, get_account_size, get_risk_per_trade
from egx_radar.core.accumulation import evaluate_accumulation_context
from egx_radar.core.indicators import (
    compute_atr,
    compute_atr_risk,
    compute_cmf,
    compute_liquidity_shock,
    compute_vol_zscore,
    compute_vwap_dist,
    detect_ema_cross,
    detect_vol_divergence,
    safe_clamp,
)

log = logging.getLogger(__name__)


def _last(series: pd.Series, default: float = 0.0) -> float:
    data = pd.Series(series).dropna()
    return float(data.iloc[-1]) if not data.empty else default


def compute_rsi_value(close: pd.Series, period: int = 14) -> float:
    """Wilder RSI implemented locally for deterministic live/backtest parity."""
    if close is None or len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    gain_v = _last(avg_gain, 0.0)
    loss_v = _last(avg_loss, 0.0)
    if loss_v <= 1e-9:
        return 100.0 if gain_v > 0 else 50.0
    rs = gain_v / loss_v
    return float(100.0 - (100.0 / (1.0 + rs)))


def compute_adx_value(df: pd.DataFrame, period: int = 14) -> float:
    """Wilder ADX implemented locally to avoid live/backtest divergence."""
    required = {"High", "Low", "Close"}
    if df is None or len(df) < period * 2 or not required.issubset(df.columns):
        return 0.0

    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    if _last(atr, 0.0) <= 1e-9:
        return 0.0

    plus_di = 100.0 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return float(np.nan_to_num(_last(adx, 0.0), nan=0.0, posinf=0.0, neginf=0.0))


def _avg_turnover(close: pd.Series, volume: pd.Series, window: int = 20) -> float:
    turnover = close * volume
    return _last(turnover.rolling(window).mean(), 0.0)


def _spread_proxy_pct(df: pd.DataFrame, window: int = 5) -> float:
    spread = ((df["High"] - df["Low"]) / df["Close"].replace(0.0, np.nan)).abs() * 100.0
    return float(np.nan_to_num(_last(spread.tail(window).median(), 0.0), nan=0.0))


def _ema_slope_pct(series: pd.Series, bars: int = 10) -> float:
    if len(series) < bars + 1:
        return 0.0
    base = float(series.iloc[-bars - 1]) if float(series.iloc[-bars - 1]) != 0 else 1e-9
    return ((float(series.iloc[-1]) - base) / base) * 100.0


def _confidence_label(score: float) -> str:
    if score >= 82:
        return "ELITE"
    if score >= 75:
        return "STRONG"
    if score >= 70:
        return "GOOD"
    if score >= 60:
        return "BUILDING"
    return "WEAK"


def _phase_from_context(accumulation_detected: bool, fake_move: bool, entry_ready: bool) -> str:
    if fake_move:
        return "Exhaustion"
    if accumulation_detected:
        return "Accumulation"
    if entry_ready:
        return "Transition"
    return "Base"


def _zone_from_context(accumulation_detected: bool, fake_move: bool, minor_break_pct: float) -> str:
    if fake_move or minor_break_pct > K.ACCUM_MAX_MINOR_BREAK_PCT:
        return "ðŸ”´ LATE"
    if accumulation_detected:
        return "ðŸŸ¢ EARLY"
    return "ðŸŸ¡ MID"


def classify_trade_type(score: float) -> Optional[str]:
    if score >= K.TRADE_TYPE_STRONG_MIN:
        return "STRONG"
    if score >= K.TRADE_TYPE_MEDIUM_MIN:
        return "MEDIUM"
    return None


def trade_risk_fraction(trade_type: Optional[str]) -> float:
    base_risk = min(float(get_risk_per_trade()), float(K.RISK_PER_TRADE_STRONG))
    if trade_type == "STRONG":
        return base_risk
    if trade_type == "MEDIUM":
        return min(base_risk * 0.5, float(K.RISK_PER_TRADE_MEDIUM))
    return 0.0


def trigger_fill_tolerance(trigger_price: float) -> float:
    if trigger_price <= 0:
        return 0.0
    return max(0.01, float(trigger_price) * float(K.TRIGGER_FILL_TOLERANCE_PCT))


def candle_hits_trigger(high_price: float, trigger_price: float) -> bool:
    if trigger_price <= 0:
        return True
    return float(high_price) + trigger_fill_tolerance(trigger_price) >= float(trigger_price)


def _position_plan(
    *,
    price: float,
    entry_price: float,
    base_low: float,
    smart_rank: float,
    entry_ready: bool,
    regime: str,
) -> Dict[str, float]:
    ref_price = max(entry_price, 1e-9)
    raw_stop = base_low * 0.995 if base_low > 0 else ref_price * (1.0 - K.MAX_STOP_LOSS_PCT)
    risk_pct = (ref_price - raw_stop) / max(ref_price, 1e-9)
    stop_capped = risk_pct > K.MAX_STOP_LOSS_PCT
    risk_viable = 0.0 < risk_pct <= 0.10
    stop = raw_stop if not stop_capped else ref_price * (1.0 - K.MAX_STOP_LOSS_PCT)
    stop = min(stop, ref_price * 0.995)
    if stop >= ref_price:
        stop = ref_price * (1.0 - K.MAX_STOP_LOSS_PCT)

    trade_type = classify_trade_type(smart_rank)
    risk_used = trade_risk_fraction(trade_type)
    risk_amount = get_account_size() * risk_used
    risk_per_share = max(ref_price - stop, ref_price * 0.005)
    size = max(1, int(risk_amount / max(risk_per_share, 1e-9))) if risk_amount > 0 else 0
    max_notional = get_account_size() * K.PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT
    if size > 0:
        size = max(1, min(size, int(max_notional / max(ref_price, 1e-9))))

    if not entry_ready or regime != "BULL" or not risk_viable or trade_type is None:
        action = "WAIT"
        size = 0
        trade_type = "SKIP"
        risk_used = 0.0
    elif trade_type == "STRONG":
        action = "ACCUMULATE"
    else:
        action = "PROBE"

    target_pct = float(K.POSITION_MAIN_TP_PCT)
    target = ref_price * (1.0 + target_pct)
    partial_target = ref_price * (1.0 + K.PARTIAL_TP_PCT)
    trailing_trigger = ref_price * (1.0 + K.TRAILING_TRIGGER_PCT)
    rr = abs(target - ref_price) / max(abs(ref_price - stop), 1e-9)
    return {
        "action": action,
        "entry": round(ref_price, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "partial_target": round(partial_target, 2),
        "trailing_trigger": round(trailing_trigger, 2),
        "trailing_stop_pct": round(float(K.TRAILING_STOP_PCT), 4),
        "size": int(size),
        "rr": round(rr, 2),
        "timeframe": "Position (5-20d)",
        "force_wait": action == "WAIT",
        "winrate": 0.0,
        "winrate_na": action == "WAIT",
        "risk_pct": round((ref_price - stop) / max(ref_price, 1e-9), 4),
        "risk_used": round(float(risk_used), 4),
        "trade_type": trade_type,
        "score": round(float(smart_rank), 2),
        "target_pct": round(target_pct, 4),
        "max_hold_bars": int(K.BT_MAX_BARS),
        "stop_capped": bool(stop_capped),
        "trigger_price": round(entry_price, 2),
        "trigger_tolerance_pct": round(float(K.TRIGGER_FILL_TOLERANCE_PCT), 4),
    }


def evaluate_symbol_snapshot(
    df_ta: pd.DataFrame,
    sym: str,
    sector: str,
    regime: str = "BULL",
) -> Optional[dict]:
    """Evaluate one symbol using shared EGX accumulation logic."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    if df_ta is None or len(df_ta) < max(K.MIN_BARS, 210) or not required.issubset(df_ta.columns):
        return None

    df_ta = df_ta.tail(260).copy()
    close = df_ta["Close"].astype(float).dropna()
    if len(close) < max(K.MIN_BARS, 210):
        return None

    price = float(close.iloc[-1])
    if price < K.PRICE_FLOOR:
        return None
    if df_ta["Close"].iloc[-5:].nunique() <= 1:
        return None

    open_ = df_ta["Open"].astype(float)
    high = df_ta["High"].astype(float)
    low = df_ta["Low"].astype(float)
    volume = df_ta["Volume"].fillna(0.0).astype(float)

    ema20_s = close.ewm(span=20, adjust=False).mean()
    ema50_s = close.ewm(span=50, adjust=False).mean()
    ema200_s = close.ewm(span=200, adjust=False).mean()
    ema20 = _last(ema20_s, price)
    ema50 = _last(ema50_s, price)
    ema200 = _last(ema200_s, price)
    ema20_slope_pct = _ema_slope_pct(ema20_s, bars=8)
    ema50_slope_pct = _ema_slope_pct(ema50_s, bars=10)
    ema200_slope_pct = _ema_slope_pct(ema200_s, bars=10)

    adx = compute_adx_value(df_ta, period=K.ADX_LENGTH)
    rsi = compute_rsi_value(close, period=14)
    momentum = _last(close.pct_change(10), 0.0) * 100.0
    adaptive_mom = momentum * min(1.10, max(0.60, adx / 22.0 if adx > 0 else 0.60))
    atr = compute_atr(df_ta)
    atr_label, atr_pct_rank = compute_atr_risk(df_ta, price)
    vwap_dist = compute_vwap_dist(df_ta, price)
    vol_zscore = compute_vol_zscore(df_ta)
    cmf = compute_cmf(df_ta)
    avg_vol = _last(volume.rolling(20).mean(), 0.0)
    vol_ratio = safe_clamp(float(volume.iloc[-1]) / max(avg_vol, 1e-9), 0.0, 4.0) if avg_vol > 0 else 0.0
    avg_turnover = _avg_turnover(close, volume)
    turnover = price * float(volume.iloc[-1])
    spread_pct = _spread_proxy_pct(df_ta)
    pct_ema200 = safe_clamp(((price - ema200) / max(ema200, 1e-9)) * 100.0, -50.0, 50.0)

    if avg_turnover < K.MIN_TURNOVER_EGP:
        return None
    if spread_pct > K.MAX_SPREAD_PCT:
        return None

    ctx = evaluate_accumulation_context(
        df_ta,
        price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        ema20_slope_pct=ema20_slope_pct,
        ema50_slope_pct=ema50_slope_pct,
        ema200_slope_pct=ema200_slope_pct,
        rsi=rsi,
        adx=adx,
        avg_turnover=avg_turnover,
        spread_pct=spread_pct,
        avg_vol=avg_vol,
        vol_ratio=vol_ratio,
        vol_zscore=vol_zscore,
    )

    smart_rank = round(
        ctx["accumulation_quality_score"] * 0.40
        + ctx["structure_strength_score"] * 0.25
        + ctx["volume_quality_score"] * 0.20
        + ctx["trend_alignment_score"] * 0.15,
        2,
    )

    phase = _phase_from_context(
        accumulation_detected=ctx["accumulation_detected"],
        fake_move=ctx["fake_move"],
        entry_ready=ctx["entry_ready"],
    )
    zone = _zone_from_context(
        accumulation_detected=ctx["accumulation_detected"],
        fake_move=ctx["fake_move"],
        minor_break_pct=ctx["minor_break_pct"],
    )
    trigger_price = float(ctx["trigger_price"])
    plan = _position_plan(
        price=price,
        entry_price=trigger_price,
        base_low=float(ctx["base_low"]),
        smart_rank=smart_rank,
        entry_ready=bool(ctx["entry_ready"]),
        regime=regime,
    )

    if plan["action"] == "ACCUMULATE":
        tag = "buy"
        signal = "ACCUMULATE"
    elif plan["action"] == "PROBE":
        tag = "early"
        signal = "PROBE"
    else:
        tag = "watch"
        signal = "WATCH"

    tech_score = int(
        round(
            safe_clamp(
                (ctx["accumulation_quality_score"] * 0.55 + ctx["structure_strength_score"] * 0.45) / 5.56,
                0.0,
                18.0,
            )
        )
    )
    tech_score_pct = round(safe_clamp((tech_score / 18.0) * 100.0, 0.0, 100.0), 1)
    liq_shock = compute_liquidity_shock(df_ta, atr, avg_vol)
    ema_cross = detect_ema_cross(close)
    vol_div = detect_vol_divergence(close, volume)
    vcp_detected = bool(
        ctx["compression_score"] >= 70.0
        and ctx["contraction_ratio"] <= 0.95
        and not ctx["erratic_volume"]
    )
    body_ratio = abs(float(close.iloc[-1]) - float(open_.iloc[-1])) / max(float(high.iloc[-1]) - float(low.iloc[-1]), 1e-9)
    vol_tier = "High" if avg_turnover >= 15_000_000 else "Mid" if avg_turnover >= 8_000_000 else "Low"

    reasons: List[str] = []
    reasons.append("accum-base" if ctx["accumulation_detected"] else "no-base")
    reasons.append("higher-lows" if ctx["higher_lows"] else "flat-support")
    reasons.append(f"turnover {avg_turnover/1_000_000:.1f}m")
    reasons.append(f"spread {spread_pct:.2f}%")
    reasons.append(f"base {ctx['compression_window']}d/{ctx['compression_range_pct']:.1f}%")
    reasons.append(f"minor-break {ctx['minor_break_pct']:.1f}%")
    if ctx["entry_ready"] and not ctx["break_confirmed"]:
        reasons.append("trigger-ready")
    if not ctx["volume_confirmed"]:
        reasons.append("volume-unconfirmed")
    if ctx["erratic_volume"]:
        reasons.append("erratic-volume")
    if ctx["fake_move"]:
        reasons.append("fake-move")
    if not ctx["risk_viable"]:
        reasons.append("risk-too-wide")
    elif ctx["stop_capped"]:
        reasons.append("stop-capped-5%")
    if regime != "BULL":
        reasons.append(f"regime-{regime.lower()}")

    result = {
        "sym": sym,
        "sector": sector,
        "price": round(price, 3),
        "adx": round(adx, 2),
        "rsi": round(rsi, 2),
        "momentum": round(momentum, 3),
        "adaptive_mom": round(adaptive_mom, 3),
        "pct_ema200": round(pct_ema200, 2),
        "ema20": round(ema20, 3),
        "ema50": round(ema50, 3),
        "ema200": round(ema200, 3),
        "ema20_slope_pct": round(ema20_slope_pct, 3),
        "ema50_slope_pct": round(ema50_slope_pct, 3),
        "ema200_slope_pct": round(ema200_slope_pct, 3),
        "vol_ratio": round(vol_ratio, 3),
        "avg_vol": round(avg_vol, 2),
        "avg_turnover": round(avg_turnover, 2),
        "turnover": round(turnover, 2),
        "spread_pct": round(spread_pct, 3),
        "vol_tier": vol_tier,
        "tech_score": tech_score,
        "tech_score_pct": tech_score_pct,
        "signal": signal,
        "tag": tag,
        "phase": phase,
        "trend_acc": round(ema200_slope_pct / 100.0, 4),
        "breakout": False,
        "minor_breakout": bool(ctx["entry_ready"]),
        "clv": round((price - float(ctx["base_low"])) / max(float(ctx["base_high"]) - float(ctx["base_low"]), 1e-9), 3),
        "whale": "",
        "hunter": "Builder" if ctx["accumulation_detected"] else "",
        "silent": bool(ctx["accumulation_detected"] and body_ratio < 0.35),
        "expansion": False,
        "fake_expansion": bool(ctx["fake_move"]),
        "vcp_detected": vcp_detected,
        "cpi": round(ctx["volume_quality_score"] / 100.0, 3),
        "iet": round(ctx["structure_strength_score"] / 100.0, 3),
        "whale_score": round(safe_clamp((ctx["up_down_volume_ratio"] - 0.9) / 0.8, 0.0, 1.0), 3),
        "anticipation": round(ctx["accumulation_quality_score"] / 100.0, 3),
        "quantum": round(ctx["compression_score"] / 100.0, 3),
        "gravity_label": "ALIGNED" if ctx["trend_alignment_score"] >= 75 else "BUILDING" if ctx["trend_alignment_score"] >= 60 else "LIGHT",
        "gravity_score": round(ctx["trend_alignment_score"] / 100.0, 3),
        "zone": zone,
        "hidden": 0.0,
        "ema_cross": ema_cross,
        "vol_div": vol_div,
        "mom_arrow": "",
        "atr": round(float(atr), 4) if atr else None,
        "atr_risk": atr_label,
        "atr_pct_rank": round(float(atr_pct_rank), 1),
        "vwap_dist": round(vwap_dist, 4),
        "vol_zscore": round(vol_zscore, 3),
        "cmf": round(cmf, 4),
        "liq_shock": round(liq_shock, 3),
        "one_day_gain_pct": ctx["one_day_gain_pct"],
        "two_day_gain_pct": ctx["two_day_gain_pct"],
        "last_3_days_gain_pct": ctx["last_3_days_gain_pct"],
        "gap_up_pct": ctx["gap_up_pct"],
        "smart_rank": round(smart_rank, 2),
        "accumulation_quality_score": ctx["accumulation_quality_score"],
        "structure_strength_score": ctx["structure_strength_score"],
        "volume_quality_score": ctx["volume_quality_score"],
        "trend_alignment_score": ctx["trend_alignment_score"],
        "compression_range_pct": ctx["compression_range_pct"],
        "compression_window": ctx["compression_window"],
        "support_slope_pct": ctx["support_slope_pct"],
        "up_down_volume_ratio": ctx["up_down_volume_ratio"],
        "gradual_volume_ratio": ctx["gradual_volume_ratio"],
        "volume_variation_ratio": ctx["volume_variation_ratio"],
        "base_low": ctx["base_low"],
        "base_high": ctx["base_high"],
        "minor_resistance": ctx["minor_resistance"],
        "trigger_price": ctx["trigger_price"],
        "minor_break_pct": ctx["minor_break_pct"],
        "accumulation_detected": ctx["accumulation_detected"],
        "break_confirmed": ctx["break_confirmed"],
        "entry_ready": ctx["entry_ready"],
        "higher_lows": ctx["higher_lows"],
        "volume_confirmed": ctx["volume_confirmed"],
        "erratic_volume": ctx["erratic_volume"],
        "abnormal_candle": ctx["abnormal_candle"],
        "fake_move": ctx["fake_move"],
        "confidence": round(smart_rank, 1),
        "leader": False,
        "plan": plan,
        "inst_conf": _confidence_label(smart_rank),
        "signal_dir": "BULLISH" if tag in ("buy", "early") else "NEUTRAL",
        "signal_reason": " | ".join(reasons),
        "signal_display": signal,
        "guard_reason": "",
    }
    return result


def detect_conservative_market_regime(results: List[dict]) -> str:
    """Broad market regime for EGX accumulation mode."""
    if not results:
        return "NEUTRAL"

    n = len(results)
    breadth_above_50 = sum(1 for r in results if r.get("price", 0.0) > r.get("ema50", 0.0)) / n
    breadth_stacked = sum(1 for r in results if r.get("price", 0.0) > r.get("ema50", 0.0) > r.get("ema200", 0.0)) / n
    avg_slope = sum(r.get("ema200_slope_pct", 0.0) for r in results) / n
    avg_rank = sum(r.get("smart_rank", 0.0) for r in results) / n

    if (breadth_above_50 >= K.MARKET_BREADTH_THRESHOLD
            and breadth_stacked >= K.MARKET_BULL_STACKED_MIN
            and avg_slope >= -0.03
            and avg_rank >= 45.0):
        return "BULL"
    if breadth_above_50 <= K.MARKET_BEAR_BREADTH_MAX or avg_slope < -0.12:
        return "BEAR"
    return "NEUTRAL"


def apply_regime_gate(result: dict, regime: str) -> dict:
    """Apply regime-based capital preservation.

    BULL   -> all signals pass through unchanged.
    NEUTRAL -> STRONG signals (SR >= TRADE_TYPE_STRONG_MIN) pass through;
               weaker signals are gated to WAIT.
    BEAR   -> all signals forced to WAIT.
    """
    if regime == "BULL":
        return result

    # NEUTRAL: allow STRONG signals through for the hybrid approach
    if regime == "NEUTRAL":
        sr = result.get("smart_rank", 0.0)
        action = (result.get("plan") or {}).get("action", "WAIT")
        if sr >= K.TRADE_TYPE_STRONG_MIN and action in ("ACCUMULATE", "PROBE"):
            gated = dict(result)
            gated["signal_reason"] = f"{result.get('signal_reason', '')} | regime-neutral-pass".strip(" |")
            return gated

    # BEAR or weak NEUTRAL signals -> force WAIT
    plan = dict(result.get("plan") or {})
    plan["action"] = "WAIT"
    plan["size"] = 0
    plan["force_wait"] = True
    plan["winrate"] = 0.0
    plan["winrate_na"] = True

    gated = dict(result)
    gated["tag"] = "watch"
    gated["signal"] = "WAIT"
    gated["signal_display"] = "WAIT"
    gated["signal_dir"] = "NEUTRAL"
    gated["plan"] = plan
    gated["signal_reason"] = f"{result.get('signal_reason', '')} | regime-{regime.lower()}".strip(" |")
    return gated


__all__ = [
    "apply_regime_gate",
    "compute_adx_value",
    "compute_rsi_value",
    "detect_conservative_market_regime",
    "evaluate_symbol_snapshot",
]
```

==================================================
FILE: egx_radar/core/signals.py
===============================

```python
"""Signal engine: market regime, phase, zones and raw signals (Layer 5)."""

import logging
import math
from typing import Dict, List, Optional, Tuple

from egx_radar.config.settings import K
from egx_radar.core.scoring import score_tech_signal

log = logging.getLogger(__name__)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LAYER 5: SIGNAL ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


def detect_market_regime(
    results: List[dict],
    ema200_slopes: Optional[Dict[str, float]] = None,
) -> str:
    """
    FIX-C: Market regime now requires EMA200 slope confirmation.
    States: ACCUMULATION | MOMENTUM | DISTRIBUTION | NEUTRAL

    Rules:
      ACCUMULATION: ADX < 20, vol < 1.3, EMA200 slope is flat or rising (â‰¥ -0.001)
                    â†’ prevents false ACCUM in downtrending bearish markets
      MOMENTUM:     ADX > 25, vol > 1.4
      DISTRIBUTION: RSI > 65, ADX > REGIME_ADX_DIST, EMA200 slope falling (< 0)
      NEUTRAL:      everything else
    """
    if not results:
        return "NEUTRAL"

    n       = len(results)
    avg_adx = sum(r["adx"]       for r in results) / n
    avg_rsi = sum(r["rsi"]       for r in results) / n
    avg_vol = sum(r["vol_ratio"] for r in results) / n

    # EMA200 slope: average across all symbols with valid slope
    avg_slope = 0.0
    if ema200_slopes:
        valid_slopes = [v for v in ema200_slopes.values() if math.isfinite(v)]
        if valid_slopes:
            avg_slope = sum(valid_slopes) / len(valid_slopes)

    if avg_adx < 20 and avg_vol < 1.3 and avg_slope >= -0.001:
        # FIX-C: Require non-negative EMA200 slope to confirm ACCUMULATION
        return "ACCUMULATION"
    if avg_adx > K.REGIME_ADX_BULL and avg_vol > 1.4:
        return "MOMENTUM"
    if avg_rsi > K.REGIME_RSI_DIST_MIN and avg_adx > K.REGIME_ADX_DIST and avg_slope < 0:
        # FIX-C: Distribution only when EMA200 is falling
        return "DISTRIBUTION"
    # BEAR: broad market below EMA200 with falling slope â€” clear downtrend
    # Different from DISTRIBUTION (which is a topping pattern at high RSI)
    if avg_slope < K.REGIME_BEAR_SLOPE_THRESH and avg_rsi < K.REGIME_BEAR_RSI_MAX:
        return "BEAR"
    return "NEUTRAL"


def detect_phase(
    adx: float, rsi: float, vol_ratio: float, trend_acc: float,
    clv: float, adaptive_mom: float, ema50: float, price: float,
    body_ratio: float = 0.3,
) -> str:
    """
    FIX-2: body_ratio is now a real parameter (was hardcoded 0.3 and unused).
    A small candle body (< 0.35) during quiet conditions is a classic
    accumulation footprint â€” smart money absorbing without showing intent.
    """
    hidden = 0.0
    if adx < 20 and 45 < rsi < 60:      hidden += 1.5
    if vol_ratio < 1.2 and clv > 0.4:   hidden += 1.0
    if trend_acc > 0:                    hidden += 1.0
    if body_ratio < 0.35:               hidden += 0.5   # FIX-2: real body signal
    if hidden > K.ACCUM_SCORE_THRESH:
        return "Accumulation"
    if adaptive_mom > 1.5 and adx > K.ADX_MID and price > ema50:
        return "Expansion"
    return "Exhaustion"


def detect_predictive_zone(rsi: float, adaptive_mom: float, pct_ema200: float, vol_ratio: float) -> str:
    """Determine predictive early/mid/late zone. EGX-calibrated thresholds.

    Wider RSI band and relaxed momentum threshold to avoid over-classifying
    normal EGX market conditions as LATE.
    """
    s = 0
    if 45 <= rsi <= 65:    s += 2   # was 48-60 â€” wider RSI band for EGX
    if adaptive_mom > -1:  s += 2   # was >0 â€” allow slightly negative momentum
    if pct_ema200 < 20:    s += 1   # was <15 â€” EGX stocks often run 15-20% above EMA200
    if vol_ratio < 1.6:    s += 1   # was <1.4 â€” EGX volume is spikier
    if s >= 5: return "ðŸŸ¢ EARLY"
    if s >= 3: return "ðŸŸ¡ MID"
    return "ðŸ”´ LATE"


def build_signal(
    price: float, ema200: float, ema50: float, adx: float, rsi: float,
    adaptive_mom: float, vol_ratio: float, breakout: bool, pct_ema200: float,
    phase: str, brain_score_req: int = K.BRAIN_SCORE_NEUTRAL, vol_div: str = "",
) -> Tuple[str, str, int]:
    """Build the final raw signal, tag, and technical score."""
    score = score_tech_signal(
        price, ema200, ema50, adx, rsi, adaptive_mom, vol_ratio, breakout, pct_ema200
    )

    if phase == "Accumulation":
        if 48 <= rsi <= 62:                      score += 3
        elif 40 <= rsi < 48 or 62 < rsi <= 70:  score += 1
    elif phase == "Expansion":
        if 55 < rsi < 70:                        score += 3
        elif 48 <= rsi <= 55:                    score += 1

    zone = detect_predictive_zone(rsi, adaptive_mom, pct_ema200, vol_ratio)
    # â”€â”€ ultra signal strict guards â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # BT: ultra WR=5% when firing in LATE zone â€” downgrade to buy, never wait.
    _ultra_ok = (
        adaptive_mom > 0.8
        and vol_ratio > 1.15
        and zone != "ðŸ”´ LATE"
        and adaptive_mom > 0.0
        and vol_div not in ("BEAR_DIV", "ðŸ”€BEAR_DIV")
    )

    if phase == "Accumulation" and adaptive_mom > 0.8 and vol_ratio > 1.15:
        raw_sig, raw_tag = ("ðŸ§  ULTRA EARLY", "ultra") if _ultra_ok else ("ðŸ”¥ BUY", "buy")
    elif phase == "Expansion" and adx > K.ADX_MID and adaptive_mom > 1.5:
        raw_sig, raw_tag = "ðŸš€ EARLY", "early"
    else:
        score_watch_adj = max(K.SCORE_WATCH, brain_score_req - 3)
        if score >= brain_score_req:
            raw_sig, raw_tag = "ðŸ”¥ BUY",   "buy"
        elif score >= score_watch_adj:
            raw_sig, raw_tag = "ðŸ‘€ WATCH", "watch"
        else:
            raw_sig, raw_tag = "âŒ SELL",  "sell"

    if raw_tag in ("buy", "ultra", "early") and rsi > K.RSI_OVERBOUGHT:
        raw_sig  = "ðŸ‘€ WATCH âš ï¸OB"
        raw_tag  = "watch"

    return raw_sig, raw_tag, score


def build_signal_reason(
    rsi: float, adx: float, pct_ema200: float, phase: str,
    vol_div: str, ema_cross: str, adaptive_mom: float,
    clv: float, vol_ratio: float, tag: str = "",
) -> str:
    passed: List[str] = []
    failed: List[str] = []

    # Phase
    if phase == "Accumulation":    passed.append("Accum phase")
    elif phase == "Expansion":     passed.append("Expansion phase")
    else:                          failed.append("No clear phase")

    # ADX
    if adx > 30:                   passed.append(f"ADX strong ({adx:.0f})")
    elif adx < 18:                 failed.append(f"ADX weak ({adx:.0f})")

    # RSI
    if 48 <= rsi <= 62:            passed.append("RSI healthy")
    elif rsi > K.RSI_OVERBOUGHT:   failed.append(f"RSI overbought ({rsi:.0f})")
    elif rsi < 35:                 failed.append(f"RSI oversold ({rsi:.0f})")
    else:                          failed.append(f"RSI neutral ({rsi:.0f})")

    # Volume
    if vol_div == "ðŸŸ¢BULL_CONF":   passed.append("Vol confirmed")
    elif vol_div == "ðŸ”€BEAR_DIV":  failed.append("Bear vol div")
    elif vol_div == "âš ï¸CLIMAX_SELL": failed.append("Climax sell")

    # Momentum
    if adaptive_mom > 2:           passed.append("Strong mom")
    elif adaptive_mom < -1:        failed.append("Weak mom")

    # EMA cross
    if ema_cross == "BULL_CROSS":  passed.append("Bull EMA cross")
    elif ema_cross == "BEAR_CROSS": failed.append("Bear EMA cross")

    # Distance from EMA200
    if pct_ema200 > 30:            failed.append(f"Extended {pct_ema200:.0f}% vs EMA200")
    elif pct_ema200 < 0:           failed.append("Below EMA200")

    # Build output: show up to 2 passed + up to 2 failed
    parts = passed[:2] + [f"âœ—{f}" for f in failed[:2]]
    return " | ".join(parts) if parts else "Mixed signals"


def get_signal_direction(tag: str) -> str:
    """Determine the text direction (Bullish/Bearish/Neutral) from the signal tag."""
    if tag in ("buy", "ultra", "early"):
        return "ðŸ“ˆ BULLISH"
    if tag == "sell":
        return "ðŸ“‰ BEARISH"
    return "â¸ï¸ NEUTRAL"
```

==================================================
FILE: egx_radar/market_data/__init__.py
=======================================

```python
"""Market data and live signals module."""

from egx_radar.market_data.manager import (
    MarketDataManager,
    get_market_data_manager
)

from egx_radar.market_data.signals import (
    LiveSignalGenerator,
    TradingSignal,
    SignalType,
    SignalStrength,
    get_signal_generator
)

from egx_radar.market_data.notifications import (
    NotificationManager,
    SignalAlertGenerator,
    Alert,
    AlertType,
    AlertLevel,
    get_notification_manager,
    get_alert_generator
)

__all__ = [
    'MarketDataManager',
    'get_market_data_manager',
    'LiveSignalGenerator',
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    'get_signal_generator',
    'NotificationManager',
    'SignalAlertGenerator',
    'Alert',
    'AlertType',
    'AlertLevel',
    'get_notification_manager',
    'get_alert_generator',
]
```

==================================================
FILE: egx_radar/market_data/manager.py
======================================

```python
"""Market data and real-time data management."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import threading
import time
from collections import deque


class MarketDataManager:
    """Manages real-time and historical market data."""
    
    def __init__(self, cache_size: int = 5000):
        """Initialize market data manager.
        
        Args:
            cache_size: Maximum number of price points to keep in memory
        """
        self.cache_size = cache_size
        self._price_cache: Dict[str, deque] = {}  # symbol -> deque of (timestamp, price)
        self._last_update: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
        self._subscribers: Dict[str, List[callable]] = {}  # callbacks for price updates
    
    def get_historical_data(self, symbol: str, days: int = 365, interval: str = '1d') -> pd.DataFrame:
        """Fetch historical OHLCV data.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            days: Number of days of history to fetch
            interval: Candle interval ('1m', '5m', '1h', '1d', etc.)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Adj Close
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )
            
            return data if isinstance(data, pd.DataFrame) else data.to_frame()
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None if unable to fetch
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d')
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            print(f"Error fetching current price for {symbol}: {e}")
        return None
    
    def get_multi_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """Get current prices for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to prices
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
            time.sleep(0.1)  # Rate limiting
        return prices
    
    def cache_price(self, symbol: str, price: float, timestamp: Optional[datetime] = None) -> None:
        """Cache price data for a symbol.
        
        Args:
            symbol: Stock symbol
            price: Current price
            timestamp: Timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        with self._lock:
            if symbol not in self._price_cache:
                self._price_cache[symbol] = deque(maxlen=self.cache_size)
            
            self._price_cache[symbol].append((timestamp, price))
            self._last_update[symbol] = timestamp
            
            # Notify subscribers
            if symbol in self._subscribers:
                for callback in self._subscribers[symbol]:
                    try:
                        callback(symbol, price, timestamp)
                    except Exception as e:
                        print(f"Error in price callback: {e}")
    
    def get_cached_prices(self, symbol: str, limit: int = 100) -> List[Tuple[datetime, float]]:
        """Get cached price history for a symbol.
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of cached prices to return
            
        Returns:
            List of (timestamp, price) tuples
        """
        with self._lock:
            if symbol not in self._price_cache:
                return []
            return list(self._price_cache[symbol])[-limit:]
    
    def get_price_stats(self, symbol: str) -> Dict[str, float]:
        """Get statistics on cached prices.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with min, max, avg, latest price
        """
        prices = self.get_cached_prices(symbol)
        if not prices:
            return {}
        
        price_values = [p[1] for p in prices]
        return {
            'min': min(price_values),
            'max': max(price_values),
            'avg': sum(price_values) / len(price_values),
            'latest': price_values[-1],
            'count': len(price_values),
            'last_update': prices[-1][0].isoformat() if prices else None
        }
    
    def subscribe(self, symbol: str, callback: callable) -> None:
        """Subscribe to price updates for a symbol.
        
        Args:
            symbol: Stock symbol
            callback: Function to call on price updates (symbol, price, timestamp)
        """
        if symbol not in self._subscribers:
            self._subscribers[symbol] = []
        self._subscribers[symbol].append(callback)
    
    def unsubscribe(self, symbol: str, callback: callable) -> None:
        """Unsubscribe from price updates.
        
        Args:
            symbol: Stock symbol
            callback: Callback function to remove
        """
        if symbol in self._subscribers:
            self._subscribers[symbol] = [
                cb for cb in self._subscribers[symbol] if cb != callback
            ]
    
    def get_intraday_volatility(self, symbol: str, minutes: int = 60) -> Optional[float]:
        """Calculate intraday volatility over recent period.
        
        Args:
            symbol: Stock symbol
            minutes: Period in minutes
            
        Returns:
            Volatility percentage or None
        """
        try:
            data = yf.download(symbol, period='5d', interval='1m', progress=False)
            if data.empty or len(data) < 2:
                return None
            
            returns = data['Close'].pct_change().dropna()
            if len(returns) > 0:
                volatility = float(returns.std() * 100)
                return volatility if not pd.isna(volatility) else None
        except Exception as e:
            print(f"Error calculating volatility for {symbol}: {e}")
        return None
    
    def get_sentiment_indicators(self, symbol: str) -> Dict[str, float]:
        """Get general market sentiment indicators.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with momentum, trend, strength indicators
        """
        try:
            data = self.get_historical_data(symbol, days=30, interval='1d')
            if data.empty or len(data) < 5:
                return {}
            
            # Simple momentum calculation
            close_prices = data['Close'].values
            momentum = (close_prices[-1] - close_prices[-5]) / close_prices[-5] * 100
            
            # Trend (5-day vs 20-day average)
            avg_5 = close_prices[-5:].mean()
            avg_20 = close_prices[-20:].mean() if len(close_prices) >= 20 else close_prices.mean()
            trend = 'bullish' if avg_5 > avg_20 else 'bearish'
            
            # Simple RSI approximation
            deltas = pd.Series(close_prices).diff().dropna().values
            seed = deltas[:1]
            up = seed[seed >= 0].sum()
            down = -seed[seed < 0].sum()
            rs = up / down if down != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            return {
                'momentum': float(momentum),
                'trend': trend,
                'rsi': float(rsi),
                'strength': float(abs(momentum))
            }
        except Exception as e:
            print(f"Error calculating sentiment for {symbol}: {e}")
            return {}
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear cached price data.
        
        Args:
            symbol: Specific symbol to clear, or None for all
        """
        with self._lock:
            if symbol:
                if symbol in self._price_cache:
                    self._price_cache[symbol].clear()
            else:
                self._price_cache.clear()
                self._last_update.clear()


# Global market data manager instance
_market_data_manager: Optional[MarketDataManager] = None


def get_market_data_manager() -> MarketDataManager:
    """Get or create global market data manager."""
    global _market_data_manager
    if _market_data_manager is None:
        _market_data_manager = MarketDataManager()
    return _market_data_manager
```

==================================================
FILE: egx_radar/market_data/notifications.py
============================================

```python
"""Notification and alert system for trading signals."""

from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
import threading


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    SIGNAL = "signal"
    TRADE = "trade"
    RISK = "risk"
    SYSTEM = "system"
    PRICE_ALERT = "price_alert"


@dataclass
class Alert:
    """A single notification/alert."""
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    symbol: Optional[str] = None
    price: Optional[float] = None
    value: Optional[float] = None  # For alerts with numerical values
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d['alert_type'] = self.alert_type.value
        d['level'] = self.level.value
        d['timestamp'] = self.timestamp.isoformat()
        d['metadata'] = self.metadata or {}
        return d
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class NotificationManager:
    """Manages alerts and notifications."""
    
    def __init__(self, max_alert_history: int = 10000):
        """Initialize notification manager.
        
        Args:
            max_alert_history: Maximum alerts to keep in memory
        """
        self.max_alert_history = max_alert_history
        self._alert_history = deque(maxlen=max_alert_history)
        self._subscribers: Dict[AlertType, List[Callable]] = {}
        self._level_subscribers: Dict[AlertLevel, List[Callable]] = {}
        self._symbol_subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._unread_count = 0
    
    def create_alert(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        title: str,
        message: str,
        symbol: Optional[str] = None,
        price: Optional[float] = None,
        value: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> Alert:
        """Create and dispatch an alert.
        
        Args:
            alert_type: Type of alert
            level: Alert severity
            title: Alert title
            message: Alert message
            symbol: Stock symbol (if applicable)
            price: Current price (if applicable)
            value: Numerical value associated with alert
            metadata: Additional metadata
            
        Returns:
            Created Alert object
        """
        alert = Alert(
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            symbol=symbol,
            price=price,
            value=value,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._alert_history.append(alert)
            self._unread_count += 1
        
        # Dispatch to subscribers
        self._dispatch_alert(alert)
        
        return alert
    
    def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert to all subscribers."""
        # Type subscribers
        if alert.alert_type in self._subscribers:
            for callback in self._subscribers[alert.alert_type]:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error in alert callback: {e}")
        
        # Level subscribers
        if alert.level in self._level_subscribers:
            for callback in self._level_subscribers[alert.level]:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error in level callback: {e}")
        
        # Symbol subscribers
        if alert.symbol and alert.symbol in self._symbol_subscribers:
            for callback in self._symbol_subscribers[alert.symbol]:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error in symbol callback: {e}")
    
    def subscribe_to_type(self, alert_type: AlertType, callback: Callable) -> None:
        """Subscribe to alerts of a specific type.
        
        Args:
            alert_type: Type to subscribe to
            callback: Function to call on alerts
        """
        if alert_type not in self._subscribers:
            self._subscribers[alert_type] = []
        self._subscribers[alert_type].append(callback)
    
    def subscribe_to_level(self, level: AlertLevel, callback: Callable) -> None:
        """Subscribe to alerts at a specific severity level.
        
        Args:
            level: Alert level to subscribe to
            callback: Function to call on alerts
        """
        if level not in self._level_subscribers:
            self._level_subscribers[level] = []
        self._level_subscribers[level].append(callback)
    
    def subscribe_to_symbol(self, symbol: str, callback: Callable) -> None:
        """Subscribe to alerts for a specific symbol.
        
        Args:
            symbol: Stock symbol
            callback: Function to call on alerts
        """
        if symbol not in self._symbol_subscribers:
            self._symbol_subscribers[symbol] = []
        self._symbol_subscribers[symbol].append(callback)
    
    def unsubscribe_from_type(self, alert_type: AlertType, callback: Callable) -> None:
        """Unsubscribe from type alerts."""
        if alert_type in self._subscribers:
            self._subscribers[alert_type] = [
                cb for cb in self._subscribers[alert_type] if cb != callback
            ]
    
    def unsubscribe_from_level(self, level: AlertLevel, callback: Callable) -> None:
        """Unsubscribe from level alerts."""
        if level in self._level_subscribers:
            self._level_subscribers[level] = [
                cb for cb in self._level_subscribers[level] if cb != callback
            ]
    
    def unsubscribe_from_symbol(self, symbol: str, callback: Callable) -> None:
        """Unsubscribe from symbol alerts."""
        if symbol in self._symbol_subscribers:
            self._symbol_subscribers[symbol] = [
                cb for cb in self._symbol_subscribers[symbol] if cb != callback
            ]
    
    def get_alert_history(self, limit: int = 100, alert_type: Optional[AlertType] = None) -> List[Alert]:
        """Get alert history.
        
        Args:
            limit: Maximum alerts to return
            alert_type: Filter by alert type (optional)
            
        Returns:
            List of recent alerts
        """
        with self._lock:
            alerts = list(self._alert_history)
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        return alerts[-limit:]
    
    def get_unread_count(self) -> int:
        """Get number of unread alerts."""
        with self._lock:
            return self._unread_count
    
    def mark_as_read(self, count: int = 1) -> None:
        """Mark alerts as read.
        
        Args:
            count: Number to mark as read
        """
        with self._lock:
            self._unread_count = max(0, self._unread_count - count)
    
    def clear_history(self) -> None:
        """Clear all alert history."""
        with self._lock:
            self._alert_history.clear()
            self._unread_count = 0


class SignalAlertGenerator:
    """Generates alerts from trading signals."""
    
    def __init__(self, notification_manager: NotificationManager):
        """Initialize alert generator.
        
        Args:
            notification_manager: NotificationManager instance
        """
        self.notification_manager = notification_manager
    
    def signal_alert(self, signal: 'TradingSignal') -> Alert:  # noqa: F821
        """Create alert from trading signal.
        
        Args:
            signal: TradingSignal object
            
        Returns:
            Created Alert
        """
        from egx_radar.market_data.signals import SignalType, SignalStrength
        
        # Determine alert level based on signal strength
        level_map = {
            SignalStrength.WEAK: AlertLevel.INFO,
            SignalStrength.MODERATE: AlertLevel.WARNING,
            SignalStrength.STRONG: AlertLevel.CRITICAL,
            SignalStrength.VERY_STRONG: AlertLevel.CRITICAL,
        }
        level = level_map.get(signal.strength, AlertLevel.INFO)
        
        # Create title and message
        signal_text = signal.signal_type.value.replace('_', ' ').title()
        title = f"{signal_text}: {signal.symbol}"
        message = (
            f"{signal_text} signal at ${signal.entry_price:.2f}\n"
            f"Strength: {signal.strength.value}\n"
            f"Confidence: {signal.confidence*100:.1f}%\n"
            f"Target: ${signal.target_price:.2f} | Stop: ${signal.stop_loss:.2f}"
        )
        
        # Create metadata
        metadata = {
            'signal_type': signal.signal_type.value,
            'rsi': signal.rsi,
            'macd': signal.macd,
            'confidence': signal.confidence,
            'reason': signal.reason,
        }
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.SIGNAL,
            level=level,
            title=title,
            message=message,
            symbol=signal.symbol,
            price=signal.entry_price,
            metadata=metadata
        )
    
    def trade_alert(self, symbol: str, trade_type: str, price: float, quantity: int) -> Alert:
        """Create alert for executed trade.
        
        Args:
            symbol: Stock symbol
            trade_type: 'buy' or 'sell'
            price: Execution price
            quantity: Number of shares
            
        Returns:
            Created Alert
        """
        title = f"Trade Executed: {trade_type.upper()} {symbol}"
        message = f"{trade_type.title()} {quantity} shares at ${price:.2f}"
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.TRADE,
            level=AlertLevel.WARNING,
            title=title,
            message=message,
            symbol=symbol,
            price=price,
            value=float(price * quantity),
            metadata={'quantity': quantity, 'type': trade_type}
        )
    
    def price_alert(self, symbol: str, price: float, alert_condition: str) -> Alert:
        """Create alert for price level.
        
        Args:
            symbol: Stock symbol
            price: Current/trigger price
            alert_condition: Description of condition (e.g., "above $100")
            
        Returns:
            Created Alert
        """
        title = f"Price Alert: {symbol}"
        message = f"Price {alert_condition} at ${price:.2f}"
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.PRICE_ALERT,
            level=AlertLevel.INFO,
            title=title,
            message=message,
            symbol=symbol,
            price=price
        )
    
    def risk_alert(self, symbol: str, risk_type: str, value: float) -> Alert:
        """Create alert for risk event.
        
        Args:
            symbol: Stock symbol
            risk_type: Type of risk (e.g., "Stop Loss Hit", "Daily Loss Limit")
            value: Associated value
            
        Returns:
            Created Alert
        """
        title = f"Risk Alert: {symbol}"
        message = f"{risk_type} triggered at {value:.2f}%"
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.RISK,
            level=AlertLevel.CRITICAL,
            title=title,
            message=message,
            symbol=symbol,
            value=value
        )


# Global instances
_notification_manager: Optional[NotificationManager] = None
_alert_generator: Optional[SignalAlertGenerator] = None


def get_notification_manager() -> NotificationManager:
    """Get or create global notification manager."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def get_alert_generator() -> SignalAlertGenerator:
    """Get or create global alert generator."""
    global _alert_generator
    if _alert_generator is None:
        _alert_generator = SignalAlertGenerator(get_notification_manager())
    return _alert_generator
```

==================================================
FILE: egx_radar/market_data/signals.py
======================================

```python
"""Live signal generation from market data."""

import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
import json
from enum import Enum

from egx_radar.market_data.manager import get_market_data_manager


class SignalStrength(str, Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class SignalType(str, Enum):
    """Types of trading signals."""
    BUY = "buy"
    SELL = "sell"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"
    HOLD = "hold"


@dataclass
class TradingSignal:
    """A single trading signal with all relevant data."""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    timestamp: datetime
    entry_price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence: float = 0.5  # 0.0 to 1.0
    
    # Technical indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bollinger_band_position: Optional[float] = None  # -1 to 1 (lower to upper)
    moving_avg_crossover: Optional[float] = None
    volume_surge: bool = False
    
    # Market sentiment
    momentum: Optional[float] = None
    trend: Optional[str] = None
    
    # Metadata
    reason: str = ""
    indicators_used: List[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['signal_type'] = self.signal_type.value
        d['strength'] = self.strength.value
        d['timestamp'] = self.timestamp.isoformat()
        return d
    
    @staticmethod
    def from_dict(data: Dict) -> 'TradingSignal':
        """Create from dictionary."""
        data['signal_type'] = SignalType(data['signal_type'])
        data['strength'] = SignalStrength(data['strength'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return TradingSignal(**data)


class LiveSignalGenerator:
    """Generates real-time trading signals from market data."""
    
    def __init__(self, lookback_days: int = 30):
        """Initialize signal generator.
        
        Args:
            lookback_days: Days of historical data to use for calculations
        """
        self.lookback_days = lookback_days
        self.market_data = get_market_data_manager()
        self._signal_history: Dict[str, List[TradingSignal]] = {}
    
    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Generate trading signal for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            TradingSignal or None if unable to generate
        """
        try:
            # Get historical data
            data = self.market_data.get_historical_data(
                symbol, 
                days=self.lookback_days
            )
            
            if data.empty or len(data) < 10:
                return None
            
            # Get current price
            current_price = float(data['Close'].iloc[-1])
            timestamp = data.index[-1]
            if hasattr(timestamp, 'to_pydatetime'):
                timestamp = timestamp.to_pydatetime()
            
            # Calculate indicators
            rsi = self._calculate_rsi(data['Close'])
            macd, signal_line = self._calculate_macd(data['Close'])
            bb_position = self._calculate_bollinger_position(data['Close'])
            
            # Calculate moving averages
            sma_20 = data['Close'].rolling(20).mean()
            sma_50 = data['Close'].rolling(50).mean() if len(data) >= 50 else None
            sma_20_val = float(sma_20.iloc[-1]) if sma_20 is not None and not pd.isna(sma_20.iloc[-1]) else None
            sma_50_val = float(sma_50.iloc[-1]) if sma_50 is not None and not pd.isna(sma_50.iloc[-1]) else None
            
            momentum = self._calculate_momentum(data['Close'])
            sentiment = self.market_data.get_sentiment_indicators(symbol)
            
            # Generate signal based on indicators
            signal_type, strength, confidence, reason = self._evaluate_signals(
                rsi=rsi,
                macd=macd,
                macd_signal=signal_line,
                bb_position=bb_position,
                sma_20=sma_20_val,
                sma_50=sma_50_val,
                momentum=momentum,
                sentiment=sentiment
            )
            
            # Calculate targets
            volatility = self.market_data.get_intraday_volatility(symbol)
            atr = self._calculate_atr(data) if 'High' in data.columns else None
            
            target_price = None
            stop_loss = None
            
            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                if volatility:
                    target_price = current_price * (1 + volatility / 100)
                    stop_loss = current_price * (1 - volatility / 100 * 0.5)
            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                if volatility:
                    target_price = current_price * (1 - volatility / 100)
                    stop_loss = current_price * (1 + volatility / 100 * 0.5)
            
            # Create signal object
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                timestamp=datetime.now(),
                entry_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                confidence=confidence,
                rsi=rsi,
                macd=macd,
                bollinger_band_position=bb_position,
                moving_avg_crossover=momentum,
                momentum=sentiment.get('momentum'),
                trend=sentiment.get('trend'),
                reason=reason,
                indicators_used=['RSI', 'MACD', 'Bollinger Bands', 'Moving Averages', 'Momentum']
            )
            
            # Store in history
            if symbol not in self._signal_history:
                self._signal_history[symbol] = []
            self._signal_history[symbol].append(signal)
            
            return signal
        
        except Exception as e:
            print(f"Error generating signal for {symbol}: {e}")
            return None
    
    def generate_signals_batch(self, symbols: List[str]) -> Dict[str, Optional[TradingSignal]]:
        """Generate signals for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to signals
        """
        signals = {}
        for symbol in symbols:
            signals[symbol] = self.generate_signal(symbol)
        return signals
    
    def get_signal_history(self, symbol: str, limit: int = 100) -> List[TradingSignal]:
        """Get signal history for a symbol.
        
        Args:
            symbol: Stock symbol
            limit: Maximum signals to return
            
        Returns:
            List of recent signals
        """
        if symbol not in self._signal_history:
            return []
        return self._signal_history[symbol][-limit:]
    
    # ==================== INDICATOR CALCULATIONS ====================
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss if loss.iloc[-1] != 0 else 0
        rsi_value = 100 - (100 / (1 + rs.iloc[-1]))
        return float(rsi_value) if not pd.isna(rsi_value) else 50.0
    
    @staticmethod
    def _calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float]:
        """Calculate MACD and signal line."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        
        macd_val = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0.0
        signal_val = float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else 0.0
        return macd_val, signal_val
    
    @staticmethod
    def _calculate_bollinger_position(prices: pd.Series, period: int = 20, std_dev: int = 2) -> float:
        """Calculate position within Bollinger Bands (-1 to 1).
        -1 = lower band, 0 = middle, 1 = upper band
        """
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        current = float(prices.iloc[-1])
        band_range = float(upper.iloc[-1]) - float(lower.iloc[-1])
        
        if band_range == 0:
            return 0.0
        
        position = 2 * (current - float(lower.iloc[-1])) / band_range - 1
        return float(max(-1, min(1, position)))
    
    @staticmethod
    def _calculate_momentum(prices: pd.Series, period: int = 10) -> float:
        """Calculate price momentum."""
        if len(prices) < period:
            return 0.0
        momentum = (float(prices.iloc[-1]) - float(prices.iloc[-period])) / float(prices.iloc[-period]) * 100
        return float(momentum)
    
    @staticmethod
    def _calculate_atr(data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        atr_val = float(atr.iloc[-1]) if not atr.isna().all() else 0.0
        return atr_val
    
    @staticmethod
    def _evaluate_signals(
        rsi: float,
        macd: float,
        macd_signal: float,
        bb_position: float,
        sma_20: Optional[float],
        sma_50: Optional[float],
        momentum: float,
        sentiment: Dict
    ) -> Tuple[SignalType, SignalStrength, float, str]:
        """Evaluate all indicators to generate signal."""
        
        buy_signals = 0
        sell_signals = 0
        confidence_factors = []
        reasons = []
        
        # RSI analysis
        if rsi < 30:
            buy_signals += 2
            confidence_factors.append(0.8)
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 70:
            sell_signals += 2
            confidence_factors.append(0.8)
            reasons.append(f"RSI overbought ({rsi:.1f})")
        
        # MACD analysis
        if macd > macd_signal:
            buy_signals += 1
            confidence_factors.append(0.6)
            reasons.append("MACD positive crossover")
        else:
            sell_signals += 1
            confidence_factors.append(0.6)
            reasons.append("MACD negative crossover")
        
        # Bollinger Bands analysis
        if bb_position < -0.5:
            buy_signals += 1
            confidence_factors.append(0.7)
            reasons.append("Price near lower Bollinger Band")
        elif bb_position > 0.5:
            sell_signals += 1
            confidence_factors.append(0.7)
            reasons.append("Price near upper Bollinger Band")
        
        # Moving Average analysis
        if sma_20 and sma_50:
            if sma_20 > sma_50:
                buy_signals += 1
                confidence_factors.append(0.5)
                reasons.append("SMA 20 > SMA 50")
            else:
                sell_signals += 1
                confidence_factors.append(0.5)
                reasons.append("SMA 20 < SMA 50")
        
        # Momentum analysis
        if momentum > 2:
            buy_signals += 1
            confidence_factors.append(0.6)
            reasons.append(f"Positive momentum ({momentum:.1f}%)")
        elif momentum < -2:
            sell_signals += 1
            confidence_factors.append(0.6)
            reasons.append(f"Negative momentum ({momentum:.1f}%)")
        
        # Market sentiment
        if sentiment.get('rsi', 50) > 70:
            sell_signals += 0.5
        elif sentiment.get('rsi', 50) < 30:
            buy_signals += 0.5
        
        # Determine signal type and strength
        signal_diff = buy_signals - sell_signals
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
        
        if signal_diff > 4:
            return SignalType.STRONG_BUY, SignalStrength.VERY_STRONG, min(0.95, confidence), " + ".join(reasons)
        elif signal_diff > 2:
            return SignalType.BUY, SignalStrength.STRONG, min(0.85, confidence), " + ".join(reasons)
        elif signal_diff > 0:
            return SignalType.BUY, SignalStrength.MODERATE, confidence, " + ".join(reasons)
        elif signal_diff < -4:
            return SignalType.STRONG_SELL, SignalStrength.VERY_STRONG, min(0.95, confidence), " + ".join(reasons)
        elif signal_diff < -2:
            return SignalType.SELL, SignalStrength.STRONG, min(0.85, confidence), " + ".join(reasons)
        elif signal_diff < 0:
            return SignalType.SELL, SignalStrength.MODERATE, confidence, " + ".join(reasons)
        else:
            return SignalType.HOLD, SignalStrength.WEAK, 0.5, "No clear signal"


# Global instance
_signal_generator: Optional[LiveSignalGenerator] = None


def get_signal_generator() -> LiveSignalGenerator:
    """Get or create global signal generator."""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = LiveSignalGenerator()
    return _signal_generator
```

==================================================
FILE: egx_radar/advanced/risk_management.py
===========================================

```python
"""Advanced risk management tools."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics."""
    value_at_risk: float  # VaR at 95% confidence
    conditional_var: float  # CVaR (Expected Shortfall)
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    return_per_unit_risk: float


class RiskManager:
    """Advanced risk management and sizing."""
    
    def __init__(self, account_size: float = 100000):
        """Initialize risk manager.
        
        Args:
            account_size: Total account size in dollars
        """
        self.account_size = account_size
        self.max_drawdown_pct = 0.20  # 20% max drawdown
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.daily_loss_limit = account_size * 0.05  # 5% daily loss limit
        self.correlation_threshold = 0.7
    
    def calculate_position_size(
        self,
        entry: float,
        stop_loss: float,
        confidence: float = 0.5
    ) -> float:
        """Calculate position size based on risk.
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price
            confidence: Confidence in trade (0-1)
            
        Returns:
            Position size in dollars
        """
        risk_amount = self.account_size * self.risk_per_trade
        risk_per_unit = abs(entry - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        # Adjust for confidence
        position_size = (risk_amount / risk_per_unit) * confidence
        
        # Cap at max drawdown limits
        max_position = self.account_size * (self.max_drawdown_pct / 100)
        position_size = min(position_size, max_position)
        
        return float(position_size)
    
    def calculate_value_at_risk(
        self,
        returns: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """Calculate Value at Risk.
        
        Args:
            returns: Array of returns
            confidence: Confidence level (default 95%)
            
        Returns:
            VaR value
        """
        var = np.percentile(returns, (1 - confidence) * 100)
        return float(var * self.account_size)
    
    def calculate_conditional_var(
        self,
        returns: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall).
        
        Args:
            returns: Array of returns
            confidence: Confidence level
            
        Returns:
            CVaR value
        """
        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()
        return float(cvar * self.account_size)
    
    def calculate_drawdown_metrics(
        self,
        equity_curve: np.ndarray
    ) -> Tuple[float, float, List[float]]:
        """Calculate maximum and current drawdown.
        
        Args:
            equity_curve: Array of equity values over time
            
        Returns:
            (max_drawdown, current_drawdown, drawdown_series)
        """
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max * 100
        
        max_drawdown = np.min(drawdown)
        current_drawdown = drawdown[-1] if len(drawdown) > 0 else 0
        
        return float(max_drawdown), float(current_drawdown), drawdown.tolist()
    
    def calculate_sharpe_ratio(
        self,
        returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe Ratio.
        
        Args:
            returns: Array of daily returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sharpe ratio (annualized)
        """
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        if len(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        return float(sharpe)
    
    def calculate_sortino_ratio(
        self,
        returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sortino Ratio (only penalizes downside volatility).
        
        Args:
            returns: Array of daily returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sortino ratio (annualized)
        """
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        # Downside deviation
        downside = excess_returns[excess_returns < 0]
        downside_std = np.std(downside) if len(downside) > 0 else np.std(excess_returns)
        
        if downside_std == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_std * np.sqrt(252)
        return float(sortino)
    
    def calculate_calmar_ratio(
        self,
        returns: np.ndarray,
        equity_curve: np.ndarray
    ) -> float:
        """Calculate Calmar Ratio (return per unit of max drawdown).
        
        Args:
            returns: Array of daily returns
            equity_curve: Array of equity values
            
        Returns:
            Calmar ratio
        """
        annual_return = np.mean(returns) * 252
        max_dd, _, _ = self.calculate_drawdown_metrics(equity_curve)
        max_dd = abs(max_dd) / 100  # Convert percentage to decimal
        
        if max_dd == 0:
            return 0.0
        
        calmar = annual_return / max_dd
        return float(calmar)
    
    def check_correlation_risk(
        self,
        positions: Dict[str, float],
        correlation_matrix: pd.DataFrame
    ) -> List[Tuple[str, str, float]]:
        """Check for concentration risk in correlated positions.
        
        Args:
            positions: Dict of symbol -> position_size
            correlation_matrix: Correlation matrix of symbols
            
        Returns:
            List of (symbol1, symbol2, correlation) with high correlation
        """
        high_corr_pairs = []
        
        symbols = list(positions.keys())
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                if sym1 in correlation_matrix.index and sym2 in correlation_matrix.columns:
                    corr = correlation_matrix.loc[sym1, sym2]
                    if abs(corr) > self.correlation_threshold:
                        high_corr_pairs.append((sym1, sym2, float(corr)))
        
        return high_corr_pairs
    
    def check_daily_loss_limit(self, daily_pnl: float) -> bool:
        """Check if daily loss limit has been exceeded.
        
        Args:
            daily_pnl: Daily P&L
            
        Returns:
            True if limit exceeded
        """
        return daily_pnl < -self.daily_loss_limit
    
    def calculate_risk_metrics(
        self,
        returns: np.ndarray,
        equity_curve: np.ndarray
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics.
        
        Args:
            returns: Array of daily returns
            equity_curve: Array of equity values
            
        Returns:
            RiskMetrics object
        """
        return RiskMetrics(
            value_at_risk=self.calculate_value_at_risk(returns),
            conditional_var=self.calculate_conditional_var(returns),
            max_drawdown=self.calculate_drawdown_metrics(equity_curve)[0],
            sharpe_ratio=self.calculate_sharpe_ratio(returns),
            sortino_ratio=self.calculate_sortino_ratio(returns),
            calmar_ratio=self.calculate_calmar_ratio(returns, equity_curve),
            return_per_unit_risk=np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        )


class PositionSizer:
    """Intelligent position sizing."""
    
    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate Kelly Criterion for optimal position sizing.
        
        Args:
            win_rate: Percentage of winning trades (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount
            
        Returns:
            Kelly fraction (% of capital to risk)
        """
        if avg_loss == 0 or win_rate == 0 or win_rate == 1:
            return 0.0
        
        loss_rate = 1 - win_rate
        ratio = avg_win / avg_loss
        
        kelly = (win_rate * ratio - loss_rate) / ratio
        
        # Apply safety factor (never bet full Kelly)
        kelly = kelly / 4  # Quarter Kelly is safer
        
        return float(max(0, min(kelly, 0.25)))  # Cap at 25%
    
    @staticmethod
    def optimal_position_size(
        account_size: float,
        entry: float,
        stop_loss: float,
        kelly_fraction: float
    ) -> float:
        """Calculate position size using Kelly fraction.
        
        Args:
            account_size: Total account size
            entry: Entry price
            stop_loss: Stop loss price
            kelly_fraction: Kelly fraction (from Kelly Criterion)
            
        Returns:
            Position size
        """
        risk_amount = account_size * kelly_fraction
        risk_per_unit = abs(entry - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        position_size = risk_amount / risk_per_unit
        return float(position_size)


# Global instance
_risk_manager: Optional[RiskManager] = None


def get_risk_manager(account_size: float = 100000) -> RiskManager:
    """Get or create global risk manager."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager(account_size)
    return _risk_manager
```

==================================================
FILE: egx_radar/core/portfolio.py
=================================

```python
"""Portfolio guard: sector and ATR exposure limits (Layer 7)."""

import logging
from typing import Dict, List, NamedTuple, Tuple

from egx_radar.config.settings import (
    K,
    SECTORS,
    get_account_size,
    get_max_per_sector,
    get_atr_exposure,
)

log = logging.getLogger(__name__)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LAYER 7: PORTFOLIO GUARD â€” Pure function, non-mutating, idempotent
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class GuardedResult(NamedTuple):
    """Immutable wrapper for a result record with guard annotation."""
    result: dict
    guard_reason: str
    is_blocked: bool


def compute_portfolio_guard(
    results: List[dict],
    account_size: float = None,
    open_trades: List[dict] = None,
) -> Tuple[List[GuardedResult], Dict[str, int], float, List[str], bool]:
    """
    FIX-G: Pure function.  Does NOT mutate input `results`.
    Uses live account_size from DATA_SOURCE_CFG so UI changes apply immediately.
    """
    if account_size is None:
        account_size = get_account_size()
    max_per_sector = get_max_per_sector()
    atr_exposure   = get_atr_exposure()
    max_open_trades = int(getattr(K, "PORTFOLIO_MAX_OPEN_TRADES", 3))
    max_sector_exposure_value = account_size * float(getattr(K, "PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT", 0.30))

    active_tags    = {"buy", "ultra", "early"}
    sector_counts: Dict[str, int] = {s: 0 for s in SECTORS}
    sector_notional: Dict[str, float] = {s: 0.0 for s in SECTORS}
    cumulative     = 0.0
    active_positions = 0
    
    # Feature 5: Advanced Portfolio Guard
    # Pre-fill exposure with currently active trades
    if open_trades:
        for t in open_trades:
            sec = t.get("sector")
            if sec in sector_counts:
                sector_counts[sec] += 1
                sector_notional[sec] += float(t.get("entry", 0.0)) * float(t.get("size", 0))
            if t.get("status", "OPEN") == "OPEN":
                active_positions += 1
            # Assuming size and atr are present or can be calculated (using standard risk)
            # If not present, we will estimate based on standard 4% risk
            t_atr = t.get("atr", 0.0)
            if t_atr > 0 and t.get("size"):
                cumulative += (t_atr * t.get("size", 0))
            else:
                # Estimate standard risk deduction if missing from log
                cumulative += account_size * atr_exposure

    max_exposure   = account_size * atr_exposure

    DAILY_LOSS_LIMIT_PCT = 0.03  # Block new entries if daily drawdown exceeds 3%
    daily_pnl = 0.0
    if open_trades:
        for t in open_trades:
            entry  = t.get("entry", 0.0)
            stop   = t.get("stop", 0.0)
            size   = t.get("size", 0)
            status = t.get("status", "OPEN")

            # Use pnl_pct if already resolved (TIMEOUT trades have it)
            if t.get("pnl_pct") is not None and entry > 0 and size > 0:
                daily_pnl += (t["pnl_pct"] / 100) * entry * size
            # For OPEN trades: estimate unrealized at 50% of worst-case stop loss
            # (full worst-case is too conservative; true mark-to-market needs live prices)
            elif status == "OPEN" and entry > 0 and stop > 0 and size > 0:
                worst_case = (stop - entry) * size  # negative number = loss
                daily_pnl += worst_case * 0.5
    daily_loss_triggered = daily_pnl < -(account_size * DAILY_LOSS_LIMIT_PCT)

    guarded:       List[GuardedResult] = []
    blocked_syms:  List[str]           = []

    for r in results:
        if r["tag"] not in active_tags:
            guarded.append(GuardedResult(r, "", False))
            continue

        if daily_loss_triggered and r["tag"] in active_tags:
            guarded.append(GuardedResult(
                r,
                f"\U0001f6d1 Daily loss limit reached ({daily_pnl:.0f} EGP). No new entries.",
                True,
            ))
            blocked_syms.append(r.get("symbol", ""))
            continue

        sector  = r["sector"]
        atr     = r.get("atr") or 0.0
        plan    = r.get("plan") or {}
        size    = plan.get("size", 0)
        entry   = float(plan.get("entry", r.get("price", 0.0)) or 0.0)
        contrib = atr * size
        notional = entry * size

        if active_positions >= max_open_trades:
            reason = f"Open-trade cap reached ({active_positions}/{max_open_trades})"
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        if sector_counts.get(sector, 0) >= max_per_sector:
            reason = (
                f"Sector cap: {sector} already has "
                f"{sector_counts[sector]} signal(s) (max {max_per_sector})"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        if sector_notional.get(sector, 0.0) + notional > max_sector_exposure_value:
            reason = (
                f"Sector exposure cap: {sector} would reach "
                f"{(sector_notional.get(sector, 0.0) + notional):.0f} EGP "
                f"(max {max_sector_exposure_value:.0f} EGP)"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        if cumulative + contrib > max_exposure:
            reason = (
                f"ATR cap: +{contrib:.0f} EGP would bring total to "
                f"{(cumulative+contrib):.0f} EGP "
                f"({(cumulative+contrib)/max(1e-9, account_size)*100:.1f}% of account, "
                f"max {atr_exposure*100:.0f}%)"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        sector_notional[sector] = sector_notional.get(sector, 0.0) + notional
        cumulative += contrib
        active_positions += 1
        guarded.append(GuardedResult(r, "", False))

    return guarded, sector_counts, cumulative, blocked_syms, daily_loss_triggered
```

==================================================
FILE: egx_radar/core/risk.py
============================

```python
"""Risk engine: trade plan construction and institutional confidence (Layer 6)."""

import logging
from typing import Optional, Tuple

from egx_radar.config.settings import (
    K,
    get_account_size,
    get_risk_per_trade,
)
from egx_radar.core.indicators import safe_clamp

log = logging.getLogger(__name__)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LAYER 6: RISK ENGINE â€” ATR-percentile sizing, dynamic thresholds
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


def build_trade_plan(
    price: float, rsi: float, adx: float, clv: float,
    trend_acc: float, smart_rank: float, anticipation: float,
    atr_risk_label: str = "â€”",
    atr: Optional[float] = None,
    tech_score: int = 0,
    vol_ratio: float = 1.0,
    size_multiplier: float = 1.0,
) -> dict:
    """
    Produce an actionable trade plan.

    FIX-1: Thresholds now relative to SMART_RANK_SCALE (was hardcoded 7/5
            which is only 12% of the 60-point scale â€” effectively meaningless).
            New thresholds: ACCUMULATE >= 40%, PROBE >= 28%, WATCH_ONLY >= 15%.
    FIX-3: ADX soft-low gate has exception for very high tech_score + strong volume
            so strong momentum moves are not silently ignored.
    """
    _sr = K.SMART_RANK_SCALE   # 60.0

    if adx < K.ADX_SOFT_LO:
        # Relaxed gate: allow PROBE if overall evidence is strong enough
        # even when ADX is slightly below threshold (accumulation phase stocks
        # often have low ADX by design â€” worth probing on strong flow/anticipation)
        if tech_score >= 12 and vol_ratio > 2.0:
            action = "PROBE"
        elif smart_rank >= K.SMART_RANK_SCALE * 0.40 and anticipation > 0.5:
            # High rank + strong flow anticipation = worth probing despite low ADX
            action = "PROBE"
        else:
            action = "WAIT"
    elif adx < K.ADX_SOFT_HI:
        # FIX-1: was >= 6.0 (10% of scale) â†’ now 22% of scale
        action = "PROBE" if smart_rank >= _sr * 0.22 else "WAIT"
    else:
        # FIX-1: was > 7 (12%) / > 5 (8%) â†’ now 40% / 28% / 15%
        if smart_rank > _sr * 0.40 and anticipation > K.PLAN_ANTICIPATION_HI:
            action = "ACCUMULATE"
        elif smart_rank > _sr * 0.28:
            action = "PROBE"
        elif smart_rank > _sr * 0.15:
            action = "WATCH_ONLY"
        else:
            action = "WAIT"

    # Extra gate: never ACCUMULATE into HIGH-risk ATR environment
    if action == "ACCUMULATE" and atr_risk_label == "âš ï¸ HIGH":
        action = "PROBE"

    if adx < K.ADX_SOFT_HI:
        stop = round(price * K.PLAN_STOP_ADX_LOW, 2)
    elif clv > 0.5 and trend_acc > 0:
        stop = round(price * K.PLAN_STOP_CLV_HIGH, 2)
    else:
        stop = round(price * K.PLAN_STOP_DEFAULT, 2)

    entry  = round(price * K.PLAN_ENTRY_DISCOUNT, 2)
    target = round(
        price * (K.PLAN_TARGET_HIGH if anticipation > K.PLAN_ANTICIPATION_HI else K.PLAN_TARGET_DEFAULT),
        2,
    )

    # Guard: entry â‰ˆ stop â‡’ RR is undefined; return WAIT to avoid div-by-zero sizing
    if abs(entry - stop) < 0.001 * price:
        return {
            "action": "WAIT", "entry": entry, "stop": stop, "target": price,
            "size": 0, "rr": float('nan'), "timeframe": "â€”",
            "force_wait": True, "winrate": 0.0, "winrate_na": True, "rr_invalid": True,
        }

    # â”€â”€ Risk-based position sizing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    account_size = get_account_size()
    risk_amount = account_size * get_risk_per_trade()
    rps = abs(entry - stop)
    share_count = max(1, int(risk_amount / rps))

    # â”€â”€ Unified multiplier application (SINGLE application point) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _size_mult = max(K.SIZE_MULTIPLIER_FLOOR, float(size_multiplier or 1.0))
    share_count = max(1, int(share_count * _size_mult))
    rr   = round(abs(target - entry) / rps, 1)

    atr_pct = (atr / price * 100) if (atr and price > 0) else 0.0
    if adx > 35 and atr_pct > K.ATR_INTRADAY_THRESH:
        timeframe = "âš¡ Intraday"
    elif adx > K.ADX_STRONG:
        timeframe = "ðŸ“… Swing (3-10d)"
    else:
        timeframe = "ðŸ“† Position (wks)"

    return {
        "action": action, "entry": entry, "stop": stop,
        "target": target, "size": share_count, "rr": rr,
        "timeframe": timeframe,
        "force_wait": action == "WAIT",
        "winrate": 0.0,   # filled by estimate_winrate() in scoring pass
        "winrate_na": action == "WAIT",
    }


def institutional_confidence(winrate: float, smart_rank: float, sector_strength: float,
                             dg_tier: str = "", mg_passed: bool = True) -> str:
    """Calculate institutional confidence label based on rank, strength, and guard results."""
    score = winrate * 0.5 + smart_rank * 5 + sector_strength * 8
    # FIX-5: guard-based penalties
    if dg_tier == "DEGRADED":
        score *= 0.85
    elif dg_tier == "REJECTED":
        score *= 0.60
    if not mg_passed:
        score *= 0.90
    if score > 90: return "ðŸ”¥ ELITE"
    if score > 70: return "ðŸ’Ž STRONG"
    if score > 55: return "ðŸ§  GOOD"
    if score > 40: return "âš ï¸ MID"
    return "âŒ WEAK"


def compute_dynamic_stop(
    current_price: float, entry: float, current_stop: float, current_target: float,
    momentum: float, regime: str, is_short: bool = False
) -> Tuple[float, float, str]:
    """
    Feature 2: Dynamic Trailing Take-Profit
    Adjusts standard static stops/targets based on live trailing mathematics.
    Returns (new_stop, new_target, reason)
    """
    new_stop = current_stop
    new_target = current_target
    reason = "HELD"
    
    if is_short:
        # PnL logic reversed
        pnl_pct = ((entry - current_price) / (entry + 1e-9)) * 100
        if pnl_pct > 3.0:
            trail_stop = current_price * 1.02  # Trail 2% behind price
            if trail_stop < current_stop:
                new_stop = trail_stop
                reason = "TRAILEDâ¬‡"
            if momentum < -2.0:
                new_target = current_target * 0.98 # Expand downside target
                reason += " | EXPANDED"
    else:
        pnl_pct = ((current_price - entry) / (entry + 1e-9)) * 100
        
        # Scenario: Strongly winning, start trailing the stop up
        if pnl_pct > 3.0:
            trail_stop = current_price * 0.98  # Trail 2% below price
            if trail_stop > current_stop:
                new_stop = trail_stop
                reason = "TRAILEDâ¬†"
                
            # If momentum is very strong, push the target higher instead of selling
            if momentum > 2.0 and regime == "MOMENTUM":
                new_target = current_target * 1.02
                reason += " | EXPANDED"
                
        # Scenario: Exhaustion while winning (Momentum death) â†’ clamp stop aggressively
        elif pnl_pct > 1.0 and momentum < 0 and regime != "MOMENTUM":
            trail_stop = current_price * 0.99
            if trail_stop > current_stop:
                new_stop = trail_stop
                reason = "EXHAUSTION CLAMP"
    
    return round(new_stop, 3), round(new_target, 3), reason
```

==================================================
FILE: egx_radar/backtest/__init__.py
====================================

```python
"""Backtest module: walk-forward replay of signal logic on historical OHLCV."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from egx_radar.backtest.data_loader import load_backtest_data
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics
from egx_radar.backtest.missed_trades import run_missed_trade_analysis
from egx_radar.backtest.tracking_dashboard import run_dashboard

__all__ = [
    "load_backtest_data",
    "run_backtest",
    "compute_metrics",
    "run_missed_trade_analysis",
    "run_dashboard",
]


def open_backtest_window(root) -> None:
    """Lazy import to avoid circular import with ui."""
    from egx_radar.backtest.report import open_backtest_window as _open
    _open(root)
```

==================================================
FILE: egx_radar/backtest/dashboard.py
=====================================

```python
from __future__ import annotations

"""Console-friendly performance dashboard helpers for the EGX backtest engine."""

from typing import Any, Dict, List, Optional

from egx_radar.backtest.metrics import compute_metrics
from egx_radar.backtest.missed_trades import run_missed_trade_analysis


def build_performance_dashboard(
    trades: List[dict],
    diagnostics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metrics = compute_metrics(trades)
    missed_entries = list((diagnostics or {}).get("missed_entries") or [])
    approx_returns = [
        float(m["approx_pnl_pct"])
        for m in missed_entries
        if m.get("approx_pnl_pct") is not None
    ]

    # Full missed trade intelligence analysis
    missed_intel = run_missed_trade_analysis(missed_entries=missed_entries)
    analysis = missed_intel.get("analysis", {})

    return {
        "overall": metrics.get("overall", {}),
        "by_trade_type": metrics.get("per_trade_type", {}),
        "monthly": metrics.get("monthly", []),
        "missed_trades": {
            "count": len(missed_entries),
            "approx_avg_return_pct": round(sum(approx_returns) / len(approx_returns), 2) if approx_returns else 0.0,
            "approx_total_return_pct": round(sum(approx_returns), 2) if approx_returns else 0.0,
            "samples": missed_entries[:10],
        },
        "missed_trade_analysis": analysis,
        "missed_trade_report": missed_intel.get("text", ""),
        "metrics": metrics,
    }


def render_console_report(
    dashboard: Dict[str, Any],
    title: str = "SYSTEM PERFORMANCE",
) -> str:
    overall = dashboard.get("overall", {})
    by_type = dashboard.get("by_trade_type", {})
    missed = dashboard.get("missed_trades", {})
    monthly = dashboard.get("monthly", [])

    lines = [
        f"=== {title} ===",
        f"Total Trades: {overall.get('total_trades', 0)}",
        f"Win Rate: {overall.get('win_rate_pct', 0.0)}%",
        f"Avg Return: {overall.get('avg_return_pct', 0.0)}%",
        f"Max Drawdown: {overall.get('max_drawdown_pct', 0.0)}%",
        "",
        "--- By Type ---",
    ]

    for trade_type in ("STRONG", "MEDIUM"):
        stats = by_type.get(trade_type, {})
        lines.append(
            f"{trade_type}: count={stats.get('total_trades', 0)} | "
            f"win={stats.get('win_rate_pct', 0.0)}% | "
            f"avg_return={stats.get('avg_return_pct', 0.0)}% | "
            f"avg_risk={stats.get('avg_risk_used_pct', 0.0)}%"
        )

    lines.extend(
        [
            "",
            "--- Missed Trades ---",
            f"Trigger-ready but not filled: {missed.get('count', 0)}",
            f"Approx Avg Return If Forced In: {missed.get('approx_avg_return_pct', 0.0)}%",
            f"Approx Total Return If Forced In: {missed.get('approx_total_return_pct', 0.0)}%",
        ]
    )

    # Append full missed trade intelligence report if available
    missed_report = dashboard.get("missed_trade_report", "")
    if missed_report:
        lines.extend(["", missed_report])

    lines.extend(["", "--- Trades Per Month ---"])

    if monthly:
        for item in monthly:
            lines.append(
                f"{item.get('month', 'n/a')}: "
                f"count={item.get('trade_count', 0)} | "
                f"return={item.get('return_pct', 0.0)}% | "
                f"win={item.get('win_rate_pct', 0.0)}%"
            )
    else:
        lines.append("No closed trades.")

    return "\n".join(lines)


__all__ = [
    "build_performance_dashboard",
    "render_console_report",
]
```

==================================================
FILE: egx_radar/backtest/data_loader.py
=======================================

```python
from __future__ import annotations

"""Load historical OHLCV for backtest date range (2020-01-01 to today)."""

import logging
from typing import Dict

import pandas as pd
import yfinance as yf

from egx_radar.config.settings import K, SYMBOLS

log = logging.getLogger(__name__)


def load_backtest_data(
    date_from: str,
    date_to: str,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical OHLCV for all watchlist symbols over [date_from, date_to].
    Returns Dict[key=yahoo_ticker e.g. "COMI.CA", value=DataFrame with DatetimeIndex].
    Uses only past data; no look-ahead.
    """
    sym_list = list(SYMBOLS.values())
    result: Dict[str, pd.DataFrame] = {}
    for chunk_start in range(0, len(sym_list), K.CHUNK_SIZE):
        chunk = sym_list[chunk_start : chunk_start + K.CHUNK_SIZE]
        try:
            raw = yf.download(
                chunk,
                start=date_from,
                end=date_to,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                timeout=K.DOWNLOAD_TIMEOUT,
                threads=True,
            )
        except Exception as exc:
            log.warning("Backtest yfinance chunk %s failed: %s", chunk, exc)
            continue
        if raw is None or raw.empty:
            continue
        if len(chunk) == 1 and not isinstance(raw.columns, pd.MultiIndex):
            sub = _flatten(raw)
            if sub is not None and len(sub) >= K.MIN_BARS:
                result[chunk[0]] = sub
            continue
        for ticker in chunk:
            sub = _extract_ticker(raw, ticker)
            if sub is not None and len(sub) >= K.MIN_BARS:
                result[ticker] = sub
    return result


def _flatten(raw: pd.DataFrame) -> pd.DataFrame | None:
    if raw is None or raw.empty:
        return None
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip().title() for c in df.columns]
    df.rename(columns={
        "Adj Close": "Close",
        "Adjusted Close": "Close",
        "Adj_Close": "Close",
        "Turnover": "Volume",
    }, inplace=True)
    # Deduplicate columns if any (keep first)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # FIX-3D: OHLCV sanity check â€” verify Close is between Low and High on last bar.
    # If this fails, yfinance likely changed its column mapping in a new version.
    if len(df) > 0 and {"Close", "High", "Low"}.issubset(df.columns):
        last = df.iloc[-1]
        try:
            c = float(last["Close"])
            h = float(last["High"])
            l = float(last["Low"])
            if h > 0 and l > 0 and not (l <= c <= h):
                log.warning(
                    "_flatten: OHLCV sanity check failed on last bar "
                    "(Close=%.4f High=%.4f Low=%.4f). "
                    "Possible yfinance column inversion after API update. "
                    "Pin yfinance version in requirements.txt.",
                    c, h, l,
                )
                return None   # reject silently-corrupt data rather than pass it on
        except (TypeError, ValueError):
            pass   # NaN values â€” downstream layers will handle these
    
    return df if "Close" in df.columns else None


def _extract_ticker(raw: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    if raw is None or raw.empty:
        return None
    if not isinstance(raw.columns, pd.MultiIndex):
        return _flatten(raw)
    if ticker in raw.columns.get_level_values(0):
        try:
            return _flatten(raw[ticker].copy())
        except Exception:
            pass
    if ticker in raw.columns.get_level_values(1):
        try:
            return _flatten(raw.xs(ticker, axis=1, level=1).copy())
        except Exception:
            pass
    return None
```

==================================================
FILE: egx_radar/backtest/engine.py
==================================

```python
from __future__ import annotations

"""Conservative EGX backtest engine with live/backtest signal parity."""

import logging
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from egx_radar.backtest.data_loader import load_backtest_data
from egx_radar.config.settings import (
    K,
    DECISION_PRIORITY,
    SYMBOLS,
    get_account_size,
    get_risk_per_trade,
    get_sector,
)
from egx_radar.core.portfolio import compute_portfolio_guard
from egx_radar.core.signal_engine import (
    apply_regime_gate,
    candle_hits_trigger,
    detect_conservative_market_regime,
    evaluate_symbol_snapshot,
    trigger_fill_tolerance,
)

log = logging.getLogger(__name__)

REGIME_MAP = {"BULL": "BULL", "BEAR": "BEAR", "NEUTRAL": "NEUTRAL"}
LOW_TURNOVER_PRUNE_EGP = 7_000_000.0
MEDIUM_MAX_STOP_LOSS_PCT = 0.028
MEDIUM_MIN_ADX = 13.0


def detect_market_regime(index_df: pd.DataFrame) -> str:
    """Classify the broad market as STRONG or WEAK using the proxy index series."""
    if index_df is None or len(index_df) < 210:
        return "WEAK"
    required_cols = {"High", "Low", "Close"}
    if not required_cols.issubset(index_df.columns):
        return "WEAK"

    close = index_df["Close"].astype(float)
    high = index_df["High"].astype(float)
    low = index_df["Low"].astype(float)
    price = float(close.iloc[-1]) if not close.empty else 0.0
    if price <= 0.0:
        return "WEAK"

    ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])
    price_near_ema50 = abs(price - ema50) / max(ema50, 1e-9) <= K.MARKET_REGIME_EMA_NEAR_PCT

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    atr_last = float(atr.iloc[-1]) if not atr.dropna().empty else 0.0
    atr_pct = atr_last / max(price, 1e-9)

    plus_di = 100.0 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr.replace(0.0, pd.NA)
    minus_di = 100.0 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr.replace(0.0, pd.NA)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, pd.NA)
    adx = float(dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().fillna(0.0).iloc[-1])

    returns = close.pct_change().dropna().tail(K.MARKET_REGIME_VOL_LOOKBACK)
    recent_std = float(returns.std()) if not returns.empty else 0.0

    lookback = min(K.MARKET_REGIME_HIGHER_HIGHS_LOOKBACK, len(high))
    recent_window = min(K.MARKET_REGIME_RECENT_WINDOW, lookback)
    recent_highs = high.tail(recent_window)
    prior_highs = high.tail(lookback).head(max(lookback - recent_window, 1))
    recent_lows = low.tail(recent_window)
    prior_lows = low.tail(lookback).head(max(lookback - recent_window, 1))
    higher_highs = bool(not recent_highs.empty and not prior_highs.empty and recent_highs.max() > prior_highs.max())
    higher_lows = bool(not recent_lows.empty and not prior_lows.empty and recent_lows.min() > prior_lows.min())

    strong_trend = (
        price > ema50 > ema200
        and adx > K.MARKET_REGIME_STRONG_ADX
        and higher_highs
        and higher_lows
        and atr_pct <= K.MARKET_REGIME_ATR_PCT_MAX_STRONG
        and recent_std <= K.MARKET_REGIME_STD_MAX_STRONG
    )
    if strong_trend:
        return "STRONG"

    weak_trend = (
        price_near_ema50
        or adx < K.MARKET_REGIME_WEAK_ADX
        or price <= ema50
        or ema50 <= ema200
        or not higher_highs
        or recent_std > K.MARKET_REGIME_STD_MAX_STRONG
    )
    return "WEAK" if weak_trend else "STRONG"


def _yahoo_to_sym() -> Dict[str, str]:
    return {v: k for k, v in SYMBOLS.items()}


def _build_results_for_day(
    all_data: Dict[str, pd.DataFrame],
    date: pd.Timestamp,
    yahoo_to_sym: Dict[str, str],
) -> Tuple[List[dict], Dict[str, float], str, str]:
    results: List[dict] = []
    sector_strength: Dict[str, List[float]] = {}
    market_regime = "WEAK"

    proxy_df = all_data.get(K.EGX30_SYMBOL)
    if proxy_df is not None and date in proxy_df.index:
        proxy_slice = proxy_df[proxy_df.index <= date].tail(260).copy()
        market_regime = detect_market_regime(proxy_slice)

    for yahoo, df in all_data.items():
        sym = yahoo_to_sym.get(yahoo)
        if not sym or date not in df.index:
            continue
        df_slice = df[df.index <= date].tail(260).copy()
        if df_slice.empty:
            continue
        result = evaluate_symbol_snapshot(
            df_ta=df_slice,
            sym=sym,
            sector=get_sector(sym),
            regime="BULL",
        )
        if result is None:
            continue
        results.append(result)
        sector_strength.setdefault(result["sector"], []).append(result["quantum"])

    if not results:
        return [], {}, "NEUTRAL", market_regime

    regime = detect_conservative_market_regime(results)
    if regime != "BULL":
        results = [apply_regime_gate(r, regime) for r in results]

    sector_strength_avg = {
        sec: (sum(vals) / len(vals) if vals else 0.0)
        for sec, vals in sector_strength.items()
    }
    return results, sector_strength_avg, regime, market_regime


def _find_next_bar_date(df: pd.DataFrame, current_date: pd.Timestamp) -> Optional[pd.Timestamp]:
    future_dates = df.index[df.index > current_date]
    return future_dates[0] if len(future_dates) else None


def _trade_notional(entry: float, size: int, account_size: float) -> float:
    return min((entry * size) / max(account_size, 1e-9), K.PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT)


def _is_strong_rejection_candle(row: pd.Series) -> bool:
    open_px = float(row["Open"])
    high_px = float(row["High"])
    low_px = float(row["Low"])
    close_px = float(row["Close"])
    candle_range = max(high_px - low_px, 1e-9)
    body_fraction = abs(close_px - open_px) / candle_range
    close_position = (close_px - low_px) / candle_range
    return close_px < open_px and body_fraction >= 0.75 and close_position <= 0.10


# â”€â”€ High-Probability Trade Filter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Capital preservation gate: only allow trades that pass ALL quality checks.
# This is the core of the win-rate optimization system.

def _is_high_probability_trade(r: dict) -> bool:
    """
    Multi-factor quality gate for high-probability setups.
    Uses a scoring approach: each check adds a point, and the trade
    must meet a minimum quality score to pass.
    
    Hard disqualifiers are checked first (instant reject).
    Soft checks are scored with tier-aware thresholds.
    """
    # â”€â”€ Hard disqualifiers (instant reject) â”€â”€
    # Fake moves and erratic volume are unreliable signals
    if r.get("fake_move", False):
        return False
    if r.get("erratic_volume", False):
        return False
    if float(r.get("smart_rank", 0.0) or 0.0) < 50.0:
        return False
    if float(r.get("avg_turnover", 0.0) or 0.0) < LOW_TURNOVER_PRUNE_EGP:
        return False
    # Don't buy into late-stage moves
    zone = str(r.get("zone", "")).upper()
    if "LATE" in zone:
        return False

    trade_type = str(r.get("trade_type", "")).upper()
    if not trade_type:
        smart_rank = float(r.get("smart_rank", 0.0) or 0.0)
        if smart_rank >= K.TRADE_TYPE_STRONG_MIN:
            trade_type = "STRONG"
        elif smart_rank >= K.TRADE_TYPE_MEDIUM_MIN:
            trade_type = "MEDIUM"
    if trade_type == "MEDIUM":
        if float(r.get("adx", 0.0) or 0.0) < MEDIUM_MIN_ADX:
            return False
    
    # â”€â”€ Soft quality checks (scoring) â”€â”€
    score = 0
    max_score = 10
    
    # 1. Accumulation detected (strong base building)
    if r.get("accumulation_detected", False):
        score += 1
    
    # 2. Higher lows pattern (clean support)
    if r.get("higher_lows", False):
        score += 1
    
    # 3. Price above EMA50 (short-term trend up)
    if r.get("price", 0) > r.get("ema50", 0):
        score += 1
    
    # 4. Price above EMA200 (long-term trend up)
    if r.get("price", 0) > r.get("ema200", 0):
        score += 1
    
    # 5. RSI not overbought (room to run)
    rsi = r.get("rsi", 50)
    if 40 <= rsi <= 70:
        score += 1
    
    # 6. Volume confirmed (institutional interest)
    if r.get("volume_confirmed", False):
        score += 1
    
    # 7. Volume not spiking (stable participation)
    if r.get("vol_ratio", 1.0) <= 2.5:
        score += 1
    
    # 8. No excessive recent gains (not chasing)
    if abs(r.get("two_day_gain_pct", 0)) <= 5.0:
        score += 1
    
    # 9. Structure strength decent
    if r.get("structure_strength_score", 0) >= 50:
        score += 1
    
    # 10. Accumulation quality decent
    if r.get("accumulation_quality_score", 0) >= 60:
        score += 1
    
    # Precision tuning: keep STRONG flow unchanged, tighten MEDIUM slightly.
    required_checks = 5 if trade_type == "STRONG" else 6 if trade_type == "MEDIUM" else 5
    return score >= required_checks


def _build_open_trade(
    pending: dict,
    entry_base: float,
    account_size: float,
    entry_date: pd.Timestamp,
    fill_mode: str,
) -> dict:
    entry = round(entry_base * (1.0 + K.BT_SLIPPAGE_PCT / 2.0), 3)
    trade_type = str(pending.get("trade_type", "")).upper()
    stop_cap = MEDIUM_MAX_STOP_LOSS_PCT if trade_type == "MEDIUM" else K.MAX_STOP_LOSS_PCT
    stop = round(entry * (1.0 - min(float(pending["risk_pct"]), stop_cap)), 3)
    target = round(entry * (1.0 + float(pending["target_pct"])), 3)
    partial_target = round(entry * (1.0 + K.PARTIAL_TP_PCT), 3)
    trailing_trigger = round(entry * (1.0 + K.TRAILING_TRIGGER_PCT), 3)

    risk_fraction = float(pending.get("risk_used") or get_risk_per_trade())
    risk_amount = account_size * risk_fraction
    risk_per_share = max(entry - stop, entry * 0.005)
    size = max(1, int(risk_amount / max(risk_per_share, 1e-9))) if risk_amount > 0 else 0
    max_notional_shares = max(
        1,
        int((account_size * K.PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT) / max(entry, 1e-9)),
    )
    if size > 0:
        size = min(size, max_notional_shares)

    return {
        "sym": pending["sym"],
        "sector": pending["sector"],
        "signal_type": pending["signal_type"],
        "regime": pending["regime"],
        "signal_date": pending["signal_date"],
        "entry_date": entry_date.strftime("%Y-%m-%d"),
        "entry": entry,
        "initial_stop": stop,
        "stop": stop,
        "target": target,
        "partial_target": partial_target,
        "trailing_trigger": trailing_trigger,
        "trailing_stop_pct": float(K.TRAILING_STOP_PCT),
        "bars_held": 0,
        "status": "OPEN",
        "smart_rank": pending["smart_rank"],
        "score": pending.get("score", pending["smart_rank"]),
        "trade_type": pending.get("trade_type", "UNCLASSIFIED"),
        "risk_used": round(risk_fraction, 4),
        "anticipation": pending["anticipation"],
        "atr": pending["atr"],
        "size": size,
        "partial_taken": False,
        "partial_exit_price": None,
        "remaining_fraction": 1.0,
        "trailing_active": False,
        "trailing_anchor": entry,
        "trigger_price": float(pending.get("trigger_price") or entry_base),
        "fill_mode": fill_mode,
    }


def _process_trade_bar(trade: dict, row: pd.Series, max_bars: int) -> Tuple[dict, Optional[float], Optional[str]]:
    open_px = float(row["Open"])
    high = float(row["High"])
    low = float(row["Low"])
    close = float(row["Close"])
    trade["bars_held"] += 1

    exit_price = None
    outcome = None

    if open_px <= trade["stop"]:
        exit_price = round(open_px * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
        # FIX: classify by actual PnL, not just stop-hit event
        outcome = "STOP_HIT"  # resolved to WIN/LOSS in _close_trade by PnL
    elif low <= trade["stop"]:
        exit_price = round(trade["stop"] * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
        outcome = "STOP_HIT"  # resolved to WIN/LOSS in _close_trade by PnL
    else:
        if (not trade["partial_taken"]) and high >= trade["partial_target"]:
            trade["partial_taken"] = True
            trade["remaining_fraction"] = 0.5
            trade["partial_exit_price"] = round(
                trade["partial_target"] * (1.0 - K.BT_SLIPPAGE_PCT / 2.0),
                3,
            )
            trade["stop"] = max(trade["stop"], trade["entry"])

        if high >= trade["trailing_trigger"]:
            trade["trailing_active"] = True
            trade["trailing_anchor"] = max(trade.get("trailing_anchor", trade["entry"]), high)

        if trade.get("trailing_active"):
            trailing_stop = trade["trailing_anchor"] * (1.0 - trade["trailing_stop_pct"])
            trade["stop"] = max(trade["stop"], trailing_stop)

        if high >= trade["target"]:
            exit_price = round(trade["target"] * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "WIN"
        elif trade["bars_held"] >= max_bars:
            exit_price = round(close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "EXIT"

    return trade, exit_price, outcome


def _simulate_trade_path(
    trade: dict,
    df: pd.DataFrame,
    start_date: pd.Timestamp,
    account_size: float,
    max_bars: int,
) -> Optional[dict]:
    if df is None or df.empty:
        return None
    future = df[df.index >= start_date]
    if future.empty:
        return None

    sim_trade = dict(trade)
    for sim_date, row in future.iterrows():
        sim_trade, exit_price, outcome = _process_trade_bar(sim_trade, row, max_bars)
        if outcome is None:
            continue
        return _close_trade(sim_trade, sim_date, exit_price, outcome, account_size)

    last_date = future.index[-1]
    last_close = float(future.iloc[-1]["Close"])
    exit_price = round(last_close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
    return _close_trade(sim_trade, last_date, exit_price, "EXIT", account_size)


def _activate_pending_trades(
    date: pd.Timestamp,
    pending_entries: List[dict],
    open_trades: List[dict],
    all_data: Dict[str, pd.DataFrame],
    account_size: float,
    missed_entries: List[dict],
    entry_mode: str,
    max_bars: int,
) -> List[dict]:
    remaining_pending: List[dict] = []
    for pending in pending_entries:
        if pending["activation_date"] != date:
            remaining_pending.append(pending)
            continue

        yahoo = SYMBOLS.get(pending["sym"])
        if not yahoo or yahoo not in all_data or date not in all_data[yahoo].index:
            continue

        row = all_data[yahoo].loc[date]
        open_px = float(row["Open"])
        high_px = float(row["High"])
        if open_px <= 0:
            continue
        trigger_price = float(pending.get("trigger_price") or 0.0)
        trigger_tolerance = trigger_fill_tolerance(trigger_price)

        if entry_mode == "open_only":
            filled = trigger_price <= 0 or open_px + trigger_tolerance >= trigger_price
            entry_base = open_px
            fill_mode = "next_open"
            miss_reason = "open_below_trigger"
        else:
            filled = candle_hits_trigger(high_px, trigger_price)
            entry_base = trigger_price if trigger_price > 0 else open_px
            fill_mode = "next_candle_touch"
            miss_reason = "trigger_not_touched"

        if not filled:
            missed_trade = {
                "sym": pending["sym"],
                "sector": pending["sector"],
                "signal_date": pending["signal_date"],
                "activation_date": date.strftime("%Y-%m-%d"),
                "trigger_price": round(trigger_price, 3),
                "next_open": round(open_px, 3),
                "next_high": round(high_px, 3),
                "trade_type": pending.get("trade_type", "UNCLASSIFIED"),
                "score": round(float(pending.get("score", pending.get("smart_rank", 0.0))), 2),
                "risk_used": round(float(pending.get("risk_used") or 0.0), 4),
                "reason": miss_reason,
            }
            forced_trade = _build_open_trade(
                pending,
                entry_base=open_px,
                account_size=account_size,
                entry_date=date,
                fill_mode="forced_open_approx",
            )
            approx = _simulate_trade_path(
                forced_trade,
                all_data[yahoo],
                date,
                account_size,
                max_bars,
            )
            if approx is not None:
                missed_trade["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                missed_trade["approx_outcome"] = approx.get("outcome", "EXIT")
                missed_trade["approx_exit_date"] = approx.get("exit_date", "")
            missed_entries.append(missed_trade)
            continue

        if str(pending.get("trade_type", "")).upper() == "MEDIUM" and _is_strong_rejection_candle(row):
            missed_trade = {
                "sym": pending["sym"],
                "sector": pending["sector"],
                "signal_date": pending["signal_date"],
                "activation_date": date.strftime("%Y-%m-%d"),
                "trigger_price": round(trigger_price, 3),
                "next_open": round(open_px, 3),
                "next_high": round(high_px, 3),
                "trade_type": pending.get("trade_type", "UNCLASSIFIED"),
                "score": round(float(pending.get("score", pending.get("smart_rank", 0.0))), 2),
                "risk_used": round(float(pending.get("risk_used") or 0.0), 4),
                "reason": "next_candle_rejection",
            }
            forced_trade = _build_open_trade(
                pending,
                entry_base=entry_base,
                account_size=account_size,
                entry_date=date,
                fill_mode="forced_rejection_approx",
            )
            approx = _simulate_trade_path(
                forced_trade,
                all_data[yahoo],
                date,
                account_size,
                max_bars,
            )
            if approx is not None:
                missed_trade["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                missed_trade["approx_outcome"] = approx.get("outcome", "EXIT")
                missed_trade["approx_exit_date"] = approx.get("exit_date", "")
            missed_entries.append(missed_trade)
            continue

        open_trades.append(
            _build_open_trade(
                pending,
                entry_base=entry_base,
                account_size=account_size,
                entry_date=date,
                fill_mode=fill_mode,
            )
        )
    return remaining_pending


def _close_trade(
    trade: dict,
    exit_date: pd.Timestamp,
    exit_price: float,
    outcome: str,
    account_size: float,
) -> dict:
    partial_return_pct = 0.0
    partial_taken = bool(trade.get("partial_taken"))
    if partial_taken and trade.get("partial_exit_price"):
        partial_return_pct = 0.5 * (
            (float(trade["partial_exit_price"]) - trade["entry"]) / max(trade["entry"], 1e-9) * 100.0
        )
    remaining_fraction = 0.5 if partial_taken else 1.0
    remaining_return_pct = remaining_fraction * (
        (exit_price - trade["entry"]) / max(trade["entry"], 1e-9) * 100.0
    )
    gross_return_pct = partial_return_pct + remaining_return_pct
    pnl_pct = gross_return_pct - (K.BT_FEES_PCT * 100.0)
    stop_dist_pct = max(
        ((trade["entry"] - trade["initial_stop"]) / max(trade["entry"], 1e-9)) * 100.0,
        0.01,
    )
    rr = gross_return_pct / stop_dist_pct
    alloc_pct = _trade_notional(trade["entry"], trade["size"], account_size)

    # FIX: Resolve STOP_HIT outcome by actual PnL â€” a profitable stop-hit is WIN
    if outcome == "STOP_HIT":
        outcome = "WIN" if pnl_pct > 0 else "LOSS"

    resolved = dict(trade)
    resolved.update(
        {
            "exit_date": exit_date.strftime("%Y-%m-%d"),
            "exit": round(exit_price, 3),
            "pnl_pct": round(pnl_pct, 2),
            "gross_return_pct": round(gross_return_pct, 2),
            "rr": round(rr, 2),
            "outcome": outcome,
            "alloc_pct": round(alloc_pct, 4),
        }
    )
    return resolved


def _update_open_trades(
    date: pd.Timestamp,
    open_trades: List[dict],
    closed_trades: List[dict],
    all_data: Dict[str, pd.DataFrame],
    account_size: float,
    equity: float,
    max_bars: int,
) -> Tuple[List[dict], float]:
    still_open: List[dict] = []

    for trade in open_trades:
        yahoo = SYMBOLS.get(trade["sym"])
        if not yahoo or yahoo not in all_data or date not in all_data[yahoo].index:
            still_open.append(trade)
            continue

        row = all_data[yahoo].loc[date]
        trade, exit_price, outcome = _process_trade_bar(trade, row, max_bars)

        if outcome is None:
            still_open.append(trade)
            continue

        resolved = _close_trade(trade, date, exit_price, outcome, account_size)
        equity *= 1.0 + resolved["alloc_pct"] * resolved["pnl_pct"] / 100.0
        resolved["equity_after"] = round(equity, 4)
        closed_trades.append(resolved)

    return still_open, equity


def run_backtest(
    date_from: str,
    date_to: str,
    max_bars: int = K.BT_MAX_BARS,
    max_concurrent_trades: int = K.PORTFOLIO_MAX_OPEN_TRADES,
    entry_mode: str = "touch",
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[List[dict], List[Tuple[str, float]], Dict[str, Any], Dict[str, Any]]:
    all_data = load_backtest_data(date_from, date_to)
    if not all_data:
        empty_params = {
            "date_from": date_from,
            "date_to": date_to,
            "max_bars": max_bars,
            "entry_mode": entry_mode,
        }
        return [], [], empty_params, {"missed_entries": []}

    yahoo_to_sym = _yahoo_to_sym()
    all_dates: List[pd.Timestamp] = sorted({d for df in all_data.values() for d in df.index})
    if not all_dates:
        empty_params = {
            "date_from": date_from,
            "date_to": date_to,
            "max_bars": max_bars,
            "entry_mode": entry_mode,
        }
        return [], [], empty_params, {"missed_entries": []}

    account_size = get_account_size()
    trade_cap = min(max_concurrent_trades, K.PORTFOLIO_MAX_OPEN_TRADES)
    open_trades: List[dict] = []
    pending_entries: List[dict] = []
    closed_trades: List[dict] = []
    missed_entries: List[dict] = []
    equity = 100.0
    equity_curve: List[Tuple[str, float]] = [(all_dates[0].strftime("%Y-%m-%d"), 0.0)]
    last_market_regime: Optional[str] = None

    for day_idx, date in enumerate(all_dates):
        if progress_callback and day_idx % 5 == 0:
            progress_callback(
                f"Backtesting {date.strftime('%Y-%m-%d')} ({day_idx + 1}/{len(all_dates)})"
            )

        pending_entries = _activate_pending_trades(
            date,
            pending_entries,
            open_trades,
            all_data,
            account_size,
            missed_entries,
            entry_mode,
            max_bars,
        )
        open_trades, equity = _update_open_trades(
            date,
            open_trades,
            closed_trades,
            all_data,
            account_size,
            equity,
            max_bars,
        )

        results, _sector_strength, regime, market_regime = _build_results_for_day(all_data, date, yahoo_to_sym)
        if not results:
            equity_curve.append((date.strftime("%Y-%m-%d"), round(equity - 100.0, 2)))
            continue

        if progress_callback and market_regime != last_market_regime:
            progress_callback(f"Market regime: {market_regime} ({K.EGX30_SYMBOL})")
            last_market_regime = market_regime

        guarded_list, _, _, _, _ = compute_portfolio_guard(
            results,
            account_size=account_size,
            open_trades=open_trades,
        )

        weak_rank_floor = K.TRADE_TYPE_STRONG_MIN + 3.0 if market_regime == "WEAK" else K.BT_MIN_SMARTRANK

        # --- Track filter-rejected signals for missed-trade analysis ------
        open_or_pending = {t["sym"] for t in open_trades} | {t["sym"] for t in pending_entries}
        # Only simulate top rejects (by score) to avoid excessive compute.
        _MAX_SIM_PER_DAY = 5
        _MIN_SCORE_FOR_SIM = 50.0
        filter_rejects: List[dict] = []
        for gr in guarded_list:
            r = gr.result
            if not r.get("plan"):
                continue
            action = r["plan"].get("action", "")
            if action not in ("ACCUMULATE", "PROBE"):
                continue
            sr = r.get("smart_rank", 0.0)
            # Determine rejection reason
            if gr.is_blocked:
                reject_reason = "guard_blocked"
            elif sr < K.BT_MIN_SMARTRANK:
                reject_reason = "low_smartrank"
            elif regime != "BULL":
                reject_reason = "non_bull_regime"
            elif market_regime == "WEAK" and sr < K.TRADE_TYPE_STRONG_MIN:
                reject_reason = "weak_market_medium_block"
            elif market_regime == "WEAK" and sr < weak_rank_floor:
                reject_reason = "weak_market_rank_filter"
            elif market_regime == "WEAK" and not r.get("volume_confirmed", False):
                reject_reason = "weak_market_volume_filter"
            else:
                continue  # not rejected â€” will go through allowed path
            # Skip symbols already open/pending
            if r["sym"] in open_or_pending:
                continue
            filter_rejects.append((gr, r, sr, reject_reason))

        # Sort by score descending, simulate only top N above threshold
        filter_rejects.sort(key=lambda x: x[2], reverse=True)
        _day_sim_count = 0
        for _gr, r, sr, reject_reason in filter_rejects:
            yahoo = SYMBOLS.get(r["sym"])
            if not yahoo or yahoo not in all_data:
                continue
            act_date = _find_next_bar_date(all_data[yahoo], date)
            if act_date is None or act_date not in all_data[yahoo].index:
                continue
            row_next = all_data[yahoo].loc[act_date]
            open_px = float(row_next["Open"])
            if open_px <= 0:
                continue

            missed_entry = {
                "sym": r["sym"],
                "sector": r["sector"],
                "signal_date": date.strftime("%Y-%m-%d"),
                "activation_date": act_date.strftime("%Y-%m-%d"),
                "trigger_price": round(float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))), 3),
                "next_open": round(open_px, 3),
                "next_high": round(float(row_next["High"]), 3),
                "trade_type": r.get("plan", {}).get("trade_type", "UNCLASSIFIED"),
                "score": round(float(sr), 2),
                "risk_used": round(float(r.get("plan", {}).get("risk_used", get_risk_per_trade())), 4),
                "reason": reject_reason,
            }

            # Simulate only top rejects with score >= threshold
            if sr >= _MIN_SCORE_FOR_SIM and _day_sim_count < _MAX_SIM_PER_DAY:
                fake_pending = {
                    "sym": r["sym"], "sector": r["sector"],
                    "signal_type": r["tag"], "regime": REGIME_MAP.get(regime, regime),
                    "signal_date": date.strftime("%Y-%m-%d"),
                    "activation_date": act_date,
                    "risk_pct": max(float(r["plan"].get("risk_pct", 0.02)), 0.005),
                    "target_pct": float(r["plan"].get("target_pct", 0.08)),
                    "trigger_price": missed_entry["trigger_price"],
                    "smart_rank": float(sr),
                    "score": round(float(sr), 2),
                    "trade_type": missed_entry["trade_type"],
                    "risk_used": missed_entry["risk_used"],
                    "anticipation": float(r.get("anticipation", 0.0)),
                    "atr": float(r.get("atr") or 0.0),
                }
                forced = _build_open_trade(fake_pending, open_px, account_size, act_date, "forced_filter_approx")
                approx = _simulate_trade_path(forced, all_data[yahoo], act_date, account_size, max_bars)
                if approx is not None:
                    missed_entry["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                    missed_entry["approx_outcome"] = approx.get("outcome", "EXIT")
                    missed_entry["approx_exit_date"] = approx.get("exit_date", "")
                _day_sim_count += 1

            missed_entries.append(missed_entry)

        allowed = [
            gr.result
            for gr in guarded_list
            if not gr.is_blocked
            and gr.result.get("plan")
            and gr.result["plan"].get("action") in ("ACCUMULATE", "PROBE")
            and gr.result.get("smart_rank", 0.0) >= K.BT_MIN_SMARTRANK
            and _is_high_probability_trade(gr.result)
        ]

        if market_regime == "WEAK":
            strong_rank_floor = weak_rank_floor
            allowed = [
                r for r in allowed
                if r.get("smart_rank", 0.0) >= strong_rank_floor
                and r.get("volume_confirmed", False)
            ]

        # â”€â”€ HYBRID REGIME FLEXIBILITY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # BULL: all qualifying trades enter
        # NEUTRAL: only STRONG trades (SR >= STRONG threshold) enter
        # BEAR: no trades
        if regime == "NEUTRAL":
            allowed = [r for r in allowed
                       if r.get("smart_rank", 0.0) >= K.TRADE_TYPE_STRONG_MIN]

        # â”€â”€ HYBRID TWO-TIER RISK MODEL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Tag each allowed signal with its risk tier
        for r in allowed:
            sr = r.get("smart_rank", 0.0)
            regime_risk_mult = K.MARKET_REGIME_WEAK_RISK_MULT if market_regime == "WEAK" else 1.0
            if sr >= K.TRADE_TYPE_STRONG_MIN:
                r["_hybrid_risk"] = K.RISK_PER_TRADE_STRONG * regime_risk_mult
                r["_hybrid_tier"] = "STRONG"
            else:
                r["_hybrid_risk"] = K.RISK_PER_TRADE_MEDIUM * regime_risk_mult
                r["_hybrid_tier"] = "MEDIUM"
            r["_market_regime"] = market_regime

        allowed.sort(
            key=lambda r: (
                0 if r["plan"].get("action") == "ACCUMULATE" else 1,
                0 if r.get("_hybrid_tier") == "STRONG" else 1,
                DECISION_PRIORITY.get(r["tag"], 99),
                -r["smart_rank"],
            )
        )

        if regime in ("BULL", "NEUTRAL"):
            available_slots = max(0, trade_cap - len(open_trades) - len(pending_entries))
            added_this_day = set()
            for r in allowed:
                if available_slots <= 0:
                    # Track slot-limited signals as missed
                    if r["sym"] not in open_or_pending and r["sym"] not in added_this_day:
                        yahoo = SYMBOLS.get(r["sym"])
                        if yahoo and yahoo in all_data:
                            act_date = _find_next_bar_date(all_data[yahoo], date)
                            if act_date and act_date in all_data[yahoo].index:
                                row_next = all_data[yahoo].loc[act_date]
                                open_px = float(row_next["Open"])
                                if open_px > 0:
                                    fp = {
                                        "sym": r["sym"], "sector": r["sector"],
                                        "signal_type": r["tag"], "regime": market_regime,
                                        "signal_date": date.strftime("%Y-%m-%d"),
                                        "activation_date": act_date,
                                        "risk_pct": max(float(r["plan"].get("risk_pct", 0.02)), 0.005),
                                        "target_pct": float(r["plan"].get("target_pct", 0.08)),
                                        "trigger_price": float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))),
                                        "smart_rank": float(r.get("smart_rank", 0.0)),
                                        "score": float(r.get("plan", {}).get("score", r.get("smart_rank", 0.0))),
                                        "trade_type": r.get("plan", {}).get("trade_type", "UNCLASSIFIED"),
                                        "risk_used": float(r.get("plan", {}).get("risk_used", get_risk_per_trade())),
                                        "anticipation": float(r.get("anticipation", 0.0)),
                                        "atr": float(r.get("atr") or 0.0),
                                    }
                                    forced = _build_open_trade(fp, open_px, account_size, act_date, "forced_filter_approx")
                                    approx = _simulate_trade_path(forced, all_data[yahoo], act_date, account_size, max_bars)
                                    me = {
                                        "sym": r["sym"], "sector": r["sector"],
                                        "signal_date": date.strftime("%Y-%m-%d"),
                                        "activation_date": act_date.strftime("%Y-%m-%d"),
                                        "trigger_price": round(float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))), 3),
                                        "next_open": round(open_px, 3),
                                        "next_high": round(float(row_next["High"]), 3),
                                        "trade_type": fp["trade_type"],
                                        "score": round(float(r.get("smart_rank", 0.0)), 2),
                                        "risk_used": round(float(fp["risk_used"]), 4),
                                        "reason": "slot_limit",
                                    }
                                    if approx is not None:
                                        me["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                                        me["approx_outcome"] = approx.get("outcome", "EXIT")
                                        me["approx_exit_date"] = approx.get("exit_date", "")
                                    missed_entries.append(me)
                    continue
                if r["sym"] in open_or_pending:
                    continue
                yahoo = SYMBOLS.get(r["sym"])
                if not yahoo or yahoo not in all_data:
                    continue
                activation_date = _find_next_bar_date(all_data[yahoo], date)
                if activation_date is None:
                    continue
                pending_entries.append(
                    {
                        "sym": r["sym"],
                        "sector": r["sector"],
                        "signal_type": r["tag"],
                        "regime": market_regime,
                        "signal_date": date.strftime("%Y-%m-%d"),
                        "activation_date": activation_date,
                        "risk_pct": max(float(r["plan"].get("risk_pct", 0.02)), 0.005),
                        "target_pct": float(r["plan"].get("target_pct", 0.08)),
                        "trigger_price": float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))),
                        "smart_rank": float(r.get("smart_rank", 0.0)),
                        "score": float(r.get("plan", {}).get("score", r.get("smart_rank", 0.0))),
                        "trade_type": r.get("_hybrid_tier", r.get("plan", {}).get("trade_type", "UNCLASSIFIED")),
                        "risk_used": float(r.get("_hybrid_risk", get_risk_per_trade())),
                        "anticipation": float(r.get("anticipation", 0.0)),
                        "atr": float(r.get("atr") or 0.0),
                    }
                )
                open_or_pending.add(r["sym"])
                added_this_day.add(r["sym"])
                available_slots -= 1

        equity_curve.append((date.strftime("%Y-%m-%d"), round(equity - 100.0, 2)))

    if all_dates:
        last_date = all_dates[-1]
        for trade in list(open_trades):
            yahoo = SYMBOLS.get(trade["sym"])
            if not yahoo or yahoo not in all_data or last_date not in all_data[yahoo].index:
                continue
            close = float(all_data[yahoo].loc[last_date]["Close"])
            exit_price = round(close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            resolved = _close_trade(trade, last_date, exit_price, "EXIT", account_size)
            equity *= 1.0 + resolved["alloc_pct"] * resolved["pnl_pct"] / 100.0
            resolved["equity_after"] = round(equity, 4)
            closed_trades.append(resolved)
        equity_curve[-1] = (equity_curve[-1][0], round(equity - 100.0, 2))

    return (
        closed_trades,
        equity_curve,
        {
            "date_from": date_from,
            "date_to": date_to,
            "max_bars": max_bars,
            "max_concurrent_trades": trade_cap,
            "entry_mode": entry_mode,
            "execution": f"next_candle_{entry_mode}_stop_first_partial_tp_trailing",
            "slippage_pct": K.BT_SLIPPAGE_PCT,
            "fees_pct": K.BT_FEES_PCT,
        },
        {
            "missed_entries": missed_entries,
        },
    )
```

==================================================
FILE: egx_radar/backtest/engine_with_guards.py
==============================================

```python
from __future__ import annotations

"""Compatibility wrapper around the unified conservative backtest engine."""

from egx_radar.backtest.engine import REGIME_MAP, run_backtest

__all__ = ["REGIME_MAP", "run_backtest"]
```

==================================================
FILE: egx_radar/backtest/metrics.py
===================================

```python
from __future__ import annotations

"""Performance metrics from backtest trades."""

import logging
from collections import defaultdict
from typing import Any, Dict, List

from egx_radar.config.settings import K

log = logging.getLogger(__name__)


def compute_metrics(trades: List[dict]) -> Dict[str, Any]:
    """
    Compute overall, per-regime, per-signal, per-sector, per-symbol, and monthly metrics.
    trades: list of closed trade dicts with keys entry_date, exit_date, sym, sector,
            signal_type, regime, entry, exit, pnl_pct, rr, outcome, etc.
    """
    if not trades:
        return _empty_metrics()

    # Overall
    total_trades = len(trades)
    wins = [t for t in trades if t.get("pnl_pct", 0) > 0]
    losses = [t for t in trades if t.get("pnl_pct", 0) <= 0]
    win_rate = len(wins) / total_trades * 100 if total_trades else 0.0
    rr_list = [t["rr"] for t in trades if t.get("rr") is not None]
    avg_return = sum(t.get("pnl_pct", 0.0) for t in trades) / total_trades if total_trades else 0.0
    avg_rr = sum(rr_list) / len(rr_list) if rr_list else 0.0
    total_return = sum(t["pnl_pct"] for t in trades)
    gross_profit = sum(t["pnl_pct"] for t in wins)
    gross_loss = abs(sum(t["pnl_pct"] for t in losses))
    profit_factor = gross_profit / (gross_loss + 1e-9) if gross_loss else (float("inf") if gross_profit else 0.0)
    bars_list = [t.get("bars_held", 0) for t in trades]
    avg_bars = sum(bars_list) / len(bars_list) if bars_list else 0.0
    largest_win = max((t["pnl_pct"] for t in wins), default=0.0)
    largest_loss = min((t["pnl_pct"] for t in losses), default=0.0)

    # Equity curve for drawdown using actual backtest allocations when available.
    if all(t.get("equity_after") is not None for t in trades):
        equity_points = [100.0] + [float(t["equity_after"]) for t in trades]
    else:
        equity_points = [100.0]
        equity_m = 100.0
        for t in trades:
            alloc = float(t.get("alloc_pct", 0.20))
            equity_m *= (1 + alloc * t["pnl_pct"] / 100)
            equity_points.append(equity_m)
    peak = equity_points[0]
    max_dd = 0.0
    for point in equity_points[1:]:
        peak = max(peak, point)
        dd = (peak - point) / peak * 100 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    max_drawdown_pct = max_dd
    total_return = (equity_points[-1] - 100.0) / 100.0 * 100

    # Sharpe: annualized, scaled by trades-per-year (not sqrt(252))
    # since these are per-trade returns, not daily returns
    if total_trades >= 2:
        returns = [t["pnl_pct"] for t in trades]
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std = variance ** 0.5 if variance > 0 else 1e-9
        daily_rf = K.RISK_FREE_ANNUAL_PCT / K.TRADING_DAYS_PER_YEAR / 100
        per_trade_rf = daily_rf * avg_bars if avg_bars > 0 else daily_rf
        trades_per_year = K.TRADING_DAYS_PER_YEAR / max(avg_bars, 1)
        sharpe = ((mean_ret / 100 - per_trade_rf) / (std / 100 + 1e-9)) * (trades_per_year ** 0.5) if std > 0 else 0.0
    else:
        sharpe = 0.0

    overall = {
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 1),
        "avg_return_pct": round(avg_return, 2),
        "expectancy_pct": round(avg_return, 2),
        "avg_rr": round(avg_rr, 2),
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_bars_in_trade": round(avg_bars, 1),
        "largest_win_pct": round(largest_win, 2),
        "largest_loss_pct": round(largest_loss, 2),
    }

    # Per regime
    by_regime: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"trades": [], "pnl": 0.0})
    for t in trades:
        reg = t.get("regime", "NEUTRAL")
        by_regime[reg]["trades"].append(t)
        by_regime[reg]["pnl"] += t["pnl_pct"]
    per_regime = {}
    for reg, data in by_regime.items():
        tr = data["trades"]
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        wr = w / n * 100 if n else 0.0
        rrs = [x["rr"] for x in tr if x.get("rr") is not None]
        per_regime[reg] = {
            "win_rate_pct": round(wr, 1),
            "avg_rr": round(sum(rrs) / len(rrs), 2) if rrs else 0.0,
            "total_trades": n,
        }

    # Per signal type
    by_signal: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_signal[t.get("signal_type", "â€”")].append(t)
    per_signal = {}
    for sig, tr in by_signal.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        rrs = [x["rr"] for x in tr if x.get("rr") is not None]
        per_signal[sig] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_rr": round(sum(rrs) / len(rrs), 2) if rrs else 0.0,
            "avg_return_pct": round(sum(x.get("pnl_pct", 0.0) for x in tr) / n, 2) if n else 0.0,
            "total_trades": n,
        }

    # Per trade type
    by_trade_type: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_trade_type[t.get("trade_type", "UNCLASSIFIED")].append(t)
    per_trade_type = {}
    for trade_type, tr in by_trade_type.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        rrs = [x["rr"] for x in tr if x.get("rr") is not None]
        per_trade_type[trade_type] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(x.get("pnl_pct", 0.0) for x in tr) / n, 2) if n else 0.0,
            "avg_rr": round(sum(rrs) / len(rrs), 2) if rrs else 0.0,
            "avg_risk_used_pct": round(sum(float(x.get("risk_used", 0.0)) for x in tr) / n * 100.0, 2) if n else 0.0,
            "total_trades": n,
        }

    # Per sector
    by_sector: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_sector[t.get("sector", "â€”")].append(t)
    per_sector = {}
    for sec, tr in by_sector.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        ret = sum(x["pnl_pct"] for x in tr)
        per_sector[sec] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "total_trades": n,
            "avg_return_pct": round(ret / n, 2) if n else 0.0,
        }

    # Per symbol
    by_sym: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_sym[t.get("sym", "â€”")].append(t)
    per_symbol = {}
    for sym, tr in by_sym.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        ret = sum(x["pnl_pct"] for x in tr)
        pnls = [x["pnl_pct"] for x in tr]
        per_symbol[sym] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "total_trades": n,
            "avg_return_pct": round(ret / n, 2) if n else 0.0,
            "best_trade_pct": round(max(pnls), 2) if pnls else 0.0,
            "worst_trade_pct": round(min(pnls), 2) if pnls else 0.0,
        }

    # Monthly
    by_month: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        exit_d = t.get("exit_date", "")
        if len(exit_d) >= 7:
            month_key = exit_d[:7]
            by_month[month_key].append(t)
    monthly = []
    for month in sorted(by_month.keys()):
        tr = by_month[month]
        ret = sum(x["pnl_pct"] for x in tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        monthly.append({
            "month": month,
            "trade_count": len(tr),
            "return_pct": round(ret, 2),
            "win_rate_pct": round(w / len(tr) * 100, 1) if tr else 0.0,
        })

    return {
        "overall": overall,
        "per_regime": dict(per_regime),
        "per_signal": per_signal,
        "per_trade_type": per_trade_type,
        "per_sector": per_sector,
        "per_symbol": per_symbol,
        "monthly": monthly,
    }


def _empty_metrics() -> Dict[str, Any]:
    return {
        "overall": {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "avg_return_pct": 0.0,
            "expectancy_pct": 0.0,
            "avg_rr": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0,
            "avg_bars_in_trade": 0.0,
            "largest_win_pct": 0.0,
            "largest_loss_pct": 0.0,
        },
        "per_regime": {},
        "per_signal": {},
        "per_trade_type": {},
        "per_sector": {},
        "per_symbol": {},
        "monthly": [],
    }
```

==================================================
FILE: egx_radar/backtest/missed_trades.py
=========================================

```python
from __future__ import annotations

"""Missed Trade Intelligence System.

Analyzes all trades that were generated as signals but never entered,
classifying them as correctly rejected (bad trades) or incorrectly
rejected (missed opportunities).

Usage:
    from egx_radar.backtest.missed_trades import run_missed_trade_analysis
    report = run_missed_trade_analysis(missed_entries)
    print(report["text"])
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quality scoring thresholds (based on SmartRank / score)
# ---------------------------------------------------------------------------
_QUALITY_HIGH = 75.0
_QUALITY_MEDIUM = 65.0


def _classify_quality(score: float) -> str:
    """Classify a missed trade by its SmartRank score."""
    if score >= _QUALITY_HIGH:
        return "HIGH"
    if score >= _QUALITY_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _classify_outcome(pnl_pct: float) -> str:
    """Classify a missed trade by its simulated outcome."""
    return "MISSED_WIN" if pnl_pct > 0 else "MISSED_LOSS"


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_missed_trades(missed_entries: List[dict]) -> Dict[str, Any]:
    """Compute full analytics on a list of missed trade entries.

    Each entry is expected to have at least:
        sym, sector, signal_date, score (SmartRank),
        approx_pnl_pct (simulated P&L), approx_outcome,
        reason (why missed), trade_type.

    Returns a dict with all metrics, breakdowns, and recommendations.
    """
    if not missed_entries:
        return _empty_analysis()

    total = len(missed_entries)

    # --- Classification ---------------------------------------------------
    for m in missed_entries:
        pnl = float(m.get("approx_pnl_pct") or 0.0)
        score = float(m.get("score", m.get("smart_rank", 0.0)))
        m["classification"] = _classify_outcome(pnl)
        m["quality"] = _classify_quality(score)

    wins = [m for m in missed_entries if m["classification"] == "MISSED_WIN"]
    losses = [m for m in missed_entries if m["classification"] == "MISSED_LOSS"]

    win_count = len(wins)
    loss_count = len(losses)
    win_pct = round(win_count / total * 100, 1) if total else 0.0
    loss_pct = round(loss_count / total * 100, 1) if total else 0.0

    all_pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in missed_entries]
    avg_return = round(sum(all_pnls) / total, 2) if total else 0.0
    total_pnl = round(sum(all_pnls), 2)

    win_pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in wins]
    loss_pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in losses]
    avg_win_return = round(sum(win_pnls) / len(win_pnls), 2) if win_pnls else 0.0
    avg_loss_return = round(sum(loss_pnls) / len(loss_pnls), 2) if loss_pnls else 0.0

    # --- Quality breakdown ------------------------------------------------
    by_quality: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_quality[m["quality"]].append(m)

    quality_breakdown: Dict[str, Dict[str, Any]] = {}
    for q in ("HIGH", "MEDIUM", "LOW"):
        group = by_quality.get(q, [])
        n = len(group)
        w = sum(1 for m in group if m["classification"] == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        quality_breakdown[q] = {
            "count": n,
            "win_count": w,
            "loss_count": n - w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
            "total_pnl_pct": round(sum(pnls), 2),
        }

    # --- By rejection reason ----------------------------------------------
    by_reason: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_reason[m.get("reason", "unknown")].append(m)

    reason_breakdown: Dict[str, Dict[str, Any]] = {}
    for reason, group in by_reason.items():
        n = len(group)
        w = sum(1 for m in group if m.get("classification") == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        reason_breakdown[reason] = {
            "count": n,
            "win_count": w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
        }

    # --- By sector --------------------------------------------------------
    by_sector: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_sector[m.get("sector", "UNKNOWN")].append(m)

    sector_breakdown: Dict[str, Dict[str, Any]] = {}
    for sector, group in by_sector.items():
        n = len(group)
        w = sum(1 for m in group if m.get("classification") == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        sector_breakdown[sector] = {
            "count": n,
            "win_count": w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
        }

    # --- By trade type ----------------------------------------------------
    by_type: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_type[m.get("trade_type", "UNCLASSIFIED")].append(m)

    type_breakdown: Dict[str, Dict[str, Any]] = {}
    for ttype, group in by_type.items():
        n = len(group)
        w = sum(1 for m in group if m.get("classification") == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        type_breakdown[ttype] = {
            "count": n,
            "win_count": w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
        }

    # --- Decision engine & recommendations --------------------------------
    recommendations = _generate_recommendations(
        total=total,
        win_count=win_count,
        loss_count=loss_count,
        win_pct=win_pct,
        avg_return=avg_return,
        quality_breakdown=quality_breakdown,
    )

    return {
        "total_missed": total,
        "missed_wins": win_count,
        "missed_losses": loss_count,
        "missed_wins_pct": win_pct,
        "missed_losses_pct": loss_pct,
        "avg_return_pct": avg_return,
        "avg_win_return_pct": avg_win_return,
        "avg_loss_return_pct": avg_loss_return,
        "total_pnl_impact_pct": total_pnl,
        "quality_breakdown": quality_breakdown,
        "reason_breakdown": reason_breakdown,
        "sector_breakdown": sector_breakdown,
        "type_breakdown": type_breakdown,
        "recommendations": recommendations,
        "entries": missed_entries,
    }


def _generate_recommendations(
    total: int,
    win_count: int,
    loss_count: int,
    win_pct: float,
    avg_return: float,
    quality_breakdown: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Decision engine: generate actionable insights from missed trade data."""
    insights: List[str] = []
    action = "KEEP_FILTERS"  # default

    high = quality_breakdown.get("HIGH", {})
    medium = quality_breakdown.get("MEDIUM", {})
    high_win_rate = high.get("win_rate_pct", 0.0)
    high_count = high.get("count", 0)
    medium_win_rate = medium.get("win_rate_pct", 0.0)

    # Rule 1: If most missed trades are losses â†’ filters are working
    if loss_count > win_count and win_pct < 35:
        insights.append(
            f"System correctly filters most bad trades "
            f"({loss_count}/{total} missed were losses, {win_pct}% win rate)."
        )

    # Rule 2: HIGH quality missed wins > 20% â†’ consider loosening entry rules
    if high_count > 0 and high_win_rate > 20:
        insights.append(
            f"WARNING: {high.get('win_count', 0)} HIGH-quality trades were missed "
            f"(win rate {high_win_rate}%). Consider loosening entry trigger rules."
        )
        action = "REVIEW_ENTRY_RULES"

    # Rule 3: HIGH quality missed wins > 50% â†’ strong signal to loosen
    if high_count >= 3 and high_win_rate > 50:
        insights.append(
            f"STRONG: HIGH-quality missed trades have {high_win_rate}% win rate. "
            f"Entry triggers may be too tight."
        )
        action = "LOOSEN_ENTRY_RULES"

    # Rule 4: Average return of missed trades is positive â†’ leaving money on table
    if avg_return > 0:
        insights.append(
            f"Avg missed trade return is +{avg_return}% â€” "
            f"system is leaving potential profit on the table."
        )
        if action == "KEEP_FILTERS":
            action = "REVIEW_ENTRY_RULES"

    # Rule 5: Average return negative â†’ filters are protecting capital
    if avg_return < 0:
        insights.append(
            f"Avg missed trade return is {avg_return}% â€” "
            f"filters are protecting capital effectively."
        )

    # Rule 6: MEDIUM quality has decent win rate â†’ might be worth investigating
    if medium.get("count", 0) >= 3 and medium_win_rate > 40:
        insights.append(
            f"MEDIUM-quality missed trades have {medium_win_rate}% win rate. "
            f"Some could be recoverable with adjusted triggers."
        )

    if not insights:
        insights.append("Not enough data to generate meaningful recommendations.")

    # Conclusion
    if action == "KEEP_FILTERS":
        conclusion = "Ø§Ù„Ù†Ø¸Ø§Ù… Ø¨ÙŠØ­Ù…ÙŠÙƒ â€” Ø§Ù„ÙÙ„Ø§ØªØ± Ø´ØºØ§Ù„Ø© ØµØ­. (System is protecting you.)"
    elif action == "LOOSEN_ENTRY_RULES":
        conclusion = "Ø§Ù„Ù†Ø¸Ø§Ù… Ø¨ÙŠØ¶ÙŠØ¹ ÙØ±Øµ ÙƒØªÙŠØ± â€” Ù„Ø§Ø²Ù… ØªØ±Ø§Ø¬Ø¹ Ø´Ø±ÙˆØ· Ø§Ù„Ø¯Ø®ÙˆÙ„. (System is missing opportunities â€” review entry rules.)"
    else:
        conclusion = "ÙÙŠ ÙØ±Øµ Ø¨ØªØªØ¶ÙŠØ¹ â€” Ù…Ø­ØªØ§Ø¬ Ù…Ø±Ø§Ø¬Ø¹Ø© Ø¨Ø³ÙŠØ·Ø©. (Some opportunities are lost â€” needs minor review.)"

    return {
        "action": action,
        "conclusion": conclusion,
        "insights": insights,
    }


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def format_missed_trade_report(analysis: Dict[str, Any]) -> str:
    """Format a human-readable text report from the analysis dict."""
    if not analysis or analysis.get("total_missed", 0) == 0:
        return "=== MISSED TRADE ANALYSIS ===\n\nNo missed trades to analyze.\n"

    lines = [
        "=== MISSED TRADE ANALYSIS ===",
        "",
        f"Total Missed: {analysis['total_missed']}",
        f"Missed Wins: {analysis['missed_wins']} ({analysis['missed_wins_pct']}%)",
        f"Missed Losses: {analysis['missed_losses']} ({analysis['missed_losses_pct']}%)",
        "",
        f"Avg Missed Return: {analysis['avg_return_pct']}%",
        f"Avg Win Return: {analysis['avg_win_return_pct']}%",
        f"Avg Loss Return: {analysis['avg_loss_return_pct']}%",
        f"Total PnL Impact: {analysis['total_pnl_impact_pct']}%",
        "",
        "--- By Quality ---",
    ]

    for q in ("HIGH", "MEDIUM", "LOW"):
        qd = analysis["quality_breakdown"].get(q, {})
        lines.extend([
            f"{q}:",
            f"    count: {qd.get('count', 0)}",
            f"    win rate: {qd.get('win_rate_pct', 0.0)}%",
            f"    avg return: {qd.get('avg_return_pct', 0.0)}%",
            f"    total PnL: {qd.get('total_pnl_pct', 0.0)}%",
        ])

    lines.extend(["", "--- By Rejection Reason ---"])
    for reason, rd in analysis.get("reason_breakdown", {}).items():
        lines.append(
            f"{reason}: count={rd['count']} | "
            f"win rate={rd['win_rate_pct']}% | "
            f"avg return={rd['avg_return_pct']}%"
        )

    lines.extend(["", "--- By Sector ---"])
    for sector, sd in sorted(
        analysis.get("sector_breakdown", {}).items(),
        key=lambda x: x[1].get("count", 0),
        reverse=True,
    ):
        lines.append(
            f"{sector}: count={sd['count']} | "
            f"win rate={sd['win_rate_pct']}% | "
            f"avg return={sd['avg_return_pct']}%"
        )

    recs = analysis.get("recommendations", {})
    lines.extend([
        "",
        "--- Recommendations ---",
        f"Action: {recs.get('action', 'N/A')}",
    ])
    for insight in recs.get("insights", []):
        lines.append(f"  * {insight}")
    lines.extend([
        "",
        "--- Conclusion ---",
        recs.get("conclusion", ""),
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Top-level callable
# ---------------------------------------------------------------------------

def run_missed_trade_analysis(
    missed_entries: Optional[List[dict]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    print_report: bool = False,
) -> Dict[str, Any]:
    """Run a complete missed-trade intelligence analysis.

    Args:
        missed_entries: List of missed trade dicts (from backtest diagnostics).
            If None, extracted from *diagnostics*.
        diagnostics: The diagnostics dict returned by run_backtest() as 4th element.
        print_report: If True, print the text report to stdout.

    Returns:
        Dict with keys: analysis (full metrics), text (formatted report).
    """
    if missed_entries is None and diagnostics is not None:
        missed_entries = list(diagnostics.get("missed_entries") or [])
    if missed_entries is None:
        missed_entries = []

    analysis = analyze_missed_trades(missed_entries)
    text = format_missed_trade_report(analysis)

    if print_report:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('utf-8', errors='replace').decode('ascii', errors='replace'))

    return {
        "analysis": analysis,
        "text": text,
    }


# ---------------------------------------------------------------------------
# Empty result
# ---------------------------------------------------------------------------

def _empty_analysis() -> Dict[str, Any]:
    empty_quality = {
        q: {"count": 0, "win_count": 0, "loss_count": 0,
            "win_rate_pct": 0.0, "avg_return_pct": 0.0, "total_pnl_pct": 0.0}
        for q in ("HIGH", "MEDIUM", "LOW")
    }
    return {
        "total_missed": 0,
        "missed_wins": 0,
        "missed_losses": 0,
        "missed_wins_pct": 0.0,
        "missed_losses_pct": 0.0,
        "avg_return_pct": 0.0,
        "avg_win_return_pct": 0.0,
        "avg_loss_return_pct": 0.0,
        "total_pnl_impact_pct": 0.0,
        "quality_breakdown": empty_quality,
        "reason_breakdown": {},
        "sector_breakdown": {},
        "type_breakdown": {},
        "recommendations": {
            "action": "NO_DATA",
            "conclusion": "No missed trades to analyze.",
            "insights": [],
        },
        "entries": [],
    }


__all__ = [
    "run_missed_trade_analysis",
    "analyze_missed_trades",
    "format_missed_trade_report",
]
```

==================================================
FILE: egx_radar/backtest/report.py
==================================

```python
from __future__ import annotations

"""Backtest report UI: tab with controls, summary, equity curve, trades table, CSV export."""

import csv
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from egx_radar.config.settings import C, F_HEADER, F_SMALL, F_MICRO, K
from egx_radar.state.app_state import STATE

from egx_radar.backtest.dashboard import build_performance_dashboard
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics

log = logging.getLogger(__name__)


def open_backtest_window(root: tk.Tk) -> None:
    """Open Backtest Toplevel: date range, Run, Export, summary, equity curve, trades table, breakdown tabs."""
    from egx_radar.ui.components import _enqueue

    win = tk.Toplevel(root)
    win.title("ðŸ“Š Backtest")
    win.configure(bg=C.BG)
    win.geometry("1200x720")

    # Controls
    ctrl = tk.Frame(win, bg=C.BG, pady=8)
    ctrl.pack(fill="x", padx=14)
    tk.Label(ctrl, text="Date From:", font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 4))
    date_from_var = tk.StringVar(value="2020-01-01")
    tk.Entry(ctrl, textvariable=date_from_var, font=F_SMALL, width=12).pack(side="left", padx=(0, 12))
    tk.Label(ctrl, text="Date To:", font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 4))
    date_to_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    tk.Entry(ctrl, textvariable=date_to_var, font=F_SMALL, width=12).pack(side="left", padx=(0, 12))
    tk.Label(ctrl, text="Max Bars:", font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 4))
    max_bars_var = tk.StringVar(value=str(K.BT_MAX_BARS))
    tk.Entry(ctrl, textvariable=max_bars_var, font=F_SMALL, width=4).pack(side="left", padx=(0, 16))

    progress_var = tk.StringVar(value="Ready â€” set dates and click Run Backtest")
    tk.Label(ctrl, textvariable=progress_var, font=F_SMALL, fg=C.CYAN, bg=C.BG).pack(side="left", padx=8)

    def do_run() -> None:
        try:
            date_from = date_from_var.get().strip()
            date_to = date_to_var.get().strip()
            max_bars = max(int(max_bars_var.get().strip()), K.BT_MAX_BARS)
        except ValueError:
            _enqueue(lambda: messagebox.showerror("Error", "Invalid date or max bars"))
            return

        def run_in_thread() -> None:
            def progress(msg: str) -> None:
                _enqueue(lambda: progress_var.set(msg))

            _enqueue(lambda: progress_var.set("Loading dataâ€¦"))
            try:
                result = run_backtest(
                    date_from=date_from,
                    date_to=date_to,
                    max_bars=max_bars,
                    max_concurrent_trades=K.PORTFOLIO_MAX_OPEN_TRADES,
                    progress_callback=progress,
                )
                if len(result) == 4:
                    trades, equity_curve, params, diagnostics = result
                else:
                    trades, equity_curve, params = result
                    diagnostics = {}
            except Exception as exc:
                log.exception("Backtest failed: %s", exc)
                _enqueue(lambda: messagebox.showerror("Backtest Error", str(exc)))
                _enqueue(lambda: progress_var.set("Error â€” see message"))
                return

            metrics = compute_metrics(trades)
            dashboard = build_performance_dashboard(trades, diagnostics)
            with STATE._lock:
                STATE.backtest_results = {
                    "trades": trades,
                    "equity_curve": equity_curve,
                    "metrics": metrics,
                    "params": params,
                    "diagnostics": diagnostics,
                    "dashboard": dashboard,
                }

            def refresh() -> None:
                progress_var.set(f"Done â€” {len(trades)} trades")
                _refresh_summary(metrics["overall"], dashboard, summary_lbl)
                _refresh_equity_canvas(equity_curve, equity_canvas)
                _refresh_trades_table(trades, trades_tree)
                _refresh_breakdown(metrics, regime_tree, sector_tree, type_tree, month_tree)

            _enqueue(refresh)

        _enqueue(lambda: progress_var.set("Running backtestâ€¦"))
        threading.Thread(target=run_in_thread, daemon=True).start()

    tk.Button(ctrl, text="â–¶ Run Backtest", font=F_HEADER, fg=C.BG, bg=C.ACCENT,
              relief="flat", padx=12, pady=4, command=do_run).pack(side="right", padx=4)

    def do_export() -> None:
        with STATE._lock:
            data = STATE.backtest_results
        if not data or not data.get("trades"):
            messagebox.showwarning("Export", "Run a backtest first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"EGX_Radar_Backtest_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Backtest Results",
        )
        if not path:
            return
        trades = data["trades"]
        if not trades:
            messagebox.showwarning("Export", "No trades to export.")
            return
        cols = list(trades[0].keys())
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(trades)
        messagebox.showinfo("Saved âœ…", f"Exported {len(trades)} trades to:\n{path}")

    tk.Button(ctrl, text="ðŸ’¾ Export CSV", font=F_HEADER, fg=C.TEXT, bg=C.BG3,
              relief="flat", padx=10, pady=4, command=do_export).pack(side="right")

    # Content: summary + equity curve row
    content = tk.Frame(win, bg=C.BG)
    content.pack(fill="both", expand=True, padx=14, pady=4)

    left = tk.Frame(content, bg=C.BG)
    left.pack(side="left", fill="y", padx=(0, 12))
    summary_lbl = tk.Label(
        left, text="Trades: n/a\nWin Rate: n/a\nAvg Return: n/a\nMax DD: n/a\nMissed: n/a",
        font=F_SMALL, fg=C.ACCENT2, bg=C.BG2, justify="left", padx=12, pady=10,
    )
    summary_lbl.pack(anchor="w")

    equity_canvas = tk.Canvas(content, width=700, height=180, bg=C.BG2, highlightthickness=0)
    equity_canvas.pack(side="left", fill="both", expand=True)

    # Trades table
    table_frm = tk.Frame(win, bg=C.BG)
    table_frm.pack(fill="both", expand=True, padx=14, pady=4)
    cols = ("Date", "Symbol", "Signal", "Entry", "Exit", "P&L%", "Regime")
    trades_tree = ttk.Treeview(table_frm, columns=cols, show="headings", height=10)
    for c in cols:
        trades_tree.heading(c, text=c)
        trades_tree.column(c, width=90 if c != "Symbol" else 70, anchor="center")
    vsb_t = ttk.Scrollbar(table_frm, orient="vertical", command=trades_tree.yview)
    trades_tree.configure(yscrollcommand=vsb_t.set)
    vsb_t.pack(side="right", fill="y")
    trades_tree.pack(fill="both", expand=True)

    # Breakdown tabs
    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=14, pady=4)
    regime_frm = tk.Frame(nb, bg=C.BG)
    sector_frm = tk.Frame(nb, bg=C.BG)
    type_frm = tk.Frame(nb, bg=C.BG)
    month_frm = tk.Frame(nb, bg=C.BG)
    nb.add(regime_frm, text="By Regime")
    nb.add(sector_frm, text="By Sector")
    nb.add(type_frm, text="By Type")
    nb.add(month_frm, text="By Month")

    rc = ("Regime", "Win%", "Avg R:R", "Trades")
    regime_tree = ttk.Treeview(regime_frm, columns=rc, show="headings", height=6)
    for c in rc:
        regime_tree.heading(c, text=c)
        regime_tree.column(c, width=100)
    regime_tree.pack(fill="both", expand=True)

    sc = ("Sector", "Win%", "Trades", "Avg Return%")
    sector_tree = ttk.Treeview(sector_frm, columns=sc, show="headings", height=6)
    for c in sc:
        sector_tree.heading(c, text=c)
        sector_tree.column(c, width=120)
    sector_tree.pack(fill="both", expand=True)

    tc = ("Trade Type", "Win%", "Trades", "Avg Return%", "Avg Risk%")
    type_tree = ttk.Treeview(type_frm, columns=tc, show="headings", height=6)
    for c in tc:
        type_tree.heading(c, text=c)
        type_tree.column(c, width=110)
    type_tree.pack(fill="both", expand=True)

    mc = ("Month", "Return%", "Win%")
    month_tree = ttk.Treeview(month_frm, columns=mc, show="headings", height=6)
    for c in mc:
        month_tree.heading(c, text=c)
        month_tree.column(c, width=100)
    month_tree.pack(fill="both", expand=True)

    def _refresh_summary(overall: Dict[str, Any], dashboard: Dict[str, Any], lbl: tk.Label) -> None:
        o = overall or {}
        missed = (dashboard or {}).get("missed_trades", {})
        missed_analysis = (dashboard or {}).get("missed_trade_analysis", {})
        recs = missed_analysis.get("recommendations", {})
        conclusion = recs.get("conclusion", "")
        missed_wins = missed_analysis.get("missed_wins", 0)
        missed_losses = missed_analysis.get("missed_losses", 0)
        missed_total = missed_analysis.get("total_missed", missed.get("count", 0))

        missed_line = f"Missed: {missed_total}"
        if missed_total > 0:
            missed_line += f" (W:{missed_wins} L:{missed_losses})"
        verdict = ""
        if conclusion:
            # Extract short Arabic/English verdict
            verdict = f"\n{conclusion[:80]}"

        lbl.configure(
            text=(
                f"Trades: {o.get('total_trades', 'n/a')}\n"
                f"Win Rate: {o.get('win_rate_pct', 'n/a')}%\n"
                f"Avg Return: {o.get('avg_return_pct', 'n/a')}%\n"
                f"Max DD: {o.get('max_drawdown_pct', 'n/a')}%\n"
                f"{missed_line}{verdict}"
            )
        )

    def _refresh_equity_canvas(curve: List[tuple], canvas: tk.Canvas) -> None:
        canvas.delete("all")
        if not curve or len(curve) < 2:
            canvas.create_text(350, 90, text="No equity curve", fill=C.MUTED)
            return
        w, h = 700, 180
        padding = 40
        ys = [y for _, y in curve]
        y_min = min(ys)
        y_max = max(ys)
        y_range = (y_max - y_min) or 1.0
        x_step = (w - 2 * padding) / max(1, len(curve) - 1)
        points = []
        for i, (_, y) in enumerate(curve):
            px = padding + i * x_step
            ny = (y - y_min) / y_range
            py = h - padding - ny * (h - 2 * padding)
            points.append((px, py))
        peak = ys[0]
        for i in range(1, len(points)):
            y_val = curve[i][1]
            if y_val > peak:
                peak = y_val
            elif peak > y_min and i > 0:
                x0 = points[i - 1][0]
                x1 = points[i][0]
                canvas.create_rectangle(x0, 0, x1, h, fill="#2a1a1a", outline="")
        for i in range(1, len(points)):
            color = C.GREEN if curve[i][1] >= 0 else C.RED
            canvas.create_line(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1], fill=color, width=2)
        canvas.create_text(w // 2, 12, text="Cumulative return %", fill=C.MUTED, font=F_MICRO)

    def _refresh_trades_table(trades: List[dict], tree: ttk.Treeview) -> None:
        tree.delete(*tree.get_children())
        for t in trades:
            tree.insert("", tk.END, values=(
                t.get("exit_date", "â€”"),
                t.get("sym", "â€”"),
                t.get("signal_type", "â€”"),
                f"{t.get('entry', 0):.2f}",
                f"{t.get('exit', 0):.2f}",
                f"{t.get('pnl_pct', 0):.2f}%",
                t.get("regime", "â€”"),
            ))

    def _refresh_breakdown(
        metrics: Dict[str, Any],
        rt: ttk.Treeview,
        st: ttk.Treeview,
        tt: ttk.Treeview,
        mt: ttk.Treeview,
    ) -> None:
        for tree in (rt, st, tt, mt):
            tree.delete(*tree.get_children())
        for reg, data in (metrics.get("per_regime") or {}).items():
            rt.insert("", tk.END, values=(
                reg,
                f"{data.get('win_rate_pct', 0)}%",
                data.get("avg_rr", 0),
                data.get("total_trades", 0),
            ))
        for sec, data in (metrics.get("per_sector") or {}).items():
            st.insert("", tk.END, values=(
                sec,
                f"{data.get('win_rate_pct', 0)}%",
                data.get("total_trades", 0),
                f"{data.get('avg_return_pct', 0)}%",
            ))
        for trade_type, data in (metrics.get("per_trade_type") or {}).items():
            tt.insert("", tk.END, values=(
                trade_type,
                f"{data.get('win_rate_pct', 0)}%",
                data.get("total_trades", 0),
                f"{data.get('avg_return_pct', 0)}%",
                f"{data.get('avg_risk_used_pct', 0)}%",
            ))
        for m in metrics.get("monthly") or []:
            mt.insert("", tk.END, values=(
                m.get("month", "n/a"),
                f"{m.get('return_pct', 0)}%",
                f"{m.get('win_rate_pct', 0)}%",
            ))

    # Pre-fill from last run if any
    with STATE._lock:
        data = STATE.backtest_results
    if data:
        _refresh_summary(data.get("metrics", {}).get("overall", {}), data.get("dashboard", {}), summary_lbl)
        _refresh_equity_canvas(data.get("equity_curve", []), equity_canvas)
        _refresh_trades_table(data.get("trades", []), trades_tree)
        _refresh_breakdown(data.get("metrics", {}), regime_tree, sector_tree, type_tree, month_tree)
```

==================================================
FILE: egx_radar/backtest/tracking_dashboard.py
==============================================

```python
from __future__ import annotations

"""
Trade Tracking Dashboard â€” real-time system quality evaluation.

Answers: "Ù‡Ù„ Ø£Ù†Ø§ Ø¬Ø§Ù‡Ø² Ø£Ø¯Ø®Ù„ ÙÙ„ÙˆØ³â€¦ ÙˆÙ„Ø§ Ù„Ø³Ù‡ Ø¨Ø¯Ø±ÙŠØŸ"

Reads REAL trade data from backtest results and/or CSV logs.
All metrics are computed dynamically â€” no hardcoded values.
"""

import csv
import logging
import math
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from egx_radar.backtest.metrics import compute_metrics
from egx_radar.config.settings import K

log = logging.getLogger(__name__)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 1 & 2: Core Metrics + Progress Tracking
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_TRADE_THRESHOLD_INSUFFICIENT = 20
_TRADE_THRESHOLD_PRELIMINARY = 50


def _progress_status(trade_count: int) -> Tuple[str, str]:
    """Return (status_label, status_icon) based on trade count."""
    if trade_count < _TRADE_THRESHOLD_INSUFFICIENT:
        return "INSUFFICIENT DATA", "ðŸ”´"
    elif trade_count < _TRADE_THRESHOLD_PRELIMINARY:
        return "PRELIMINARY", "âš ï¸"
    else:
        return "STATISTICALLY SIGNIFICANT", "âœ…"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 3: Trade Classification (STRONG / MEDIUM)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _classify_trades(trades: List[dict]) -> Dict[str, Dict[str, Any]]:
    """Split trades into STRONG / MEDIUM / other and compute per-class stats."""
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        tt = t.get("trade_type", "UNCLASSIFIED")
        buckets[tt].append(t)

    result: Dict[str, Dict[str, Any]] = {}
    for label in ("STRONG", "MEDIUM", "UNCLASSIFIED"):
        group = buckets.get(label, [])
        n = len(group)
        wins = sum(1 for t in group if t.get("pnl_pct", 0) > 0)
        avg_ret = sum(t.get("pnl_pct", 0.0) for t in group) / n if n else 0.0
        result[label] = {
            "count": n,
            "win_rate_pct": round(wins / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(avg_ret, 2),
        }
    return result


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 4: Equity Tracking â€” curve, drawdown, losing streaks
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _build_equity_curve(trades: List[dict]) -> List[Tuple[str, float]]:
    """Build equity curve from trade sequence."""
    if not trades:
        return [("start", 100.0)]

    # Use real equity_after if available (from the backtest engine)
    if all(t.get("equity_after") is not None for t in trades):
        curve = [("start", 100.0)]
        for t in trades:
            date_str = t.get("exit_date", "")
            curve.append((date_str, float(t["equity_after"])))
        return curve

    # Fallback: reconstruct from alloc_pct * pnl_pct
    equity = 100.0
    curve = [("start", equity)]
    for t in trades:
        alloc = float(t.get("alloc_pct", 0.20))
        equity *= (1 + alloc * t.get("pnl_pct", 0.0) / 100)
        date_str = t.get("exit_date", "")
        curve.append((date_str, round(equity, 4)))
    return curve


def _compute_drawdown_series(equity_curve: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """Compute drawdown % at each equity point."""
    peak = 0.0
    dd_series = []
    for date_str, eq in equity_curve:
        peak = max(peak, eq)
        dd = (peak - eq) / peak * 100 if peak > 0 else 0.0
        dd_series.append((date_str, round(dd, 2)))
    return dd_series


def _worst_losing_streak(trades: List[dict]) -> Dict[str, Any]:
    """Find the worst consecutive losing streak."""
    max_streak = 0
    current_streak = 0
    streak_pnl = 0.0
    max_streak_pnl = 0.0
    max_streak_start = ""
    max_streak_end = ""
    current_start = ""

    for t in trades:
        if t.get("pnl_pct", 0) <= 0:
            if current_streak == 0:
                current_start = t.get("entry_date", "")
            current_streak += 1
            streak_pnl += t.get("pnl_pct", 0.0)
            if current_streak > max_streak:
                max_streak = current_streak
                max_streak_pnl = streak_pnl
                max_streak_start = current_start
                max_streak_end = t.get("exit_date", "")
        else:
            current_streak = 0
            streak_pnl = 0.0

    return {
        "length": max_streak,
        "total_pnl_pct": round(max_streak_pnl, 2),
        "start_date": max_streak_start,
        "end_date": max_streak_end,
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 5: Risk Monitoring
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _compute_risk_metrics(
    trades: List[dict],
    equity_curve: List[Tuple[str, float]],
) -> Dict[str, Any]:
    """Compute risk metrics and generate alerts."""
    if not trades:
        return {
            "max_loss_pct": 0.0,
            "consecutive_losses": 0,
            "current_drawdown_pct": 0.0,
            "alerts": [],
        }

    pnls = [t.get("pnl_pct", 0.0) for t in trades]
    max_loss = min(pnls) if pnls else 0.0

    # Current consecutive losses (from the end of the trade list)
    consec = 0
    for t in reversed(trades):
        if t.get("pnl_pct", 0) <= 0:
            consec += 1
        else:
            break

    # Current drawdown
    if equity_curve:
        peak = max(eq for _, eq in equity_curve)
        current_eq = equity_curve[-1][1]
        current_dd = (peak - current_eq) / peak * 100 if peak > 0 else 0.0
    else:
        current_dd = 0.0

    alerts = []
    if current_dd > 5.0:
        alerts.append(f"DRAWDOWN ALERT: Current drawdown is {current_dd:.1f}% (> 5%)")
    if consec >= 3:
        alerts.append(f"STREAK ALERT: {consec} consecutive losses")
    if max_loss < -8.0:
        alerts.append(f"LOSS ALERT: Worst single trade was {max_loss:.1f}%")

    return {
        "max_loss_pct": round(max_loss, 2),
        "consecutive_losses": consec,
        "current_drawdown_pct": round(current_dd, 2),
        "alerts": alerts,
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 6: Trade Distribution (monthly)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _monthly_distribution(trades: List[dict]) -> List[Dict[str, Any]]:
    """Compute trades per month and returns per month."""
    by_month: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        exit_d = t.get("exit_date", "")
        if len(exit_d) >= 7:
            by_month[exit_d[:7]].append(t)

    result = []
    for month in sorted(by_month.keys()):
        group = by_month[month]
        n = len(group)
        total_ret = sum(t.get("pnl_pct", 0.0) for t in group)
        wins = sum(1 for t in group if t.get("pnl_pct", 0) > 0)
        result.append({
            "month": month,
            "trade_count": n,
            "total_return_pct": round(total_ret, 2),
            "avg_return_pct": round(total_ret / n, 2) if n else 0.0,
            "win_rate_pct": round(wins / n * 100, 1) if n else 0.0,
        })
    return result


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 7: System Health Score
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _compute_health_score(
    win_rate_pct: float,
    avg_return_pct: float,
    max_drawdown_pct: float,
) -> float:
    """
    Compute normalized system health score (0â€“100).

    health = win_rate_norm * 0.3 + return_norm * 0.3 + dd_norm * 0.4

    win_rate_norm:  0% â†’ 0, 100% â†’ 100
    return_norm:    clamp avg_return to [-10, +10], map to 0â€“100
    dd_norm:        0% DD â†’ 100, 20%+ DD â†’ 0
    """
    wr_norm = max(0.0, min(100.0, win_rate_pct))

    # Map avg_return: -10% â†’ 0, 0% â†’ 50, +10% â†’ 100
    clamped_ret = max(-10.0, min(10.0, avg_return_pct))
    ret_norm = (clamped_ret + 10.0) / 20.0 * 100.0

    # Map drawdown: 0% â†’ 100, 20% â†’ 0
    clamped_dd = max(0.0, min(20.0, max_drawdown_pct))
    dd_norm = (1 - clamped_dd / 20.0) * 100.0

    raw = wr_norm * 0.3 + ret_norm * 0.3 + dd_norm * 0.4
    return round(max(0.0, min(100.0, raw)), 1)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 10: Final Decision Engine
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _final_verdict(
    total_trades: int,
    win_rate_pct: float,
    max_drawdown_pct: float,
    profit_factor: float,
    health_score: float,
) -> Dict[str, Any]:
    """Determine if the system is ready for real-money trading."""
    reasons = []
    passed = True

    if total_trades < _TRADE_THRESHOLD_PRELIMINARY:
        reasons.append(f"Need {_TRADE_THRESHOLD_PRELIMINARY}+ trades (have {total_trades})")
        passed = False

    if win_rate_pct < 55.0:
        reasons.append(f"Win rate {win_rate_pct:.1f}% < 55% required")
        passed = False

    if max_drawdown_pct > 5.0:
        reasons.append(f"Max drawdown {max_drawdown_pct:.1f}% > 5% limit")
        passed = False

    if profit_factor < 1.2:
        reasons.append(f"Profit factor {profit_factor:.2f} < 1.2 required")
        passed = False

    if health_score < 60:
        reasons.append(f"Health score {health_score:.0f} < 60 required")
        passed = False

    if passed:
        verdict = "READY FOR REAL MONEY"
        verdict_ar = "Ø¬Ø§Ù‡Ø² ØªØ¯Ø®Ù„ ÙÙ„ÙˆØ³ Ø­Ù‚ÙŠÙ‚ÙŠØ©!"
        icon = "âœ…"
    else:
        verdict = "NOT READY"
        verdict_ar = "Ù„Ø³Ù‡ Ø¨Ø¯Ø±ÙŠ â€” Ø§Ù„Ø£Ø³Ø¨Ø§Ø¨ Ø£Ø¯Ù†Ø§Ù‡."
        icon = "ðŸ”´"

    return {
        "verdict": verdict,
        "verdict_ar": verdict_ar,
        "icon": icon,
        "passed": passed,
        "reasons": reasons,
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CSV Loader â€” read backtest CSV trades into trade dicts
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_trades_from_csv(csv_path: str) -> List[dict]:
    """
    Load trades from a backtest CSV file.
    Expected columns: sym,sector,signal_type,regime,entry_date,entry,stop,
                      target,bars_held,is_short,smart_rank,exit_date,exit,
                      pnl_pct,rr,outcome
    """
    if not os.path.exists(csv_path):
        log.warning("CSV file not found: %s", csv_path)
        return []

    trades = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trade = {
                "sym": row.get("sym", ""),
                "sector": row.get("sector", ""),
                "signal_type": row.get("signal_type", ""),
                "regime": row.get("regime", ""),
                "entry_date": row.get("entry_date", ""),
                "entry": _safe_float(row.get("entry", 0)),
                "stop": _safe_float(row.get("stop", 0)),
                "target": _safe_float(row.get("target", 0)),
                "bars_held": int(row.get("bars_held", 0) or 0),
                "smart_rank": _safe_float(row.get("smart_rank", 0)),
                "exit_date": row.get("exit_date", ""),
                "exit": _safe_float(row.get("exit", 0)),
                "pnl_pct": _safe_float(row.get("pnl_pct", 0)),
                "rr": _safe_float(row.get("rr", 0)),
                "outcome": row.get("outcome", ""),
                "trade_type": _classify_trade_type(
                    _safe_float(row.get("smart_rank", 0))
                ),
            }
            trades.append(trade)
    return trades


def _safe_float(val: Any) -> float:
    try:
        v = float(val)
        return v if math.isfinite(v) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _classify_trade_type(smart_rank: float) -> str:
    if smart_rank >= K.SMARTRANK_ENTRY_THRESHOLD:
        return "STRONG"
    elif smart_rank >= K.SMARTRANK_MIN_ACTIONABLE:
        return "MEDIUM"
    return "UNCLASSIFIED"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 8 & 9: Main Dashboard Builder + Console Output
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_tracking_dashboard(
    trades: List[dict],
    title: str = "TRADING SYSTEM DASHBOARD",
) -> Dict[str, Any]:
    """
    Build the complete tracking dashboard from a list of closed trades.
    Returns a dict with all metrics, classifications, risk data, and verdict.
    """
    metrics = compute_metrics(trades)
    overall = metrics.get("overall", {})

    total_trades = overall.get("total_trades", 0)
    win_rate = overall.get("win_rate_pct", 0.0)
    avg_return = overall.get("avg_return_pct", 0.0)
    total_return = overall.get("total_return_pct", 0.0)
    max_dd = overall.get("max_drawdown_pct", 0.0)
    pf = overall.get("profit_factor", 0.0)
    expectancy = overall.get("expectancy_pct", 0.0)
    sharpe = overall.get("sharpe_ratio", 0.0)

    # PART 2: Progress
    status_label, status_icon = _progress_status(total_trades)

    # PART 3: Classification
    classification = _classify_trades(trades)

    # PART 4: Equity
    equity_curve = _build_equity_curve(trades)
    drawdown_series = _compute_drawdown_series(equity_curve)
    losing_streak = _worst_losing_streak(trades)

    # PART 5: Risk
    risk = _compute_risk_metrics(trades, equity_curve)

    # PART 6: Monthly
    monthly = _monthly_distribution(trades)

    # PART 7: Health
    health_score = _compute_health_score(win_rate, avg_return, max_dd)

    # PART 10: Verdict
    verdict = _final_verdict(total_trades, win_rate, max_dd, pf, health_score)

    return {
        "title": title,
        "core_metrics": {
            "total_trades": total_trades,
            "win_rate_pct": win_rate,
            "avg_return_pct": avg_return,
            "total_return_pct": total_return,
            "max_drawdown_pct": max_dd,
            "profit_factor": pf,
            "expectancy_pct": expectancy,
            "sharpe_ratio": sharpe,
            "largest_win_pct": overall.get("largest_win_pct", 0.0),
            "largest_loss_pct": overall.get("largest_loss_pct", 0.0),
        },
        "progress": {
            "trades_completed": total_trades,
            "status": status_label,
            "icon": status_icon,
        },
        "classification": classification,
        "equity_curve": equity_curve,
        "drawdown_series": drawdown_series,
        "losing_streak": losing_streak,
        "risk": risk,
        "monthly": monthly,
        "health_score": health_score,
        "verdict": verdict,
        "full_metrics": metrics,
    }


def format_dashboard_report(dashboard: Dict[str, Any]) -> str:
    """
    Format the dashboard as a console-friendly report string.

    PART 8: Output format.
    """
    cm = dashboard["core_metrics"]
    prog = dashboard["progress"]
    cls = dashboard["classification"]
    risk = dashboard["risk"]
    streak = dashboard["losing_streak"]
    monthly = dashboard["monthly"]
    health = dashboard["health_score"]
    verdict = dashboard["verdict"]
    title = dashboard.get("title", "TRADING SYSTEM DASHBOARD")

    lines = [
        f"===== {title} =====",
        "",
        f"Trades: {cm['total_trades']}",
        f"Status: {prog['status']} {prog['icon']}",
        "",
        f"Win Rate: {cm['win_rate_pct']}%",
        f"Avg Return: {cm['avg_return_pct']}%",
        f"Total Return: {cm['total_return_pct']}%",
        f"Max Drawdown: {cm['max_drawdown_pct']}%",
        f"Profit Factor: {cm['profit_factor']}",
        f"Expectancy: {cm['expectancy_pct']}%",
        f"Sharpe Ratio: {cm['sharpe_ratio']}",
        "",
        "--- By Type ---",
    ]

    for label in ("STRONG", "MEDIUM"):
        s = cls.get(label, {})
        lines.append(
            f"{label}: {s.get('count', 0)} trades | "
            f"{s.get('win_rate_pct', 0.0)}% win | "
            f"{s.get('avg_return_pct', 0.0):+.2f}%"
        )

    lines.extend([
        "",
        "--- Risk ---",
        f"Max Loss: {cm['largest_loss_pct']}%",
        f"Losing Streak: {streak['length']} trades ({streak['total_pnl_pct']}%)",
        f"Current DD: {risk['current_drawdown_pct']}%",
        f"Consec. Losses (now): {risk['consecutive_losses']}",
    ])

    if risk["alerts"]:
        lines.append("")
        lines.append("--- Alerts ---")
        for alert in risk["alerts"]:
            lines.append(f"  >> {alert}")

    lines.extend([
        "",
        "--- Monthly ---",
    ])
    if monthly:
        for m in monthly:
            lines.append(
                f"  {m['month']}: {m['trade_count']} trades | "
                f"{m['total_return_pct']:+.1f}% return | "
                f"{m['win_rate_pct']}% win"
            )
    else:
        lines.append("  No trades yet.")

    lines.extend([
        "",
        f"--- Health Score: {health}/100 ---",
        "",
        "--- Verdict ---",
        f"{verdict['icon']} {verdict['verdict']}",
    ])

    if verdict["reasons"]:
        for r in verdict["reasons"]:
            lines.append(f"  - {r}")

    lines.extend([
        "",
        f"  {verdict['verdict_ar']}",
        "",
        "=" * (len(title) + 12),
    ])

    return "\n".join(lines)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PART 9: Integration entry point
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_dashboard(
    trades: Optional[List[dict]] = None,
    csv_path: Optional[str] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    print_report: bool = True,
) -> Dict[str, Any]:
    """
    Main entry point for the Trade Tracking Dashboard.

    Args:
        trades:      List of closed trade dicts (from run_backtest or paper trading).
        csv_path:    Path to a backtest CSV file to load trades from.
        diagnostics: Optional diagnostics dict from the backtest engine.
        print_report: If True, print the formatted report to console.

    Returns:
        Complete dashboard dict with all metrics, equity, risk, and verdict.
    """
    # Merge trades from all sources
    all_trades: List[dict] = []

    if trades:
        all_trades.extend(trades)

    if csv_path:
        csv_trades = load_trades_from_csv(csv_path)
        all_trades.extend(csv_trades)

    # Sort by exit_date for correct equity curve construction
    all_trades.sort(key=lambda t: t.get("exit_date", ""))

    dashboard = build_tracking_dashboard(all_trades)

    text = format_dashboard_report(dashboard)
    dashboard["text"] = text

    if print_report:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode("utf-8", errors="replace").decode("ascii", errors="replace"))

    return dashboard


__all__ = [
    "run_dashboard",
    "build_tracking_dashboard",
    "format_dashboard_report",
    "load_trades_from_csv",
]
```

==================================================
FILE: egx_radar/data/__init__.py
================================

```python
"""Data layer: source fetchers and OHLCV merge/orchestration (Layer 2)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.data.fetchers import (
    _obfuscate,
    _deobfuscate,
    load_source_settings,
    save_source_settings,
    _atomic_json_write,
    _flatten_df,
    _yfin_extract,
    _chunker,
    _fetch_yahoo,
    _fetch_stooq_single,
    _fetch_stooq,
    _fetch_av_single,
    _fetch_investing_single,
    _fetch_investing,
    _td_dispatch_lock,
    _fetch_td_single,
    _fetch_twelve_data,
)

from egx_radar.data.merge import (
    _merge_ohlcv,
    download_all,
    _source_labels,
    _source_labels_lock,
)

__all__ = [
    # fetchers
    "_obfuscate",
    "_deobfuscate",
    "load_source_settings",
    "save_source_settings",
    "_atomic_json_write",
    "_flatten_df",
    "_yfin_extract",
    "_chunker",
    "_fetch_yahoo",
    "_fetch_stooq_single",
    "_fetch_stooq",
    "_fetch_av_single",
    "_fetch_investing_single",
    "_fetch_investing",
    "_td_dispatch_lock",
    "_fetch_td_single",
    "_fetch_twelve_data",
    # merge
    "_merge_ohlcv",
    "download_all",
    "_source_labels",
    "_source_labels_lock",
]
```

==================================================
FILE: egx_radar/data/fetchers.py
================================

```python
"""Data fetchers: multi-source OHLCV and supporting helpers (Layer 2)."""

import base64
import csv
import json
import logging
import math
import os
import re
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from egx_radar.config.settings import K, DATA_SOURCE_CFG, _data_cfg_lock, SOURCE_SETTINGS_FILE

log = logging.getLogger(__name__)


def _obfuscate(key: str) -> str:
    return base64.b64encode(key.encode()).decode() if key else ""


def _deobfuscate(enc: str) -> str:
    if not enc:
        return ""
    try:
        return base64.b64decode(enc.encode()).decode()
    except Exception:
        return enc


def load_source_settings() -> None:
    if not os.path.exists(SOURCE_SETTINGS_FILE):
        return
    try:
        with open(SOURCE_SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        saved["alpha_vantage_key"] = _deobfuscate(saved.get("alpha_vantage_key", ""))
        saved["twelve_data_key"]   = _deobfuscate(saved.get("twelve_data_key",   ""))
        with _data_cfg_lock:
            DATA_SOURCE_CFG.update(saved)
    except Exception as e:
        log.warning("load_source_settings: %s", e)


def save_source_settings() -> None:
    try:
        with _data_cfg_lock:
            snap = dict(DATA_SOURCE_CFG)
        snap["alpha_vantage_key"] = _obfuscate(str(snap.get("alpha_vantage_key", "")))
        snap["twelve_data_key"]   = _obfuscate(str(snap.get("twelve_data_key",   "")))
        _atomic_json_write(SOURCE_SETTINGS_FILE, snap)
    except Exception as e:
        log.error("save_source_settings: %s", e)


def _atomic_json_write(filepath: str, data: object) -> None:
    """Write JSON atomically: temp â†’ os.replace()."""
    dirpath = os.path.dirname(os.path.abspath(filepath)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp", prefix=".egx_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, filepath)
    except Exception as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _flatten_df(raw: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Normalise OHLCV column names and strip MultiIndex.

    Handles new yfinance (>=0.2.x) format where MultiIndex is (field, ticker)
    AND old format where it was (ticker, field).
    """
    if raw is None or raw.empty:
        return None
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # Auto-detect format by checking if level 0 contains field names
        lv0_vals = set(str(v).title() for v in df.columns.get_level_values(0))
        ohlcv = {"Close", "Open", "High", "Low", "Volume", "Adj Close"}
        if lv0_vals & ohlcv:
            # New yfinance format: (field, ticker) â€” collapse level 0
            df.columns = df.columns.get_level_values(0)
        else:
            # Old format: (ticker, field) â€” take first ticker's slice
            first_ticker = df.columns.get_level_values(0)[0]
            df = df[first_ticker].copy()
    # Guarantee every column is a 1-D Series, not a nested DataFrame
    for col in list(df.columns):
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    df.columns = [str(c).strip().title() for c in df.columns]
    df.rename(columns={
        "Adj Close": "Close", "Adjusted Close": "Close",
        "Adj_Close": "Close", "Turnover": "Volume",
    }, inplace=True)
    seen: dict = {}
    df = df.loc[:, [not (c in seen or seen.update({c: True})) for c in df.columns]]
    return df if "Close" in df.columns else None


def _yfin_extract(raw: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
    """Robustly extract a single ticker from a yfinance MultiIndex DataFrame.

    Handles both old format (ticker, field) and new yfinance (field, ticker).
    """
    if raw is None or raw.empty:
        return None
    if not isinstance(raw.columns, pd.MultiIndex):
        return _flatten_df(raw)

    lv0 = set(raw.columns.get_level_values(0))
    lv1 = set(raw.columns.get_level_values(1))

    # Detect new yfinance format: level 0 = field names, level 1 = tickers
    ohlcv = {"Close", "Open", "High", "Low", "Volume", "Adj Close"}
    lv0_titled = {str(v).title() for v in lv0}
    if lv0_titled & ohlcv:
        # New format: (field, ticker) â€” look for ticker in level 1
        if ticker in lv1:
            try:
                sub = raw.xs(ticker, axis=1, level=1).copy()
                return _flatten_df(sub)
            except Exception as exc:
                log.debug("_yfin_extract %s: %s", ticker, exc)
        # Case-insensitive fallback on level 1
        for v in lv1:
            if str(v).upper() == ticker.upper():
                try:
                    sub = raw.xs(v, axis=1, level=1).copy()
                    return _flatten_df(sub)
                except Exception as exc:
                    log.debug("_yfin_extract %s: %s", ticker, exc)
                    continue
        return None

    # Old format: (ticker, field) â€” look for ticker in level 0
    if ticker in lv0:
        try:
            return _flatten_df(raw[ticker].copy())
        except Exception as exc:
            log.debug("_yfin_extract %s: %s", ticker, exc)
            return None
    if ticker in lv1:
        try:
            return _flatten_df(raw.xs(ticker, axis=1, level=1).copy())
        except Exception as exc:
            log.debug("_yfin_extract %s: %s", ticker, exc)
            return None
    # Case-insensitive fallback
    for lv, vals in [(0, lv0), (1, lv1)]:
        for v in vals:
            if str(v).upper() == ticker.upper():
                try:
                    sub = raw[v].copy() if lv == 0 else raw.xs(v, axis=1, level=1).copy()
                    return _flatten_df(sub)
                except Exception as exc:
                    log.debug("_yfin_extract %s: %s", ticker, exc)
                    continue
    return None


def _chunker(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def _fetch_yahoo(yahoo_syms: List[str]) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    for chunk in _chunker(yahoo_syms, K.CHUNK_SIZE):
        for attempt in range(K.MAX_DOWNLOAD_RETRIES + 1):
            try:
                # auto_adjust=False: let _normalise_df() apply Adj Close â†’ Close
                # uniformly across all sources to avoid double-adjustment.
                raw = yf.download(
                    chunk, interval="1d", period="2y",
                    group_by="ticker", auto_adjust=False,
                    progress=False, timeout=K.DOWNLOAD_TIMEOUT,
                )
                if raw is None or raw.empty:
                    break
                for ticker in chunk:
                    if len(chunk) == 1 and not isinstance(raw.columns, pd.MultiIndex):
                        sub = _flatten_df(raw)
                    else:
                        sub = _yfin_extract(raw, ticker)
                    if sub is not None and not sub.empty:
                        result[ticker] = sub
                break
            except Exception as exc:
                if attempt < K.MAX_DOWNLOAD_RETRIES:
                    time.sleep(K.RETRY_BACKOFF_BASE ** attempt)
                else:
                    log.error("Yahoo chunk %s failed: %s", chunk, exc)
    return result


def _fetch_stooq_single(sym: str) -> Optional[pd.DataFrame]:
    url = f"https://stooq.com/q/d/l/?s={sym.lower()}.eg&i=d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        if "No data" in text or len(text.strip()) < 50:
            return None
        df = pd.read_csv(StringIO(text), parse_dates=["Date"], index_col="Date")
        df.columns = [c.strip().title() for c in df.columns]
        df = df.sort_index()
        return df if not df.empty and "Close" in df.columns else None
    except Exception as exc:
        log.debug("Stooq %s: %s", sym, exc)
        return None


def _fetch_stooq(sym_list: List[str]) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    lock   = threading.Lock()

    def _work(sym: str):
        df = _fetch_stooq_single(sym)
        if df is not None:
            with lock:
                result[sym] = df

    with ThreadPoolExecutor(max_workers=K.STOOQ_MAX_WORKERS) as pool:
        futs = [pool.submit(_work, s) for s in sym_list]
        for f in as_completed(futs, timeout=25):
            try:
                f.result()
            except Exception as exc:
                log.debug("Stooq worker: %s", exc)
    return result


def _fetch_av_single(sym: str, api_key: str) -> Optional[pd.DataFrame]:
    url = (
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY_ADJUSTED&symbol={urllib.parse.quote(sym+'.CA')}"
        f"&outputsize=full&apikey={api_key}&datatype=csv"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        if "Invalid API" in text or len(text) < 100:
            return None
        df = pd.read_csv(StringIO(text), parse_dates=["timestamp"], index_col="timestamp")
        df.index.name = "Date"
        df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume", "adjusted_close": "Adj Close"
        }, inplace=True)
        df = df.sort_index()
        if "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        return df if not df.empty and "Close" in df.columns else None
    except Exception as exc:
        log.debug("AlphaVantage %s: %s", sym, exc)
        return None


def _fetch_investing_single(sym: str) -> Optional[float]:
    slug_map: Dict[str, str] = {
        "COMI": "commercial-international-bank-egypt", "CIEB": "cib-egypt",
        "TMGH": "talaat-moustafa-group", "ETEL": "telecom-egypt",
        "ORAS": "orascom-construction", "PHDC": "palm-hills-developments",
        "SKPC": "sidi-kerir-petrochemicals", "AMOC": "alexandria-mineral-oils",
        "EAST": "eastern-company", "ABUK": "abu-kir-fertilizers",
    }
    slug = slug_map.get(sym)
    if not slug:
        return None
    url = f"https://www.investing.com/equities/{slug}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'data-test="instrument-price-last"[^>]*>([\d,.]+)', html)
        if not m:
            m = re.search(r'"price":\s*"([\d.]+)"', html)
        if not m:
            return None
        price = float(m.group(1).replace(",", ""))
        return price if price > 0 else None
    except Exception as exc:
        log.debug("Investing.com %s: %s", sym, exc)
        return None


def _fetch_investing(sym_list: List[str]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    lock   = threading.Lock()

    def _work(sym: str):
        price = _fetch_investing_single(sym)
        if price:
            with lock:
                result[sym] = price

    with ThreadPoolExecutor(max_workers=K.INVESTING_MAX_WORKERS) as pool:
        futs = [pool.submit(_work, s) for s in sym_list]
        for f in as_completed(futs, timeout=30):
            try:
                f.result()
            except Exception as exc:
                log.debug("Investing worker: %s", exc)
    return result


_td_dispatch_lock = threading.Lock()


def _fetch_td_single(sym: str, api_key: str) -> Optional[pd.DataFrame]:
    url = (
        "https://api.twelvedata.com/time_series"
        f"?symbol={urllib.parse.quote(sym)}&exchange=EGX"
        f"&interval=1day&outputsize={K.TD_BARS}&format=JSON"
        f"&apikey={urllib.parse.quote(api_key)}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        if "code" in data and data["code"] != 200:
            return None
        values = data.get("values") or []
        records = []
        for bar in values:
            try:
                records.append({
                    "Date":   pd.Timestamp(bar["datetime"]),
                    "Open":   float(bar["open"]),   "High":   float(bar["high"]),
                    "Low":    float(bar["low"]),    "Close":  float(bar["close"]),
                    "Volume": float(bar.get("volume", 0)),
                })
            except (KeyError, ValueError, TypeError):
                continue
        if not records:
            return None
        df = pd.DataFrame(records).set_index("Date").sort_index()
        return df if len(df) >= K.MIN_BARS_RELAXED else None
    except Exception as exc:
        log.debug("TwelveData %s: %s", sym, exc)
        return None


def _fetch_twelve_data(sym_list: List[str], api_key: str) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    result_lock = threading.Lock()

    def _work(sym: str):
        with _td_dispatch_lock:
            time.sleep(K.TD_REQUEST_DELAY)
            df = _fetch_td_single(sym, api_key)
        if df is not None:
            with result_lock:
                result[sym] = df

    with ThreadPoolExecutor(max_workers=K.TD_MAX_WORKERS) as pool:
        futs = [pool.submit(_work, s) for s in sym_list]
        timeout = len(sym_list) * K.TD_REQUEST_DELAY + 30
        for f in as_completed(futs, timeout=timeout):
            try:
                f.result()
            except Exception as exc:
                log.debug("TD worker: %s", exc)
    return result


__all__ = [
    "_obfuscate",
    "_deobfuscate",
    "load_source_settings",
    "save_source_settings",
    "_atomic_json_write",
    "_flatten_df",
    "_yfin_extract",
    "_chunker",
    "_fetch_yahoo",
    "_fetch_stooq_single",
    "_fetch_stooq",
    "_fetch_av_single",
    "_fetch_investing_single",
    "_fetch_investing",
    "_td_dispatch_lock",
    "_fetch_td_single",
    "_fetch_twelve_data",
]
```

==================================================
FILE: egx_radar/data/merge.py
=============================

```python
"""Data merge and orchestration for multi-source OHLCV (Layer 2)."""

import logging
import math
import threading
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd

from egx_radar.config.settings import K, SYMBOLS, DATA_SOURCE_CFG, _data_cfg_lock
from egx_radar.data.fetchers import (
    _fetch_yahoo,
    _fetch_stooq,
    _fetch_av_single,
    _fetch_investing,
    _fetch_twelve_data,
)

log = logging.getLogger(__name__)


# â”€â”€ Cross-Source Agreement Check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _cross_source_agreement(
    sym: str,
    candidates: list,          # list of (df, label) tuples
    threshold: float = None,
) -> tuple:
    """Return (agreement_score_0_to_1, spread_pct, details_str).

    Computes the percentage spread between the highest and lowest
    last-close price across all available sources.

    spread = (max_close - min_close) / median_close

    If spread > threshold, data sources disagree â€” flag it.
    threshold default: K.DG_CROSS_SOURCE_SPREAD_LIMIT (e.g. 0.05 = 5%)
    """
    if threshold is None:
        threshold = K.DG_CROSS_SOURCE_SPREAD_LIMIT  # add to settings: default 0.05

    closes = []
    labels = []
    for df_, lbl in candidates:
        try:
            v = float(df_["Close"].iloc[-1])
            if math.isfinite(v) and v > 0:
                closes.append(v)
                labels.append(lbl)
        except (IndexError, ValueError, TypeError):
            continue

    if len(closes) < 2:
        return 1.0, 0.0, "only one source â€” cannot cross-check"

    min_c = min(closes)
    max_c = max(closes)
    median_c = sorted(closes)[len(closes) // 2]
    spread = (max_c - min_c) / (median_c + 1e-9)

    src_str = ", ".join(f"{lbl}={c:.2f}" for lbl, c in zip(labels, closes))

    if spread <= threshold:
        return 1.0, spread, f"sources agree ({src_str}) spread={spread:.1%}"
    else:
        score = max(0.0, 1.0 - spread / (threshold * 4))
        details = f"PRICE DISAGREEMENT ({src_str}) spread={spread:.1%} > {threshold:.0%}"
        log.warning("Cross-source %s: %s", sym, details)
        return score, spread, details

_source_labels: Dict[str, str] = {}
_source_labels_lock = threading.Lock()


def _merge_ohlcv(
    sym: str,
    yahoo_df: Optional[pd.DataFrame],
    stooq_df: Optional[pd.DataFrame],
    av_df:    Optional[pd.DataFrame],
    inv_price: Optional[float],
    td_df:    Optional[pd.DataFrame] = None,
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Select best available OHLCV source with priority:
      Yahoo-available:  Yahoo > Stooq > TD > AV
      Yahoo-absent:     TD    > Stooq > AV
    Consensus close = trimmed mean of sources within 5% of each other.
    """
    yahoo_ok = yahoo_df is not None and len(yahoo_df) >= K.MIN_BARS

    for df_, label in [(yahoo_df, "Yahoo"), (stooq_df, "Stooq"), (av_df, "AV"), (td_df, "TD")]:
        if df_ is not None:
            if "Volume" not in df_.columns:
                df_.loc[:, "Volume"] = 0.0

    candidates: List[Tuple[pd.DataFrame, str]] = []
    for df_, lbl in [(yahoo_df, "Yahoo"), (stooq_df, "Stooq"), (av_df, "AV"), (td_df, "TD")]:
        if df_ is None or "Close" not in df_.columns:
            continue
        thresh = K.MIN_BARS if lbl == "Yahoo" else K.MIN_BARS_RELAXED
        if len(df_) >= thresh and df_["Close"].notna().sum() >= thresh:
            last10 = df_["Close"].dropna().iloc[-10:]
            if len(last10) >= 10 and last10.nunique() <= 1 and df_["Volume"].iloc[-5:].sum() == 0:
                log.debug("%s source %s has stale/frozen OHLC â€” ignoring", sym, lbl)
                continue
            candidates.append((df_, lbl))

    if not candidates:
        return None, "â€”"

    priority = ["Yahoo", "Stooq", "TD", "AV"] if yahoo_ok else ["TD", "Stooq", "AV"]
    candidates.sort(key=lambda x: priority.index(x[1]) if x[1] in priority else 99)
    base_df, base_src = candidates[0]

    # Drop rows where Close is NaN to prevent propagation
    base_df = base_df.copy()
    base_df = base_df.dropna(subset=["Close"])
    if len(base_df) < K.MIN_BARS_RELAXED:
        log.warning("_merge_ohlcv %s: too few valid Close rows after NaN drop", sym)
        return None, "â€”"

    # Consensus close: trimmed mean within 5%
    closes = []
    for c_df, _ in candidates:
        try:
            v = float(c_df["Close"].iloc[-1])
            if math.isfinite(v) and v > 0:
                closes.append(v)
        except (IndexError, ValueError, TypeError):
            pass

    if len(closes) >= 2:
        mean_c   = sum(closes) / len(closes)
        filtered = [v for v in closes if abs(v - mean_c) / (mean_c + 1e-9) < 0.05]
        if filtered:
            consensus = sum(filtered) / len(filtered)
            base_df = base_df.copy()
            try:
                base_df.iloc[-1, base_df.columns.get_loc("Close")] = consensus
                base_src += "+" + "+".join(c[1] for c in candidates[1:])
            except (KeyError, IndexError):
                pass

    # Investing.com cross-check
    if inv_price and inv_price > 0:
        try:
            last = float(base_df["Close"].iloc[-1])
            if math.isfinite(last) and abs(last - inv_price) / (last + 1e-9) > 0.03:
                log.warning("Price mismatch %s: base=%.2f INV=%.2f", sym, last, inv_price)
                base_src += "âš ï¸"
            else:
                base_src += "+INV"
        except (IndexError, ValueError, TypeError):
            pass

    # Cross-source agreement check (Yahoo vs Stooq vs TD)
    if len(candidates) >= 2:
        cs_score, cs_spread, cs_detail = _cross_source_agreement(sym, candidates)
        if cs_spread > K.DG_CROSS_SOURCE_SPREAD_LIMIT:
            # Append disagreement warning to source label so UI shows it
            base_src += f" âš ï¸DISAGREE({cs_spread:.0%})"

    # Final sanity check: last Close must be a valid positive number
    try:
        last_close = float(base_df["Close"].iloc[-1])
        if math.isnan(last_close) or not math.isfinite(last_close) or last_close <= 0:
            log.warning("_merge_ohlcv %s: invalid final Close=%.4f â€” discarding", sym, last_close)
            return None, "â€”"
    except (IndexError, ValueError, TypeError) as exc:
        log.warning("_merge_ohlcv %s: Close extraction failed: %s", sym, exc)
        return None, "â€”"

    return base_df, base_src


def download_all() -> Dict[str, pd.DataFrame]:
    """Download OHLCV from all enabled sources and return merged results."""
    global _source_labels
    with _source_labels_lock:
        _source_labels = {}

    sym_list = list(SYMBOLS.keys())
    with _data_cfg_lock:
        cfg = dict(DATA_SOURCE_CFG)

    yahoo_by_sym: Dict[str, pd.DataFrame] = {}
    stooq_by_sym: Dict[str, pd.DataFrame] = {}
    inv_prices: Dict[str, float] = {}
    td_by_sym: Dict[str, pd.DataFrame] = {}

    def _do_yahoo():
        nonlocal yahoo_by_sym
        if cfg.get("use_yahoo"):
            yfin_syms = list(SYMBOLS.values())
            if K.EGX30_SYMBOL not in yfin_syms:
                yfin_syms.append(K.EGX30_SYMBOL)
            log.info("Yahoo Finance: downloading %d symbols...", len(yfin_syms))
            raw = _fetch_yahoo(yfin_syms)
            yahoo_by_sym = {k.replace(".CA", ""): v for k, v in raw.items()}

    def _do_stooq():
        nonlocal stooq_by_sym
        if cfg.get("use_stooq"):
            log.info("Stooq: downloading...")
            stooq_by_sym = _fetch_stooq(sym_list)

    def _do_investing():
        nonlocal inv_prices
        if cfg.get("use_investing"):
            log.info("Investing.com: cross-checking prices...")
            inv_prices = _fetch_investing(sym_list)

    def _do_td():
        nonlocal td_by_sym
        td_key = str(cfg.get("twelve_data_key", "")).strip()
        if cfg.get("use_twelve_data") and td_key:
            log.info("TwelveData: downloading %d symbols...", len(sym_list))
            td_by_sym = _fetch_twelve_data(sym_list, td_key)

    av_by_sym: Dict[str, pd.DataFrame] = {}
    _av_lock = threading.Lock()  # always created; guards av_by_sym writes from _av_bg
    av_thread: Optional[threading.Thread] = None
    av_key = str(cfg.get("alpha_vantage_key", "")).strip()
    if cfg["use_alpha_vantage"] and av_key:
        def _av_bg():
            for s in sym_list[:5]:
                df = _fetch_av_single(s, av_key)
                if df is not None:
                    with _av_lock:   # FIX: guard dict writes from background thread
                        av_by_sym[s] = df
                time.sleep(12)
        av_thread = threading.Thread(target=_av_bg, daemon=True)
        av_thread.start()

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(_do_yahoo)
        f2 = executor.submit(_do_stooq)
        f3 = executor.submit(_do_investing)
        f4 = executor.submit(_do_td)
        f1.result(); f2.result(); f3.result(); f4.result()

    if av_thread is not None and av_thread.is_alive():
        av_thread.join(timeout=5)

    merged: Dict[str, pd.DataFrame] = {}
    local_labels: Dict[str, str]    = {}

    for sym in sym_list:
        df_y  = yahoo_by_sym.get(sym)
        df_s  = stooq_by_sym.get(sym)
        with _av_lock:           # FIX: safely read av_by_sym
            df_a = av_by_sym.get(sym)
        df_t  = td_by_sym.get(sym)
        inv_p = inv_prices.get(sym)

        df_final, label = _merge_ohlcv(sym, df_y, df_s, df_a, inv_p, td_df=df_t)
        if df_final is not None:
            # Ensure Volume column exists
            if "Volume" not in df_final.columns:
                df_final = df_final.copy()
                df_final["Volume"] = 0.0
            merged[SYMBOLS[sym]] = df_final
            local_labels[sym]    = label

    # Add EGX30 Proxy to merged results if available from Yahoo
    egx_proxy_sym = K.EGX30_SYMBOL.replace(".CA", "") # It shouldn't have .CA, but just in case
    if egx_proxy_sym in yahoo_by_sym:
        df_proxy = yahoo_by_sym[egx_proxy_sym]
        if df_proxy is not None and len(df_proxy) >= K.EGX30_HEALTH_BARS:
            if "Volume" not in df_proxy.columns:
                df_proxy = df_proxy.copy()
                df_proxy["Volume"] = 0.0
            merged[K.EGX30_SYMBOL] = df_proxy
            local_labels["EGX30"] = "Yahoo"

    with _source_labels_lock:
        _source_labels = local_labels

    log.info(
        "Merged: %d symbols | Y:%d S:%d AV:%d INV:%d TD:%d",
        len(merged), len(yahoo_by_sym), len(stooq_by_sym),
        len(av_by_sym), len(inv_prices), len(td_by_sym),
    )
    return merged


__all__ = [
    "_merge_ohlcv",
    "download_all",
    "_source_labels",
    "_source_labels_lock",
]
```

==================================================
FILE: egx_radar/database/__init__.py
====================================

```python
"""Database module for EGX Radar - persistent data management."""

from egx_radar.database.manager import DatabaseManager
from egx_radar.database.models import Base, BacktestResult, Trade, Signal, StrategyMetrics

__all__ = [
    'DatabaseManager',
    'Base',
    'BacktestResult',
    'Trade',
    'Signal',
    'StrategyMetrics',
]
```

==================================================
FILE: egx_radar/database/alembic_env.py
=======================================

```python
"""Alembic migration configuration for EGX Radar database.

To set up Alembic for the first time:
    alembic init egx_radar/database/migrations
    
To create a new migration:
    alembic revision --autogenerate -m "Description of changes"
    
To apply migrations:
    alembic upgrade head
    
To rollback:
    alembic downgrade -1

For more info: https://alembic.sqlalchemy.org/
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# This is the Alembic Config object, which provides the values
# of the [alembic] section of the .ini file, as well as other
# options containing message to user code.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from egx_radar.database.models import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    sqlalchemy_url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

==================================================
FILE: egx_radar/database/config.py
==================================

```python
"""Database configuration for different environments."""

import os
from typing import Optional
from enum import Enum


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = 'sqlite'
    POSTGRESQL = 'postgresql'


class DatabaseConfig:
    """Database configuration manager."""
    
    @staticmethod
    def get_url(
        db_type: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        """
        Get database connection URL.
        
        Priority:
        1. Environment variable DATABASE_URL
        2. Provided parameters
        3. Default SQLite
        
        Args:
            db_type: Database type (sqlite, postgresql)
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        
        Returns:
            Connection URL string
        """
        # Check environment variable first
        if 'DATABASE_URL' in os.environ:
            return os.environ['DATABASE_URL']
        
        # Use provided parameters
        db_type = db_type or os.environ.get('DB_TYPE', 'sqlite')
        
        if db_type.lower() == 'postgresql':
            host = host or os.environ.get('DB_HOST', 'localhost')
            port = port or int(os.environ.get('DB_PORT', 5432))
            database = database or os.environ.get('DB_NAME', 'egx_radar')
            user = user or os.environ.get('DB_USER', 'postgres')
            password = password or os.environ.get('DB_PASSWORD', '')
            
            if password:
                url = f'postgresql://{user}:{password}@{host}:{port}/{database}'
            else:
                url = f'postgresql://{user}@{host}:{port}/{database}'
            
            return url
        
        elif db_type.lower() == 'sqlite':
            db_path = database or os.environ.get('DB_PATH', 'egx_radar.db')
            return f'sqlite:///{db_path}'
        
        else:
            raise ValueError(f'Unsupported database type: {db_type}')
    
    @staticmethod
    def get_development_url() -> str:
        """Get development database URL (SQLite in-memory)."""
        return 'sqlite:///:memory:'
    
    @staticmethod
    def get_testing_url() -> str:
        """Get testing database URL (SQLite temporary file)."""
        return 'sqlite:///test_egx_radar.db'
    
    @staticmethod
    def get_production_url() -> str:
        """
        Get production database URL from environment.
        
        Requires:
        - DATABASE_URL or
        - DB_TYPE=postgresql with DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            return db_url
        
        # Try to construct from individual env vars
        return DatabaseConfig.get_url(
            db_type=os.environ.get('DB_TYPE'),
            host=os.environ.get('DB_HOST'),
            port=int(os.environ.get('DB_PORT', 5432)) if os.environ.get('DB_PORT') else None,
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
        )


# Recommended environment setup:
"""
DEVELOPMENT:
    export DATABASE_URL=sqlite:///egx_radar.db

TESTING:
    export DATABASE_URL=sqlite:///:memory:
    or use DatabaseConfig.get_testing_url()

PRODUCTION:
    export DATABASE_URL=postgresql://user:password@host:5432/egx_radar
    
    OR set individual variables:
    export DB_TYPE=postgresql
    export DB_HOST=db.example.com
    export DB_PORT=5432
    export DB_NAME=egx_radar
    export DB_USER=app_user
    export DB_PASSWORD=secure_password
"""
```

==================================================
FILE: egx_radar/database/manager.py
===================================

```python
"""Database manager for EGX Radar - connection management and CRUD operations."""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from egx_radar.database.models import (
    Base, BacktestResult, Trade, Signal, StrategyMetrics, EquityHistory
)


class DatabaseManager:
    """Database connection and operations manager."""
    
    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        """
        Initialize database manager.
        
        Args:
            database_url: Connection string (default: sqlite:///egx_radar.db)
            echo: Enable SQLAlchemy query logging
        """
        if database_url is None:
            database_url = os.environ.get(
                'DATABASE_URL',
                'sqlite:///egx_radar.db'
            )
        
        self.database_url = database_url
        self.echo = echo
        
        # Create engine with appropriate pool configuration
        if database_url.startswith('sqlite'):
            # SQLite: use StaticPool for better concurrent access
            self.engine = create_engine(
                database_url,
                connect_args={'check_same_thread': False},
                poolclass=StaticPool,
                echo=echo
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                database_url,
                echo=echo,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections hourly
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,  # Don't expire objects after commit
            bind=self.engine
        )
    
    def init_db(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_db(self) -> None:
        """Drop all tables (be careful with this)."""
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ==================== BACKTEST RESULTS ====================
    
    def save_backtest(
        self,
        backtest_id: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        metrics: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> int:
        """
        Save backtest result to database.
        
        Args:
            backtest_id: Unique backtest identifier
            start_date: Backtest start date
            end_date: Backtest end date
            symbols: List of symbols tested
            metrics: Performance metrics dict
            parameters: Configuration parameters used
        
        Returns:
            Backtest ID (use with get_backtest() to retrieve full object)
        """
        backtest = BacktestResult(
            backtest_id=backtest_id,
            backtest_date=datetime.utcnow(),
            start_date=start_date,
            end_date=end_date,
            symbols=','.join(symbols),
            symbol_count=len(symbols),
            
            total_trades=metrics.get('total_trades', 0),
            winning_trades=metrics.get('winning_trades', 0),
            losing_trades=metrics.get('losing_trades', 0),
            win_rate=metrics.get('win_rate', 0.0),
            
            total_pnl=metrics.get('total_pnl', 0),
            gross_profit=metrics.get('gross_profit', 0),
            gross_loss=metrics.get('gross_loss', 0),
            profit_factor=metrics.get('profit_factor', 0.0),
            
            max_drawdown=metrics.get('max_drawdown', 0.0),
            max_drawdown_pct=metrics.get('max_drawdown_pct', 0.0),
            sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
            sortino_ratio=metrics.get('sortino_ratio', 0.0),
            calmar_ratio=metrics.get('calmar_ratio', 0.0),
            
            avg_trade_return=metrics.get('avg_trade_return', 0.0),
            std_dev_returns=metrics.get('std_dev_returns', 0.0),
            expectancy=metrics.get('expectancy', 0.0),
            recovery_factor=metrics.get('recovery_factor', 0.0),
            
            execution_time_seconds=metrics.get('execution_time_seconds'),
            workers_used=metrics.get('workers_used', 1),
            status=metrics.get('status', 'completed'),
            notes=metrics.get('notes'),
            parameters=parameters,
        )
        
        with self.get_session() as session:
            session.add(backtest)
            session.flush()
            backtest_id_result = backtest.id
        
        return backtest_id_result
    
    def get_backtest(self, backtest_id: int) -> Optional[BacktestResult]:
        """Get backtest by ID."""
        with self.get_session() as session:
            return session.query(BacktestResult).filter(
                BacktestResult.id == backtest_id
            ).first()
    
    def get_backtests(
        self,
        limit: int = 100,
        offset: int = 0,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = None
    ) -> List[BacktestResult]:
        """
        Get backtests with optional filtering.
        
        Args:
            limit: Number of results to return
            offset: Number of results to skip
            symbol: Filter by symbol
            status: Filter by status
            days: Filter by last N days
        
        Returns:
            List of BacktestResult objects
        """
        with self.get_session() as session:
            query = session.query(BacktestResult)
            
            if symbol:
                query = query.filter(BacktestResult.symbols.ilike(f'%{symbol}%'))
            if status:
                query = query.filter(BacktestResult.status == status)
            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(BacktestResult.backtest_date >= cutoff)
            
            return query.order_by(BacktestResult.backtest_date.desc()).offset(offset).limit(limit).all()
    
    # ==================== TRADES ====================
    
    def save_trade(
        self,
        backtest_id: int,
        symbol: str,
        entry_date: datetime,
        entry_price: float,
        entry_signal: str,
        quantity: int,
        exit_date: Optional[datetime] = None,
        exit_price: Optional[float] = None,
        exit_reason: Optional[str] = None,
        pnl: Optional[float] = None,
        pnl_pct: Optional[float] = None
    ) -> int:
        """Save individual trade. Returns trade ID."""
        trade = Trade(
            backtest_id=backtest_id,
            symbol=symbol,
            entry_date=entry_date,
            entry_price=entry_price,
            entry_signal=entry_signal,
            quantity=quantity,
            exit_date=exit_date,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl=pnl,
            pnl_pct=pnl_pct,
            result='win' if (pnl and pnl > 0) else ('loss' if (pnl and pnl < 0) else 'breakeven'),
        )
        if exit_date and entry_date:
            trade.duration_minutes = int(
                (exit_date - entry_date).total_seconds() / 60
            )
        
        with self.get_session() as session:
            session.add(trade)
            session.flush()
            trade_id = trade.id
        
        return trade_id
    
    def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID."""
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.id == trade_id).first()
    
    def get_trades(
        self,
        backtest_id: int,
        symbol: Optional[str] = None,
        result: Optional[str] = None
    ) -> List[Trade]:
        """Get trades for a backtest."""
        with self.get_session() as session:
            query = session.query(Trade).filter(
                Trade.backtest_id == backtest_id
            )
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if result:
                query = query.filter(Trade.result == result)
            
            return query.order_by(Trade.entry_date).all()
    
    def save_trade_signal(self, trade_data: Dict[str, Any]) -> Optional[int]:
        """
        Save a live scanner trade signal to the database.
        
        This is used by the core scanner to persist live trading signals
        to the database. Unlike backtest trades, these are not associated
        with a backtest_id (backtest_id is None).
        
        Args:
            trade_data: Dictionary containing:
                - sym (str): Symbol
                - sector (str): Sector
                - entry (float): Entry price
                - stop (float): Stop loss price
                - target (float): Target price
                - atr (float): ATR value
                - smart_rank (float): SmartRank score
                - anticipation (float): Anticipation score
                - action (str): Action type (buy, sell, accumulate, etc.)
                - recorded_at (str): ISO datetime string
        
        Returns:
            Trade ID if successful, None on error
        """
        try:
            # Parse the recorded_at timestamp
            recorded_at = None
            if 'recorded_at' in trade_data:
                try:
                    recorded_at = datetime.fromisoformat(trade_data['recorded_at'])
                except (ValueError, TypeError):
                    recorded_at = datetime.utcnow()
            else:
                recorded_at = datetime.utcnow()
            
            # Create trade with minimal required fields
            # backtest_id is None for live signals (not from a backtest)
            trade = Trade(
                backtest_id=None,  # Live signal, not from backtest
                symbol=trade_data.get('sym', 'UNKNOWN'),
                entry_date=recorded_at,
                entry_price=float(trade_data.get('entry', 0.0)),
                entry_signal=trade_data.get('action', 'buy').lower(),
                quantity=1,  # Scanner does not compute shares yet
                exit_date=None,
                exit_price=None,
                exit_reason=None,
                pnl=None,
                pnl_pct=None,
                result=None,  # Not resolved yet
                max_profit=None,
                max_loss=None,
                duration_minutes=None,
            )
            
            with self.get_session() as session:
                session.add(trade)
                session.flush()
                trade_id = trade.id
            
            return trade_id
        
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(
                "Failed to save trade signal: %s", e
            )
            return None
    
    def update_trade_outcome(
        self,
        symbol: str,
        entry_date: datetime,
        exit_date: datetime,
        exit_price: float,
        pnl_pct: float,
        outcome: str,  # 'WIN', 'LOSS', 'TIMEOUT'
        exit_reason: Optional[str] = None,
    ) -> bool:
        """
        Update an open trade with its resolution outcome.
        
        Finds the most recent open trade for the symbol and entry_date,
        then updates it with exit information: exit_date, exit_price, pnl_pct,
        result (calculated from pnl_pct), and exit_reason.
        
        Args:
            symbol: Stock symbol
            entry_date: Original entry date (used to match the trade)
            exit_date: Date when trade was resolved
            exit_price: Price at resolution
            pnl_pct: P&L percentage
            outcome: 'WIN', 'LOSS', or 'TIMEOUT'
            exit_reason: Optional exit reason (hit stop, hit target, etc.)
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            with self.get_session() as session:
                # Find the open trade for this symbol and entry date
                trade = session.query(Trade).filter(
                    Trade.symbol == symbol,
                    Trade.entry_date <= entry_date + timedelta(days=1),
                    Trade.entry_date >= entry_date - timedelta(days=1),
                    Trade.result.is_(None)  # Still open
                ).order_by(Trade.entry_date.desc()).first()
                
                if not trade:
                    return False
                
                # Update with outcome information
                trade.exit_date = exit_date
                trade.exit_price = exit_price
                trade.pnl_pct = pnl_pct
                trade.pnl = (trade.entry_price * pnl_pct / 100.0) if trade.entry_price else 0.0
                
                # Determine result from outcome
                if outcome == "WIN":
                    trade.result = "win"
                elif outcome == "LOSS":
                    trade.result = "loss"
                elif outcome == "TIMEOUT":
                    trade.result = "timeout" if pnl_pct < 0 else "win"
                else:
                    trade.result = "unknown"
                
                trade.exit_reason = exit_reason or ("Hit " + outcome.lower())
                
                # Calculate duration
                if trade.exit_date and trade.entry_date:
                    trade.duration_minutes = int(
                        (trade.exit_date - trade.entry_date).total_seconds() / 60
                    )
                
                session.merge(trade)
            
            return True
        
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(
                "Failed to update trade outcome for %s: %s", symbol, e
            )
            return False
    
    # ==================== SIGNALS ====================
    
    def save_signal(
        self,
        backtest_id: int,
        symbol: str,
        signal_date: datetime,
        signal_type: str,
        strength: int = 50,
        momentum: Optional[float] = None,
        trend: Optional[str] = None,
        volatility: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        indicators: Optional[List[str]] = None,
        source: Optional[str] = None,
        trade_taken: bool = False
    ) -> int:
        """Save trading signal. Returns signal ID."""
        signal = Signal(
            backtest_id=backtest_id,
            symbol=symbol,
            signal_date=signal_date,
            signal_type=signal_type,
            strength=strength,
            momentum=momentum,
            trend=trend,
            volatility=volatility,
            volume_ratio=volume_ratio,
            indicators=indicators,
            source=source,
            trade_taken=trade_taken,
        )
        
        with self.get_session() as session:
            session.add(signal)
            session.flush()
            signal_id = signal.id
        
        return signal_id
    
    def get_signal(self, signal_id: int) -> Optional[Signal]:
        """Get signal by ID."""
        with self.get_session() as session:
            return session.query(Signal).filter(Signal.id == signal_id).first()
    
    def get_signals(
        self,
        backtest_id: int,
        symbol: Optional[str] = None,
        signal_type: Optional[str] = None
    ) -> List[Signal]:
        """Get signals for a backtest."""
        with self.get_session() as session:
            query = session.query(Signal).filter(
                Signal.backtest_id == backtest_id
            )
            if symbol:
                query = query.filter(Signal.symbol == symbol)
            if signal_type:
                query = query.filter(Signal.signal_type == signal_type)
            
            return query.order_by(Signal.signal_date).all()
    
    # ==================== STRATEGY METRICS ====================
    
    def save_strategy_metrics(
        self,
        backtest_id: int,
        symbol: str,
        metrics: Dict[str, Any]
    ) -> int:
        """Save per-symbol strategy metrics. Returns metrics ID."""
        strategy_metric = StrategyMetrics(
            backtest_id=backtest_id,
            symbol=symbol,
            num_trades=metrics.get('num_trades', 0),
            winning_trades=metrics.get('winning_trades', 0),
            losing_trades=metrics.get('losing_trades', 0),
            win_rate=metrics.get('win_rate', 0.0),
            total_return=metrics.get('total_return', 0.0),
            avg_win=metrics.get('avg_win', 0.0),
            avg_loss=metrics.get('avg_loss', 0.0),
            largest_win=metrics.get('largest_win', 0.0),
            largest_loss=metrics.get('largest_loss', 0.0),
            max_drawdown=metrics.get('max_drawdown', 0.0),
            sharpe=metrics.get('sharpe', 0.0),
            sortino=metrics.get('sortino', 0.0),
            signals_generated=metrics.get('signals_generated', 0),
            signals_acted=metrics.get('signals_acted', 0),
            signal_accuracy=metrics.get('signal_accuracy', 0.0),
            recommendation=metrics.get('recommendation', 'hold'),
            confidence=metrics.get('confidence', 0.0),
        )
        
        with self.get_session() as session:
            session.add(strategy_metric)
            session.flush()
            metric_id = strategy_metric.id
        
        return metric_id
    
    def get_strategy_metrics(self, metric_id: int) -> Optional[StrategyMetrics]:
        """Get strategy metrics by ID."""
        with self.get_session() as session:
            return session.query(StrategyMetrics).filter(
                StrategyMetrics.id == metric_id
            ).first()
    
    def get_strategy_metrics_by_symbol(
        self,
        backtest_id: int,
        symbol: str
    ) -> Optional[StrategyMetrics]:
        """Get strategy metrics for a specific symbol in a backtest."""
        with self.get_session() as session:
            return session.query(StrategyMetrics).filter(
                and_(
                    StrategyMetrics.backtest_id == backtest_id,
                    StrategyMetrics.symbol == symbol
                )
            ).first()
    
    # ==================== STATISTICS & REPORTS ====================
    
    def get_summary_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary statistics for the last N days.
        
        Args:
            days: Number of days to include
        
        Returns:
            Dictionary with summary statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            backtests = session.query(BacktestResult).filter(
                BacktestResult.backtest_date >= cutoff
            ).all()
            
            total_backtests = len(backtests)
            total_trades = sum(b.total_trades for b in backtests)
            total_pnl = sum(float(b.total_pnl) for b in backtests if b.total_pnl)
            avg_win_rate = sum(b.win_rate for b in backtests) / total_backtests if backtests else 0
            avg_sharpe = sum(b.sharpe_ratio for b in backtests) / total_backtests if backtests else 0
            
            return {
                'period_days': days,
                'total_backtests': total_backtests,
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'avg_win_rate': avg_win_rate,
                'avg_sharpe_ratio': avg_sharpe,
                'best_trade_day': max(
                    (b.backtest_date for b in backtests if b.total_pnl and b.total_pnl > 0),
                    default=None
                ),
            }
    
    def get_symbol_performance(self, symbol: str, days: int = 90) -> Dict[str, Any]:
        """Get performance statistics for a specific symbol."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            metrics = session.query(StrategyMetrics).join(
                BacktestResult
            ).filter(
                and_(
                    StrategyMetrics.symbol == symbol,
                    BacktestResult.backtest_date >= cutoff
                )
            ).all()
            
            if not metrics:
                return {}
            
            return {
                'symbol': symbol,
                'backtests': len(metrics),
                'total_trades': sum(m.num_trades for m in metrics),
                'avg_win_rate': sum(m.win_rate for m in metrics) / len(metrics),
                'avg_return': sum(m.total_return for m in metrics) / len(metrics),
                'avg_sharpe': sum(m.sharpe for m in metrics) / len(metrics),
                'recommendation': metrics[-1].recommendation if metrics else 'hold',
            }
    
    def cleanup_old_data(self, days: int = 180) -> int:
        """
        Delete backtests older than N days.
        
        Args:
            days: Age threshold in days
        
        Returns:
            Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            deleted = session.query(BacktestResult).filter(
                BacktestResult.backtest_date < cutoff
            ).delete()
            
            return deleted
```

==================================================
FILE: egx_radar/database/models.py
==================================

```python
"""SQLAlchemy ORM models for EGX Radar database."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Numeric, Text, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class BacktestResult(Base):
    """Backtest execution results and performance metrics."""
    
    __tablename__ = 'backtest_results'
    __table_args__ = (
        Index('idx_backtest_date', 'backtest_date'),
        Index('idx_backtest_symbols', 'symbols'),
        Index('idx_backtest_status', 'status'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(String(100), unique=True, nullable=False, index=True)
    backtest_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    symbols = Column(String(1000), nullable=False)  # Comma-separated
    symbol_count = Column(Integer, nullable=False)
    
    # Performance Metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    total_pnl = Column(Numeric(15, 2), default=0)  # Total P&L
    gross_profit = Column(Numeric(15, 2), default=0)
    gross_loss = Column(Numeric(15, 2), default=0)
    profit_factor = Column(Float, default=0.0)
    
    # Risk Metrics
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    calmar_ratio = Column(Float, default=0.0)
    
    # Statistical
    avg_trade_return = Column(Float, default=0.0)
    std_dev_returns = Column(Float, default=0.0)
    expectancy = Column(Float, default=0.0)
    recovery_factor = Column(Float, default=0.0)
    
    # Execution
    execution_time_seconds = Column(Float, nullable=True)
    workers_used = Column(Integer, default=1)
    
    # Status & Details
    status = Column(String(50), default='completed')  # completed, failed, partial
    notes = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True)  # Settings used
    
    trades = relationship('Trade', back_populates='backtest', cascade='all, delete-orphan')
    signals = relationship('Signal', back_populates='backtest', cascade='all, delete-orphan')
    metrics = relationship('StrategyMetrics', back_populates='backtest', cascade='all, delete-orphan')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BacktestResult(id={self.backtest_id}, symbols={self.symbol_count}, trades={self.total_trades})>"


class Trade(Base):
    """Individual trades from backtest execution or live signals."""
    
    __tablename__ = 'trades'
    __table_args__ = (
        Index('idx_trade_backtest', 'backtest_id'),
        Index('idx_trade_symbol', 'symbol'),
        Index('idx_trade_entry_date', 'entry_date'),
        Index('idx_trade_result', 'result'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=True)
    
    symbol = Column(String(20), nullable=False)
    entry_date = Column(DateTime, nullable=False)
    entry_price = Column(Numeric(15, 6), nullable=False)
    entry_signal = Column(String(50), nullable=False)  # buy, sell, short
    
    exit_date = Column(DateTime, nullable=True)
    exit_price = Column(Numeric(15, 6), nullable=True)
    exit_reason = Column(String(100), nullable=True)  # take_profit, stop_loss, signal, timeout
    
    quantity = Column(Integer, nullable=False)
    result = Column(String(20), nullable=True)  # win, loss, breakeven
    pnl = Column(Numeric(15, 2), nullable=True)
    pnl_pct = Column(Float, nullable=True)
    
    max_profit = Column(Numeric(15, 2), nullable=True)  # Highest unrealized profit
    max_loss = Column(Numeric(15, 2), nullable=True)    # Lowest unrealized profit
    
    duration_minutes = Column(Integer, nullable=True)
    
    backtest = relationship('BacktestResult', back_populates='trades')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade(symbol={self.symbol}, entry={self.entry_date.strftime('%Y-%m-%d')}, pnl={self.pnl})>"


class Signal(Base):
    """Trading signals generated during backtest."""
    
    __tablename__ = 'signals'
    __table_args__ = (
        Index('idx_signal_backtest', 'backtest_id'),
        Index('idx_signal_symbol', 'symbol'),
        Index('idx_signal_date', 'signal_date'),
        Index('idx_signal_type', 'signal_type'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=False)
    
    symbol = Column(String(20), nullable=False)
    signal_date = Column(DateTime, nullable=False)
    signal_type = Column(String(50), nullable=False)  # buy, sell, strong_buy, strong_sell
    strength = Column(Integer, default=50)  # 0-100 confidence
    
    # Signal components
    momentum = Column(Float, nullable=True)
    trend = Column(String(20), nullable=True)  # uptrend, downtrend, sideways
    volatility = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    
    # Indicators used
    indicators = Column(JSON, nullable=True)  # List of indicators that contributed
    source = Column(String(100), nullable=True)  # Which module generated signal
    
    # Outcome tracking
    trade_taken = Column(Boolean, default=False)
    trade_successful = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
    
    backtest = relationship('BacktestResult', back_populates='signals')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Signal(symbol={self.symbol}, type={self.signal_type}, strength={self.strength})>"


class StrategyMetrics(Base):
    """Per-symbol strategy performance metrics."""
    
    __tablename__ = 'strategy_metrics'
    __table_args__ = (
        Index('idx_metrics_backtest', 'backtest_id'),
        Index('idx_metrics_symbol', 'symbol'),
        UniqueConstraint('backtest_id', 'symbol', name='uq_backtest_symbol'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=False)
    
    symbol = Column(String(20), nullable=False)
    
    # Trade Statistics
    num_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # Returns
    total_return = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    
    # Risk
    max_drawdown = Column(Float, default=0.0)
    sharpe = Column(Float, default=0.0)
    sortino = Column(Float, default=0.0)
    
    # Signal performance
    signals_generated = Column(Integer, default=0)
    signals_acted = Column(Integer, default=0)
    signal_accuracy = Column(Float, default=0.0)
    
    # Recommendation
    recommendation = Column(String(50), default='hold')  # buy, sell, hold, avoid
    confidence = Column(Float, default=0.0)
    
    backtest = relationship('BacktestResult', back_populates='metrics')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<StrategyMetrics(symbol={self.symbol}, trades={self.num_trades}, win_rate={self.win_rate:.2%})>"


class EquityHistory(Base):
    """Daily equity curve tracking for risk analysis."""
    
    __tablename__ = 'equity_history'
    __table_args__ = (
        Index('idx_equity_backtest', 'backtest_id'),
        Index('idx_equity_date', 'date'),
    )
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtest_results.id'), nullable=False)
    
    date = Column(DateTime, nullable=False)
    starting_equity = Column(Numeric(15, 2), nullable=False)
    ending_equity = Column(Numeric(15, 2), nullable=False)
    daily_pnl = Column(Numeric(15, 2), nullable=False)
    daily_return = Column(Float, nullable=False)
    
    cumulative_return = Column(Float, nullable=False)
    drawdown = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<EquityHistory(date={self.date.strftime('%Y-%m-%d')}, equity={self.ending_equity})>"
```

==================================================
FILE: egx_radar/database/utils.py
=================================

```python
"""Database utilities and initialization functions."""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from egx_radar.database.manager import DatabaseManager
from egx_radar.database.config import DatabaseConfig
from egx_radar.database.models import BacktestResult


def init_database(database_url: str = None) -> DatabaseManager:
    """
    Initialize database with tables.
    
    Args:
        database_url: Connection URL (uses env or default if None)
    
    Returns:
        DatabaseManager instance
    """
    db_url = database_url or DatabaseConfig.get_url()
    manager = DatabaseManager(database_url=db_url)
    manager.init_db()
    return manager


def import_backtest_from_csv(
    manager: DatabaseManager,
    csv_file: str,
    backtest_id: str,
    start_date: datetime,
    end_date: datetime,
    symbols: List[str],
    metrics: Dict[str, Any]
) -> BacktestResult:
    """
    Import backtest results from CSV file.
    
    Args:
        manager: DatabaseManager instance
        csv_file: Path to backtest CSV file
        backtest_id: Unique backtest identifier
        start_date: Backtest start date
        end_date: Backtest end date
        symbols: List of symbols backtested
        metrics: Performance metrics
    
    Returns:
        BacktestResult object
    """
    import pandas as pd
    
    # Read trades from CSV
    trades_df = pd.read_csv(csv_file)
    
    # Save backtest
    backtest = manager.save_backtest(
        backtest_id=backtest_id,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        metrics=metrics,
        parameters={
            'imported_from': csv_file,
            'import_date': datetime.utcnow().isoformat(),
        }
    )
    
    # Save individual trades
    for _, row in trades_df.iterrows():
        manager.save_trade(
            backtest_id=backtest.id,
            symbol=row['Symbol'],
            entry_date=pd.to_datetime(row['Entry Date']),
            entry_price=float(row['Entry Price']),
            entry_signal=row.get('Entry Signal', 'buy'),
            quantity=int(row.get('Quantity', 1)),
            exit_date=pd.to_datetime(row['Exit Date']) if 'Exit Date' in row else None,
            exit_price=float(row['Exit Price']) if 'Exit Price' in row else None,
            exit_reason=row.get('Exit Reason'),
            pnl=float(row['PnL']) if 'PnL' in row else None,
            pnl_pct=float(row['PnL %']) if 'PnL %' in row else None,
        )
    
    return backtest


def export_backtest_to_json(
    manager: DatabaseManager,
    backtest_id: int,
    output_file: str
) -> None:
    """
    Export backtest results to JSON.
    
    Args:
        manager: DatabaseManager instance
        backtest_id: Backtest ID to export
        output_file: Path to output JSON file
    """
    backtest = manager.get_backtest(backtest_id)
    if not backtest:
        raise ValueError(f'Backtest {backtest_id} not found')
    
    trades = manager.get_trades(backtest_id)
    signals = manager.get_signals(backtest_id)
    
    data = {
        'backtest': {
            'id': backtest.id,
            'backtest_id': backtest.backtest_id,
            'date': backtest.backtest_date.isoformat(),
            'start_date': backtest.start_date.isoformat(),
            'end_date': backtest.end_date.isoformat(),
            'symbols': backtest.symbols.split(','),
            'metrics': {
                'total_trades': backtest.total_trades,
                'winning_trades': backtest.winning_trades,
                'losing_trades': backtest.losing_trades,
                'win_rate': backtest.win_rate,
                'total_pnl': float(backtest.total_pnl),
                'profit_factor': backtest.profit_factor,
                'max_drawdown': backtest.max_drawdown,
                'max_drawdown_pct': backtest.max_drawdown_pct,
                'sharpe_ratio': backtest.sharpe_ratio,
                'sortino_ratio': backtest.sortino_ratio,
                'steadiness': backtest.calmar_ratio,
            },
            'execution': {
                'execution_time_seconds': backtest.execution_time_seconds,
                'workers_used': backtest.workers_used,
            },
        },
        'trades': [
            {
                'symbol': t.symbol,
                'entry_date': t.entry_date.isoformat(),
                'entry_price': float(t.entry_price),
                'entry_signal': t.entry_signal,
                'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                'exit_price': float(t.exit_price) if t.exit_price else None,
                'exit_reason': t.exit_reason,
                'quantity': t.quantity,
                'result': t.result,
                'pnl': float(t.pnl) if t.pnl else None,
                'pnl_pct': t.pnl_pct,
                'duration_minutes': t.duration_minutes,
            }
            for t in trades
        ],
        'signals': [
            {
                'symbol': s.symbol,
                'date': s.signal_date.isoformat(),
                'type': s.signal_type,
                'strength': s.strength,
                'trend': s.trend,
                'volatility': s.volatility,
                'trade_taken': s.trade_taken,
            }
            for s in signals
        ],
    }
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def generate_performance_report(
    manager: DatabaseManager,
    days: int = 30,
    output_file: str = None
) -> Dict[str, Any]:
    """
    Generate comprehensive performance report.
    
    Args:
        manager: DatabaseManager instance
        days: Number of days to include
        output_file: Optional file to save report
    
    Returns:
        Report dictionary
    """
    summary = manager.get_summary_stats(days=days)
    
    with manager.get_session() as session:
        backtests = session.query(BacktestResult).limit(100).all()
        top_symbols = {}
        
        for backtest in backtests:
            for symbol in backtest.symbols.split(','):
                if symbol not in top_symbols:
                    top_symbols[symbol] = manager.get_symbol_performance(symbol, days=days)
    
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'period_days': days,
        'summary': summary,
        'top_performers': sorted(
            top_symbols.items(),
            key=lambda x: x[1].get('avg_win_rate', 0),
            reverse=True
        )[:10],
    }
    
    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
    
    return report
```

==================================================
FILE: egx_radar/outcomes/__init__.py
====================================

```python
"""Trade outcomes and logging engine (Layer 9)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.outcomes.engine import (
    oe_load_log,
    oe_save_log,
    oe_load_history,
    oe_save_history_batch,
    _normalise_df_index,
    oe_resolve_trade,
    oe_record_signal,
    oe_process_open_trades,
    oe_save_rejections,
)

__all__ = [
    "oe_load_log",
    "oe_save_log",
    "oe_load_history",
    "oe_save_history_batch",
    "_normalise_df_index",
    "oe_resolve_trade",
    "oe_record_signal",
    "oe_process_open_trades",
    "oe_save_rejections",
]
```

==================================================
FILE: egx_radar/outcomes/engine.py
==================================

```python
"""Trade outcome engine: logging, history, and resolution (Layer 9)."""

import json
import logging
import math
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import pathlib

import pandas as pd

from egx_radar.config.settings import K, SYMBOLS
from egx_radar.state.app_state import STATE
from egx_radar.core.indicators import pct_change_safe
from egx_radar.core.signal_engine import candle_hits_trigger

log = logging.getLogger(__name__)

_LOG_DIR = pathlib.Path(K.OUTCOME_LOG_FILE).parent
_LOG_DIR.mkdir(parents=True, exist_ok=True)
import threading
_io_lock = threading.Lock()

# â”€â”€ Database integration (lazy-loaded) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_DB_ENABLED = False
_db_manager = None


def _get_db_manager():
    """Lazy-load DatabaseManager to avoid circular imports.
    
    This function is called optionally by oe_record_signal() to persist
    trades to the database. If the database is unavailable, the scanner
    continues using JSON logs as the fallback.
    
    Returns:
        DatabaseManager instance if available, None otherwise.
    """
    global _db_manager, _DB_ENABLED
    if _db_manager is not None:
        return _db_manager
    
    try:
        from egx_radar.database.manager import DatabaseManager
        _db_manager = DatabaseManager()
        _db_manager.init_db()
        _DB_ENABLED = True
        return _db_manager
    except Exception as exc:
        log.debug("DatabaseManager unavailable (%s) â€” using JSON only", exc)
        _DB_ENABLED = False
        return None


def _atomic_json_write(filepath: str, data: object) -> None:
    """Write JSON atomically: temp â†’ os.replace()."""
    import tempfile

    dirpath = os.path.dirname(os.path.abspath(filepath)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp", prefix=".egx_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, filepath)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def oe_load_log() -> List[dict]:
    with _io_lock:
        if not os.path.exists(K.OUTCOME_LOG_FILE):
            return []
        try:
            with open(K.OUTCOME_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.warning("oe_load_log: %s", e)
            return []


def oe_save_log(trades: List[dict]) -> None:
    with _io_lock:
        try:
            _atomic_json_write(K.OUTCOME_LOG_FILE, trades)
        except OSError as e:
            log.error("oe_save_log: %s", e)


def _oe_load_history_unsafe() -> List[dict]:
    """Load history WITHOUT acquiring _io_lock (caller must hold it)."""
    if not os.path.exists(K.OUTCOME_HISTORY_FILE):
        return []
    try:
        with open(K.OUTCOME_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("oe_load_history: %s", e)
        return []


def oe_load_history() -> List[dict]:
    with _io_lock:
        return _oe_load_history_unsafe()


def oe_save_history_batch(new_trades: List[dict]) -> None:
    if not new_trades:
        return
    with _io_lock:
        history = _oe_load_history_unsafe()
        history.extend(new_trades)
        try:
            _atomic_json_write(K.OUTCOME_HISTORY_FILE, history)
        except OSError as e:
            log.error("oe_save_history_batch: %s", e)


def _normalise_df_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    try:
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert(None)
    except Exception as e:
        try:
            df.index = pd.to_datetime(df.index).tz_localize(None)
        except Exception as e2:
            log.warning("oe_normalise_df_index failed: %s", e2)
    return df


def oe_resolve_trade(trade: dict, df: Optional[pd.DataFrame]) -> Optional[dict]:
    """Resolve a logged signal using the same next-candle trigger logic as the backtest."""
    if df is None or df.empty:
        return None

    try:
        df = _normalise_df_index(df)
    except Exception as e:
        log.warning("oe_resolve_trade normalise error: %s", e)
        return None

    trade_date_str = trade.get("date", "")
    if not trade_date_str:
        return None

    try:
        signal_dt = pd.Timestamp(trade_date_str[:10])
    except (ValueError, TypeError) as e:
        log.warning("oe_resolve_trade date parse error for %s: %s", trade.get("sym"), e)
        return None

    future_positions = [i for i, d in enumerate(df.index) if d > signal_dt]
    if not future_positions:
        return None

    activation_idx = future_positions[0]
    activation_date = df.index[activation_idx]
    activation_row = df.iloc[activation_idx]
    trigger_price = float(trade.get("trigger_price") or trade.get("entry") or 0.0)
    if trigger_price <= 0:
        return None

    next_open = float(activation_row["Open"])
    next_high = float(activation_row["High"])
    if not candle_hits_trigger(next_high, trigger_price):
        resolved = dict(trade)
        resolved.update({
            "status": "MISSED",
            "entry_date": activation_date.strftime("%Y-%m-%d"),
            "trigger_price": round(trigger_price, 3),
            "next_open": round(next_open, 3),
            "next_high": round(next_high, 3),
            "days_held": 0,
            "mfe_pct": 0.0,
            "mae_pct": 0.0,
            "pnl_pct": 0.0,
            "result_pct": 0.0,
            "stop_hit": False,
            "resolved_date": datetime.now().strftime("%Y-%m-%d"),
            "fill_mode": "next_candle_touch",
        })
        return resolved

    entry = round(trigger_price * (1.0 + K.BT_SLIPPAGE_PCT / 2.0), 3)
    stop = float(trade.get("stop") or (entry * (1.0 - K.MAX_STOP_LOSS_PCT)))
    stop = min(stop, entry * 0.995)
    if stop >= entry:
        stop = entry * (1.0 - K.MAX_STOP_LOSS_PCT)
    target = float(trade.get("target") or (entry * (1.0 + K.POSITION_MAIN_TP_PCT)))
    partial_target = float(trade.get("partial_target") or (entry * (1.0 + K.PARTIAL_TP_PCT)))
    trailing_trigger = float(trade.get("trailing_trigger") or (entry * (1.0 + K.TRAILING_TRIGGER_PCT)))
    trailing_stop_pct = float(trade.get("trailing_stop_pct") or K.TRAILING_STOP_PCT)

    window = df.iloc[activation_idx:activation_idx + K.OUTCOME_LOOKFORWARD_DAYS + 1]
    if len(window) < K.OUTCOME_MIN_BARS_NEEDED:
        return None

    outcome = None
    exit_price = None
    bars_held = 0
    mfe = 0.0
    mae = 0.0
    partial_taken = False
    partial_exit_price = None
    trailing_active = False
    trailing_anchor = entry

    for ts, row in window.iterrows():
        open_px = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        bars_held += 1

        mfe = max(mfe, pct_change_safe(high, entry))
        mae = max(mae, -pct_change_safe(low, entry))

        if open_px <= stop:
            exit_price = round(open_px * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "LOSS"
        elif low <= stop:
            exit_price = round(stop * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "LOSS"
        else:
            if (not partial_taken) and high >= partial_target:
                partial_taken = True
                partial_exit_price = round(partial_target * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
                stop = max(stop, entry)

            if high >= trailing_trigger:
                trailing_active = True
                trailing_anchor = max(trailing_anchor, high)

            if trailing_active:
                stop = max(stop, trailing_anchor * (1.0 - trailing_stop_pct))

            if high >= target:
                exit_price = round(target * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
                outcome = "WIN"
            elif bars_held >= K.OUTCOME_LOOKFORWARD_DAYS:
                exit_price = round(close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
                outcome = "TIMEOUT"

        if outcome is not None:
            exit_date = ts
            break

    if outcome is None:
        age = (datetime.now() - datetime.strptime(trade_date_str[:10], "%Y-%m-%d")).days
        if age <= K.OUTCOME_LOOKFORWARD_DAYS * K.OUTCOME_STALE_MULTIPLIER:
            return None
        exit_date = window.index[-1]
        exit_price = round(float(window.iloc[-1]["Close"]) * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
        outcome = "TIMEOUT"

    partial_return_pct = 0.0
    if partial_taken and partial_exit_price:
        partial_return_pct = 0.5 * ((partial_exit_price - entry) / max(entry, 1e-9) * 100.0)
    remaining_fraction = 0.5 if partial_taken else 1.0
    remaining_return_pct = remaining_fraction * ((exit_price - entry) / max(entry, 1e-9) * 100.0)
    gross_return_pct = partial_return_pct + remaining_return_pct
    pnl_pct = gross_return_pct - (K.BT_FEES_PCT * 100.0)

    resolved = dict(trade)
    resolved.update({
        "status": outcome,
        "entry": entry,
        "entry_date": activation_date.strftime("%Y-%m-%d"),
        "trigger_price": round(trigger_price, 3),
        "exit_price": round(float(exit_price), 3),
        "days_held": bars_held,
        "mfe_pct": round(mfe, 2),
        "mae_pct": round(mae, 2),
        "pnl_pct": round(pnl_pct, 2),
        "result_pct": round(pnl_pct, 2),
        "stop_hit": outcome == "LOSS",
        "resolved_date": datetime.now().strftime("%Y-%m-%d"),
        "fill_mode": "next_candle_touch",
        "partial_taken": partial_taken,
        "trade_type": trade.get("trade_type", "UNCLASSIFIED"),
        "score": round(float(trade.get("score", trade.get("smart_rank", 0.0))), 2),
        "risk_used": round(float(trade.get("risk_used") or 0.0), 4),
    })

    # Feed breakout result back to MomentumGuard for fatigue tracking
    setup = trade.get("setup_type", "")
    if "breakout" in setup.lower() or trade.get("action", "").lower() in ("buy", "ultra"):
        followed_through = outcome == "WIN"
        try:
            entry_date = date.fromisoformat(trade.get("date", "")[:10])
            if hasattr(STATE, "momentum_guard") and STATE.momentum_guard:
                STATE.momentum_guard.record_breakout_result(
                    symbol=trade.get("sym", ""),
                    followed_through=followed_through,
                    trade_date=entry_date,
                )
        except Exception as e:
            log.warning("[engine] breakout feedback failed: %s", e)

    return resolved


def oe_record_signal(
    sym: str, sector: str, entry: float, stop: float, target: float,
    atr: float, smart_rank: float, anticipation: float, action: str,
    existing_trades: Optional[List[dict]] = None,
    tag: str = "",
    trade_type: str = "UNCLASSIFIED",
    score: float = 0.0,
    risk_used: float = 0.0,
    trigger_price: Optional[float] = None,
    partial_target: Optional[float] = None,
    trailing_trigger: Optional[float] = None,
    trailing_stop_pct: Optional[float] = None,
) -> None:
    today_str = datetime.now().strftime("%Y-%m-%d")
    trades    = existing_trades if existing_trades is not None else oe_load_log()
    for t in trades:
        if t.get("sym") == sym and t.get("date", "")[:10] == today_str:
            return
    trades.append({
        "sym": sym, "sector": sector, "date": today_str,
        "entry": round(entry, 3), "stop": round(stop, 3), "target": round(target, 3),
        "atr": round(atr, 3) if (atr is not None and math.isfinite(atr)) else 0.0,
        "smart_rank": round(smart_rank, 2) if (smart_rank is not None and math.isfinite(smart_rank)) else 0.0,
        "anticipation": round(anticipation, 2) if (anticipation is not None and math.isfinite(anticipation)) else 0.0,
        "action": action, "status": "PENDING_TRIGGER",
        # Fields for alpha_monitor (populated here or at resolution)
        "setup_type": tag or action,  # signal tag (ultra/early/buy/watch)
        "exit_price": None,           # set by oe_resolve_trade()
        "result_pct": None,           # set by oe_resolve_trade()
        "stop_hit": None,             # set by oe_resolve_trade() â†’ True if status=="LOSS"
        "trade_type": trade_type,
        "score": round(score, 2) if (score is not None and math.isfinite(score)) else 0.0,
        "risk_used": round(risk_used, 4) if (risk_used is not None and math.isfinite(risk_used)) else 0.0,
        "trigger_price": round(trigger_price if trigger_price is not None else entry, 3),
        "partial_target": round(partial_target, 3) if partial_target else None,
        "trailing_trigger": round(trailing_trigger, 3) if trailing_trigger else None,
        "trailing_stop_pct": round(trailing_stop_pct, 4) if trailing_stop_pct else K.TRAILING_STOP_PCT,
        "fill_mode": "next_candle_touch",
    })
    oe_save_log(trades)
    
    # â”€â”€ Database write (additive â€” JSON log remains primary) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        db = _get_db_manager()
        if db is not None:
            db.save_trade_signal({
                "sym":          sym,
                "sector":       sector,
                "entry":        entry,
                "stop":         stop,
                "target":       target,
                "atr":          atr if atr is not None else 0.0,
                "smart_rank":   smart_rank if smart_rank and math.isfinite(smart_rank) else 0.0,
                "anticipation": anticipation if anticipation is not None else 0.0,
                "action":       action,
                "recorded_at":  datetime.utcnow().isoformat(),
            })
    except Exception as _db_exc:
        log.debug("DB trade write failed (non-critical): %s", _db_exc)
        # Never let a DB failure break the scanner â€” JSON remains the source of truth


def oe_process_open_trades(all_data: Dict[str, pd.DataFrame]) -> Tuple[List[dict], int, int]:
    """Resolve open trades. Returns (remaining, wins, losses)."""
    trades = oe_load_log()
    if not trades:
        return [], 0, 0

    remaining: List[dict] = []
    batch:     List[dict] = []
    wins = losses = 0

    for trade in trades:
        sym   = trade.get("sym", "")
        yahoo = SYMBOLS.get(sym)
        df    = all_data.get(yahoo) if yahoo else None
        resolved = oe_resolve_trade(trade, df)
        if resolved is None:
            remaining.append(trade)
            continue
        batch.append(resolved)
        outcome = resolved["status"]
        rank    = trade.get("smart_rank", 0.0)
        ant     = trade.get("anticipation", 0.0)
        sec     = trade.get("sector", "")
        t_tag   = trade.get("action", "").lower()   # FIX-5: pass sector+tag
        if outcome == "WIN":
            wins += 1
            STATE.record_win(rank, ant, sector=sec, tag=t_tag)
        elif outcome == "LOSS":
            losses += 1
            STATE.record_loss(rank, ant, sector=sec, tag=t_tag)
        elif outcome == "TIMEOUT":
            # Neutral outcome: did not win or lose â€” record as a partial loss
            # with reduced weight (0.5) so it slightly dampens WinRate
            # without fully penalizing the signal
            timeout_pnl = resolved.get("pnl_pct", 0.0)
            if timeout_pnl >= 0:
                # Timed out with small gain or flat â†’ treat as weak win
                STATE.record_win(rank * 0.5, ant, sector=sec, tag=t_tag)
            else:
                # Timed out in the red â†’ treat as weak loss
                STATE.record_loss(rank * 0.5, ant, sector=sec, tag=t_tag)

    oe_save_history_batch(batch)
    oe_save_log(remaining)
    
    # â”€â”€ Database write for resolved outcomes (new) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Update each resolved trade in the database with exit/outcome information
    try:
        db = _get_db_manager()
        if db is not None and batch:
            for resolved_trade in batch:
                try:
                    entry_date_str = resolved_trade.get("date", "")
                    if entry_date_str:
                        entry_dt = datetime.strptime(entry_date_str[:10], "%Y-%m-%d")
                        db.update_trade_outcome(
                            symbol=resolved_trade.get("sym", ""),
                            entry_date=entry_dt,
                            exit_date=datetime.strptime(
                                resolved_trade.get("resolved_date", ""), "%Y-%m-%d"
                            ) if resolved_trade.get("resolved_date") else datetime.utcnow(),
                            exit_price=resolved_trade.get("exit_price", 0.0),
                            pnl_pct=resolved_trade.get("pnl_pct", 0.0),
                            outcome=resolved_trade.get("status", "TIMEOUT"),
                            exit_reason="Hit " + resolved_trade.get("status", "").lower(),
                        )
                except Exception as trade_exc:
                    log.debug("DB outcome update failed for %s: %s", 
                              resolved_trade.get("sym"), trade_exc)
    except Exception as db_exc:
        log.debug("DB outcome batch update skipped: %s", db_exc)
        # Never let DB failure break the outcome resolution â€” JSON is source of truth
    
    return remaining, wins, losses


def oe_save_rejections(rejections: List[Dict[str, str]]) -> None:
    """Save a list of rejected symbols and reasons to a CSV file."""
    if not rejections:
        return
        
    filepath = _LOG_DIR / "rejected_symbols.csv"
    try:
        df = pd.DataFrame(rejections)
        df["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Append if exists and today, else overwrite
        mode = 'a' if os.path.exists(filepath) else 'w'
        header = not os.path.exists(filepath)
        df.to_csv(filepath, mode=mode, header=header, index=False, encoding="utf-8")
    except Exception as e:
        log.error("Failed to save rejections: %s", e)


def oe_save_daily_scan(results: list, scan_date: str = None) -> str:
    """Save full scan results as a dated CSV snapshot.
    
    Saves to: egx_radar/history/YYYY-MM-DD_scan.csv
    Returns the filepath string.
    """
    if not results:
        return ""

    if scan_date is None:
        scan_date = datetime.now().strftime("%Y-%m-%d")

    history_dir = _LOG_DIR / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    filepath = history_dir / f"{scan_date}_scan.csv"

    # Build flat rows â€” only the columns useful for review
    rows = []
    for r in results:
        plan = r.get("plan", {})
        rows.append({
            "date":        scan_date,
            "symbol":      r.get("sym", ""),
            "sector":      r.get("sector", ""),
            "price":       r.get("price", 0.0),
            "action":      plan.get("action", "WAIT"),
            "trade_type":  plan.get("trade_type", "SKIP"),
            "score":       round(plan.get("score", r.get("smart_rank", 0.0)), 2),
            "risk_used":   round(plan.get("risk_used", 0.0), 4),
            "signal":      r.get("signal", ""),
            "smart_rank":  round(r.get("smart_rank", 0.0), 2),
            "confidence":  round(r.get("confidence", 0.0), 1),
            "zone":        r.get("zone", ""),
            "rsi":         round(r.get("rsi", 0.0), 1),
            "adx":         round(r.get("adx", 0.0), 1),
            "entry":       round(plan.get("entry", 0.0), 2),
            "trigger_price": round(plan.get("trigger_price", r.get("trigger_price", 0.0)), 2),
            "stop":        round(plan.get("stop", 0.0), 2),
            "target":      round(plan.get("target", 0.0), 2),
            "rr":          plan.get("rr", 0.0),
            "atr":         round(r.get("atr", 0.0), 3) if r.get("atr") else "",
            "vol_ratio":   round(r.get("vol_ratio", 0.0), 2),
            "pct_ema200":  round(r.get("pct_ema200", 0.0), 1),
            "adapt_mom":   round(r.get("adaptive_mom", 0.0), 2),
            "dg_tier":     r.get("dg_tier", ""),
            "signal_reason": r.get("signal_reason", ""),
            # Paper trading columns â€” filled manually later
            "price_1w":    "",   # price after 1 week
            "price_2w":    "",   # price after 2 weeks
            "result":      "",   # WIN / LOSS / HOLD
            "notes":       "",
        })

    df = pd.DataFrame(rows)

    # Don't overwrite existing file â€” append a suffix if needed
    if filepath.exists():
        ts = datetime.now().strftime("%H-%M")
        filepath = history_dir / f"{scan_date}_{ts}_scan.csv"

    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    log.info("Daily scan saved â†’ %s (%d symbols)", filepath.name, len(rows))
    return str(filepath)


def oe_weekly_report() -> str:
    """Scan the history folder and produce a summary of PROBE signals
    from the past 7 days, comparing entry price to latest close.
    
    Returns a formatted text report string.
    """
    from datetime import timedelta

    history_dir = _LOG_DIR / "history"
    if not history_dir.exists():
        return "No scan history found. Run at least one scan first."

    cutoff = datetime.now() - timedelta(days=7)
    all_rows = []

    for csv_file in sorted(history_dir.glob("*_scan.csv")):
        try:
            file_date_str = csv_file.name[:10]
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
            if file_date < cutoff:
                continue
            df = pd.read_csv(csv_file, encoding="utf-8-sig")
            # Only PROBE signals are worth tracking
            probe_rows = df[df["action"] == "PROBE"].copy()
            if not probe_rows.empty:
                probe_rows["scan_date"] = file_date_str
                all_rows.append(probe_rows)
        except Exception:
            continue

    if not all_rows:
        return "No PROBE signals found in the past 7 days."

    combined = pd.concat(all_rows, ignore_index=True)

    lines = ["=" * 50]
    lines.append(f"EGX Radar â€” Weekly PROBE Signal Report")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Signals tracked: {len(combined)}")
    lines.append("=" * 50)
    lines.append("")

    for _, row in combined.iterrows():
        result = row.get("result", "")
        price_1w = row.get("price_1w", "")
        
        if result:
            status = f"â†’ {result}"
        elif price_1w:
            try:
                p1w = float(price_1w)
                entry = float(row["entry"])
                pct = (p1w - entry) / (entry + 1e-9) * 100
                status = f"â†’ {p1w:.2f} ({pct:+.1f}%)"
            except (ValueError, TypeError):
                status = "â†’ pending"
        else:
            status = "â†’ pending review"

        lines.append(
            f"[{row['scan_date']}] {row['symbol']:6s} | "
            f"Entry={row['entry']:.2f} Stop={row['stop']:.2f} Target={row['target']:.2f} "
            f"R:R={row['rr']:.1f}x | {status}"
        )

    lines.append("")
    lines.append("=" * 50)
    lines.append("HOW TO UPDATE: Open the CSV in history/ folder,")
    lines.append("fill in 'price_1w' column with actual price after 1 week.")
    lines.append("=" * 50)

    return "\n".join(lines)


__all__ = [
    "oe_load_log",
    "oe_save_log",
    "oe_load_history",
    "oe_save_history_batch",
    "_normalise_df_index",
    "oe_resolve_trade",
    "oe_record_signal",
    "oe_process_open_trades",
    "oe_save_rejections",
    "oe_save_daily_scan",
    "oe_weekly_report",
]
```

==================================================
FILE: egx_radar/scan/__init__.py
================================

```python
"""Scan core: orchestrates data, scoring, portfolio and UI updates (Layer 9/scan)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.scan.runner import (
    build_capital_flow_map,
    _scan_lock,
    run_scan,
    start_scan,
)

__all__ = [
    "build_capital_flow_map",
    "_scan_lock",
    "run_scan",
    "start_scan",
]
```

==================================================
FILE: egx_radar/scan/runner.py
==============================

```python
"""Scan core: orchestrates all layers into one scan pass."""

import logging
import math
import sys
import threading
import time
from datetime import datetime
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pandas_ta as pta

from egx_radar.config.settings import (
    K,
    SECTORS,
    SYMBOLS,
    DECISION_PRIORITY,
    get_account_size,
    get_sector,
)
from egx_radar.core.indicators import (
    safe_clamp,
    last_val,
    compute_atr,
    compute_atr_risk,
    compute_vwap_dist,
    compute_vol_zscore,
    detect_ema_cross,
    detect_vol_divergence,
    compute_ud_ratio,
    detect_vcp,
    compute_cmf,
    is_atr_shrinking,
    compute_liquidity_shock,
)
from egx_radar.core.scoring import (
    _norm,
    score_capital_pressure,
    score_institutional_entry,
    score_whale_footprint,
    score_flow_anticipation,
    score_quantum,
    score_gravity,
    smart_rank_score,
)
from egx_radar.core.signals import (
    detect_market_regime,
    detect_phase,
    detect_predictive_zone,
    build_signal,
    build_signal_reason,
    get_signal_direction,
)
from egx_radar.core.risk import build_trade_plan, institutional_confidence
from egx_radar.core.portfolio import compute_portfolio_guard
from egx_radar.core.signal_engine import (
    apply_regime_gate,
    detect_conservative_market_regime,
    evaluate_symbol_snapshot,
)
from egx_radar.core.data_guard import DataGuard
from egx_radar.core.momentum_guard import MomentumGuard
from egx_radar.core.alpha_monitor import AlphaMonitor, AlphaStatus
from egx_radar.core.position_manager import PositionManager, AddOnResult
from egx_radar.state.app_state import STATE

_data_guard = DataGuard()
_momentum_guard = MomentumGuard()
STATE.momentum_guard = _momentum_guard
_alpha_monitor = AlphaMonitor()
_position_manager = PositionManager()
STATE.position_manager = _position_manager
from egx_radar.data.merge import download_all, _source_labels, _source_labels_lock
from egx_radar.outcomes.engine import (
    oe_load_log,
    oe_process_open_trades,
    oe_record_signal,
    oe_save_rejections,
    oe_save_daily_scan,
)
from egx_radar.ui.components import (
    _enqueue,
    _pulse,
    draw_gauge,
    _update_heatmap,
    _update_rotation_map,
    _update_flow_map,
    _update_guard_bar,
    _update_regime_label,
    _update_brain_label,
)

log = logging.getLogger(__name__)


def build_capital_flow_map(results: List[dict], sector_strength: Dict[str, float]) -> Tuple[Dict[str, float], str]:
    sec_cpi  = {k: [] for k in SECTORS}
    sec_rank = {k: [] for k in SECTORS}
    for r in results:
        s = r["sector"]
        if s in sec_cpi:
            sec_cpi[s].append(r["cpi"])
            sec_rank[s].append(r["smart_rank"])

    flow_scores: Dict[str, float] = {}
    for sec in SECTORS:
        if not sec_cpi[sec]:
            flow_scores[sec] = 0.0
            continue
        avg_cpi  = sum(sec_cpi[sec])  / len(sec_cpi[sec])
        avg_rank = sum(sec_rank[sec]) / len(sec_rank[sec])
        prev_avg = STATE.get_sector_flow_avg(sec)
        delta    = avg_cpi - prev_avg
        flow_scores[sec] = delta + avg_rank * 0.05
        STATE.update_sector_flow(sec, avg_cpi)

    leader = max(flow_scores, key=flow_scores.get)
    return flow_scores, leader


_scan_lock = threading.Lock()
_INDICATOR_CACHE: Dict[str, dict] = {}
_INDICATOR_CACHE_LOCK = threading.Lock()

_shutdown_requested = False


def request_shutdown():
    global _shutdown_requested
    _shutdown_requested = True


def run_scan(widgets: dict) -> None:
    """
    FIX-H: All UI updates go through _enqueue() â†’ _pump() on the main thread.
    Worker thread never touches Tkinter directly.
    """
    if _shutdown_requested or sys.is_finalizing():
        return
    if not _scan_lock.acquire(blocking=False):
        return
    scan_start = time.time()

    tree       = widgets["tree"]
    pbar       = widgets["pbar"]
    status_var = widgets["status_var"]
    g_rank     = widgets["gauge_rank"]
    g_flow     = widgets["gauge_flow"]
    heat_lbl   = widgets["heat_labels"]
    rot_lbl    = widgets["rot_labels"]
    flow_lbl   = widgets["flow_labels"]
    regime_lbl = widgets["regime_lbl"]
    brain_lbl  = widgets["brain_lbl"]
    verdict_var= widgets["verdict_var"]
    verdict_frm= widgets["verdict_frm"]
    verdict_w  = widgets["verdict_lbl_w"]
    scan_btn   = widgets["scan_btn"]
    guard_slbl = widgets["guard_sector_labels"]
    guard_elbl = widgets["guard_exposure_lbl"]
    guard_blbl = widgets["guard_blocked_lbl"]

    try:
        force_refresh_var = widgets.get("force_refresh_var")
        is_force = force_refresh_var.get() if force_refresh_var else False
        
        current_time = time.time()
        if is_force:
            _INDICATOR_CACHE.clear()
            if force_refresh_var:
                _enqueue(lambda: force_refresh_var.set(False))

        all_cached = False
        if _INDICATOR_CACHE:
            all_cached = True
            for sym in SYMBOLS.keys():
                c = _INDICATOR_CACHE.get(sym)
                if not c or (current_time - c.get("timestamp", 0)) > K.CACHE_TTL_SECONDS:
                    all_cached = False
                    break

        _enqueue(_pulse.stop)
        _enqueue(lambda: tree.delete(*tree.get_children()))
        _enqueue(lambda: pbar.configure(value=0))

        if all_cached:
            _enqueue(status_var.set, "âš¡ Using cached indicator DataFrames (loaded instantly)â€¦")
            all_data = {}
        else:
            _enqueue(status_var.set, "â³ Loading data from multiple sourcesâ€¦")
            all_data = download_all()
            if not all_data:
                _enqueue(status_var.set, "âŒ Download failed â€” no data from any source.")
                return
            _enqueue(status_var.set, f"âœ… {len(all_data)} symbols loaded â€” computing signalsâ€¦")

        oe_open, oe_wins, oe_losses = oe_process_open_trades(all_data)
        if oe_wins or oe_losses:
            _enqueue(status_var.set, f"ðŸ“Š Outcomes: {oe_wins}W/{oe_losses}L resolvedâ€¦")

        current_open_trades = oe_load_log()
        results:  List[dict] = []
        sec_quant: Dict[str, List[float]] = {k: [] for k in SECTORS}
        _sec_quant_lock = threading.Lock()
        ema200_slopes: Dict[str, float]   = {}
        _ema200_slopes_lock = threading.Lock()
        whale_global = False
        rejections: List[Dict[str, str]]  = []
        
        # â”€â”€ Market Breadth Health (internal â€” no external symbol dependency) â”€â”€â”€â”€
        # Strategy: count how many scanned symbols have price > EMA50.
        # If >50% of stocks are above their EMA50, market is healthy.
        # This is computed from raw all_data BEFORE the parallel scan so
        # _process_symbol can use market_healthy to gate breakout signals.
        if all_cached and "_MARKET_HEALTHY" in _INDICATOR_CACHE:
            market_healthy = _INDICATOR_CACHE["_MARKET_HEALTHY"]
        elif not all_data:
            # Cache-only path: no raw data downloaded â€” keep previous value
            market_healthy = _INDICATOR_CACHE.get("_MARKET_HEALTHY", True)
        else:
            above_ema50 = 0
            total_checked = 0
            for yahoo_sym, df_raw in all_data.items():
                if df_raw is None or df_raw.empty:
                    continue
                close = df_raw["Close"].dropna() if "Close" in df_raw.columns else None
                if close is None or len(close) < 52:
                    continue
                try:
                    ema50_val = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
                    price_val = float(close.iloc[-1])
                    total_checked += 1
                    if price_val > ema50_val:
                        above_ema50 += 1
                except (IndexError, ValueError, TypeError) as e:
                    log.warning("Error calculating EMA50 for %s: %s", yahoo_sym, e)
                    continue

            if total_checked == 0:
                market_healthy = True   # no data to decide â€” allow all
                log.warning("Market breadth: 0 symbols had sufficient bars â€” defaulting healthy=True.")
            else:
                breadth_ratio = above_ema50 / total_checked
                market_healthy = breadth_ratio > K.MARKET_BREADTH_THRESHOLD
                log.warning(
                    "Market breadth: %d/%d symbols above EMA50 (%.0f%%) â†’ healthy=%s",
                    above_ema50, total_checked, breadth_ratio * 100, market_healthy,
                )

            _INDICATOR_CACHE["_MARKET_HEALTHY"] = market_healthy

        total = len(SYMBOLS)
        
        _reject_lock = threading.Lock()

        def _process_symbol(sym: str, yahoo: str):
            current_time = time.time()
            with _INDICATOR_CACHE_LOCK:
                c_data = _INDICATOR_CACHE.get(sym)
                if c_data and (current_time - c_data.get("timestamp", 0)) <= 3600:
                    res_copy = c_data["res_dict"].copy()
                    # FIX-5.4: Deep copy nested dicts so cache isn't corrupted
                    if "plan" in res_copy and res_copy["plan"] is not None:
                        res_copy["plan"] = dict(res_copy["plan"])
                    return res_copy, c_data["slope"], c_data["quantum_n"]

            if yahoo not in all_data:
                with _reject_lock: rejections.append({"sym": sym, "reason": "No data downloaded"})
                return None
            df = all_data[yahoo].copy()

            required = {"Close", "High", "Low", "Open"}
            if not required.issubset(set(df.columns)):
                with _reject_lock: rejections.append({"sym": sym, "reason": "Missing OHLC columns"})
                return None
            if "Volume" not in df.columns:
                df["Volume"] = 0.0

            # Safety net: squeeze any OHLCV column that is a DataFrame into a 1-D Series.
            # This can happen when yfinance returns a MultiIndex that was not fully flattened.
            for col in ["Close", "High", "Low", "Open", "Volume"]:
                if col in df.columns and isinstance(df[col], pd.DataFrame):
                    df[col] = df[col].iloc[:, 0]

            close = df["Close"].dropna()
            if len(close) < K.MIN_BARS:
                with _reject_lock: rejections.append({"sym": sym, "reason": f"Insufficient bars (<{K.MIN_BARS})"})
                return None
            price = float(close.iloc[-1])
            if price < K.PRICE_FLOOR:
                with _reject_lock: rejections.append({"sym": sym, "reason": f"Price below floor (<{K.PRICE_FLOOR})"})
                return None

            df_ta = df.tail(250).copy()

            last10 = df_ta["Close"].iloc[-10:]
            if len(last10) >= 10 and last10.nunique() <= 1 and df_ta["Volume"].iloc[-5:].sum() == 0:
                log.warning("Stale/frozen OHLC detected for %s â€” skipping", sym)
                with _reject_lock: rejections.append({"sym": sym, "reason": "Stale/frozen OHLC detected"})
                return None

            # â”€â”€ Data Guard (Module 1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            dg_result = _data_guard.evaluate(df_ta, sym)
            if not dg_result.passed:
                log.warning("DataGuard REJECTED %s (conf=%.1f): %s", sym, dg_result.confidence, dg_result.reason)
                with _reject_lock: rejections.append({"sym": sym, "reason": f"DataGuard: {dg_result.reason}"})
                return None
            dg_confidence = dg_result.confidence
            dg_tier       = dg_result.confidence_tier   # "FULL" or "DEGRADED"

            result = evaluate_symbol_snapshot(
                df_ta=df_ta,
                sym=sym,
                sector=get_sector(sym),
                regime="BULL",
            )
            if result is None:
                with _reject_lock:
                    rejections.append({"sym": sym, "reason": "Failed conservative EGX filters"})
                return None

            mom_series = close.pct_change(5).rolling(3).mean()
            raw_mom_prev = mom_series.iloc[-2] if len(mom_series) >= 2 else float("nan")
            momentum_prev = float(raw_mom_prev) * 100 if pd.notna(raw_mom_prev) else 0.0

            mg_result = _momentum_guard.evaluate(
                symbol=sym,
                momentum_today=result["momentum"],
                momentum_yesterday=momentum_prev,
                adx=result["adx"],
                vol_ratio=result["vol_ratio"],
                df=df_ta,
                price=result["price"],
            )

            result["mom_arrow"] = STATE.momentum_arrow(sym, result["momentum"])
            result["dg_confidence"] = dg_confidence
            result["dg_tier"] = dg_tier
            result["mg_passed"] = mg_result.passed
            result["mg_position_scale"] = mg_result.position_scale
            result["mg_rank_boost"] = mg_result.effective_rank_threshold_boost
            result["mg_defensive"] = mg_result.defensive_mode
            result["mg_fatigue"] = mg_result.fatigue_mode
            result["mg_exemption_threshold"] = mg_result.exemption_threshold
            result["mg_flags"] = mg_result.flags
            result["mg_message"] = mg_result.message
            result["alpha_warning_level"] = _alpha_status.warning_level
            result["size_multiplier"] = mg_result.position_scale * _alpha_status.position_scale
            result["combined_position_scale"] = mg_result.position_scale * _alpha_status.position_scale
            result["combined_rank_boost"] = mg_result.effective_rank_threshold_boost + _alpha_status.rank_threshold_boost
            result["signal_display"] = result["signal"]
            result["signal_dir"] = get_signal_direction(result["tag"])

            slope = float(result.get("ema200_slope_pct", 0.0)) / 100.0
            return result, slope, float(result.get("quantum", 0.0))
        completed_count = 0

        _alpha_status = _alpha_monitor.evaluate()
        if _alpha_status.warning_level >= 1:
            log.warning("[AlphaMonitor] Level %d - %s", _alpha_status.warning_level, _alpha_status.message)
        if _alpha_status.pause_new_entries:
            log.warning("[AlphaMonitor] Level 3 - new entries paused this session. %s", _alpha_status.message)

        try:
            with ThreadPoolExecutor(max_workers=K.SCAN_MAX_WORKERS) as executor:
                future_to_sym = {executor.submit(_process_symbol, k, v): k for k, v in SYMBOLS.items()}
                for future in as_completed(future_to_sym):
                    sym = future_to_sym[future]
                    completed_count += 1
                    if completed_count % 4 == 0:
                        _enqueue(pbar.configure, value=int(completed_count / max(1, total) * 100))
                    try:
                        res = future.result()
                        if res is not None:
                            res_dict, slope, quantum_n = res
                            results.append(res_dict)
                            if slope != 0.0:
                                with _ema200_slopes_lock:
                                    ema200_slopes[res_dict["sym"]] = slope
                            with _sec_quant_lock:
                                sec_quant[res_dict["sector"]].append(quantum_n)
                            if res_dict.get("whale"):
                                whale_global = True
                    except Exception as exc:
                        log.error("Error processing %s: %s", sym, exc)
        except (RuntimeError, KeyboardInterrupt) as exc:
            log.warning("Scan interrupted during executor phase: %s", exc)
            return results if results else []

        if not results:
            _enqueue(
                status_var.set,
                f"No symbols passed conservative EGX filters - {len(all_data)} loaded. "
                f"Check turnover ({K.MIN_TURNOVER_EGP:,.0f} EGP), spread ({K.MAX_SPREAD_PCT:.1f}%), "
                f"price floor ({K.PRICE_FLOOR} EGP), or min bars ({K.MIN_BARS}).",
            )
            return

        sector_strength = {sec: (sum(v) / len(v) if v else 0.0) for sec, v in sec_quant.items()}
        _enqueue(_update_heatmap, heat_lbl, sector_strength)

        regime = detect_conservative_market_regime(results)
        _enqueue(_update_regime_label, regime_lbl, regime)

        rotation_scores = {}
        for sec in SECTORS:
            vals = [r["anticipation"] for r in results if r["sector"] == sec]
            avg = sum(vals) / len(vals) if vals else 0.0
            STATE.update_sector_rotation(sec, avg)
            rotation_scores[sec] = avg
        future_sector = max(rotation_scores, key=rotation_scores.get) if rotation_scores else "-"
        _enqueue(_update_rotation_map, rot_lbl, rotation_scores, future_sector)

        flow_map, flow_leader = build_capital_flow_map(results, sector_strength)
        _enqueue(_update_flow_map, flow_lbl, flow_map, flow_leader)

        buy_count = sum(1 for r in results if (r.get("plan") or {}).get("action") in ("ACCUMULATE", "PROBE"))
        if regime != "BULL" or not market_healthy:
            brain_mode = "defensive"
        elif buy_count >= 3:
            brain_mode = "aggressive"
        else:
            brain_mode = "neutral"
        brain_vol_req = 1.0
        STATE.set_brain(brain_mode)
        _enqueue(_update_brain_label, brain_lbl, brain_mode)

        try:
            STATE.update_neural_weights(results)
            nw = STATE.get_neural_weights()
        except Exception:
            nw = {"flow": 1.0, "structure": 1.0, "timing": 1.0}

        def _set_wait(r: dict, reason: str) -> None:
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

        def _downgrade_to_probe(r: dict, reason: str) -> None:
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

        weak_sectors = [s for s, _ in sorted(sector_strength.items(), key=lambda x: x[1])[:2] if sector_strength.get(s, 0.0) > 0.0]
        sector_rank_map = {sec: (val * 100.0) for sec, val in sector_strength.items()}

        for r in results:
            r["leader"] = r["smart_rank"] >= sector_rank_map.get(r["sector"], 0.0) + 8.0

            if r["smart_rank"] < K.SMARTRANK_MIN_ACTIONABLE:
                _set_wait(r, f"rank-below-{K.SMARTRANK_MIN_ACTIONABLE:.0f}")

            if regime != "BULL":
                r.update(apply_regime_gate(r, regime))
            elif not market_healthy and r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
                _set_wait(r, "market-breadth-weak")

            if r.get("zone") == "ðŸ”´ LATE" and r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
                _set_wait(r, "late-zone")

            if r.get("rsi", 0.0) > 65.0 and r.get("plan", {}).get("action") == "ACCUMULATE":
                _downgrade_to_probe(r, "rsi-high")
            if r.get("rsi", 0.0) >= K.RSI_OB_HARD_LIMIT:
                _set_wait(r, f"rsi-overbought-{r['rsi']:.0f}")

            atr_pct = (r["atr"] / r["price"] * 100.0) if r.get("atr") and r.get("price") else 0.0
            if atr_pct >= K.ATR_PCT_HARD_LIMIT:
                _set_wait(r, f"atr-too-high-{atr_pct:.1f}%")
            elif atr_pct >= K.ATR_PCT_SOFT_LIMIT and r.get("plan", {}).get("action") == "ACCUMULATE":
                _downgrade_to_probe(r, f"atr-elevated-{atr_pct:.1f}%")

            if r.get("sector") in weak_sectors and r.get("plan", {}).get("action") == "ACCUMULATE":
                _downgrade_to_probe(r, "weak-sector")

            if r.get("dg_tier") == "DEGRADED":
                if r.get("plan", {}).get("action") == "ACCUMULATE":
                    _downgrade_to_probe(r, f"dataguard-{r['dg_confidence']:.0f}")
                elif r.get("plan", {}).get("action") == "PROBE":
                    _set_wait(r, f"dataguard-{r['dg_confidence']:.0f}")
                r["confidence"] = round(r.get("confidence", 0.0) * 0.70, 1)

            if not r.get("mg_passed", True):
                mg_flags = " ".join(r.get("mg_flags", []))
                if r.get("accumulation_detected"):
                    if "LOSS_CLUSTER" in mg_flags or "FATIGUE" in mg_flags:
                        if r.get("smart_rank", 0.0) < K.SMARTRANK_ENTRY_THRESHOLD + r.get("mg_rank_boost", 0.0):
                            _set_wait(r, "momentum-guard-hard")
                        elif r.get("plan", {}).get("action") == "ACCUMULATE":
                            _downgrade_to_probe(r, "momentum-guard-hard")
                    elif r.get("plan", {}).get("action") == "ACCUMULATE":
                        _downgrade_to_probe(r, "momentum-guard-soft")
                    r["confidence"] = round(r.get("confidence", 0.0) * 0.92, 1)
                else:
                    if r.get("smart_rank", 0.0) < K.SMARTRANK_ENTRY_THRESHOLD + r.get("mg_rank_boost", 0.0):
                        _set_wait(r, "momentum-guard")
                    elif r.get("plan", {}).get("action") == "ACCUMULATE":
                        _downgrade_to_probe(r, "momentum-guard")
                    r["confidence"] = round(r.get("confidence", 0.0) * 0.85, 1)

            combined_scale = float(r.get("combined_position_scale", 1.0) or 1.0)
            if r.get("plan", {}).get("action") in ("ACCUMULATE", "PROBE"):
                r["plan"]["size"] = max(1, int(max(1, r["plan"].get("size", 1)) * combined_scale))

            winrate = STATE.estimate_winrate(
                r["smart_rank"],
                r["anticipation"],
                sector=r["sector"],
                tag=r["tag"],
                regime=regime,
            )
            r["plan"]["winrate"] = winrate if not r["plan"].get("force_wait") else 0.0
            r["plan"]["winrate_na"] = r["plan"].get("force_wait", False)

            if r.get("mg_flags"):
                r["signal_reason"] = (r.get("signal_reason", "") + f" | MomGuard:{','.join(r['mg_flags'])}").strip(" |")

            r["signal_dir"] = get_signal_direction(r["tag"])
            direction = "UP " if r["tag"] in ("buy", "ultra", "early") else "SIDE "
            r["signal_display"] = direction + r["signal"]
            if r["plan"].get("action") == "WAIT":
                r["inst_conf"] = "WEAK"
            elif r["plan"].get("action") == "PROBE":
                r["inst_conf"] = "GOOD"
            else:
                r["inst_conf"] = "STRONG"

        STATE.record_signal_bias(results)

        # â”€â”€ Post-scoring cache update: Write final results to cache â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # FIX: Cache must be written AFTER SmartRank scoring pass, sector blacklist,
        # liquidity gate, and all signal assignments complete. This ensures cached
        # data has correct smart_rank, action, plan, and guard_reason values.
        if K.INDICATOR_CACHE_ENABLED:
            current_time = time.time()
            with _INDICATOR_CACHE_LOCK:
                for r in results:
                    sym = r.get("sym")
                    if sym:
                        _INDICATOR_CACHE[sym] = {
                            "timestamp": current_time,
                            "res_dict": r,  # Full scored result
                            "slope": ema200_slopes.get(sym, 0.0),
                            "quantum_n": r.get("quantum", 0.0)
                        }

        # Pre-sort for guard priority (guard processes in this order)
        results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))

        # â”€â”€ Portfolio guard (FIX-G: pure function) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        guarded_list, guard_counts, guard_exp, guard_blocked, daily_loss_triggered = compute_portfolio_guard(results, open_trades=current_open_trades)

        # Apply guard annotations to results (create new copies â€” no mutation of scoring data)
        annotated_results: List[dict] = []
        for gr in guarded_list:
            r_copy = dict(gr.result)
            r_copy["guard_reason"] = gr.guard_reason
            if gr.is_blocked:
                r_copy["tag"]            = "watch"
                r_copy["signal"]         = "ðŸ›¡ï¸ BLOCKED"
                r_copy["signal_display"] = "â†’ ðŸ›¡ï¸ BLOCKED"
                r_copy["plan"]           = {**r_copy["plan"], "action": "WAIT ðŸ›¡ï¸"}
                rejections.append({"sym": r_copy["sym"], "reason": f"Guard Blocked: {gr.guard_reason}"})
            annotated_results.append(r_copy)

        # FIX BUG#2: Re-sort using post-guard tag so BLOCKED items no longer
        # appear above active BUY/EARLY signals in the display table.
        annotated_results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))

        if daily_loss_triggered:
            _enqueue(status_var.set, "ðŸ›‘ DAILY LOSS LIMIT REACHED â€” new entries blocked")
            log.warning("[PortfolioGuard] Daily loss limit triggered â€” all new entries blocked.")

        _enqueue(_update_guard_bar, guard_slbl, guard_elbl, guard_blbl,
                 guard_counts, guard_exp, guard_blocked)

        # â”€â”€ Record new signals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        smart_rank_entry_threshold = float(getattr(K, "SMARTRANK_ENTRY_THRESHOLD", 20))
        for r in annotated_results:
            if (r.get("plan") and
                r["plan"]["action"] in ("ACCUMULATE", "PROBE") and
                not r["guard_reason"]):
                
                # â”€â”€ Position Manager: check for add-on opportunity
                _existing = _position_manager.get_open_position(r["sym"])
                if _existing is not None:
                    # Symbol already has an open trade â€” evaluate add-on instead of new entry
                    _addon = _position_manager.evaluate_addon(
                        symbol=r["sym"],
                        current_price=r["price"],
                        adx=r["adx"],
                        momentum=r["momentum"],
                        smart_rank=r["smart_rank"],
                        smart_rank_threshold=smart_rank_entry_threshold + r.get("combined_rank_boost", 0),
                        bearish_divergence=r.get("bearish_divergence", False),
                    )
                    if _addon.approved:
                        log.info("[PositionManager] Add-on approved for %s | %s", r["sym"], _addon.reason)
                        r["addon_approved"] = True
                        r["addon"] = _addon
                        # NOTE: confirm_addon() called only after broker execution confirms
                        # _position_manager.confirm_addon(sym)  â† call this from UI/execution layer
                    else:
                        log.debug("[PositionManager] Add-on rejected for %s: %s", r["sym"], _addon.reason)
                        r["addon_approved"] = False
                    # Do NOT record a new signal for an already-open position
                    continue

                if not _alpha_status.pause_new_entries:
                    oe_record_signal(
                        sym=r["sym"], sector=r["sector"],
                        entry=r["plan"]["entry"], stop=r["plan"]["stop"],
                        target=r["plan"]["target"],
                        atr=r["atr"] or 0.0,
                        smart_rank=r["smart_rank"], anticipation=r["anticipation"],
                        action=r["plan"]["action"],
                        existing_trades=current_open_trades,
                        tag=r["tag"],
                        trade_type=r["plan"].get("trade_type", "UNCLASSIFIED"),
                        score=r["plan"].get("score", r.get("smart_rank", 0.0)),
                        risk_used=r["plan"].get("risk_used", 0.0),
                        trigger_price=r["plan"].get("trigger_price", r["plan"]["entry"]),
                        partial_target=r["plan"].get("partial_target"),
                        trailing_trigger=r["plan"].get("trailing_trigger"),
                        trailing_stop_pct=r["plan"].get("trailing_stop_pct"),
                    )
                else:
                    log.info("[AlphaMonitor] Signal for %s blocked â€” system in Level 3 pause", r["sym"])

        # â”€â”€ Market Health Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        avg_rank_all = sum(r["smart_rank"] for r in annotated_results) / len(annotated_results) if annotated_results else 0.0
        if annotated_results:
            act_cnt = sum(1 for r in annotated_results if r["smart_rank"] >= K.ACCUM_SCORE_MIN)
            elite_cnt = sum(1 for r in annotated_results if r["smart_rank"] >= K.ACCUM_SCORE_ENTRY)
            sell_cnt = sum(1 for r in annotated_results if r["tag"] == "sell")
            
            if avg_rank_all >= 65: lbl_text, fg = "ACTIVE", "#00ff00"
            elif avg_rank_all >= 55: lbl_text, fg = "BUILDING", "#ffcc33"
            else: lbl_text, fg = "QUIET", "#ff6666"
            
            if all_cached:
                lbl_text += " (cached)"
            
            _enqueue(widgets["health_avg_var"].set, f"Avg Rank: {avg_rank_all:.1f}")
            _enqueue(widgets["health_act_var"].set, f"Actionable (>={int(K.ACCUM_SCORE_MIN)}): {act_cnt}")
            _enqueue(widgets["health_elite_var"].set, f"Elite (>={int(K.ACCUM_SCORE_ENTRY)}): {elite_cnt}")
            _enqueue(widgets["health_sell_var"].set, f"SELL Signals: {sell_cnt}")
            _enqueue(lambda: widgets["health_lbl"].configure(text=f"Label: {lbl_text}", fg=fg))

        # â”€â”€ Entry window verdict â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        early_cnt    = sum(1 for r in annotated_results if r["zone"] == "ðŸŸ¢ EARLY")
        late_cnt     = sum(1 for r in annotated_results if r["zone"] == "ðŸ”´ LATE")
        if avg_rank_all >= 55 and early_cnt >= late_cnt:
            entry_txt, entry_col = "ðŸŸ¢ ACCUMULATION WINDOW", "#062016"
        elif late_cnt > early_cnt:
            entry_txt, entry_col = "ðŸŸ¡ WAIT FOR CLEAN BASES", "#2a260a"
        else:
            entry_txt, entry_col = "ðŸš« NO POSITION ZONE",    "#2b0a0a"

        # â”€â”€ Insert rows â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        medals       = ["ðŸ¥‡ ", "ðŸ¥ˆ ", "ðŸ¥‰ "]
        phase_icon   = {"Accumulation": "ðŸŸ¡", "Transition": "ðŸŸ¢", "Exhaustion": "ðŸ”´", "Base": "âšª"}
        accum_syms   = [r["sym"] for r in annotated_results if (r.get("plan") or {}).get("action") == "ACCUMULATE"][:3]
        with STATE._lock:
            win_sample = len(STATE.neural_win_memory) + len(STATE.neural_loss_memory)

        def _insert_all():
            for i, r in enumerate(annotated_results):
                prefix = medals[i] if i < 3 else f"#{i+1} "
                icons  = phase_icon.get(r["phase"], "âšª")
                if r["breakout"]:                   icons += "ðŸ’¥"
                if r["quantum"] > 0.5:              icons += "ðŸ§¿"
                if r["fake_expansion"]:             icons += "â˜ ï¸"
                if r["leader"]:                     icons += "ðŸ‘‘"
                if r["ema_cross"] == "BULL_CROSS":  icons += "ðŸ””"
                if r["ema_cross"] == "BEAR_CROSS":  icons += "ðŸ”•"
                if r["vol_div"]:                    icons += r["vol_div"]

                extras = (
                    f"{icons} {r['whale']} {r['hunter']} "
                    f"{'ðŸ§¬' if r['silent'] else ''}{'âš¡' if r['expansion'] else ''}"
                ).strip()

                disp = f"{prefix}{r['signal_display']}"

                if r["plan"].get("winrate_na"):
                    wr_str = "â€”"
                elif win_sample < K.WINRATE_MIN_SAMPLE:
                    wr_str = "âŒ› Building"
                else:
                    wr_str = f"{r['plan']['winrate']:.0f}%"

                row = (
                    r["sym"], r["sector"],
                    f"{r['price']:.2f}", f"{r['adx']:.1f}", f"{r['rsi']:.0f}",
                    f"{r['adaptive_mom']:+.1f}", f"{r['pct_ema200']:+.1f}%",
                    f"{r['vol_ratio']:.1f}x",
                    f"{r.get('tech_score_pct', 0):.0f}%", r["gravity_label"], r["zone"],
                    f"{r['anticipation']:.2f}", f"{r['cpi']:.2f}",
                    f"{r['iet']:.2f}", f"{r['whale_score']:.2f}",
                    extras, disp, r["signal_dir"],
                    f"{r['confidence']:.1f}%", f"{r['smart_rank']:.2f}",
                    r["plan"]["action"], r["plan"]["timeframe"],
                    f"{r['plan']['entry']:.2f}", f"{r['plan']['stop']:.2f}",
                    f"{r['plan']['target']:.2f}", str(r["plan"]["size"]),
                    wr_str, f"{r['plan']['rr']:.1f}x",
                    r["inst_conf"], r["atr_risk"],
                    r["mom_arrow"],
                    f"{r['atr']:.2f}" if r["atr"] else "â€”",
                    f"{r['vwap_dist']*100:.1f}%", f"{r['vol_zscore']:.1f}",
                    r["signal_reason"],
                    r["guard_reason"] if r["guard_reason"] else "âœ… OK",
                )

                if r["guard_reason"]:
                    row_tag = "blocked"
                else:
                    row_tag = (
                        "accum_top" if r["sym"] in accum_syms
                        else ("radar" if r["silent"] else r["tag"])
                    )
                tree.insert("", "end", values=row, tags=(row_tag,))

        _enqueue(_insert_all)

        # â”€â”€ Status summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        mood    = ("Institutional Positioning" if avg_rank_all >= 70
                   else ("Bases Building" if avg_rank_all >= 55 else "Capital Protection"))
        
        if not market_healthy:
            mood += " | âš ï¸ Market EMA50 Breakdown"
            
        safe_s  = [r["sym"] for r in annotated_results if r["smart_rank"] >= K.ACCUM_SCORE_ENTRY][:3]
        watch_s = [r["sym"] for r in annotated_results if K.ACCUM_SCORE_MIN <= r["smart_rank"] < K.ACCUM_SCORE_ENTRY][:3]
        avoid_s = [r["sym"] for r in annotated_results if r["smart_rank"] < K.ACCUM_SCORE_MIN][:3]

        verdict_txt = (
            f"ðŸ§  BRAIN | {entry_txt} | {mood} | "
            f"ðŸŸ¢ {', '.join(safe_s) or 'â€”'} | "
            f"ðŸŸ¡ {', '.join(watch_s) or 'â€”'} | "
            f"ðŸ”´ {', '.join(avoid_s) or 'â€”'}"
        )
        if guard_blocked:
            verdict_txt += f" | ðŸ›¡ï¸ BLOCKED: {', '.join(guard_blocked)}"
        _enqueue(verdict_var.set, verdict_txt)
        _enqueue(verdict_frm.configure, bg=entry_col)
        _enqueue(verdict_w.configure, bg=entry_col)

        avg_future = sum(r["anticipation"] for r in annotated_results) / len(annotated_results) if annotated_results else 0.0
        _enqueue(draw_gauge, g_rank, avg_rank_all, K.SMART_RANK_SCALE, "SmartRank", brain_mode)
        _enqueue(draw_gauge, g_flow, avg_future,   1.0,  "FutureFlow", "anticipation")

        if whale_global:
            _enqueue(_pulse.start, verdict_frm, verdict_w, entry_col)

        elapsed   = round(time.time() - scan_start, 1)
        nw_str    = f"F{nw['flow']:.2f} S{nw['structure']:.2f} T{nw['timing']:.2f}"
        guard_pct = (guard_exp / (get_account_size() + 1e-9)) * 100
        guard_sum = f"ðŸ›¡ï¸{len(guard_blocked)}blk" if guard_blocked else f"ðŸ›¡ï¸OK({guard_pct:.1f}%)"
        oe_sum    = f"ðŸ“Š{len(current_open_trades)}open/{oe_wins}W/{oe_losses}L"

        with _source_labels_lock:
            src_snap = dict(_source_labels)
        src_counts: Dict[str, int] = {}
        for lbl in src_snap.values():
            base = lbl.split("+")[0].replace("âš ï¸", "")
            src_counts[base] = src_counts.get(base, 0) + 1
        src_summary = " | ".join(f"{k}:{v}" for k, v in src_counts.items()) or "â€”"

        _enqueue(status_var.set,
                 f"âœ… {len(annotated_results)} symbols | Regime:{regime} | Next:{future_sector} | "
                 f"Brain:{brain_mode} | Neural:{nw_str} | {guard_sum} | {oe_sum} | "
                 f"ðŸŒ{src_summary} | â± {elapsed}s | {datetime.now().strftime('%H:%M:%S')}")
        _enqueue(pbar.configure, value=100)
        with STATE._lock:          # FIX: scan_count must be mutated under lock
            STATE.scan_count += 1
            
        # Feature 7: Record Rejections DataFrame
        # Ensure symbols that were never processed are logged as rejections
        processed_syms = {r["sym"] for r in annotated_results}
        rejected_syms  = {r["sym"] for r in rejections}
        all_syms       = set(SYMBOLS.keys())
        ghost_syms     = all_syms - processed_syms - rejected_syms

        for sym in sorted(ghost_syms):
            log.warning("Symbol %s never processed â€” possibly missing from all_data", sym)
            rejections.append({"sym": sym, "reason": "Never processed (no data from any source)"})

        oe_save_rejections(rejections)

        # â”€â”€ Auto-save daily scan snapshot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if K.SCAN_HISTORY_ENABLED:
            try:
                saved_path = oe_save_daily_scan(annotated_results)
                if saved_path:
                    log.info("Scan history saved: %s", saved_path)
            except Exception as e:
                log.warning("Could not save daily scan: %s", e)

        # â”€â”€ Save latest scan results for API consumption (thread-safe JSON snapshot) â”€â”€â”€â”€
        try:
            import json
            import tempfile
            import os
            
            _snapshot_path = os.path.join(
                os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
            )
            
            snapshot = [{
                "sym":        r["sym"],
                "sector":     r["sector"],
                "price":      r["price"],
                "signal":     r["signal"],
                "tag":        r["tag"],
                "smart_rank": r.get("smart_rank", 0.0),
                "confidence": r.get("confidence", 0.0),
                "direction":  r.get("signal_dir", ""),
                "phase":      r.get("phase", ""),
                "zone":       r.get("zone", ""),
                "action":     r.get("plan", {}).get("action", "WAIT") if r.get("plan") else "WAIT",
                "entry":      r.get("plan", {}).get("entry", 0.0)    if r.get("plan") else 0.0,
                "stop":       r.get("plan", {}).get("stop", 0.0)     if r.get("plan") else 0.0,
                "target":     r.get("plan", {}).get("target", 0.0)   if r.get("plan") else 0.0,
                "winrate":    r.get("plan", {}).get("winrate", 0.0)  if r.get("plan") else 0.0,
                "scan_time":  datetime.utcnow().isoformat(),
            } for r in annotated_results]
            
            # Atomic write: temp file â†’ replace
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(_snapshot_path), suffix='.tmp')
            with os.fdopen(fd, 'w') as f:
                json.dump(snapshot, f, default=str)
            os.replace(tmp, _snapshot_path)
            log.debug("API scan snapshot saved: %d signals", len(snapshot))
        except Exception as _snap_exc:
            log.debug("scan snapshot write failed: %s", _snap_exc)

        # â”€â”€ Emit WebSocket event to dashboard clients â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        try:
            from egx_radar.dashboard.websocket import emit_scan_complete
            emit_scan_complete(annotated_results)
        except Exception as _ws_exc:
            log.debug("WebSocket emit skipped: %s", _ws_exc)
            # Expected when running scanner without the Flask dashboard

    except Exception as exc:
        log.error("Scan fatal: %s", exc, exc_info=True)
        _enqueue(status_var.set, f"âŒ Error: {exc}")
    finally:
        _enqueue(scan_btn.configure, state="normal")
        _scan_lock.release()


def start_scan(widgets: dict) -> None:
    if _shutdown_requested:
        return
    widgets["scan_btn"].configure(state="disabled")
    threading.Thread(target=run_scan, args=(widgets,), daemon=True).start()


__all__ = [
    "build_capital_flow_map",
    "_scan_lock",
    "run_scan",
    "start_scan",
    "request_shutdown",
]
```

==================================================
FILE: egx_radar/state/__init__.py
=================================

```python
"""Application state package (Layer 8)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.state.app_state import AppState, STATE

__all__ = ["AppState", "STATE"]
```

==================================================
FILE: egx_radar/state/app_state.py
==================================

```python
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

        # â”€â”€ Neural adaptive weights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.neural_weights: Dict[str, float] = {
            "flow": 1.0, "structure": 1.0, "timing": 1.0
        }
        self.neural_memory      = deque(maxlen=K.NEURAL_MEM_SIZE)

        # â”€â”€ Win/loss memory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.neural_win_memory  = deque(maxlen=80)
        self.neural_loss_memory = deque(maxlen=80)
        self.neural_bias_memory = deque(maxlen=80)

        # â”€â”€ FIX-5: Per-sector win/loss tracking for smarter WinRate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Each entry: (rank, anticipation)
        self.sector_win_memory:  Dict[str, deque] = {s: deque(maxlen=30) for s in SECTORS}
        self.sector_loss_memory: Dict[str, deque] = {s: deque(maxlen=30) for s in SECTORS}
        # Per-tag win/loss (ultra/early/buy/watch)
        self.tag_win_memory:  Dict[str, deque] = defaultdict(lambda: deque(maxlen=30))
        self.tag_loss_memory: Dict[str, deque] = defaultdict(lambda: deque(maxlen=30))

        # â”€â”€ Signal history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.signal_history: Dict[str, deque]  = defaultdict(lambda: deque(maxlen=5))
        self.prev_ranks:     Dict[str, float]  = {}

        # â”€â”€ Momentum â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.momentum_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=4))

        # â”€â”€ Sector memory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.sector_flow_memory     = {k: deque(maxlen=15) for k in SECTORS}
        self.sector_rotation_memory = {k: deque(maxlen=20) for k in SECTORS}

        # â”€â”€ Brain mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.brain_mode      = "neutral"
        self.brain_vol_req   = 1.0
        self.brain_score_req = K.BRAIN_SCORE_NEUTRAL

        self.scan_count = 0

        # â”€â”€ Backtest results (persist in memory while app is open) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.backtest_results: dict = {}

    # â”€â”€ Neural weights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Win rate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        regime_mult:    MOMENTUM Ã— 1.1 boosts confidence; DISTRIBUTION Ã— 0.9 dampens
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

    # â”€â”€ Win/loss recording â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Signal & momentum history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            return "â†’"
        avg  = sum(hist_copy[:-1]) / (len(hist_copy) - 1)
        diff = hist_copy[-1] - avg
        if diff > 0.3:  return "â†‘"
        if diff < -0.3: return "â†“"
        return "â†’"

    # â”€â”€ Prev rank â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def get_prev_rank(self, sym: str, default: float) -> float:
        with self._lock:
            return self.prev_ranks.get(sym, default)

    def set_prev_rank(self, sym: str, val: float) -> None:
        with self._lock:
            self.prev_ranks[sym] = val

    # â”€â”€ Brain mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Sector flow â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Persist / restore â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
```

==================================================
FILE: egx_radar/tools/__init__.py
=================================

```python
"""EGX Radar tools and utilities."""
```

==================================================
FILE: egx_radar/tools/__main__.py
=================================

```python
"""Tools module entry point."""

import sys

# Simple dispatcher to allow running tools
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "paper_trading_tracker":
        from egx_radar.tools.paper_trading_tracker import create_tracker
        create_tracker()
    else:
        print("Usage: python -m egx_radar.tools <tool_name>")
        print("Available tools:")
        print("  - paper_trading_tracker")
```

==================================================
FILE: egx_radar/tools/paper_trading_tracker.py
==============================================

```python
"""
One-time script to generate a Paper Trading Excel tracker.
Run from project root:
    python -m egx_radar.tools.paper_trading_tracker

Generates: paper_trading_tracker.xlsx
"""

import pathlib
import sys

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("Install openpyxl first: pip install openpyxl")
    sys.exit(1)


def create_tracker():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Paper Trades"

    # Header style
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    center = Alignment(horizontal="center", vertical="center")

    headers = [
        "Date", "Symbol", "Sector", "Rank", "Zone",
        "Entry", "Stop", "Target", "R:R",
        "Price 1W", "Price 2W",
        "Result", "P&L %", "Notes"
    ]

    col_widths = [12, 8, 12, 8, 10, 8, 8, 8, 6, 10, 10, 10, 8, 20]

    for col, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.row_dimensions[1].height = 25
    ws.freeze_panes = "A2"

    # Result dropdown (Data Validation)
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(
        type="list",
        formula1='"WIN,LOSS,HOLD,PENDING"',
        allow_blank=True,
        showDropDown=False,
    )
    ws.add_data_validation(dv)
    dv.sqref = "L2:L500"

    # Conditional formatting for Result column
    from openpyxl.styles.differential import DifferentialStyle
    from openpyxl.formatting.rule import Rule

    win_fill  = PatternFill("solid", fgColor="C6EFCE")
    loss_fill = PatternFill("solid", fgColor="FFC7CE")

    ws.conditional_formatting.add(
        "L2:L500",
        Rule(type="containsText", operator="containsText", text="WIN",
             dxf=DifferentialStyle(fill=win_fill))
    )
    ws.conditional_formatting.add(
        "L2:L500",
        Rule(type="containsText", operator="containsText", text="LOSS",
             dxf=DifferentialStyle(fill=loss_fill))
    )

    # Summary sheet
    ws2 = wb.create_sheet("Summary")
    ws2["A1"] = "EGX Radar â€” Paper Trading Summary"
    ws2["A1"].font = Font(bold=True, size=14)

    summary_labels = [
        ("A3", "Total Signals:"),
        ("A4", "WIN:"),
        ("A5", "LOSS:"),
        ("A6", "PENDING:"),
        ("A8", "Win Rate:"),
        ("A9", "Avg R:R (wins):"),
        ("A10", "Avg R:R (losses):"),
    ]
    for cell_ref, label in summary_labels:
        ws2[cell_ref] = label
        ws2[cell_ref].font = Font(bold=True)

    # Formulas referencing Paper Trades sheet
    ws2["B3"] = "=COUNTA('Paper Trades'!A2:A500)"
    ws2["B4"] = "=COUNTIF('Paper Trades'!L2:L500,\"WIN\")"
    ws2["B5"] = "=COUNTIF('Paper Trades'!L2:L500,\"LOSS\")"
    ws2["B6"] = "=COUNTIF('Paper Trades'!L2:L500,\"PENDING\")"
    ws2["B8"] = "=IF(B4+B5>0, B4/(B4+B5), 0)"
    ws2["B8"].number_format = "0.0%"

    output_path = pathlib.Path("paper_trading_tracker.xlsx")
    wb.save(output_path)
    print(f"âœ… Paper Trading Tracker saved â†’ {output_path.absolute()}")
    print("ðŸ“‹ Instructions:")
    print("   1. After each scan, copy PROBE signals from the daily CSV to this file")
    print("   2. After 1 week, fill in 'Price 1W' column")
    print("   3. Set Result to WIN/LOSS/HOLD")
    print("   4. Check Summary sheet for Win Rate")


if __name__ == "__main__":
    create_tracker()
```

==================================================
FILE: egx_radar/dashboard/__init__.py
=====================================

```python
"""Dashboard API module - Flask-based web interface for EGX Radar."""

from egx_radar.dashboard.app import create_app
from egx_radar.dashboard.routes import api_bp, dashboard_bp
from egx_radar.dashboard.websocket import socketio

__all__ = [
    'create_app',
    'api_bp',
    'dashboard_bp',
    'socketio',
]
```

==================================================
FILE: egx_radar/dashboard/app.py
================================

```python
"""Flask application factory and configuration."""

import os
from flask import Flask
from flask_cors import CORS

from egx_radar.database import DatabaseManager
from egx_radar.database.config import DatabaseConfig


def create_app(config_name: str = 'production') -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config_name: Environment (development, testing, production)
    
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Configuration
    if config_name == 'development':
        app.config['DEBUG'] = True
        app.config['TESTING'] = False
        app.config['DATABASE_URL'] = 'sqlite:///egx_radar.db'
    elif config_name == 'testing':
        app.config['DEBUG'] = True
        app.config['TESTING'] = True
        app.config['DATABASE_URL'] = 'sqlite:///:memory:'
    else:  # production
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['DATABASE_URL'] = DatabaseConfig.get_production_url()
    
    # CORS support
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Database initialization
    db_url = os.environ.get('DATABASE_URL', app.config['DATABASE_URL'])
    app.db_manager = DatabaseManager(database_url=db_url)
    
    # Ensure database tables exist
    app.db_manager.init_db()
    
    # Register blueprints
    from egx_radar.dashboard.routes import api_bp, dashboard_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'version': '0.8.3'}, 200
    
    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=True)
```

==================================================
FILE: egx_radar/dashboard/routes.py
===================================

```python
"""Flask blueprints for API and dashboard routes."""

from flask import Blueprint, jsonify, request, render_template, current_app
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import os


# Create blueprints
api_bp = Blueprint('api', __name__)
dashboard_bp = Blueprint('dashboard', __name__)


def _load_scan_snapshot() -> list:
    """Load the latest scanner results from the snapshot file.
    
    Returns:
        List of signal dicts from the most recent scan, or empty list if no snapshot exists.
    """
    try:
        from egx_radar.config.settings import K
        
        snapshot_path = os.path.join(
            os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
        )
        
        if not os.path.exists(snapshot_path):
            return []
        
        with open(snapshot_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return []


# ==================== DASHBOARD ROUTES ====================

@dashboard_bp.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@dashboard_bp.route('/backtests')
def backtests_page():
    """Backtests history page."""
    return render_template('backtests.html')


@dashboard_bp.route('/trades')
def trades_page():
    """Trades browser page."""
    return render_template('trades.html')


@dashboard_bp.route('/signals')
def signals_page():
    """Trading signals page."""
    return render_template('signals.html')


@dashboard_bp.route('/settings')
def settings_page():
    """Settings page."""
    return render_template('settings.html')


# ==================== API: BACKTESTS ====================

@api_bp.route('/backtests', methods=['GET'])
def get_backtests():
    """Get list of backtests with optional filtering."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        days = request.args.get('days', 30, type=int)
        symbol = request.args.get('symbol', None, type=str)
        status = request.args.get('status', None, type=str)
        
        backtests = current_app.db_manager.get_backtests(
            limit=limit,
            offset=offset,
            symbol=symbol,
            status=status,
            days=days
        )
        
        return jsonify({
            'success': True,
            'count': len(backtests),
            'backtests': [
                {
                    'id': bt.id,
                    'backtest_id': bt.backtest_id,
                    'date': bt.backtest_date.isoformat(),
                    'symbols': bt.symbols.split(','),
                    'symbol_count': bt.symbol_count,
                    'trades': bt.total_trades,
                    'win_rate': round(bt.win_rate, 4),
                    'pnl': float(bt.total_pnl),
                    'sharpe': round(bt.sharpe_ratio, 3),
                    'max_drawdown': round(bt.max_drawdown_pct, 2),
                    'execution_time': bt.execution_time_seconds,
                    'status': bt.status,
                }
                for bt in backtests
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/backtests/<int:backtest_id>', methods=['GET'])
def get_backtest_detail(backtest_id: int):
    """Get detailed backtest information."""
    try:
        backtest = current_app.db_manager.get_backtest(backtest_id)
        if not backtest:
            return jsonify({'success': False, 'error': 'Backtest not found'}), 404
        
        trades = current_app.db_manager.get_trades(backtest_id)
        signals = current_app.db_manager.get_signals(backtest_id)
        
        return jsonify({
            'success': True,
            'backtest': {
                'id': backtest.id,
                'backtest_id': backtest.backtest_id,
                'date': backtest.backtest_date.isoformat(),
                'start_date': backtest.start_date.isoformat(),
                'end_date': backtest.end_date.isoformat(),
                'symbols': backtest.symbols.split(','),
                'metrics': {
                    'total_trades': backtest.total_trades,
                    'winning_trades': backtest.winning_trades,
                    'losing_trades': backtest.losing_trades,
                    'win_rate': round(backtest.win_rate, 4),
                    'total_pnl': float(backtest.total_pnl),
                    'gross_profit': float(backtest.gross_profit),
                    'gross_loss': float(backtest.gross_loss),
                    'profit_factor': round(backtest.profit_factor, 2),
                    'max_drawdown': round(backtest.max_drawdown, 4),
                    'max_drawdown_pct': round(backtest.max_drawdown_pct, 2),
                    'sharpe_ratio': round(backtest.sharpe_ratio, 3),
                    'sortino_ratio': round(backtest.sortino_ratio, 3),
                    'calmar_ratio': round(backtest.calmar_ratio, 3),
                    'avg_trade_return': round(backtest.avg_trade_return, 4),
                    'expectancy': round(backtest.expectancy, 2),
                    'recovery_factor': round(backtest.recovery_factor, 2),
                },
                'execution': {
                    'time_seconds': backtest.execution_time_seconds,
                    'workers_used': backtest.workers_used,
                    'status': backtest.status,
                },
                'trades_count': len(trades),
                'signals_count': len(signals),
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: TRADES ====================

@api_bp.route('/trades', methods=['GET'])
def get_trades():
    """Get trades with filtering."""
    try:
        backtest_id = request.args.get('backtest_id', type=int)
        symbol = request.args.get('symbol', None, type=str)
        result = request.args.get('result', None, type=str)  # win, loss
        
        if not backtest_id:
            return jsonify({'success': False, 'error': 'backtest_id required'}), 400
        
        trades = current_app.db_manager.get_trades(
            backtest_id,
            symbol=symbol,
            result=result
        )
        
        return jsonify({
            'success': True,
            'count': len(trades),
            'trades': [
                {
                    'id': t.id,
                    'symbol': t.symbol,
                    'entry_date': t.entry_date.isoformat(),
                    'entry_price': float(t.entry_price),
                    'entry_signal': t.entry_signal,
                    'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                    'exit_price': float(t.exit_price) if t.exit_price else None,
                    'exit_reason': t.exit_reason,
                    'quantity': t.quantity,
                    'result': t.result,
                    'pnl': float(t.pnl) if t.pnl else None,
                    'pnl_pct': round(t.pnl_pct, 4) if t.pnl_pct else None,
                    'duration_minutes': t.duration_minutes,
                }
                for t in trades
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: SIGNALS ====================

@api_bp.route('/signals', methods=['GET'])
def get_signals():
    """Get signals with filtering."""
    try:
        backtest_id = request.args.get('backtest_id', type=int)
        symbol = request.args.get('symbol', None, type=str)
        signal_type = request.args.get('type', None, type=str)
        
        if not backtest_id:
            return jsonify({'success': False, 'error': 'backtest_id required'}), 400
        
        signals = current_app.db_manager.get_signals(
            backtest_id,
            symbol=symbol,
            signal_type=signal_type
        )
        
        return jsonify({
            'success': True,
            'count': len(signals),
            'signals': [
                {
                    'id': s.id,
                    'symbol': s.symbol,
                    'date': s.signal_date.isoformat(),
                    'type': s.signal_type,
                    'strength': s.strength,
                    'momentum': s.momentum,
                    'trend': s.trend,
                    'volatility': s.volatility,
                    'volume_ratio': s.volume_ratio,
                    'indicators': s.indicators,
                    'source': s.source,
                    'trade_taken': s.trade_taken,
                }
                for s in signals
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: STATISTICS ====================

@api_bp.route('/statistics/summary', methods=['GET'])
def get_summary_statistics():
    """Get summary statistics for recent backtests."""
    try:
        days = request.args.get('days', 30, type=int)
        
        summary = current_app.db_manager.get_summary_stats(days=days)
        
        return jsonify({
            'success': True,
            'summary': {
                'period_days': summary.get('period_days'),
                'total_backtests': summary.get('total_backtests'),
                'total_trades': summary.get('total_trades'),
                'total_pnl': round(summary.get('total_pnl', 0), 2),
                'avg_win_rate': round(summary.get('avg_win_rate', 0) * 100, 2),
                'avg_sharpe_ratio': round(summary.get('avg_sharpe_ratio', 0), 3),
                'best_trade_day': summary.get('best_trade_day').isoformat() if summary.get('best_trade_day') else None,
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/statistics/symbol/<symbol>', methods=['GET'])
def get_symbol_statistics(symbol: str):
    """Get performance statistics for a specific symbol."""
    try:
        days = request.args.get('days', 90, type=int)
        
        performance = current_app.db_manager.get_symbol_performance(symbol, days=days)
        
        if not performance:
            return jsonify({
                'success': True,
                'symbol': symbol,
                'data': None,
                'message': 'No data available'
            }), 200
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': {
                'backtests': performance.get('backtests', 0),
                'total_trades': performance.get('total_trades', 0),
                'avg_win_rate': round(performance.get('avg_win_rate', 0) * 100, 2),
                'avg_return': round(performance.get('avg_return', 0) * 100, 2),
                'avg_sharpe': round(performance.get('avg_sharpe', 0), 3),
                'recommendation': performance.get('recommendation', 'hold'),
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: CONFIGURATION ====================

@api_bp.route('/config', methods=['GET'])
def get_configuration():
    """Get current configuration from environment."""
    try:
        import os
        
        # Try to import configuration if available, otherwise use defaults
        config_obj = None
        try:
            from egx_radar.configuration import K
            config_obj = K
        except ImportError:
            pass
        
        config_info = {
            'database': {
                'type': 'postgresql' if 'postgresql' in os.environ.get('DATABASE_URL', '') else 'sqlite',
                'url': os.environ.get('DATABASE_URL', 'sqlite:///egx_radar.db')[:50] + '...',
            },
            'workers': getattr(config_obj, 'WORKERS_COUNT', 4) if config_obj else 4,
            'chunk_size': getattr(config_obj, 'CHUNK_SIZE', 2) if config_obj else 2,
            'backtest': {
                'min_smartrank': getattr(config_obj, 'BT_MIN_SMARTRANK', 50) if config_obj else 50,
                'position_size': getattr(config_obj, 'BT_POSITION_SIZE', 1000) if config_obj else 1000,
                'stop_loss': getattr(config_obj, 'BT_STOP_LOSS_PERCENT', 0.05) if config_obj else 0.05,
                'take_profit': getattr(config_obj, 'BT_TAKE_PROFIT_PERCENT', 0.10) if config_obj else 0.10,
            },
            'data': {
                'min_bars': getattr(config_obj, 'DATA_MIN_BARS', 250) if config_obj else 250,
                'date_format': getattr(config_obj, 'DATE_FORMAT', '%Y-%m-%d') if config_obj else '%Y-%m-%d',
            },
            'version': '0.8.3'
        }
        
        return jsonify({
            'success': True,
            'config': config_info
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: HEALTH ====================

@api_bp.route('/health', methods=['GET'])
def api_health():
    """API health check."""
    try:
        # Try to access database
        current_app.db_manager.get_backtests(limit=1)
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'version': '0.8.3',
            'database': 'connected',
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
        }), 503


# ==================== API: MARKET DATA & SIGNALS ====================

@api_bp.route('/market/price/<symbol>', methods=['GET'])
def get_market_price(symbol: str):
    """Get current market price for a symbol."""
    try:
        from egx_radar.market_data import get_market_data_manager
        
        market_data = get_market_data_manager()
        price = market_data.get_current_price(symbol)
        
        if price is None:
            return jsonify({'success': False, 'error': f'Unable to fetch price for {symbol}'}), 400
        
        stats = market_data.get_price_stats(symbol)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'current_price': price,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/market/prices', methods=['POST'])
def get_market_prices():
    """Get current prices for multiple symbols."""
    try:
        from egx_radar.market_data import get_market_data_manager
        
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'success': False, 'error': 'No symbols provided'}), 400
        
        market_data = get_market_data_manager()
        prices = market_data.get_multi_prices(symbols)
        
        return jsonify({
            'success': True,
            'prices': prices
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/scanner', methods=['GET'])
def get_scanner_signals():
    """Return latest SmartRank signals from the core scanner.
    
    This endpoint returns real signals from the EGX Radar core scanner
    (using SmartRank scoring), not from the parallel market_data engine.
    
    Query Parameters:
        tag (str, optional): Filter by signal tag (buy, ultra, early, watch, sell)
        min_rank (float, optional): Minimum SmartRank threshold (0-100)
        sector (str, optional): Filter by sector
    
    Returns:
        success (bool): Whether the request was successful
        count (int): Number of signals returned
        source (str): Always 'core_scanner_smartrank'
        signals (list): List of signal dicts
        scan_time (str): ISO timestamp of when the scan was performed
    """
    try:
        snapshot = _load_scan_snapshot()
        if not snapshot:
            return jsonify({
                'success': False,
                'error': 'No scan results available. Run a scan first.',
                'hint': 'Launch the desktop scanner and press Gravity Scan.',
            }), 404

        # Optional filters
        tag_filter = request.args.get('tag', None)
        min_rank   = request.args.get('min_rank', 0, type=float)
        sector     = request.args.get('sector', None)

        results = snapshot
        if tag_filter:
            results = [r for r in results if r.get('tag') == tag_filter]
        if min_rank > 0:
            results = [r for r in results if r.get('smart_rank', 0) >= min_rank]
        if sector:
            results = [r for r in results if r.get('sector') == sector]

        return jsonify({
            'success':    True,
            'count':      len(results),
            'source':     'core_scanner_smartrank',
            'signals':    results,
            'scan_time':  results[0].get('scan_time') if results else (snapshot[0].get('scan_time') if snapshot else None),
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/generate/<symbol>', methods=['GET'])
def generate_signal(symbol: str):
    """Generate trading signal for a symbol."""
    try:
        from egx_radar.market_data import get_signal_generator
        
        signal_gen = get_signal_generator()
        signal = signal_gen.generate_signal(symbol)
        
        if signal is None:
            return jsonify({'success': False, 'error': f'Unable to generate signal for {symbol}'}), 400
        
        return jsonify({
            'success': True,
            'signal': signal.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/batch', methods=['POST'])
def generate_signals_batch():
    """Generate signals for multiple symbols."""
    try:
        from egx_radar.market_data import get_signal_generator
        
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'success': False, 'error': 'No symbols provided'}), 400
        
        signal_gen = get_signal_generator()
        signals = signal_gen.generate_signals_batch(symbols)
        
        # Convert to dict, filtering out None values
        signals_dict = {
            symbol: sig.to_dict() if sig else None
            for symbol, sig in signals.items()
        }
        
        return jsonify({
            'success': True,
            'signals': signals_dict
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/history/<symbol>', methods=['GET'])
def get_signal_history(symbol: str):
    """Get signal history for a symbol."""
    try:
        from egx_radar.market_data import get_signal_generator
        
        limit = request.args.get('limit', 100, type=int)
        signal_gen = get_signal_generator()
        signals = signal_gen.get_signal_history(symbol, limit=limit)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'count': len(signals),
            'signals': [s.to_dict() for s in signals]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/history', methods=['GET'])
def get_alerts():
    """Get alert history."""
    try:
        from egx_radar.market_data import get_notification_manager
        
        limit = request.args.get('limit', 50, type=int)
        alert_type = request.args.get('type', None, type=str)
        
        notification_mgr = get_notification_manager()
        
        # Import AlertType if filtering by type
        alerts = notification_mgr.get_alert_history(limit=limit)
        
        if alert_type:
            from egx_radar.market_data import AlertType
            try:
                atype = AlertType(alert_type)
                alerts = [a for a in alerts if a.alert_type == atype]
            except ValueError:
                pass
        
        return jsonify({
            'success': True,
            'count': len(alerts),
            'unread': notification_mgr.get_unread_count(),
            'alerts': [a.to_dict() for a in alerts]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/mark-read', methods=['POST'])
def mark_alerts_read():
    """Mark alerts as read."""
    try:
        from egx_radar.market_data import get_notification_manager
        
        data = request.get_json()
        count = data.get('count', 1)
        
        notification_mgr = get_notification_manager()
        notification_mgr.mark_as_read(count)
        
        return jsonify({
            'success': True,
            'unread': notification_mgr.get_unread_count()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/market/volatility/<symbol>', methods=['GET'])
def get_volatility(symbol: str):
    """Get intraday volatility for a symbol."""
    try:
        from egx_radar.market_data import get_market_data_manager
        
        market_data = get_market_data_manager()
        volatility = market_data.get_intraday_volatility(symbol)
        
        if volatility is None:
            return jsonify({'success': False, 'error': f'Unable to calculate volatility for {symbol}'}), 400
        
        sentiment = market_data.get_sentiment_indicators(symbol)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'volatility_percent': volatility,
            'sentiment': sentiment
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'success': False, 'error': 'Not found'}), 404


@api_bp.route('/backtest/missed-trades', methods=['GET'])
def get_missed_trade_analysis():
    """Return missed trade intelligence analysis from the latest backtest."""
    try:
        from egx_radar.state.app_state import STATE
        bt = getattr(STATE, "backtest_results", None) or {}
        dashboard = bt.get("dashboard", {})
        analysis = dashboard.get("missed_trade_analysis", {})
        report_text = dashboard.get("missed_trade_report", "")
        missed_info = dashboard.get("missed_trades", {})

        if not analysis or analysis.get("total_missed", 0) == 0:
            return jsonify({
                'success': False,
                'error': 'No missed trade data. Run a backtest first.',
            }), 404

        return jsonify({
            'success': True,
            'total_missed': analysis.get("total_missed", 0),
            'missed_wins': analysis.get("missed_wins", 0),
            'missed_losses': analysis.get("missed_losses", 0),
            'missed_wins_pct': analysis.get("missed_wins_pct", 0.0),
            'missed_losses_pct': analysis.get("missed_losses_pct", 0.0),
            'avg_return_pct': analysis.get("avg_return_pct", 0.0),
            'total_pnl_impact_pct': analysis.get("total_pnl_impact_pct", 0.0),
            'quality_breakdown': analysis.get("quality_breakdown", {}),
            'reason_breakdown': analysis.get("reason_breakdown", {}),
            'sector_breakdown': analysis.get("sector_breakdown", {}),
            'recommendations': analysis.get("recommendations", {}),
            'report': report_text,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/backtest/tracking-dashboard', methods=['GET'])
def get_tracking_dashboard():
    """Return the full trade tracking dashboard from the latest backtest."""
    try:
        from egx_radar.state.app_state import STATE
        bt = getattr(STATE, "backtest_results", None) or {}
        trades = bt.get("trades", [])

        # Also accept a CSV path via query param
        csv_path = request.args.get('csv', None)

        from egx_radar.backtest.tracking_dashboard import build_tracking_dashboard, format_dashboard_report, load_trades_from_csv

        all_trades = list(trades)
        if csv_path and os.path.exists(csv_path):
            all_trades.extend(load_trades_from_csv(csv_path))

        if not all_trades:
            return jsonify({
                'success': False,
                'error': 'No trade data. Run a backtest first or provide a CSV path.',
            }), 404

        all_trades.sort(key=lambda t: t.get('exit_date', ''))
        dashboard = build_tracking_dashboard(all_trades)
        dashboard['text'] = format_dashboard_report(dashboard)

        # Serialize equity curve and drawdown as lists of [date, value]
        return jsonify({
            'success': True,
            'core_metrics': dashboard['core_metrics'],
            'progress': dashboard['progress'],
            'classification': dashboard['classification'],
            'equity_curve': dashboard['equity_curve'],
            'drawdown_series': dashboard['drawdown_series'],
            'losing_streak': dashboard['losing_streak'],
            'risk': dashboard['risk'],
            'monthly': dashboard['monthly'],
            'health_score': dashboard['health_score'],
            'verdict': dashboard['verdict'],
            'report': dashboard['text'],
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'success': False, 'error': 'Server error'}), 500
```

==================================================
FILE: egx_radar/dashboard/run.py
================================

```python
"""Main entry point for EGX Radar Dashboard server."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from egx_radar.dashboard.app import create_app
from egx_radar.dashboard.websocket import socketio


def run_dashboard(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """
    Run the dashboard server.
    
    Args:
        host: Server host address
        port: Server port
        debug: Enable debug mode
    """
    app = create_app(config_name='development' if debug else 'production')
    socketio.init_app(app)
    
    print(f"""
    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
    â•‘       EGX Radar Dashboard Server                         â•‘
    â•‘       Version 0.8.3                                      â•‘
    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    
    Starting server...
    
    Dashboard: http://{host}:{port}
    API: http://{host}:{port}/api
    WebSocket: ws://{host}:{port}/socket.io
    
    Press Ctrl+C to stop
    """)
    
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=debug
    )


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='EGX Radar Dashboard Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host address')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    run_dashboard(host=args.host, port=args.port, debug=args.debug)
```

==================================================
FILE: egx_radar/dashboard/websocket.py
======================================

```python
"""WebSocket support for real-time dashboard updates."""

from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from typing import Dict, Any, Optional

socketio = SocketIO(cors_allowed_origins="*")


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f'Client connected')
    emit('response', {
        'status': 'connected',
        'server_time': datetime.utcnow().isoformat(),
        'message': 'Connected to EGX Radar Dashboard'
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f'Client disconnected')


@socketio.on('subscribe_backtest')
def handle_subscribe_backtest(data):
    """Subscribe to real-time backtest updates."""
    backtest_id = data.get('backtest_id')
    room = f'backtest_{backtest_id}'
    
    join_room(room)
    emit('subscribed', {
        'backtest_id': backtest_id,
        'room': room,
        'message': f'Subscribed to backtest {backtest_id}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_backtest')
def handle_unsubscribe_backtest(data):
    """Unsubscribe from backtest updates."""
    backtest_id = data.get('backtest_id')
    room = f'backtest_{backtest_id}'
    
    leave_room(room)
    emit('unsubscribed', {
        'backtest_id': backtest_id,
        'message': f'Unsubscribed from backtest {backtest_id}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('subscribe_symbol')
def handle_subscribe_symbol(data):
    """Subscribe to symbol updates."""
    symbol = data.get('symbol')
    room = f'symbol_{symbol}'
    
    join_room(room)
    emit('subscribed', {
        'symbol': symbol,
        'room': room,
        'message': f'Subscribed to {symbol} updates',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_symbol')
def handle_unsubscribe_symbol(data):
    """Unsubscribe from symbol updates."""
    symbol = data.get('symbol')
    room = f'symbol_{symbol}'
    
    leave_room(room)
    emit('unsubscribed', {
        'symbol': symbol,
        'message': f'Unsubscribed from {symbol} updates',
        'timestamp': datetime.utcnow().isoformat()
    })


def emit_backtest_update(backtest_id: int, update: Dict[str, Any]):
    """
    Emit backtest update to all subscribers.
    
    Args:
        backtest_id: Backtest ID
        update: Update data
    """
    room = f'backtest_{backtest_id}'
    socketio.emit('backtest_update', {
        'backtest_id': backtest_id,
        'update': update,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


def emit_trade_update(backtest_id: int, trade_data: Dict[str, Any]):
    """
    Emit new trade to subscribers.
    
    Args:
        backtest_id: Backtest ID
        trade_data: Trade information
    """
    room = f'backtest_{backtest_id}'
    socketio.emit('trade_executed', {
        'backtest_id': backtest_id,
        'trade': trade_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)
    
    # Also emit to symbol-specific room
    symbol = trade_data.get('symbol')
    if symbol:
        room = f'symbol_{symbol}'
        socketio.emit('trade_executed', {
            'symbol': symbol,
            'trade': trade_data,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)


def emit_signal_alert(symbol: str, signal_data: Dict[str, Any]):
    """
    Emit trading signal alert.
    
    Args:
        symbol: Symbol that generated signal
        signal_data: Signal information
    """
    room = f'symbol_{symbol}'
    socketio.emit('signal_alert', {
        'symbol': symbol,
        'signal': signal_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


def emit_system_update(message: str, level: str = 'info'):
    """
    Emit system-wide update to all connected clients.
    
    Args:
        message: Update message
        level: Log level (info, warning, error)
    """
    socketio.emit('system_update', {
        'message': message,
        'level': level,
        'timestamp': datetime.utcnow().isoformat()
    }, broadcast=True)


# ==================== MARKET DATA & SIGNALS ====================

@socketio.on('subscribe_market_symbol')
def handle_subscribe_market(data):
    """Subscribe to real-time market data for a symbol."""
    symbol = data.get('symbol')
    room = f'market_{symbol}'
    
    join_room(room)
    emit('market_subscribed', {
        'symbol': symbol,
        'room': room,
        'message': f'Subscribed to market data for {symbol}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_market_symbol')
def handle_unsubscribe_market(data):
    """Unsubscribe from market data."""
    symbol = data.get('symbol')
    room = f'market_{symbol}'
    
    leave_room(room)
    emit('market_unsubscribed', {
        'symbol': symbol,
        'message': f'Unsubscribed from market data for {symbol}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('subscribe_signals')
def handle_subscribe_signals(data):
    """Subscribe to real-time trading signals."""
    signal_type = data.get('type', 'all')  # 'all', 'buy', 'sell', etc.
    room = f'signals_{signal_type}'
    
    join_room(room)
    emit('signals_subscribed', {
        'type': signal_type,
        'room': room,
        'message': f'Subscribed to {signal_type} signals',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_signals')
def handle_unsubscribe_signals(data):
    """Unsubscribe from signals."""
    signal_type = data.get('type', 'all')
    room = f'signals_{signal_type}'
    
    leave_room(room)
    emit('signals_unsubscribed', {
        'type': signal_type,
        'message': f'Unsubscribed from {signal_type} signals',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('subscribe_alerts')
def handle_subscribe_alerts(data):
    """Subscribe to real-time alerts and notifications."""
    alert_level = data.get('level', 'all')  # 'all', 'warning', 'critical', etc.
    room = 'alerts'
    
    join_room(room)
    emit('alerts_subscribed', {
        'level': alert_level,
        'message': f'Subscribed to alerts (level: {alert_level})',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_alerts')
def handle_unsubscribe_alerts(data):
    """Unsubscribe from alerts."""
    room = 'alerts'
    leave_room(room)
    emit('alerts_unsubscribed', {
        'message': 'Unsubscribed from alerts',
        'timestamp': datetime.utcnow().isoformat()
    })


def emit_price_update(symbol: str, price: float, timestamp: Optional[datetime] = None):
    """
    Emit real-time price update.
    
    Args:
        symbol: Stock symbol
        price: Current price
        timestamp: Update timestamp
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    room = f'market_{symbol}'
    socketio.emit('price_update', {
        'symbol': symbol,
        'price': price,
        'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
    }, room=room)


def emit_signal_generated(signal_data: Dict[str, Any]):
    """
    Emit newly generated trading signal.
    
    Args:
        signal_data: Signal information (dict)
    """
    # Emit to all signals subscribers
    socketio.emit('signal_generated', {
        'signal': signal_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room='signals_all')


def emit_scan_complete(results: list) -> None:
    """
    Emit scan_complete event to all connected dashboard clients.
    Called by scan/runner.py after every scan completes.
    
    Args:
        results: List of result dicts from run_scan() â€” same format as
                 scan_snapshot.json. Each result contains signal analysis
                 with SmartRank scores.
    """
    try:
        payload = {
            "event":     "scan_complete",
            "count":     len(results),
            "timestamp": datetime.utcnow().isoformat(),
            "signals": [{
                "sym":        r.get("sym"),
                "sector":     r.get("sector"),
                "signal":     r.get("signal"),
                "tag":        r.get("tag"),
                "smart_rank": r.get("smart_rank", 0.0),
                "direction":  r.get("signal_dir", r.get("direction", "")),
                "action":     r.get("plan", {}).get("action", "WAIT")
                               if isinstance(r.get("plan"), dict) else "WAIT",
                "entry":      r.get("plan", {}).get("entry", 0.0)
                               if isinstance(r.get("plan"), dict) else 0.0,
                "stop":       r.get("plan", {}).get("stop", 0.0)
                               if isinstance(r.get("plan"), dict) else 0.0,
                "target":     r.get("plan", {}).get("target", 0.0)
                               if isinstance(r.get("plan"), dict) else 0.0,
            } for r in results[:50]],  # cap at 50 to keep payload small
        }
        socketio.emit("scan_complete", payload, namespace="/", broadcast=True)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("emit_scan_complete failed: %s", exc)


def emit_alert(alert_data: Dict[str, Any]):
    """
    Emit alert/notification to subscribers.
    
    Args:
        alert_data: Alert information (dict)
    """
    socketio.emit('alert', {
        'alert': alert_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room='alerts')


def emit_market_update(symbol: str, update_data: Dict[str, Any]):
    """
    Emit comprehensive market update for a symbol.
    
    Args:
        symbol: Stock symbol
        update_data: Market data (price, volatility, sentiment, etc.)
    """
    room = f'market_{symbol}'
    socketio.emit('market_update', {
        'symbol': symbol,
        'data': update_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)
```

==================================================
FILE: egx_radar/ui/__init__.py
==============================

```python
"""UI layer: Tkinter main window, gauges, tooltips, and helpers (Layer 10)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.ui.components import (
    _ui_q,
    _enqueue,
    _pump,
    PulseController,
    _pulse,
    draw_gauge,
    _update_heatmap,
    _update_rotation_map,
    _update_flow_map,
    _update_guard_bar,
    _update_regime_label,
    _update_brain_label,
    _show_tooltip,
    _destroy_tooltip,
    export_csv,
)


def main() -> None:
    from egx_radar.ui.main_window import main as _main
    _main()

__all__ = [
    "_ui_q",
    "_enqueue",
    "_pump",
    "PulseController",
    "_pulse",
    "draw_gauge",
    "_update_heatmap",
    "_update_rotation_map",
    "_update_flow_map",
    "_update_guard_bar",
    "_update_regime_label",
    "_update_brain_label",
    "_show_tooltip",
    "_destroy_tooltip",
    "export_csv",
    "main",
]
```

==================================================
FILE: egx_radar/ui/components.py
================================

```python
from __future__ import annotations

"""UI primitives: Tkinter queue, gauges, heatmaps, tooltips, and export (Layer 10)."""

import csv
import logging
import math
import queue
import tkinter.messagebox as messagebox
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, ttk

from egx_radar import __version__
from egx_radar.config.settings import (
    K,
    C,
    F_BODY,
    F_HEADER,
    F_SMALL,
    F_MICRO,
    SECTORS,
    get_account_size,
    get_max_per_sector,
    get_atr_exposure,
)

log = logging.getLogger(__name__)


# â”€â”€ UI event queue (FIX-H) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_ui_q: queue.Queue = queue.Queue()


def _enqueue(fn, *args, **kwargs):
    _ui_q.put((fn, args, kwargs))


def _pump(root: tk.Tk) -> None:
    """Drain the UI queue on the main thread. Called every UI_POLL_MS ms."""
    while True:
        try:
            fn, args, kwargs = _ui_q.get_nowait()
            fn(*args, **kwargs)
        except queue.Empty:
            break
        except Exception as exc:
            log.error("UI queue error: %s", exc)
    root.after(K.UI_POLL_MS, lambda: _pump(root))


# â”€â”€ Pulse controller â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class PulseController:
    def __init__(self) -> None:
        self._active   = False
        self._state    = 0
        self._frm: Optional[tk.Frame] = None
        self._lbl: Optional[tk.Label] = None
        self._base_col = C.BG

    def start(self, frm: tk.Frame, lbl: tk.Label, base_col: str) -> None:
        self._frm, self._lbl, self._base_col = frm, lbl, base_col
        if not self._active:
            self._active = True
            self._tick()

    def stop(self) -> None:
        self._active = False
        if self._frm:
            try:
                self._frm.configure(bg=self._base_col)
                if self._lbl:
                    self._lbl.configure(bg=self._base_col)
            except tk.TclError:
                pass

    def _tick(self) -> None:
        if not self._active or not self._frm:
            return
        self._state ^= 1
        col = "#113a2c" if self._state else self._base_col
        try:
            self._frm.configure(bg=col)
            if self._lbl:
                self._lbl.configure(bg=col)
            self._frm.after(K.UI_PULSE_MS, self._tick)
        except tk.TclError:
            self._active = False


_pulse = PulseController()


def _clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


# â”€â”€ Gauge widget â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def draw_gauge(canvas: tk.Canvas, val: float, max_val: float, label: str, sublabel: str = "") -> None:
    canvas.delete("all")
    W, H   = 160, 110
    cx, cy = W // 2, H - 18
    R      = 58
    ratio  = _clamp01(val / (max_val + 1e-9))
    col    = C.GREEN if ratio >= 0.65 else (C.YELLOW if ratio >= 0.38 else C.RED)
    canvas.create_arc(cx-R, cy-R, cx+R, cy+R, start=0, extent=180, style="arc", width=14, outline=C.BG3)
    if ratio > 0.005:
        canvas.create_arc(cx-R, cy-R, cx+R, cy+R, start=0, extent=ratio*180, style="arc", width=14, outline=col)
    ang = math.radians(180 - ratio * 180)
    nx  = cx + (R-9) * math.cos(ang)
    ny  = cy - (R-9) * math.sin(ang)
    canvas.create_line(cx, cy, nx, ny, fill=col, width=2)
    canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=col, outline="")
    canvas.create_text(cx, cy-24, text=f"{val:.1f}", fill=col, font=("Consolas", 15, "bold"))
    canvas.create_text(cx, cy-8,  text=label,    fill=C.ACCENT2, font=("Consolas", 8, "bold"))
    if sublabel:
        canvas.create_text(cx, cy+6, text=sublabel, fill=C.MUTED, font=("Consolas", 7))


# â”€â”€ UI update helpers (called from _pump, safe on main thread) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _update_heatmap(heat_labels: dict, sector_strength: Dict[str, float]) -> None:
    for sec, val in sector_strength.items():
        if val > 0.6:   bg, fg = "#0a2218", C.GREEN
        elif val > 0.3: bg, fg = "#1c1a08", C.YELLOW
        else:           bg, fg = "#220a0a", C.RED
        heat_labels[sec].configure(text=f"{sec}\n{val:.2f}", bg=bg, fg=fg)


def _update_rotation_map(rot_labels: dict, scores: Dict[str, float], future: str) -> None:
    for sec, val in scores.items():
        if sec == future:  col, bg = C.GREEN,  "#061f14"
        elif val > 0.6:    col, bg = C.CYAN,   "#06131f"
        elif val > 0.35:   col, bg = C.YELLOW, "#1c1a08"
        else:              col, bg = C.MUTED,  C.BG3
        rot_labels[sec].configure(
            text=f"{'ðŸ‘‘ ' if sec == future else ''}{sec}\n{val:.2f}", fg=col, bg=bg
        )


def _update_flow_map(flow_labels: dict, flow_scores: Dict[str, float], leader: str) -> None:
    for sec, val in flow_scores.items():
        if sec == leader: col, bg = C.GREEN,  "#061f14"
        elif val > 0.3:   col, bg = C.CYAN,   "#06131f"
        elif val > 0:     col, bg = C.YELLOW, "#1c1a08"
        else:             col, bg = C.RED,    "#220a0a"
        flow_labels[sec].configure(
            text=f"{'ðŸ’° ' if sec == leader else ''}{sec}\n{val:+.2f}", fg=col, bg=bg
        )


def _update_guard_bar(guard_slbl, guard_elbl, guard_blbl,
                      sector_counts, total_exp, blocked_syms) -> None:
    cap     = get_max_per_sector()
    max_pct = get_atr_exposure() * 100
    acct    = get_account_size()
    for sec, count in sector_counts.items():
        if count >= cap:     col, bg = C.RED,    "#220a0a"
        elif count == cap-1: col, bg = C.YELLOW, "#1c1a08"
        elif count > 0:      col, bg = C.GREEN,  "#062016"
        else:                col, bg = C.MUTED,  C.BG3
        guard_slbl[sec].configure(text=f"{sec}\n{count}/{cap}", fg=col, bg=bg)
    pct = (total_exp / (acct + 1e-9)) * 100
    exp_col = C.RED if pct >= max_pct else (C.YELLOW if pct >= max_pct * 0.75 else C.GREEN)
    guard_elbl.configure(text=f"ATR Exp: {pct:.1f}% / {max_pct:.0f}%  (Ø­Ø³Ø§Ø¨: {acct:,.0f} Ø¬.Ù…)", fg=exp_col)
    if blocked_syms:
        guard_blbl.configure(text=f"ðŸ›¡ï¸ Blocked: {', '.join(blocked_syms)}", fg=C.RED)
    else:
        guard_blbl.configure(text="ðŸ›¡ï¸ Blocked: â€”", fg=C.MUTED)


def _update_regime_label(lbl: tk.Label, regime: str) -> None:
    icons = {
        "ACCUMULATION": ("ðŸ“¦ ACCUMULATION", C.CYAN),
        "MOMENTUM":     ("ðŸš€ MOMENTUM",      C.GREEN),
        "DISTRIBUTION": ("ðŸ“¤ DISTRIBUTION",  C.RED),
        "NEUTRAL":      ("ðŸ“Š NEUTRAL",        C.MUTED),
    }
    txt, col = icons.get(regime, ("ðŸ“Š NEUTRAL", C.MUTED))
    lbl.configure(text=txt, fg=col)


def _update_brain_label(lbl: tk.Label, mode: str) -> None:
    if mode == "aggressive":  lbl.configure(text="ðŸ§ ðŸ”¥ AGGRESSIVE", fg=C.GREEN)
    elif mode == "defensive": lbl.configure(text="ðŸ§ ðŸ›¡ï¸ DEFENSIVE",  fg=C.YELLOW)
    else:                     lbl.configure(text="ðŸ§  NEUTRAL",       fg=C.MUTED)


# â”€â”€ Tooltip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_tooltip_win: Optional[tk.Toplevel] = None


def _show_tooltip(event, tree: ttk.Treeview, cols: tuple) -> None:
    global _tooltip_win
    item = tree.identify_row(event.y)
    if not item:
        return
    raw_vals = tree.item(item, "values")
    if not raw_vals or len(raw_vals) < len(cols):
        return
    v = dict(zip(cols, raw_vals))
    tip = (
        f"  Symbol  : {v.get('Symbol','â€”')}  Sector: {v.get('Sector','â€”')}\n"
        f"  Price   : {v.get('Price','â€”')}  ADX: {v.get('ADX','â€”')}  RSI: {v.get('RSI','â€”')}\n"
        f"  CPI     : {v.get('ðŸ§ CPI','â€”')}  IET: {v.get('ðŸ›ï¸IET','â€”')}  Whale: {v.get('ðŸ³Whale','â€”')}\n"
        f"  Signal  : {v.get('Signal','â€”')}  Dir: {v.get('Direction','â€”')}\n"
        f"  Conf    : {v.get('Confidence%','â€”')}  Timeframe: {v.get('Timeframe','â€”')}\n"
        f"  Action  : {v.get('Action','â€”')}  Entry: {v.get('Entry','â€”')}  Stop: {v.get('Stop','â€”')}\n"
        f"  Target  : {v.get('Target','â€”')}  R:R: {v.get('R:R','â€”')}  WinRate: {v.get('WinRate%','â€”')}\n"
        f"  ATR Risk: {v.get('ATR Risk','â€”')}  VWAP%: {v.get('VWAP%','â€”')}\n"
        f"  Reason  : {v.get('Signal Reason','â€”')}\n"
        f"  ðŸ›¡ï¸Guard : {v.get('ðŸ›¡ï¸Guard','â€”')}"
    )
    _destroy_tooltip()
    tw = tk.Toplevel()
    tw.wm_overrideredirect(True)
    tw.wm_geometry(f"+{event.x_root+12}+{event.y_root+10}")
    tk.Label(tw, text=tip, justify="left", font=("Consolas", 9),
             bg="#1a2a3a", fg=C.CYAN, relief="flat", padx=8, pady=6,
             bd=1, highlightbackground=C.ACCENT, highlightthickness=1).pack()
    _tooltip_win = tw


def _destroy_tooltip(*_) -> None:
    global _tooltip_win
    if _tooltip_win:
        try:
            _tooltip_win.destroy()
        except tk.TclError:
            pass
        _tooltip_win = None


def export_csv(tree: ttk.Treeview, cols: tuple) -> None:
    rows = [tree.item(k)["values"] for k in tree.get_children("")]
    if not rows:
        messagebox.showwarning("Export", "No data to export!")
        return
    now  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        initialfile=f"EGX_Radar_v{__version__.replace('.', '')}_{now}.csv",
        filetypes=[("CSV files", "*.csv")],
        title="Save Radar Results",
    )
    if not path:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows([cols, *rows])
    messagebox.showinfo("Saved âœ…", f"File saved:\n{path}")


__all__ = [
    "_ui_q",
    "_enqueue",
    "_pump",
    "PulseController",
    "_pulse",
    "draw_gauge",
    "_update_heatmap",
    "_update_rotation_map",
    "_update_flow_map",
    "_update_guard_bar",
    "_update_regime_label",
    "_update_brain_label",
    "_show_tooltip",
    "_destroy_tooltip",
    "export_csv",
]
```

==================================================
FILE: egx_radar/ui/main_window.py
=================================

```python
"""Tkinter main window and layout wiring (Layer 10)."""

import logging
from typing import Dict

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from egx_radar.config.settings import (
    K,
    C,
    F_TITLE,
    F_HEADER,
    F_BODY,
    F_SMALL,
    F_MICRO,
    SECTORS,
    DATA_SOURCE_CFG,
    _data_cfg_lock,
    get_account_size,
)
from egx_radar.state.app_state import STATE
from egx_radar.ui.components import (
    _enqueue,
    _pump,
    _pulse,
    draw_gauge,
    _show_tooltip,
    _destroy_tooltip,
    export_csv,
)
from egx_radar.outcomes.engine import oe_load_log, oe_load_history
from egx_radar.data.fetchers import load_source_settings, save_source_settings
from egx_radar.backtest import open_backtest_window
from egx_radar import __version__

log = logging.getLogger(__name__)


def main() -> None:
    from egx_radar.scan.runner import start_scan, request_shutdown

    STATE.load()
    load_source_settings()

    root = tk.Tk()
    root.title(f"EGX Capital Flow Radar v{__version__} â€” Signal Quality Upgrade")
    root.geometry("2400x980")
    root.configure(bg=C.BG)

    # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    hdr = tk.Frame(root, bg=C.BG, pady=6)
    hdr.pack(fill="x", padx=16)
    tk.Label(hdr, text=f"âš¡ EGX CAPITAL FLOW RADAR v{__version__} ðŸ§²ðŸ§ ðŸ”®ðŸŽ¯ðŸ§­ðŸ””ðŸ›¡ï¸ðŸ“Š",
             font=F_TITLE, fg=C.ACCENT, bg=C.BG).pack(side="left")

    gauge_flow = tk.Canvas(hdr, width=160, height=110, bg=C.BG, highlightthickness=0)
    gauge_flow.pack(side="right", padx=(4, 8))
    gauge_rank = tk.Canvas(hdr, width=160, height=110, bg=C.BG, highlightthickness=0)
    gauge_rank.pack(side="right", padx=(4, 2))
    draw_gauge(gauge_rank, 0, K.SMART_RANK_SCALE, "SmartRank",  "waitingâ€¦")
    draw_gauge(gauge_flow, 0, 1.0,                "FutureFlow", "waitingâ€¦")

    scan_btn = tk.Button(hdr, text="ðŸš€ Gravity Scan [F5]",
                         font=F_HEADER, fg=C.BG, bg=C.ACCENT, relief="flat", padx=12, pady=4)
    scan_btn.pack(side="right", padx=4)

    force_refresh_var = tk.BooleanVar(value=False)
    tk.Checkbutton(hdr, text="Force Refresh", variable=force_refresh_var,
                   font=F_BODY, fg=C.MUTED, bg=C.BG, selectcolor=C.BG3,
                   activebackground=C.BG).pack(side="right", padx=8)

    # â”€â”€ Top bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    top_bar = tk.Frame(root, bg=C.BG, pady=4)
    top_bar.pack(fill="x", padx=16)
    tk.Label(top_bar, text="ðŸ”¥ Sector Flow:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 6))

    heat_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(top_bar, text=f"{sec}\nâ€”", width=15, height=2,
                       bg=C.BG3, fg=C.MUTED, font=("Consolas", 9, "bold"))
        lbl.pack(side="left", padx=3)
        heat_labels[sec] = lbl

    brain_lbl = tk.Label(top_bar, text="ðŸ§  NEUTRAL", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    brain_lbl.pack(side="right", padx=12)

    save_btn = tk.Button(top_bar, text="ðŸ’¾ Save CSV", font=F_HEADER,
                         fg=C.TEXT, bg=C.BG3, relief="flat", padx=8, pady=3)
    save_btn.pack(side="right", padx=6)

    # â”€â”€ Outcomes window â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def open_outcomes() -> None:
        win = tk.Toplevel(root)
        win.title("ðŸ“Š Trade Outcomes")
        win.configure(bg=C.BG)
        win.geometry("1100x660")

        stats_frm = tk.Frame(win, bg=C.BG, pady=6)
        stats_frm.pack(fill="x", padx=14)
        stats_lbl = tk.Label(stats_frm, text="Loadingâ€¦", font=F_HEADER, fg=C.ACCENT, bg=C.BG, anchor="w")
        stats_lbl.pack(side="left", fill="x", expand=True)

        nb   = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=14, pady=4)

        oc   = ("Symbol", "Sector", "Date", "Entry", "Stop", "Target", "ATR", "Rank", "Action")
        oc_w = (60, 90, 90, 70, 70, 70, 50, 60, 90)
        hc   = ("Symbol", "Sector", "Date", "Entry", "Exit", "Stop", "Target", "Status", "Days", "MFE%", "MAE%", "PnL%", "Rank")
        hc_w = (60, 90, 90, 70, 70, 70, 70, 72, 46, 60, 60, 60, 60)

        open_frm  = tk.Frame(nb, bg=C.BG); nb.add(open_frm, text="ðŸ”“ Open")
        open_tree = ttk.Treeview(open_frm, columns=oc, show="headings", height=18, style="Dark.Treeview")
        for col, w in zip(oc, oc_w):
            open_tree.heading(col, text=col); open_tree.column(col, width=w, anchor="center", stretch=False)
        vsb_o = ttk.Scrollbar(open_frm, orient="vertical", command=open_tree.yview)
        open_tree.configure(yscrollcommand=vsb_o.set); vsb_o.pack(side="right", fill="y")
        open_tree.pack(fill="both", expand=True)

        hist_frm  = tk.Frame(nb, bg=C.BG); nb.add(hist_frm, text="ðŸ“œ History")
        hist_tree = ttk.Treeview(hist_frm, columns=hc, show="headings", height=18, style="Dark.Treeview")
        for col, w in zip(hc, hc_w):
            hist_tree.heading(col, text=col); hist_tree.column(col, width=w, anchor="center", stretch=False)
        hist_tree.tag_configure("WIN",     background="#0a2218", foreground=C.GREEN)
        hist_tree.tag_configure("LOSS",    background="#220a0a", foreground=C.RED)
        hist_tree.tag_configure("TIMEOUT", background="#1c1a08", foreground=C.YELLOW)
        vsb_h = ttk.Scrollbar(hist_frm, orient="vertical", command=hist_tree.yview)
        hist_tree.configure(yscrollcommand=vsb_h.set); vsb_h.pack(side="right", fill="y")
        hist_tree.pack(fill="both", expand=True)

        def _refresh():
            ot = oe_load_log(); hist = oe_load_history()
            tot  = len(hist); w = sum(1 for t in hist if t.get("status") == "WIN")
            l    = sum(1 for t in hist if t.get("status") == "LOSS")
            to   = sum(1 for t in hist if t.get("status") == "TIMEOUT")
            wr   = (w / tot * 100) if tot else 0.0
            avmf = (sum(t.get("mfe_pct", 0) for t in hist) / tot) if tot else 0.0
            avma = (sum(t.get("mae_pct", 0) for t in hist) / tot) if tot else 0.0
            avpn = (sum(t.get("pnl_pct", 0) for t in hist) / tot) if tot else 0.0
            stats_lbl.configure(text=(
                f"ðŸ“Š Resolved:{tot}  âœ…W:{w}  âŒL:{l}  â±TO:{to}  "
                f"WR:{wr:.1f}%  MFE:{avmf:.1f}%  MAE:{avma:.1f}%  PnL:{avpn:.1f}%  Open:{len(ot)}"
            ))
            nb.tab(0, text=f"ðŸ”“ Open ({len(ot)})"); nb.tab(1, text=f"ðŸ“œ History ({tot})")
            open_tree.delete(*open_tree.get_children())
            for t in sorted(ot, key=lambda x: x.get("date", ""), reverse=True):
                open_tree.insert("", tk.END, values=(
                    t.get("sym","â€”"), t.get("sector","â€”"), t.get("date","â€”"),
                    f"{t.get('entry',0):.2f}", f"{t.get('stop',0):.2f}",
                    f"{t.get('target',0):.2f}", f"{t.get('atr',0):.2f}",
                    f"{t.get('smart_rank',0):.1f}", t.get("action","â€”"),
                ))
            hist_tree.delete(*hist_tree.get_children())
            for t in sorted(hist, key=lambda x: x.get("resolved_date",""), reverse=True):
                status = t.get("status","â€”")
                hist_tree.insert("", tk.END, values=(
                    t.get("sym","â€”"), t.get("sector","â€”"), t.get("date","â€”"),
                    f"{t.get('entry',0):.2f}", f"{t.get('exit_price',0):.2f}",
                    f"{t.get('stop',0):.2f}", f"{t.get('target',0):.2f}",
                    status, t.get("days_held","â€”"),
                    f"{t.get('mfe_pct',0):.1f}%", f"{t.get('mae_pct',0):.1f}%",
                    f"{t.get('pnl_pct',0):.1f}%", f"{t.get('smart_rank',0):.1f}",
                ), tags=(status,))

        tk.Button(stats_frm, text="ðŸ”„ Refresh", font=F_HEADER, fg=C.BG, bg=C.ACCENT,
                  relief="flat", padx=8, pady=2, command=_refresh).pack(side="right", padx=8)
        _refresh()

    outcomes_btn = tk.Button(top_bar, text="ðŸ“Š Outcomes", font=F_HEADER,
                              fg=C.BG, bg="#1a5276", relief="flat", padx=8, pady=3, command=open_outcomes)
    outcomes_btn.pack(side="right", padx=6)

    backtest_btn = tk.Button(top_bar, text="ðŸ“Š Backtest", font=F_HEADER,
                             fg=C.BG, bg="#1a5c4d", relief="flat", padx=8, pady=3,
                             command=lambda: open_backtest_window(root))
    backtest_btn.pack(side="right", padx=6)

    # â”€â”€ Capital calculator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def open_calc() -> None:
        rows_data = [tree.item(k)["values"] for k in tree.get_children("")]
        if not rows_data:
            messagebox.showwarning("Calc", "Run a scan first!")
            return
        win = tk.Toplevel(root)
        win.title("ðŸ’° Capital Calculator")
        win.geometry("680x520")
        win.configure(bg=C.BG)
        win.grab_set()
        tk.Label(win, text="ðŸ’° Position Size Calculator", font=F_TITLE, fg=C.GOLD, bg=C.BG).pack(pady=(12, 4))
        inp_frm = tk.Frame(win, bg=C.BG2, padx=16, pady=10)
        inp_frm.pack(fill="x", padx=16, pady=4)
        tk.Label(inp_frm, text="Account Size (EGP):", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).grid(row=0, column=0, sticky="e", padx=6)
        acct_var = tk.StringVar(value=str(int(K.ACCOUNT_SIZE)))
        tk.Entry(inp_frm, textvariable=acct_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=14).grid(row=0, column=1, padx=6)
        tk.Label(inp_frm, text="Risk per trade (%):", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).grid(row=0, column=2, sticky="e", padx=6)
        risk_var = tk.StringVar(value="2")
        tk.Entry(inp_frm, textvariable=risk_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=6).grid(row=0, column=3, padx=6)

        ctf = tk.Frame(win, bg=C.BG); ctf.pack(fill="both", expand=True, padx=16, pady=6)
        CCOLS = ("Symbol","Action","Entry","Stop","Target","Risk/Share","# Shares","Total Invest","Max Loss","Max Profit")
        ctree = ttk.Treeview(ctf, columns=CCOLS, show="headings", height=14)
        for c in CCOLS:
            ctree.heading(c, text=c); ctree.column(c, width=88 if c in ("Symbol","Action","Total Invest","Max Profit") else 68, anchor="center")
        cvsb = ttk.Scrollbar(ctf, orient="vertical", command=ctree.yview)
        ctree.configure(yscrollcommand=cvsb.set); cvsb.pack(side="right", fill="y"); ctree.pack(fill="both", expand=True)

        col_idx = {c: i for i, c in enumerate(COLS)}

        def recalc(*_):
            ctree.delete(*ctree.get_children())
            try:
                acct = float(acct_var.get().replace(",", ""))
                risk_pct = float(risk_var.get()) / 100.0
            except ValueError:
                return
            risk_amt = acct * risk_pct
            for row in rows_data:
                try:
                    sym    = row[col_idx["Symbol"]]
                    action = row[col_idx["Action"]]
                    entry  = float(row[col_idx["Entry"]])
                    stop   = float(row[col_idx["Stop"]])
                    target = float(row[col_idx["Target"]])
                except (IndexError, ValueError, KeyError):
                    continue
                rps   = max(abs(entry - stop), 0.01)
                shares = max(1, int(risk_amt / rps))
                ctree.insert("", tk.END, values=(
                    sym, action, f"{entry:.2f}", f"{stop:.2f}", f"{target:.2f}",
                    f"{rps:.2f}", shares, f"{shares*entry:,.0f}", f"{shares*rps:,.0f}", f"{shares*abs(target-entry):,.0f}",
                ))

        recalc()
        acct_var.trace_add("write", recalc)
        risk_var.trace_add("write", recalc)
        tk.Label(win, text="ðŸ’¡ Change account size or risk% â€” table updates live",
                 font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(pady=4)

    calc_btn = tk.Button(top_bar, text="ðŸ’° Calc", font=F_HEADER,
                          fg=C.BG, bg=C.GOLD, relief="flat", padx=8, pady=3, command=open_calc)
    calc_btn.pack(side="right", padx=6)

    # â”€â”€ Source settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def open_settings() -> None:
        win = tk.Toplevel(root)
        win.title("âš™ï¸ Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª")
        win.geometry("520x700")
        win.configure(bg=C.BG)
        win.grab_set()

        bottom_frm = tk.Frame(win, bg=C.BG)
        bottom_frm.pack(side="bottom", fill="x", pady=10)

        content_frm = tk.Frame(win, bg=C.BG)
        content_frm.pack(side="top", fill="both", expand=True)

        tk.Label(content_frm, text="âš™ï¸ Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª", font=F_TITLE, fg=C.ACCENT, bg=C.BG).pack(pady=(14, 4))

        nb = ttk.Notebook(content_frm)
        nb.pack(fill="both", expand=True, padx=12, pady=4)

        # â”€â”€ Tab 1: Account & Data Sources â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tab_main = tk.Frame(nb, bg=C.BG2); nb.add(tab_main, text="ðŸ“Š Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ø¹Ø§Ù…Ø©")

        # --- Section 1: Capital ---
        cap_frm = tk.LabelFrame(tab_main, text="ðŸ’° Ø±Ø£Ø³ Ø§Ù„Ù…Ø§Ù„ (Capital)", bg=C.BG2, fg=C.GOLD, font=F_HEADER, padx=10, pady=10)
        cap_frm.pack(fill="x", padx=10, pady=10)

        tk.Label(cap_frm, text="Ø­Ø¬Ù… Ø§Ù„Ø­Ø³Ø§Ø¨ (Ø¬.Ù…):", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).grid(row=0, column=0, sticky="w", pady=5)
        
        with _data_cfg_lock:
            _acct = float(DATA_SOURCE_CFG.get("account_size", K.ACCOUNT_SIZE))
            
        acct_var = tk.StringVar(value=f"{_acct:,.0f}")
        tk.Entry(cap_frm, textvariable=acct_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=16).grid(row=0, column=1, padx=10, pady=5)

        def _apply_capital():
            try:
                new_acct = float(acct_var.get().replace(",", ""))
                assert new_acct > 0
            except (ValueError, AssertionError):
                messagebox.showerror("Ø®Ø·Ø£", "Ù‚ÙŠÙ…Ø© ØºÙŠØ± ØµØ­ÙŠØ­Ø© ÙÙŠ Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ø­Ø³Ø§Ø¨.")
                return

            with _data_cfg_lock:
                DATA_SOURCE_CFG["account_size"] = new_acct

            save_source_settings()
            _refresh_account_badge()
            messagebox.showinfo("ØªÙ… Ø§Ù„Ø­ÙØ¸ âœ…", f"ØªÙ… ØªØ­Ø¯ÙŠØ« Ø±Ø£Ø³ Ø§Ù„Ù…Ø§Ù„ Ø¥Ù„Ù‰: {new_acct:,.0f} Ø¬.Ù…")

        tk.Button(cap_frm, text="Set Capital", font=F_BODY, fg=C.BG, bg=C.GOLD, relief="flat", padx=10, command=_apply_capital).grid(row=0, column=2, padx=10)

        # --- Section 2: Data Sources ---
        src_frm = tk.LabelFrame(tab_main, text="ðŸŒ Ù…ØµØ§Ø¯Ø± Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª (Data Sources)", bg=C.BG2, fg=C.CYAN, font=F_HEADER, padx=10, pady=10)
        src_frm.pack(fill="x", padx=10, pady=10)

        vars_map = {}
        for key, label, desc in [
            ("use_yahoo",        "âœ… Yahoo Finance", "Primary â€” 2yr history"),
            ("use_stooq",        "ðŸ“Š Stooq",         "Free, no key"),
            ("use_alpha_vantage","ðŸ”‘ Alpha Vantage",  "Requires free API key"),
            ("use_investing",    "ðŸŒ Investing.com",  "Price cross-check only"),
            ("use_twelve_data",  "ðŸ• Twelve Data",    "Best EGX coverage"),
        ]:
            with _data_cfg_lock:
                cur = bool(DATA_SOURCE_CFG.get(key, False))
            v = tk.BooleanVar(value=cur); vars_map[key] = v
            row = tk.Frame(src_frm, bg=C.BG2); row.pack(fill="x", pady=2)
            tk.Checkbutton(row, text=label, variable=v, font=F_BODY, fg=C.TEXT,
                           bg=C.BG2, selectcolor=C.BG3, activebackground=C.BG2).pack(side="left")
            tk.Label(row, text=desc, font=F_SMALL, fg=C.MUTED, bg=C.BG2).pack(side="left", padx=8)

        tk.Label(src_frm, text="ðŸ”‘ Alpha Vantage API Key:", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).pack(anchor="w", pady=(8,0))
        with _data_cfg_lock:
            cur_av = str(DATA_SOURCE_CFG.get("alpha_vantage_key", ""))
        av_var = tk.StringVar(value=cur_av)
        tk.Entry(src_frm, textvariable=av_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=38).pack(pady=4, fill="x")

        tk.Label(src_frm, text="ðŸ• Twelve Data API Key:", font=F_BODY, fg=C.GOLD, bg=C.BG2).pack(anchor="w", pady=(10,0))
        with _data_cfg_lock:
            cur_td = str(DATA_SOURCE_CFG.get("twelve_data_key", ""))
        td_var = tk.StringVar(value=cur_td)
        td_entry = tk.Entry(src_frm, textvariable=td_var, font=F_BODY, fg=C.TEXT, bg=C.BG3,
                            insertbackground=C.TEXT, width=38, show="*")
        td_entry.pack(pady=2, fill="x")

        def _apply_sources():
            with _data_cfg_lock:
                for k, v in vars_map.items():
                    DATA_SOURCE_CFG[k] = v.get()
                DATA_SOURCE_CFG["alpha_vantage_key"] = av_var.get().strip()
                DATA_SOURCE_CFG["twelve_data_key"]   = td_var.get().strip()
            
            save_source_settings()
            src_badge_var.set(_build_src_badge())
            messagebox.showinfo("ØªÙ… Ø§Ù„Ø­ÙØ¸ âœ…", "ØªÙ… ØªØ­Ø¯ÙŠØ« Ù…ØµØ§Ø¯Ø± Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª!")

        tk.Button(src_frm, text="Update Sources", font=F_BODY, fg=C.BG, bg=C.CYAN, relief="flat", padx=10, pady=5, command=_apply_sources).pack(pady=10)

        # â”€â”€ Tab 2: Advanced Risk â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tab_risk = tk.Frame(nb, bg=C.BG2); nb.add(tab_risk, text="âš ï¸ Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ù…Ø®Ø§Ø·Ø± (Ù…ØªÙ‚Ø¯Ù…)")
        frm_r = tk.Frame(tab_risk, bg=C.BG2, padx=20, pady=16); frm_r.pack(fill="x")

        def _lbl_entry(parent, row_i, label, var, desc="", fg=C.ACCENT2):
            tk.Label(parent, text=label, font=F_BODY, fg=fg, bg=C.BG2, anchor="w").grid(
                row=row_i, column=0, sticky="w", pady=5)
            e = tk.Entry(parent, textvariable=var, font=F_BODY, fg=C.TEXT,
                         bg=C.BG3, insertbackground=C.TEXT, width=16)
            e.grid(row=row_i, column=1, padx=10, pady=5, sticky="w")
            if desc:
                tk.Label(parent, text=desc, font=F_SMALL, fg=C.MUTED, bg=C.BG2, anchor="w").grid(
                    row=row_i, column=2, sticky="w", padx=4)
            return e

        with _data_cfg_lock:
            _risk = float(DATA_SOURCE_CFG.get("risk_per_trade", K.RISK_PER_TRADE))
            _exp  = float(DATA_SOURCE_CFG.get("portfolio_max_atr_exposure", K.PORTFOLIO_MAX_ATR_EXPOSURE))
            _mps  = int(DATA_SOURCE_CFG.get("portfolio_max_per_sector", K.PORTFOLIO_MAX_PER_SECTOR))

        risk_var = tk.StringVar(value=f"{_risk*100:.1f}")
        exp_var  = tk.StringVar(value=f"{_exp*100:.1f}")
        mps_var  = tk.StringVar(value=str(_mps))

        _lbl_entry(frm_r, 0, "âš ï¸ Ù†Ø³Ø¨Ø© Ø§Ù„Ù…Ø®Ø§Ø·Ø±Ø© Ù„ÙƒÙ„ ØµÙÙ‚Ø© %:", risk_var,
                   "Ø§Ù„Ø§ÙØªØ±Ø§Ø¶ÙŠ 2% (Ù†ØµÙŠØ­Ø©: 1-3%)")
        _lbl_entry(frm_r, 1, "ðŸ›¡ï¸ Ø­Ø¯ ATR Exposure %:", exp_var,
                   "Ø§Ù„Ø§ÙØªØ±Ø§Ø¶ÙŠ 4% â€” Ø±ÙØ¹Ù‡ ÙŠØ³Ù…Ø­ Ø¨Ø¥Ø´Ø§Ø±Ø§Øª Ø£ÙƒØ«Ø±")
        _lbl_entry(frm_r, 2, "ðŸ“Š Ø£Ù‚ØµÙ‰ Ø£Ø³Ù‡Ù… Ù„ÙƒÙ„ Ù‚Ø·Ø§Ø¹:", mps_var,
                   "Ø§Ù„Ø§ÙØªØ±Ø§Ø¶ÙŠ 2")

        def _apply_risk():
            try:
                new_risk = float(risk_var.get()) / 100
                new_exp  = float(exp_var.get()) / 100
                new_mps  = int(mps_var.get())
                assert 0 < new_risk <= 0.5 and 0 < new_exp <= 0.5 and new_mps >= 1
            except (ValueError, AssertionError):
                messagebox.showerror("Ø®Ø·Ø£", "Ù‚ÙŠÙ…Ø© ØºÙŠØ± ØµØ­ÙŠØ­Ø© ÙÙŠ Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ù…Ø®Ø§Ø·Ø±.")
                return

            with _data_cfg_lock:
                DATA_SOURCE_CFG["risk_per_trade"]             = new_risk
                DATA_SOURCE_CFG["portfolio_max_atr_exposure"] = new_exp
                DATA_SOURCE_CFG["portfolio_max_per_sector"]   = new_mps
            
            save_source_settings()
            messagebox.showinfo("ØªÙ… Ø§Ù„Ø­ÙØ¸ âœ…", "ØªÙ… ØªØ­Ø¯ÙŠØ« Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ù…Ø®Ø§Ø·Ø± Ø§Ù„Ù…ØªÙ‚Ø¯Ù…Ø©!")

        tk.Button(frm_r, text="Update Risk Settings", font=F_BODY, fg=C.BG, bg=C.ACCENT, relief="flat", padx=10, pady=5, command=_apply_risk).grid(row=3, column=0, columnspan=3, pady=10)


        tk.Button(bottom_frm, text="ðŸšª Ø¥ØºÙ„Ø§Ù‚ Ù†Ø§ÙØ°Ø© Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª (Close)", font=F_HEADER, fg=C.TEXT, bg=C.BG3,
                  relief="flat", padx=14, pady=7, command=win.destroy).pack()

    def _build_src_badge() -> str:
        with _data_cfg_lock:
            parts = []
            if DATA_SOURCE_CFG.get("use_yahoo"):         parts.append("Yahoo")
            if DATA_SOURCE_CFG.get("use_stooq"):         parts.append("Stooq")
            if DATA_SOURCE_CFG.get("use_alpha_vantage"): parts.append("AV")
            if DATA_SOURCE_CFG.get("use_investing"):     parts.append("INV")
            if DATA_SOURCE_CFG.get("use_twelve_data"):   parts.append("TDðŸ•")
        return "ðŸŒ " + "+".join(parts) if parts else "ðŸŒ Yahoo"

    src_badge_var = tk.StringVar(value=_build_src_badge())
    tk.Label(top_bar, textvariable=src_badge_var, font=F_SMALL, fg=C.CYAN, bg=C.BG).pack(side="right", padx=4)
    tk.Button(
        top_bar,
        text="âš™ï¸ Sources",
        font=("Segoe UI", 11, "bold"),
        fg="#ffffff",
        bg="#0b6a9c",
        activeforeground="#ffffff",
        activebackground="#1580b8",
        relief="flat",
        padx=12,
        pady=5,
        command=open_settings,
    ).pack(side="right", padx=4)

    # â”€â”€ Account badge (live) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    acct_badge_var = tk.StringVar(value=f"ðŸ’¼ {get_account_size():,.0f} Ø¬.Ù…")
    tk.Label(top_bar, textvariable=acct_badge_var, font=F_SMALL, fg=C.GOLD, bg=C.BG).pack(side="right", padx=6)

    def _refresh_account_badge():
        acct_badge_var.set(f"ðŸ’¼ {get_account_size():,.0f} Ø¬.Ù…")

    # â”€â”€ Market Health Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    health_bar = tk.Frame(root, bg="#0d1b2a", pady=4)
    health_bar.pack(fill="x", padx=16, pady=(4, 0))
    
    tk.Label(health_bar, text="ðŸ“ˆ Market Health:", font=F_HEADER, fg=C.CYAN, bg="#0d1b2a").pack(side="left", padx=(6, 12))
    
    health_lbl = tk.Label(health_bar, text="Label: â€”", font=("Segoe UI", 10, "bold"), fg=C.MUTED, bg="#0d1b2a")
    health_lbl.pack(side="left", padx=8)

    health_avg_var = tk.StringVar(value="Avg Rank: 0.0")
    tk.Label(health_bar, textvariable=health_avg_var, font=F_BODY, fg=C.WHITE, bg="#0d1b2a").pack(side="left", padx=8)

    health_act_var = tk.StringVar(value="Actionable (>=65): 0")
    tk.Label(health_bar, textvariable=health_act_var, font=F_BODY, fg=C.GREEN, bg="#0d1b2a").pack(side="left", padx=8)

    health_elite_var = tk.StringVar(value="Elite (>=75): 0")
    tk.Label(health_bar, textvariable=health_elite_var, font=F_BODY, fg=C.CYAN, bg="#0d1b2a").pack(side="left", padx=8)

    health_sell_var = tk.StringVar(value="SELL Signals: 0")
    tk.Label(health_bar, textvariable=health_sell_var, font=F_BODY, fg=C.RED, bg="#0d1b2a").pack(side="left", padx=8)

    verdict_frm = tk.Frame(root, bg="#06131f", pady=5)
    verdict_frm.pack(fill="x", padx=16, pady=(4, 0))
    verdict_var = tk.StringVar(value="ðŸ§  Awaiting scanâ€¦")
    verdict_lbl_w = tk.Label(verdict_frm, textvariable=verdict_var,
                              font=("Consolas", 11, "bold"), fg=C.ACCENT2, bg="#06131f", anchor="w")
    verdict_lbl_w.pack(fill="x", padx=10)

    # â”€â”€ Rotation + flow + guard bars â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    rot_bar = tk.Frame(root, bg=C.BG, pady=3)
    rot_bar.pack(fill="x", padx=16)
    tk.Label(rot_bar, text="ðŸ”® Rotation:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    rot_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(rot_bar, text=f"{sec}\nâ€”", width=15, height=2, bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); rot_labels[sec] = lbl

    flow_bar = tk.Frame(root, bg=C.BG, pady=3)
    flow_bar.pack(fill="x", padx=16)
    tk.Label(flow_bar, text="ðŸ§­ Î”Flow:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    flow_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(flow_bar, text=f"{sec}\nâ€”", width=15, height=2, bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); flow_labels[sec] = lbl
    regime_lbl = tk.Label(flow_bar, text="ðŸ“Š NEUTRAL", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    regime_lbl.pack(side="right", padx=12)

    guard_bar = tk.Frame(root, bg=C.BG, pady=3)
    guard_bar.pack(fill="x", padx=16)
    tk.Label(guard_bar, text="ðŸ›¡ï¸ Guard:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    guard_sector_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(guard_bar, text=f"{sec}\n0/{K.PORTFOLIO_MAX_PER_SECTOR}", width=15, height=2,
                       bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); guard_sector_labels[sec] = lbl
    guard_exposure_lbl = tk.Label(guard_bar, text="ATR Exp: 0.0%", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    guard_exposure_lbl.pack(side="right", padx=12)
    guard_blocked_lbl = tk.Label(guard_bar, text="ðŸ›¡ï¸ Blocked: â€”", font=F_SMALL, fg=C.MUTED, bg=C.BG)
    guard_blocked_lbl.pack(side="right", padx=8)

    # â”€â”€ Progress + status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    pbar = ttk.Progressbar(root, orient="horizontal", mode="determinate")
    pbar.pack(fill="x", padx=16, pady=4)
    status_var = tk.StringVar(value="Ready âœ… â€” Press ðŸš€ Gravity Scan or F5")
    tk.Label(root, textvariable=status_var, font=F_SMALL, fg=C.MUTED, bg=C.BG, anchor="w", pady=2).pack(fill="x", padx=20)

    # â”€â”€ Results table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tf = tk.Frame(root, bg=C.BG)
    tf.pack(fill="both", expand=True, padx=16, pady=4)

    global COLS
    COLS = (
        "Symbol", "Sector", "Price", "ADX", "RSI", "AdaptMom",
        "% EMA200", "Volume", "Tech%", "Gravity", "Zone",
        "ðŸ”®Future", "ðŸ§ CPI", "ðŸ›ï¸IET", "ðŸ³Whale",
        "Phase/Signals", "Signal", "Direction", "Confidence%", "SmartRank",
        "Action", "Timeframe", "Entry", "Stop", "Target", "Size", "WinRate%",
        "R:R", "ðŸ”¥InstConf", "ATR Risk", "Trend", "ATR", "VWAP%", "VolZ",
        "Signal Reason", "ðŸ›¡ï¸Guard",
    )
    col_w = {
        "Symbol": 50, "Sector": 88, "Price": 64, "ADX": 48, "RSI": 46,
        "AdaptMom": 68, "% EMA200": 72, "Volume": 60, "Tech%": 46,
        "Gravity": 100, "Zone": 70, "ðŸ”®Future": 68,
        "ðŸ§ CPI": 58, "ðŸ›ï¸IET": 58, "ðŸ³Whale": 62,
        "Phase/Signals": 215, "Signal": 155, "Direction": 82,
        "Confidence%": 74, "SmartRank": 80,
        "Action": 100, "Timeframe": 110, "Entry": 65, "Stop": 65, "Target": 65,
        "Size": 52, "WinRate%": 68, "R:R": 58, "ðŸ”¥InstConf": 90,
        "ATR Risk": 72, "Trend": 40, "ATR": 60, "VWAP%": 65, "VolZ": 55,
        "Signal Reason": 220, "ðŸ›¡ï¸Guard": 260,
    }

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background=C.BG2, foreground=C.TEXT,
                    rowheight=27, font=F_BODY, fieldbackground=C.BG2, borderwidth=0)
    style.configure("Treeview.Heading", background=C.BG3, foreground=C.MUTED,
                    font=F_HEADER, relief="flat")
    style.map("Treeview", background=[("selected", C.ROW_SEL)], foreground=[("selected", C.WHITE)])
    # FIX: Dark.Treeview used in Outcomes window but was never defined; inherit from Treeview
    style.configure("Dark.Treeview", background=C.BG2, foreground=C.TEXT,
                    rowheight=25, font=F_BODY, fieldbackground=C.BG2, borderwidth=0)
    style.configure("Dark.Treeview.Heading", background=C.BG3, foreground=C.MUTED,
                    font=F_SMALL, relief="flat")
    style.map("Dark.Treeview", background=[("selected", C.ROW_SEL)], foreground=[("selected", C.WHITE)])

    tree = ttk.Treeview(tf, columns=COLS, show="headings", height=18)
    for c in COLS:
        tree.heading(c, text=c)
        tree.column(c, width=col_w.get(c, 70), anchor="center", minwidth=40)

    for tag_name, (bg, fg) in {
        "ultra":     ("#071c2b", C.CYAN),
        "early":     ("#0a1f33", C.CYAN),
        "buy":       ("#0a2218", C.GREEN),
        "watch":     ("#1c1a08", C.YELLOW),
        "sell":      ("#220a0a", C.RED),
        "radar":     ("#0f1a26", C.ACCENT2),
        "accum_top": ("#2a1e00", C.GOLD),
        "blocked":   ("#1a1a2e", C.MUTED),
    }.items():
        tree.tag_configure(tag_name, background=bg, foreground=fg)

    vsb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    tree.bind("<Motion>",   lambda e: _show_tooltip(e, tree, COLS))
    tree.bind("<Leave>",    _destroy_tooltip)
    tree.bind("<Button-1>", _destroy_tooltip)

    # â”€â”€ Legend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    leg = tk.Frame(root, bg=C.BG, pady=3)
    leg.pack(fill="x", padx=20)
    for txt, col in [
        ("ðŸ§  ULTRA", C.CYAN), ("ðŸš€ EARLY", C.CYAN), ("ðŸ”¥ BUY", C.GREEN),
        ("ðŸ‘€ WATCH", C.YELLOW), ("âŒ SELL", C.RED),
        ("ðŸ§¬ Silent", C.ACCENT2), ("ðŸ³ Whale", C.PURPLE), ("ðŸŽ¯ Hunter", C.YELLOW),
        ("ðŸ’¥ Break", "#ff9f43"), ("âš¡ Exp", C.CYAN), ("ðŸ§¿ Quantum", C.PURPLE),
        ("â˜ ï¸ Fake", C.RED), ("ðŸ‘‘ Leader", C.YELLOW), ("ðŸ§² Gravity", C.CYAN),
        ("ACCUMULATE", C.GOLD), ("PROBE", C.YELLOW), ("ðŸ”” EMAâœš", C.GREEN),
        ("ðŸ”€ VolDiv", C.YELLOW), ("|  âš ï¸OB WATCH", C.YELLOW),
        ("|  âš ï¸ATR HIGH", C.RED), ("|  ðŸŸ¡ATR MED", C.YELLOW),
        ("â³ WAIT(ADX)", C.MUTED), ("|  ðŸ›¡ï¸BLOCKED", C.MUTED),
        ("|  âš¡Flow>Tech", C.YELLOW), ("|  ðŸ”’RankCap", C.MUTED),
        ("|  âŒ›WR-Build", C.MUTED), ("|  v78âœ…", C.GREEN),
    ]:
        tk.Label(leg, text=txt, font=F_MICRO, fg=col, bg=C.BG, padx=4).pack(side="left")

    tk.Label(root, text="âš ï¸  Data delayed 15 minutes â€” execution risk warning",
             fg=C.RED_DIM, bg=C.BG, font=F_MICRO).pack(side="bottom", pady=2)

    # â”€â”€ Wire up â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    widgets = {
        "tree": tree, "pbar": pbar, "status_var": status_var,
        "gauge_rank": gauge_rank, "gauge_flow": gauge_flow,
        "heat_labels": heat_labels, "rot_labels": rot_labels,
        "flow_labels": flow_labels, "regime_lbl": regime_lbl,
        "brain_lbl": brain_lbl, "verdict_var": verdict_var,
        "verdict_frm": verdict_frm, "verdict_lbl_w": verdict_lbl_w,
        "scan_btn": scan_btn,
        "guard_sector_labels": guard_sector_labels,
        "guard_exposure_lbl":  guard_exposure_lbl,
        "guard_blocked_lbl":   guard_blocked_lbl,
        "health_lbl":          health_lbl,
        "health_avg_var":      health_avg_var,
        "health_act_var":      health_act_var,
        "health_elite_var":    health_elite_var,
        "health_sell_var":     health_sell_var,
        "force_refresh_var":   force_refresh_var,
    }
    scan_btn.configure(command=lambda: start_scan(widgets))
    save_btn.configure(command=lambda: export_csv(tree, COLS))
    root.bind("<F5>", lambda _: start_scan(widgets))

    def _on_close():
        request_shutdown()
        _pulse.stop()
        STATE.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    _pump(root)
    root.mainloop()


__all__ = ["main"]
```

==================================================
FILE: egx_radar/advanced/__init__.py
====================================

```python
"""Advanced features: ML predictions, options, risk management, portfolio optimization."""

from egx_radar.advanced.ml_predictor import (
    MLPricePredictor,
    EnsemblePredictor,
    get_ensemble_predictor
)

from egx_radar.advanced.options import (
    OptionType,
    OptionStrategy,
    BlackScholesCalculator,
    OptionsPortfolio,
    GreeksData,
    get_options_calculator
)

from egx_radar.advanced.risk_management import (
    RiskManager,
    RiskMetrics,
    PositionSizer,
    get_risk_manager
)

from egx_radar.advanced.portfolio_optimization import (
    PortfolioOptimizer,
    OptimalAllocation,
    get_portfolio_optimizer
)

__all__ = [
    # ML Predictor
    'MLPricePredictor',
    'EnsemblePredictor',
    'get_ensemble_predictor',
    
    # Options
    'OptionType',
    'OptionStrategy',
    'BlackScholesCalculator',
    'OptionsPortfolio',
    'GreeksData',
    'get_options_calculator',
    
    # Risk Management
    'RiskManager',
    'RiskMetrics',
    'PositionSizer',
    'get_risk_manager',
    
    # Portfolio Optimization
    'PortfolioOptimizer',
    'OptimalAllocation',
    'get_portfolio_optimizer',
]
```

==================================================
FILE: egx_radar/advanced/ml_predictor.py
========================================

```python
"""Machine learning predictions for price movements."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pickle
from pathlib import Path


class MLPricePredictor:
    """Machine learning-based price movement predictor."""
    
    def __init__(self, model_type: str = 'gradient_boost'):
        """Initialize ML predictor.
        
        Args:
            model_type: Type of model ('random_forest', 'gradient_boost', 'svm', 'logistic')
        """
        self.model_type = model_type
        self.model = self._create_model()
        self.scaler = StandardScaler()
        self.feature_names = [
            'rsi', 'macd', 'bb_position', 'momentum',
            'sma_5_10_crossover', 'volume_ratio', 'volatility'
        ]
        self.is_trained = False
    
    def _create_model(self):
        """Create ML model based on type."""
        if self.model_type == 'random_forest':
            return RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        elif self.model_type == 'gradient_boost':
            return GradientBoostingClassifier(n_estimators=100, random_state=42)
        elif self.model_type == 'svm':
            return SVC(kernel='rbf', probability=True, random_state=42)
        else:  # logistic
            return LogisticRegression(random_state=42, max_iter=1000)
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features from OHLCV data.
        
        Args:
            data: OHLCV dataframe
            
        Returns:
            Dataframe with calculated features
        """
        features = pd.DataFrame(index=data.index)
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = data['Close'].ewm(span=12).mean()
        ema_26 = data['Close'].ewm(span=26).mean()
        features['macd'] = ema_12 - ema_26
        
        # Bollinger Bands position
        sma = data['Close'].rolling(20).mean()
        std = data['Close'].rolling(20).std()
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        band_range = upper - lower
        features['bb_position'] = 2 * (data['Close'] - lower) / band_range - 1
        
        # Momentum
        features['momentum'] = (data['Close'] - data['Close'].shift(10)) / data['Close'].shift(10) * 100
        
        # SMA crossover
        sma_5 = data['Close'].rolling(5).mean()
        sma_10 = data['Close'].rolling(10).mean()
        features['sma_5_10_crossover'] = (sma_5 > sma_10).astype(float)
        
        # Volume ratio
        features['volume_ratio'] = data['Volume'] / data['Volume'].rolling(20).mean()
        
        # Volatility (rolling std of returns)
        returns = data['Close'].pct_change()
        features['volatility'] = returns.rolling(20).std() * 100
        
        return features.dropna()
    
    def train(self, data: pd.DataFrame, lookahead_days: int = 5) -> None:
        """Train the ML model.
        
        Args:
            data: OHLCV dataframe
            lookahead_days: Days ahead to predict
        """
        # Extract features
        features = self.extract_features(data).copy()
        
        # Create target: 1 if price goes up, 0 if down
        target = (data['Close'].shift(-lookahead_days) > data['Close']).astype(int)
        target = target[features.index]
        
        # Align
        common_index = features.index.intersection(target.index)
        X = features.loc[common_index]
        y = target.loc[common_index]
        
        if len(X) < 20:
            print("Not enough data to train")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # Calculate accuracy
        accuracy = self.model.score(X_scaled, y)
        print(f"{self.model_type} model trained. Accuracy: {accuracy:.2%}")
    
    def predict(self, data: pd.DataFrame) -> Optional[Dict]:
        """Predict price movement for the next period.
        
        Args:
            data: OHLCV dataframe
            
        Returns:
            Prediction dict with probabilities and signals
        """
        if not self.is_trained:
            return None
        
        features = self.extract_features(data).copy()
        if features.empty:
            return None
        
        # Get latest features
        latest_features = features.iloc[-1:].copy()
        
        # Scale
        X_scaled = self.scaler.transform(latest_features)
        
        # Predict
        prediction = self.model.predict(X_scaled)[0]
        
        # Get probabilities
        try:
            probabilities = self.model.predict_proba(X_scaled)[0]
            prob_down = float(probabilities[0])
            prob_up = float(probabilities[1])
        except:
            prob_down = 0.5
            prob_up = 0.5
        
        # Determine signal
        if prob_up > 0.65:
            signal = 'strong_buy'
        elif prob_up > 0.55:
            signal = 'buy'
        elif prob_down > 0.65:
            signal = 'strong_sell'
        elif prob_down > 0.55:
            signal = 'sell'
        else:
            signal = 'hold'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'prob_up': prob_up,
            'prob_down': prob_down,
            'confidence': max(prob_up, prob_down),
            'prediction': 'up' if prediction == 1 else 'down',
            'model_type': self.model_type,
            'latest_features': latest_features.to_dict(orient='records')[0]
        }
    
    def save_model(self, filepath: str) -> None:
        """Save trained model to file.
        
        Args:
            filepath: Path to save model
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained,
                'model_type': self.model_type,
                'feature_names': self.feature_names
            }, f)
    
    def load_model(self, filepath: str) -> None:
        """Load trained model from file.
        
        Args:
            filepath: Path to model file
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_trained = data['is_trained']
            self.model_type = data['model_type']
            self.feature_names = data['feature_names']


class EnsemblePredictor:
    """Ensemble of multiple ML models for robust predictions."""
    
    def __init__(self, models: Optional[List[str]] = None):
        """Initialize ensemble.
        
        Args:
            models: List of model types to include
        """
        if models is None:
            models = ['gradient_boost', 'random_forest', 'svm']
        
        self.predictors = {
            name: MLPricePredictor(model_type=name)
            for name in models
        }
    
    def train(self, data: pd.DataFrame, lookahead_days: int = 5) -> None:
        """Train all models.
        
        Args:
            data: OHLCV dataframe
            lookahead_days: Days ahead to predict
        """
        for name, predictor in self.predictors.items():
            print(f"Training {name}...")
            predictor.train(data, lookahead_days=lookahead_days)
    
    def predict(self, data: pd.DataFrame) -> Dict:
        """Get ensemble prediction.
        
        Args:
            data: OHLCV dataframe
            
        Returns:
            Ensemble prediction
        """
        predictions = {}
        valid_predictions = []
        
        for name, predictor in self.predictors.items():
            pred = predictor.predict(data)
            if pred:
                predictions[name] = pred
                valid_predictions.append(pred)
        
        if not valid_predictions:
            return {}
        
        # Average probabilities
        avg_prob_up = np.mean([p['prob_up'] for p in valid_predictions])
        avg_prob_down = np.mean([p['prob_down'] for p in valid_predictions])
        
        # Determine ensemble signal
        if avg_prob_up > 0.65:
            signal = 'strong_buy'
        elif avg_prob_up > 0.55:
            signal = 'buy'
        elif avg_prob_down > 0.65:
            signal = 'strong_sell'
        elif avg_prob_down > 0.55:
            signal = 'sell'
        else:
            signal = 'hold'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'prob_up': float(avg_prob_up),
            'prob_down': float(avg_prob_down),
            'confidence': float(max(avg_prob_up, avg_prob_down)),
            'model_count': len(valid_predictions),
            'individual_predictions': predictions,
            'model_agreement': self._calculate_agreement(valid_predictions)
        }
    
    @staticmethod
    def _calculate_agreement(predictions: List[Dict]) -> float:
        """Calculate how much models agree (0-1).
        
        Args:
            predictions: List of predictions
            
        Returns:
            Agreement score
        """
        if not predictions:
            return 0.0
        
        signals = [p['signal'].replace('_', '') for p in predictions]
        most_common = max(set(signals), key=signals.count)
        agreement = signals.count(most_common) / len(signals)
        return float(agreement)


# Global instance
_ensemble_predictor: Optional[EnsemblePredictor] = None


def get_ensemble_predictor() -> EnsemblePredictor:
    """Get or create global ensemble predictor."""
    global _ensemble_predictor
    if _ensemble_predictor is None:
        _ensemble_predictor = EnsemblePredictor()
    return _ensemble_predictor
```

==================================================
FILE: egx_radar/advanced/options.py
===================================

```python
"""Options trading strategies and Greeks calculation."""

import numpy as np
from scipy.stats import norm
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum


class OptionType(str, Enum):
    """Option types."""
    CALL = "call"
    PUT = "put"


class OptionStrategy(str, Enum):
    """Predefined strategies."""
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    STRADDLE = "straddle"
    STRANGLE = "strangle"


@dataclass
class GreeksData:
    """Option Greeks data."""
    delta: float  # Price sensitivity
    gamma: float  # Delta sensitivity  
    vega: float   # Volatility sensitivity
    theta: float  # Time decay
    rho: float    # Interest rate sensitivity


class BlackScholesCalculator:
    """Black-Scholes option pricing calculator."""
    
    @staticmethod
    def calculate_price(
        S: float,  # Current  stock price
        K: float,  # Strike price
        T: float,  # Time to expiration (years)
        r: float,  # Risk-free rate
        sigma: float,  # Volatility
        option_type: OptionType = OptionType.CALL
    ) -> float:
        """Calculate option price using Black-Scholes.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration
            r: Risk-free rate
            sigma: Volatility
            option_type: Call or Put
            
        Returns:
            Option price
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == OptionType.CALL:
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # PUT
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return float(price)
    
    @staticmethod
    def calculate_greeks(
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: OptionType = OptionType.CALL
    ) -> GreeksData:
        """Calculate option Greeks.
        
        Args:
            S, K, T, r, sigma: See calculate_price
            option_type: Call or Put
            
        Returns:
            GreeksData with all Greeks
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if option_type == OptionType.CALL:
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        # Gamma (same for both)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Vega (same for both)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% change in volatility
        
        # Theta  
        sqrt_T = np.sqrt(T)
        if option_type == OptionType.CALL:
            theta = (-S * norm.pdf(d1) * sigma / (2 * sqrt_T) -
                     r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (-S * norm.pdf(d1) * sigma / (2 * sqrt_T) +
                     r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        # Rho
        if option_type == OptionType.CALL:
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100  # Per 1% change
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        return GreeksData(
            delta=float(delta),
            gamma=float(gamma),
            vega=float(vega),
            theta=float(theta),
            rho=float(rho)
        )


class OptionsPortfolio:
    """Portfolio of options positions."""
    
    @dataclass
    class Position:
        """Single option position."""
        symbol: str
        option_type: OptionType
        strike: float
        expiration: datetime
        quantity: int  # Positive for long, negative for short
        entry_price: float
    
    def __init__(self):
        """Initialize empty portfolio."""
        self.positions: List['OptionsPortfolio.Position'] = []
    
    def add_position(
        self,
        symbol: str,
        option_type: OptionType,
        strike: float,
        expiration: datetime,
        quantity: int,
        entry_price: float
    ) -> None:
        """Add position to portfolio.
        
        Args:
            symbol: Stock symbol
            option_type: Call or Put
            strike: Strike price
            expiration: Expiration date
            quantity: Position size (positive=long, negative=short)
            entry_price: Entry price
        """
        position = self.Position(
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiration=expiration,
            quantity=quantity,
            entry_price=entry_price
        )
        self.positions.append(position)
    
    def calculate_portfolio_greeks(
        self,
        stock_prices: Dict[str, float],
        vol: Dict[str, float],
        r: float = 0.05
    ) -> Dict[str, float]:
        """Calculate aggregate Greeks for portfolio.
        
        Args:
            stock_prices: Current prices by symbol
            vol: Volatilities by symbol
            r: Risk-free rate
            
        Returns:
            Aggregate Greeks
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_vega = 0.0
        total_theta = 0.0
        total_rho = 0.0
        
        calculator = BlackScholesCalculator()
        
        for pos in self.positions:
            S = stock_prices.get(pos.symbol)
            sigma = vol.get(pos.symbol, 0.25)
            
            if S is None:
                continue
            
            T = (pos.expiration - datetime.now()).days / 365
            if T <= 0:
                continue
            
            greeks = calculator.calculate_greeks(S, pos.strike, T, r, sigma, pos.option_type)
            
            total_delta += greeks.delta * pos.quantity
            total_gamma += greeks.gamma * pos.quantity
            total_vega += greeks.vega * pos.quantity
            total_theta += greeks.theta * pos.quantity
            total_rho += greeks.rho * pos.quantity
        
        return {
            'delta': float(total_delta),
            'gamma': float(total_gamma),
            'vega': float(total_vega),
            'theta': float(total_theta),
            'rho': float(total_rho)
        }
    
    def calculate_portfolio_value(
        self,
        stock_prices: Dict[str, float],
        vol: Dict[str, float],
        r: float = 0.05
    ) -> float:
        """Calculate total portfolio value.
        
        Args:
            stock_prices: Current prices by symbol
            vol: Volatilities by symbol
            r: Risk-free rate
            
        Returns:
            Total portfolio price
        """
        total_value = 0.0
        calculator = BlackScholesCalculator()
        
        for pos in self.positions:
            S = stock_prices.get(pos.symbol)
            sigma = vol.get(pos.symbol, 0.25)
            
            if S is None:
                continue
            
            T = (pos.expiration - datetime.now()).days / 365
            if T <= 0:
                continue
            
            option_price = calculator.calculate_price(
                S, pos.strike, T, r, sigma, pos.option_type
            )
            
            # Add to total (negative quantity = short, subtracts)
            total_value += option_price * pos.quantity
        
        return float(total_value)
    
    def max_profit(self, stock_prices: Dict[str, float]) -> float:
        """Calculate maximum profit from strategy.
        
        Args:
            stock_prices: Current stock prices
            
        Returns:
            Max profit
        """
        # Simplified: assume positions expire at strike
        max_profit = 0.0
        
        for pos in self.positions:
            S = stock_prices.get(pos.symbol, 0)
            
            if pos.option_type == OptionType.CALL:
                if pos.quantity > 0:  # Long call
                    intrinsic = max(0, S - pos.strike)
                else:  # Short call
                    intrinsic = max(0, pos.strike - S)
            else:  # PUT
                if pos.quantity > 0:  # Long put
                    intrinsic = max(0, pos.strike - S)
                else:  # Short put
                    intrinsic = max(0, S - pos.strike)
            
            max_profit += (intrinsic - pos.entry_price) * abs(pos.quantity)
        
        return float(max_profit)
    
    def max_loss(self, stock_prices: Dict[str, float]) -> float:
        """Calculate maximum loss from strategy.
        
        Args:
            stock_prices: Current stock prices
            
        Returns:
            Max loss (negative value)
        """
        max_loss = 0.0
        
        for pos in self.positions:
            if pos.quantity > 0:  # Long position
                # Max loss is the entry price
                max_loss -= pos.entry_price * abs(pos.quantity)
            else:  # Short position
                # Max loss is unlimited for short calls, limited for short puts
                if pos.option_type == OptionType.PUT:
                    max_loss -= pos.strike * abs(pos.quantity)
        
        return float(max_loss)
    
    def break_even_points(self) -> List[Tuple[str, float]]:
        """ Calculate break-even points for positions.
        
        Returns:
            List of (symbol, break_even_price) tuples
        """
        break_even_points = []
        
        for pos in self.positions:
            if pos.option_type == OptionType.CALL:
                be = pos.strike + pos.entry_price
            else:  # PUT
                be = pos.strike - pos.entry_price
            
            break_even_points.append((pos.symbol, be))
        
        return break_even_points


# Global instance
_options_calculator: Optional[BlackScholesCalculator] = None


def get_options_calculator() -> BlackScholesCalculator:
    """Get options calculator instance."""
    global _options_calculator
    if _options_calculator is None:
        _options_calculator = BlackScholesCalculator()
    return _options_calculator
```

==================================================
FILE: egx_radar/advanced/portfolio_optimization.py
==================================================

```python
"""Portfolio optimization and allocation strategies."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class OptimalAllocation:
    """Optimal portfolio allocation result."""
    weights: Dict[str, float]  # Symbol -> allocation %
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    portfolio_value: float


class PortfolioOptimizer:
    """Optimize portfolio allocations using modern portfolio theory."""
    
    def __init__(self, target_return: Optional[float] = None):
        """Initialize optimizer.
        
        Args:
            target_return: Target annual return (optional)
        """
        self.target_return = target_return
        self.risk_free_rate = 0.02  # 2% annual
    
    def calculate_returns(
        self,
        prices: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate daily returns from price data.
        
        Args:
            prices: DataFrame with symbols as columns
            
        Returns:
            DataFrame of daily returns
        """
        returns = prices.pct_change().dropna()
        return returns
    
    def calculate_portfolio_metrics(
        self,
        weights: np.ndarray,
        returns: pd.DataFrame,
        cov_matrix: np.ndarray
    ) -> Tuple[float, float, float]:
        """Calculate portfolio return, volatility, and Sharpe ratio.
        
        Args:
            weights: Asset weights array
            returns: DataFrame of returns
            cov_matrix: Covariance matrix
            
        Returns:
            (expected_return, volatility, sharpe_ratio)
        """
        annual_returns = returns.mean() * 252
        portfolio_return = np.sum(annual_returns * weights)
        
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
        
        return float(portfolio_return), float(portfolio_volatility), float(sharpe_ratio)
    
    def minimize_volatility(
        self,
        returns: pd.DataFrame,
        bounds: Optional[List[Tuple[float, float]]] = None
    ) -> OptimalAllocation:
        """Find minimum variance portfolio.
        
        Args:
            returns: DataFrame of returns
            bounds: Min/max weights per asset (default: 0-1)
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov().values * 252
        
        if bounds is None:
            bounds = tuple((0, 1) for _ in range(n_assets))
        
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        def objective(x):
            vol = np.sqrt(np.dot(x, np.dot(cov_matrix, x)))
            return vol
        
        result = minimize(
            objective,
            x0=np.array([1/n_assets] * n_assets),
            bounds=bounds,
            constraints=constraints,
            method='SLSQP'
        )
        
        weights_arr = result.x
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights_arr, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights_arr))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def maximize_sharpe_ratio(
        self,
        returns: pd.DataFrame,
        bounds: Optional[List[Tuple[float, float]]] = None
    ) -> OptimalAllocation:
        """Find maximum Sharpe ratio portfolio.
        
        Args:
            returns: DataFrame of returns
            bounds: Min/max weights per asset
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov().values * 252
        
        if bounds is None:
            bounds = tuple((0, 1) for _ in range(n_assets))
        
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        def objective(x):
            ret, vol, _ = self.calculate_portfolio_metrics(x, returns, cov_matrix)
            sharpe = (ret - self.risk_free_rate) / vol if vol > 0 else 0
            return -sharpe  # Minimize negative Sharpe
        
        result = minimize(
            objective,
            x0=np.array([1/n_assets] * n_assets),
            bounds=bounds,
            constraints=constraints,
            method='SLSQP'
        )
        
        weights_arr = result.x
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights_arr, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights_arr))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def generate_efficient_frontier(
        self,
        returns: pd.DataFrame,
        num_portfolios: int = 50,
        bounds: Optional[List[Tuple[float, float]]] = None
    ) -> pd.DataFrame:
        """Generate efficient frontier.
        
        Args:
            returns: DataFrame of returns
            num_portfolios: Number of portfolios to generate
            bounds: Min/max weights
            
        Returns:
            DataFrame with return, volatility, Sharpe for each portfolio
        """
        n_assets = len(returns.columns)
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov().values * 252
        
        if bounds is None:
            bounds = tuple((0, 1) for _ in range(n_assets))
        
        results = []
        
        for target_ret in np.linspace(mean_returns.min(), mean_returns.max(), num_portfolios):
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: np.sum(mean_returns * x) - target_ret}
            ]
            
            def objective(x):
                return np.sqrt(np.dot(x, np.dot(cov_matrix, x)))
            
            result = minimize(
                objective,
                x0=np.array([1/n_assets] * n_assets),
                bounds=bounds,
                constraints=constraints,
                method='SLSQP'
            )
            
            if result.success:
                ret, vol, sharpe = self.calculate_portfolio_metrics(
                    result.x, returns, cov_matrix
                )
                results.append({
                    'return': ret,
                    'volatility': vol,
                    'sharpe_ratio': sharpe
                })
        
        return pd.DataFrame(results)
    
    def risk_parity(
        self,
        returns: pd.DataFrame
    ) -> OptimalAllocation:
        """Generate risk parity portfolio (equal risk contribution).
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        cov_matrix = returns.cov().values * 252
        std_devs = np.sqrt(np.diag(cov_matrix))
        
        # Inverse volatility weighting
        weights = (1 / std_devs) / np.sum(1 / std_devs)
        
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def equal_weight(
        self,
        returns: pd.DataFrame
    ) -> OptimalAllocation:
        """Generate equal-weight portfolio.
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            OptimalAllocation
        """
        n_assets = len(returns.columns)
        weights = np.array([1/n_assets] * n_assets)
        
        cov_matrix = returns.cov().values * 252
        ret, vol, sharpe = self.calculate_portfolio_metrics(weights, returns, cov_matrix)
        
        weights_dict = dict(zip(returns.columns, weights))
        
        return OptimalAllocation(
            weights=weights_dict,
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe,
            portfolio_value=1.0
        )
    
    def get_correlation_matrix(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Get correlation matrix.
        
        Args:
            returns: DataFrame of returns
            
        Returns:
            Correlation matrix
        """
        return returns.corr()
    
    def rebalance_weights(
        self,
        current_prices: Dict[str, float],
        current_holdings: Dict[str, float],
        target_weights: Dict[str, float],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Calculate rebalancing trades needed.
        
        Args:
            current_prices: Current prices
            current_holdings: Current share counts
            target_weights: Target allocation weights
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> shares to trade (positive = buy, negative = sell)
        """
        trades = {}
        
        for symbol, target_weight in target_weights.items():
            price = current_prices.get(symbol, 0)
            current_shares = current_holdings.get(symbol, 0)
            
            if price == 0:
                continue
            
            current_value = current_shares * price
            current_weight = current_value / portfolio_value if portfolio_value > 0 else 0
            
            target_value = target_weight * portfolio_value
            target_shares = target_value / price
            
            shares_to_trade = target_shares - current_shares
            trades[symbol] = float(shares_to_trade)
        
        return trades


# Global instance
_optimizer: Optional[PortfolioOptimizer] = None


def get_portfolio_optimizer() -> PortfolioOptimizer:
    """Get or create global portfolio optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = PortfolioOptimizer()
    return _optimizer
```

==================================================
FILE: egx_radar/backup.py
=========================

```python
"""
EGX Radar â€” Automated Backup Script
=====================================
Backs up code to GitHub and data files to a local backup folder.

Usage:
    python backup.py              # full backup (code + data)
    python backup.py --code-only  # git push only
    python backup.py --data-only  # data files only
    python backup.py --check      # show status without backing up

Schedule (Windows Task Scheduler or cron):
    Daily at market close: python backup.py
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from datetime import datetime
from pathlib import Path


# â”€â”€ Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

PROJECT_ROOT = Path(__file__).parent
BACKUP_DIR   = PROJECT_ROOT.parent / "egx_radar_backups"   # adjust if needed

# Data files to back up locally (NOT pushed to git)
DATA_FILES = [
    "brain_state.json",
    "brain_state.db",
    "trades_log.json",
    "trades_history.json",
    "egx_radar.db",
    "scan_snapshot.json",
    "source_settings.json",
    "paper_trading_tracker.xlsx",
    "rejected_symbols.csv",
]

# Git commit message format
COMMIT_MSG_TEMPLATE = "Auto-backup {date} â€” {changed} files changed"


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def log(msg: str, level: str = "INFO") -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "âœ“", "WARN": "âš ", "ERROR": "âœ—", "HEAD": "â•"}.get(level, "â€¢")
    print(f"  [{timestamp}] {prefix}  {msg}")


def run(cmd: list, cwd=None, capture=True) -> tuple[int, str]:
    """Run a shell command. Returns (returncode, output)."""
    result = subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        capture_output=capture,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


# â”€â”€ Core functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def check_git() -> dict:
    """Check git status and return info dict."""
    code, out = run(["git", "status", "--porcelain"])
    if code != 0:
        return {"ok": False, "error": "Not a git repository or git not installed"}

    changed = [l for l in out.split("\n") if l.strip()]
    code2, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    code3, remote  = run(["git", "remote", "get-url", "origin"])

    return {
        "ok":      True,
        "changed": len(changed),
        "branch":  branch if code2 == 0 else "unknown",
        "remote":  remote if code3 == 0 else "none",
        "files":   changed,
    }


def backup_code() -> bool:
    """Commit and push all code changes to GitHub."""
    print()
    log("CODE BACKUP â€” GitHub", "HEAD")

    status = check_git()
    if not status["ok"]:
        log(f"Git error: {status['error']}", "ERROR")
        return False

    if status["remote"] == "none":
        log("No remote configured. Run: git remote add origin <your-repo-url>", "ERROR")
        return False

    if status["changed"] == 0:
        log("Nothing to commit â€” code is up to date")
        return True

    log(f"Branch  : {status['branch']}")
    log(f"Remote  : {status['remote']}")
    log(f"Changed : {status['changed']} file(s)")

    # Stage all changes
    code, out = run(["git", "add", "."])
    if code != 0:
        log(f"git add failed: {out}", "ERROR")
        return False

    # Commit
    msg = COMMIT_MSG_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        changed=status["changed"],
    )
    code, out = run(["git", "commit", "-m", msg])
    if code != 0:
        log(f"git commit failed: {out}", "ERROR")
        return False
    log(f"Committed: {msg}")

    # Push
    log("Pushing to GitHub...")
    code, out = run(["git", "push", "origin", status["branch"]])
    if code != 0:
        log(f"git push failed: {out}", "ERROR")
        log("Tip: check your internet connection and GitHub credentials", "WARN")
        return False

    log("Push successful âœ“")
    return True


def backup_data() -> bool:
    """Copy data files to a timestamped local backup folder."""
    print()
    log("DATA BACKUP â€” Local folder", "HEAD")

    # Create backup directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = BACKUP_DIR / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)
    log(f"Backup folder: {backup_path}")

    copied = 0
    missing = 0

    for filename in DATA_FILES:
        src = PROJECT_ROOT / filename
        dst = backup_path / filename

        if src.exists():
            shutil.copy2(src, dst)
            size = src.stat().st_size
            log(f"Copied: {filename} ({size:,} bytes)")
            copied += 1
        else:
            log(f"Skipped (not found): {filename}", "WARN")
            missing += 1

    # Save backup manifest
    manifest = {
        "timestamp":    timestamp,
        "project_root": str(PROJECT_ROOT),
        "files_copied": copied,
        "files_missing": missing,
        "filenames":    DATA_FILES,
    }
    with open(backup_path / "_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    log(f"Done: {copied} files copied, {missing} skipped")

    # Clean up old backups â€” keep last 14
    _cleanup_old_backups(BACKUP_DIR, keep=14)
    return True


def _cleanup_old_backups(backup_dir: Path, keep: int = 14) -> None:
    """Delete oldest backups, keeping only the last `keep` copies."""
    if not backup_dir.exists():
        return
    backups = sorted(
        [d for d in backup_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    to_delete = backups[:-keep] if len(backups) > keep else []
    for old in to_delete:
        shutil.rmtree(old, ignore_errors=True)
        log(f"Removed old backup: {old.name}", "WARN")


def show_status() -> None:
    """Print current backup status without doing anything."""
    print()
    log("STATUS CHECK", "HEAD")

    # Git status
    status = check_git()
    if status["ok"]:
        log(f"Git branch  : {status['branch']}")
        log(f"Git remote  : {status['remote']}")
        log(f"Uncommitted : {status['changed']} file(s)")
        if status["files"]:
            for f in status["files"][:5]:
                log(f"  {f}", "WARN")
            if len(status["files"]) > 5:
                log(f"  ... and {len(status['files'])-5} more", "WARN")
    else:
        log(f"Git: {status['error']}", "ERROR")

    # Data files
    print()
    log("Data files:")
    for filename in DATA_FILES:
        path = PROJECT_ROOT / filename
        if path.exists():
            size = path.stat().st_size
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            log(f"  {filename} ({size:,} bytes, modified {mtime})")
        else:
            log(f"  {filename} â€” not found", "WARN")

    # Last backup
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.iterdir(), key=lambda d: d.name)
        if backups:
            last = backups[-1]
            log(f"Last data backup: {last.name}")
        else:
            log("No data backups found", "WARN")
    else:
        log(f"Backup folder not created yet: {BACKUP_DIR}", "WARN")


# â”€â”€ Entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    parser = argparse.ArgumentParser(
        description="EGX Radar automated backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backup.py              Full backup (code + data)
  python backup.py --code-only  Git commit + push only
  python backup.py --data-only  Data files only
  python backup.py --check      Status report only
        """,
    )
    parser.add_argument("--code-only", action="store_true", help="Git backup only")
    parser.add_argument("--data-only", action="store_true", help="Data files only")
    parser.add_argument("--check",     action="store_true", help="Status only, no backup")
    args = parser.parse_args()

    print()
    print("  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
    print("  EGX Radar â€” Backup")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")

    if args.check:
        show_status()
        return

    success = True

    if not args.data_only:
        success &= backup_code()

    if not args.code_only:
        success &= backup_data()

    print()
    if success:
        print("  âœ… Backup complete")
    else:
        print("  âš ï¸  Backup finished with errors â€” check output above")
    print()


if __name__ == "__main__":
    main()
```

==================================================
FILE: egx_radar/data_validator.py
=================================

```python
"""Data validation framework for EGX Radar."""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class DataValidator:
    """Validates data quality for backtesting."""
    
    def __init__(self, min_bars: int = 250, max_gap_days: int = 2):
        """Initialize validator with parameters."""
        self.min_bars = min_bars
        self.max_gap_days = max_gap_days
        self.errors = []
        self.warnings = []
    
    def validate_ohlc_data(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Validate OHLC/OHLCV data.
        
        Returns:
            {
                'valid': bool,
                'errors': list,
                'warnings': list,
                'metrics': dict
            }
        """
        self.errors = []
        self.warnings = []
        result = {
            'symbol': symbol,
            'valid': True,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        # Check if DataFrame is empty
        if df is None or df.empty:
            self.errors.append("Data is empty or None")
            result['valid'] = False
            result['errors'] = self.errors
            return result
        
        # Check required columns
        required_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            self.errors.append(f"Missing columns: {missing_cols}")
        
        # Check minimum data points
        if len(df) < self.min_bars:
            self.warnings.append(f"Less than {self.min_bars} bars ({len(df)} found)")
        
        # Check for NaN values
        nan_count = df.isnull().sum().sum()
        if nan_count > 0:
            self.errors.append(f"Contains {nan_count} NaN values")
        
        # Check data types
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    self.errors.append(f"{col} is not numeric")
        
        # Check OHLC logical constraints
        if all(col in df.columns for col in numeric_cols):
            # High should be >= Low
            bad_hl = (df['High'] < df['Low']).sum()
            if bad_hl > 0:
                self.errors.append(f"{bad_hl} bars with High < Low")
            
            # Close should be between High and Low (mostly)
            bad_close = (
                ((df['Close'] > df['High']) | (df['Close'] < df['Low'])).sum()
            )
            if bad_close > len(df) * 0.01:  # Allow 1% exceptions
                self.warnings.append(f"{bad_close} bars with Close outside HL range")
            
            # Volume shouldn't be zero
            zero_volume = (df['Volume'] == 0).sum()
            if zero_volume > len(df) * 0.05:  # Allow 5% zero volume
                self.warnings.append(f"{zero_volume} bars with zero volume")
        
        # Check no negative prices
        for col in numeric_cols:
            if col in df.columns and (df[col] < 0).any():
                self.errors.append(f"{col} contains negative values")
        
        # Check date continuity
        if len(df) > 1:
            gaps = self._check_date_gaps(df)
            if gaps:
                self.warnings.append(f"Found {len(gaps)} gaps > {self.max_gap_days} days")
        
        # Metrics
        result['metrics'] = {
            'n_bars': len(df),
            'date_range': f"{df.index[0]} to {df.index[-1]}" if len(df) > 0 else "N/A",
            'price_range': f"{df['Close'].min():.2f} - {df['Close'].max():.2f}" 
                          if 'Close' in df.columns else "N/A",
            'avg_volume': df['Volume'].mean() if 'Volume' in df.columns else 0,
        }
        
        # Set validity
        result['valid'] = len(self.errors) == 0
        result['errors'] = self.errors
        result['warnings'] = self.warnings
        
        return result
    
    def _check_date_gaps(self, df: pd.DataFrame) -> List[Tuple]:
        """Find date gaps larger than max_gap_days."""
        if not isinstance(df.index, pd.DatetimeIndex):
            return []
        
        gaps = []
        diffs = df.index.to_series().diff()
        
        for i, gap in enumerate(diffs):
            if gap.days > self.max_gap_days:
                gaps.append((df.index[i-1], df.index[i], gap.days))
        
        return gaps
    
    def validate_metrics(self, trades: List[Dict]) -> Dict:
        """Validate trade metrics."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        if not trades:
            result['warnings'].append("No trades executed")
            result['metrics']['total_trades'] = 0
            return result
        
        # Check trade structure
        required_fields = {'symbol', 'entry_date', 'exit_date', 'pnl'}
        for i, trade in enumerate(trades):
            missing = required_fields - set(trade.keys())
            if missing:
                result['errors'].append(f"Trade {i} missing: {missing}")
        
        # Check numeric validity
        pnl_values = [t.get('pnl', 0) for t in trades if 'pnl' in t]
        if pnl_values:
            result['metrics']['total_pnl'] = sum(pnl_values)
            result['metrics']['avg_pnl'] = np.mean(pnl_values)
            result['metrics']['win_count'] = sum(1 for p in pnl_values if p > 0)
            result['metrics']['loss_count'] = sum(1 for p in pnl_values if p < 0)
        
        result['metrics']['total_trades'] = len(trades)
        result['valid'] = len(result['errors']) == 0
        
        return result


def validate_dataset(
    df: pd.DataFrame, 
    symbol: str, 
    min_bars: int = 250
) -> Dict:
    """Quick validation of a dataset."""
    validator = DataValidator(min_bars=min_bars)
    return validator.validate_ohlc_data(df, symbol)


def validate_all_symbols(
    symbol_data: Dict[str, pd.DataFrame]
) -> Dict[str, Dict]:
    """Validate multiple symbols."""
    validator = DataValidator()
    results = {}
    
    for symbol, df in symbol_data.items():
        results[symbol] = validator.validate_ohlc_data(df, symbol)
    
    return results


def generate_validation_report(results: Dict) -> str:
    """Generate a text report from validation results."""
    lines = ["=" * 60]
    lines.append("DATA VALIDATION REPORT")
    lines.append("=" * 60)
    
    total = len(results)
    valid = sum(1 for r in results.values() if r.get('valid'))
    
    lines.append(f"\nSummary: {valid}/{total} datasets valid")
    lines.append("")
    
    for symbol, result in results.items():
        status = "âœ“ PASS" if result['valid'] else "âœ— FAIL"
        lines.append(f"{symbol:8} {status}")
        
        if result['errors']:
            for error in result['errors']:
                lines.append(f"  ERROR: {error}")
        
        if result['warnings']:
            for warning in result['warnings']:
                lines.append(f"  WARN:  {warning}")
        
        metrics = result.get('metrics', {})
        if metrics:
            lines.append(f"  Bars: {metrics.get('n_bars')}, "
                        f"Avg Vol: {metrics.get('avg_volume', 0):.0f}")
    
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
```

==================================================
FILE: egx_radar/error_handler.py
================================

```python
"""Error handling and recovery framework for backtesting."""

import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class BacktestError:
    """Structured error information."""
    timestamp: datetime
    severity: ErrorSeverity
    message: str
    component: str
    exception_type: Optional[str] = None
    traceback_info: Optional[str] = None
    context: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'message': self.message,
            'component': self.component,
            'exception_type': self.exception_type,
            'context': self.context,
        }


class ErrorHandler:
    """Centralized error handling for backtest engine."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize error handler."""
        self.errors: List[BacktestError] = []
        self.recovery_strategies: Dict[str, Callable] = {}
        self.log_file = log_file
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        self.logger.setLevel(logging.DEBUG)
    
    def register_recovery_strategy(
        self,
        error_type: str,
        strategy: Callable
    ):
        """Register a recovery strategy for error type."""
        self.recovery_strategies[error_type] = strategy
    
    def handle_error(
        self,
        message: str,
        component: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        exception: Optional[Exception] = None,
        context: Optional[Dict] = None,
        recover: bool = True,
    ) -> Optional[Dict]:
        """
        Handle an error with optional recovery.
        
        Args:
            message: Error message
            component: Component where error occurred
            severity: Error severity level
            exception: Original exception if any
            context: Contextual information
            recover: Attempt recovery if strategy available
            
        Returns:
            Recovery result if recovery was attempted
        """
        # Create error record
        error = BacktestError(
            timestamp=datetime.now(),
            severity=severity,
            message=message,
            component=component,
            exception_type=type(exception).__name__ if exception else None,
            traceback_info=traceback.format_exc() if exception else None,
            context=context,
        )
        
        self.errors.append(error)
        
        # Log error
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }[severity]
        
        self.logger.log(
            log_level,
            f"[{component}] {message}",
            extra={'exception': exception}
        )
        
        # Attempt recovery
        if recover and error.exception_type in self.recovery_strategies:
            try:
                recovery_strategy = self.recovery_strategies[error.exception_type]
                result = recovery_strategy(error, context or {})
                self.logger.info(f"Recovery successful for {error.exception_type}")
                return result
            except Exception as recovery_error:
                self.logger.error(
                    f"Recovery failed: {recovery_error}",
                    exc_info=True
                )
                return None
        
        return None
    
    def get_error_summary(self) -> Dict:
        """Get summary of all errors."""
        by_severity = {}
        by_component = {}
        
        for error in self.errors:
            # By severity
            sev = error.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            # By component
            comp = error.component
            by_component[comp] = by_component.get(comp, 0) + 1
        
        return {
            'total_errors': len(self.errors),
            'by_severity': by_severity,
            'by_component': by_component,
            'recent_errors': [e.to_dict() for e in self.errors[-5:]],  # Last 5
        }
    
    def clear_errors(self):
        """Clear error log."""
        self.errors = []
    
    def export_errors(self, filepath: str):
        """Export errors to JSON file."""
        import json
        
        data = {
            'summary': self.get_error_summary(),
            'errors': [e.to_dict() for e in self.errors],
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)


class RetryManager:
    """Manage retry logic for transient failures."""
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        backoff_max: float = 10.0,
    ):
        """Initialize retry manager."""
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.backoff_max = backoff_max
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple[Any, bool]:
        """
        Execute function with automatic retries.
        
        Returns:
            (result, success) tuple
        """
        import time
        
        last_exception = None
        backoff = 1.0
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                return result, True
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = min(
                        backoff * self.backoff_factor,
                        self.backoff_max
                    )
                    logging.warning(
                        f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                    backoff *= 2
        
        return None, False


class TimeoutManager:
    """Manage execution timeouts."""
    
    def __init__(self, timeout_seconds: int = 60):
        """Initialize timeout manager."""
        self.timeout_seconds = timeout_seconds
    
    def execute_with_timeout(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple[Optional[Any], bool]:
        """
        Execute function with timeout.
        
        Returns:
            (result, completed_in_time) tuple
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Execution exceeded {self.timeout_seconds}s")
        
        try:
            # Set timeout signal
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_seconds)
            
            result = func(*args, **kwargs)
            
            # Cancel alarm
            signal.alarm(0)
            
            return result, True
        except TimeoutError as e:
            signal.alarm(0)
            logging.error(f"Timeout: {e}")
            return None, False
        except Exception as e:
            signal.alarm(0)
            raise


class RecoveryStrategy:
    """Pre-built recovery strategies."""
    
    @staticmethod
    def skip_symbol(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Skip current symbol and continue with others."""
        symbol = context.get('symbol')
        logging.info(f"Skipping symbol '{symbol}' due to error")
        return {'action': 'skip', 'symbol': symbol}
    
    @staticmethod
    def reduce_date_range(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Reduce date range for current backtest."""
        logging.info("Reducing date range due to memory/timeout constraints")
        return {'action': 'reduce_range'}
    
    @staticmethod
    def fallback_to_sequential(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Fall back from parallel to sequential processing."""
        logging.info("Falling back to sequential processing")
        return {'action': 'sequential', 'workers': 1}
    
    @staticmethod
    def clear_cache(
        error: BacktestError,
        context: Dict
    ) -> Dict:
        """Clear cache to free memory."""
        logging.info("Clearing cache to free memory")
        import gc
        gc.collect()
        return {'action': 'cleared_cache'}


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get or create global error handler."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_backtest_error(
    message: str,
    component: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    exception: Optional[Exception] = None,
    context: Optional[Dict] = None,
) -> Optional[Dict]:
    """Convenience function to use global error handler."""
    handler = get_error_handler()
    return handler.handle_error(
        message=message,
        component=component,
        severity=severity,
        exception=exception,
        context=context,
    )
```

==================================================
FILE: egx_radar/__init__.py
===========================

```python
"""EGX Capital Flow Radar - Algorithmic Trading System."""

__version__ = "0.8.3"
__author__ = "EGX Radar Team"

__all__ = [
    "__version__",
    "__author__",
]
```

==================================================
FILE: egx_radar/__main__.py
===========================

```python
"""Package entry point for `python -m egx_radar`."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from egx_radar.ui.main_window import main


if __name__ == "__main__":
    main()
```

==================================================
FILE: egx_radar/main.py
=======================

```python
"""EGX Capital Flow Radar â€” entry point."""

import logging

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from egx_radar.ui.main_window import main

if __name__ == "__main__":
    main()
```

==================================================
FILE: source_settings.json
==========================

```json
{
  "alpha_vantage_key": "Q0M3MFRNSEc2RVlDRFZCSA==",
  "use_yahoo": true,
  "use_stooq": true,
  "use_alpha_vantage": true,
  "use_investing": true,
  "use_twelve_data": true,
  "twelve_data_key": "MTU4ODAyM2E3ZmU0NDY3M2IyYTU3NzU5MWU3Mzc1MTA=",
  "account_size": 50000.0,
  "risk_per_trade": 0.01,
  "portfolio_max_atr_exposure": 0.04,
  "portfolio_max_per_sector": 2
}
```

==================================================
FILE: brain_state.json
======================

```json
{
  "neural_weights": {
    "flow": 1.0,
    "structure": 1.0,
    "timing": 1.0
  },
  "prev_ranks": {
    "ABUK": 28.7705,
    "ADIB": 11.0805,
    "AMOC": 17.7905,
    "CIEB": 14.639500000000002,
    "CNFN": 6.502000000000001,
    "COMI": 10.689,
    "EAST": 18.6485,
    "EGTS": 9.3285,
    "ETEL": 10.802,
    "FAIT": 15.2655,
    "FWRY": 13.3615,
    "HELI": 21.011,
    "HRHO": 12.7075,
    "ISPH": 13.267,
    "JUFO": 10.692499999999999,
    "KZPC": 16.731,
    "MFPC": 24.113500000000002,
    "OCDI": 8.759,
    "ORWE": 9.358,
    "PHDC": 11.875,
    "SAUD": 15.703,
    "SKPC": 21.75,
    "SWDY": 9.73,
    "TMGH": 12.45
  },
  "neural_win": [],
  "neural_loss": [],
  "neural_bias": [
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.049999999999999996
  ],
  "sector_flow": {
    "BANKS": [
      0.29947378772948646,
      0.29947378772948646,
      0.16715980120411175
    ],
    "REAL_ESTATE": [
      0.4339653771211771,
      0.4339653771211771,
      0.14231587271898138
    ],
    "INDUSTRIAL": [
      0.38643181246641706,
      0.38643181246641706,
      0.39798726113264166
    ],
    "SERVICES": [
      0.3121572715561106,
      0.3121572715561106,
      0.13800186817432078
    ],
    "ENERGY": [
      0.35271567162116074,
      0.35271567162116074,
      0.20489993187694466
    ]
  },
  "outcome_wins": 0,
  "outcome_losses": 0
}
```

==================================================
FILE: scan_snapshot.json
========================

```json
[{"sym": "SWDY", "sector": "ENERGY", "price": 78.53, "signal": "WAIT", "tag": "watch", "smart_rank": 84.02, "confidence": 54.1, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Accumulation", "zone": "\ud83d\udfe2 EARLY", "action": "WAIT", "entry": 80.92, "stop": 77.22, "target": 89.02, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "ABUK", "sector": "ENERGY", "price": 87.0, "signal": "WAIT", "tag": "watch", "smart_rank": 77.77, "confidence": 54.5, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 89.98, "stop": 85.48, "target": 98.98, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "MFPC", "sector": "ENERGY", "price": 43.19, "signal": "WAIT", "tag": "watch", "smart_rank": 76.26, "confidence": 45.4, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 45.9, "stop": 43.6, "target": 50.49, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "AMOC", "sector": "INDUSTRIAL", "price": 8.77, "signal": "WAIT", "tag": "watch", "smart_rank": 73.14, "confidence": 51.2, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 9.5, "stop": 9.03, "target": 10.45, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "ETEL", "sector": "SERVICES", "price": 84.39, "signal": "WAIT", "tag": "watch", "smart_rank": 72.82, "confidence": 43.4, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 85.89, "stop": 81.59, "target": 94.47, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "SAUD", "sector": "BANKS", "price": 18.84, "signal": "WAIT", "tag": "watch", "smart_rank": 72.28, "confidence": 43.0, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 18.84, "stop": 17.91, "target": 20.72, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "CIEB", "sector": "BANKS", "price": 23.24, "signal": "WAIT", "tag": "watch", "smart_rank": 67.98, "confidence": 47.6, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 23.42, "stop": 22.25, "target": 25.77, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "FWRY", "sector": "SERVICES", "price": 17.6, "signal": "WAIT", "tag": "watch", "smart_rank": 62.25, "confidence": 37.0, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 17.97, "stop": 17.07, "target": 19.76, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.411946"}, {"sym": "EGTS", "sector": "SERVICES", "price": 7.31, "signal": "WAIT", "tag": "watch", "smart_rank": 58.66, "confidence": 34.9, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 7.41, "stop": 7.04, "target": 8.15, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "HELI", "sector": "REAL_ESTATE", "price": 5.68, "signal": "WAIT", "tag": "watch", "smart_rank": 57.14, "confidence": 34.0, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 5.74, "stop": 5.45, "target": 6.31, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "SKPC", "sector": "INDUSTRIAL", "price": 17.1, "signal": "WAIT", "tag": "watch", "smart_rank": 56.99, "confidence": 33.9, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 18.89, "stop": 17.95, "target": 20.78, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "ISPH", "sector": "ENERGY", "price": 10.4, "signal": "WAIT", "tag": "watch", "smart_rank": 48.24, "confidence": 28.6, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 10.84, "stop": 10.3, "target": 11.92, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "JUFO", "sector": "SERVICES", "price": 26.59, "signal": "WAIT", "tag": "watch", "smart_rank": 47.86, "confidence": 28.5, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 26.98, "stop": 25.68, "target": 29.67, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "ORWE", "sector": "SERVICES", "price": 22.41, "signal": "WAIT", "tag": "watch", "smart_rank": 47.54, "confidence": 28.2, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 23.19, "stop": 22.03, "target": 25.51, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "OCDI", "sector": "REAL_ESTATE", "price": 17.91, "signal": "WAIT", "tag": "watch", "smart_rank": 46.24, "confidence": 27.5, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 18.53, "stop": 17.6, "target": 20.38, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "PHDC", "sector": "REAL_ESTATE", "price": 8.51, "signal": "WAIT", "tag": "watch", "smart_rank": 44.8, "confidence": 26.7, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 8.86, "stop": 8.42, "target": 9.74, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "HRHO", "sector": "SERVICES", "price": 26.38, "signal": "WAIT", "tag": "watch", "smart_rank": 44.73, "confidence": 26.6, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 26.93, "stop": 25.58, "target": 29.62, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "TMGH", "sector": "REAL_ESTATE", "price": 79.0, "signal": "WAIT", "tag": "watch", "smart_rank": 44.27, "confidence": 26.3, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 80.33, "stop": 76.31, "target": 88.36, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "KZPC", "sector": "INDUSTRIAL", "price": 9.84, "signal": "WAIT", "tag": "watch", "smart_rank": 40.49, "confidence": 24.1, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 10.26, "stop": 9.75, "target": 11.29, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "COMI", "sector": "BANKS", "price": 129.7, "signal": "WAIT", "tag": "watch", "smart_rank": 38.44, "confidence": 22.9, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Exhaustion", "zone": "\ud83d\udd34 LATE", "action": "WAIT", "entry": 129.7, "stop": 123.21, "target": 142.67, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}, {"sym": "EAST", "sector": "ENERGY", "price": 35.89, "signal": "WAIT", "tag": "watch", "smart_rank": 32.78, "confidence": 19.6, "direction": "\u23f8\ufe0f NEUTRAL", "phase": "Base", "zone": "\ud83d\udfe1 MID", "action": "WAIT", "entry": 38.28, "stop": 36.36, "target": 42.11, "winrate": 0.0, "scan_time": "2026-03-24T01:04:56.412945"}]
```

==================================================
FILE: egx_radar/source_settings.json
====================================

```json
{
  "alpha_vantage_key": "TTZORzc5NjhDQ1I1RVQ5Mw==",
  "use_yahoo": true,
  "use_stooq": true,
  "use_alpha_vantage": true,
  "use_investing": true,
  "use_twelve_data": true,
  "twelve_data_key": "ZTBkZGZlZTZlNjY1NGQyNmEwZWMzZmQyZjlkMDNkNjI=",
  "account_size": 10000.0,
  "risk_per_trade": 0.01,
  "portfolio_max_atr_exposure": 0.04,
  "portfolio_max_per_sector": 2
}
```

==================================================
FILE: egx_radar/brain_state.json
================================

```json
{
  "neural_weights": {
    "flow": 1.0,
    "structure": 1.0,
    "timing": 1.0
  },
  "prev_ranks": {
    "ABUK": 21.133222412109376,
    "ADIB": 9.135388916015625,
    "AMOC": 15.861236328124999,
    "CIEB": 10.41862451171875,
    "CNFN": 10.869412109374998,
    "COMI": 10.904336914062501,
    "EAST": 9.957091796875,
    "EGTS": 9.186958984375,
    "ETEL": 9.407631835937499,
    "FAIT": 25.0,
    "FWRY": 16.267409912109375,
    "HELI": 14.054991210937501,
    "HRHO": 8.4993408203125,
    "ISPH": 14.82369482421875,
    "JUFO": 17.6332529296875,
    "KZPC": 15.0705,
    "MFPC": 29.553090820312498,
    "OCDI": 14.806841796875,
    "ORWE": 20.864819335937497,
    "PHDC": 20.6213583984375,
    "SAUD": 8.9080703125,
    "SKPC": 16.66159375,
    "SWDY": 18.1344697265625,
    "TMGH": 11.98622119140625
  },
  "neural_win": [],
  "neural_loss": [
    [
      25.0,
      0.62
    ],
    [
      23.64,
      0.52
    ],
    [
      24.74,
      0.52
    ],
    [
      25.55,
      0.43
    ],
    [
      26.58,
      0.67
    ],
    [
      19.82,
      0.57
    ],
    [
      15.85,
      0.24
    ],
    [
      23.44,
      0.24
    ],
    [
      21.05,
      0.52
    ],
    [
      20.87,
      0.86
    ]
  ],
  "neural_bias": [
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    -0.4,
    -0.4,
    -0.4,
    -0.4,
    -0.4,
    -0.4,
    -0.4,
    -0.4,
    0.05,
    0.049999999999999996,
    -0.4,
    -0.4,
    0.05
  ],
  "sector_flow": {
    "BANKS": [
      0.22802795055505898,
      0.22802795055505898,
      0.22802795055505898,
      0.29947378772948646,
      0.29947378772948646,
      0.07723980370340473,
      0.07723980370340473,
      0.15272333175020755,
      0.15272333175020755,
      0.15272333175020755,
      0.16715980120411175,
      0.16943816348417792,
      0.16943816348417792,
      0.19716692053182325
    ],
    "REAL_ESTATE": [
      0.213836485914624,
      0.213836485914624,
      0.213836485914624,
      0.4339653771211771,
      0.4339653771211771,
      0.19359909527060426,
      0.19359909527060426,
      0.2290715030174365,
      0.2290715030174365,
      0.2290715030174365,
      0.14231587271898138,
      0.1945066579401145,
      0.1945066579401145,
      0.2892303240972398
    ],
    "INDUSTRIAL": [
      0.2785957194825676,
      0.2785957194825676,
      0.2785957194825676,
      0.38643181246641706,
      0.38643181246641706,
      0.11614297932913709,
      0.11614297932913709,
      0.1597971583297644,
      0.1597971583297644,
      0.1597971583297644,
      0.39798726113264166,
      0.13242629250724533,
      0.13242629250724533,
      0.48123306430594065
    ],
    "SERVICES": [
      0.27919080931048396,
      0.27919080931048396,
      0.27919080931048396,
      0.3121572715561106,
      0.3121572715561106,
      0.09011947478634323,
      0.09011947478634323,
      0.15919177190362044,
      0.15919177190362044,
      0.15919177190362044,
      0.13800186817432078,
      0.20541411471852478,
      0.20541411471852478,
      0.3255341835581714
    ],
    "ENERGY": [
      0.37185214131231703,
      0.37185214131231703,
      0.37185214131231703,
      0.35271567162116074,
      0.35271567162116074,
      0.13163949449391993,
      0.13163949449391993,
      0.1794353192429079,
      0.1794353192429079,
      0.1794353192429079,
      0.20489993187694466,
      0.14545278137928347,
      0.14545278137928347,
      0.3127811490669793
    ]
  },
  "outcome_wins": 0,
  "outcome_losses": 10
}
```

