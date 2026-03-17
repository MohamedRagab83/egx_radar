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
    ─────────────────────────────────────────────────────────────────────────
    NAMING CONVENTION:
      ADX_*        → ADX indicator thresholds
      MIN_*        → minimum data-quality requirements
      VOL_*        → volume-related parameters
      PRICE_*      → price filter floors
      SCORE_*      → signal score thresholds
      ATR_*        → ATR risk engine constants
      NEURAL_*     → adaptive weight parameters
      WINRATE_*    → win-rate engine constants
      SMART_*      → SmartRank composite parameters
      PORTFOLIO_*  → portfolio guard limits
      OUTCOME_*    → trade log parameters
      PLAN_*       → trade plan geometry
      BRAIN_*      → market mode thresholds
      REGIME_*     → market regime detection
      UI_*         → UI refresh timing
    ─────────────────────────────────────────────────────────────────────────
    """
    # ── Data quality ────────────────────────────────────────────────────────
    MIN_BARS            = 60       # hard minimum for Yahoo path
    MIN_BARS_RELAXED    = 30       # relaxed minimum for Stooq/TD fallback
    LOW_LIQ_FILTER      = 150_000.0   # hard reject: symbol too illiquid to score at all
    PRICE_FLOOR         = 2.0      # minimum price in EGP
    LIQUIDITY_GATE_MIN_VOLUME = 100_000.0   # post-score gate: show WAIT if below this (EGX-calibrated)

    # ── ADX ─────────────────────────────────────────────────────────────────
    ADX_LENGTH          = 14
    ADX_STRONG          = 25.0
    ADX_MID             = 18.0
    # EGX-calibrated: allow slightly lower ADX threshold for accumulation
    ADX_SOFT_LO         = 14.0     # below this → WAIT regardless of score
    ADX_SOFT_HI         = 22.0     # below this → PROBE only if rank meets bar

    # ── Volume Z-score ───────────────────────────────────────────────────────
    VOL_ROLL_WINDOW     = 20
    # FIX-D: Symmetric clamp.  v77 used asymmetric (-5, +10) which rewarded
    # abnormal upside spikes while ignoring downside. Now (-4, +4).
    VOL_ZSCORE_LO       = -4.0
    VOL_ZSCORE_HI       =  4.0

    # [P3-G5] Volume Surge
    VOL_SURGE_ENABLED   = True
    VOL_SURGE_THRESHOLD = 2.5

    # Logarithmic volume scaling — suppresses retail spikes, highlights institutional volume
    VOL_LOG_SCALE_ENABLED  = True
    VOL_LOG_SCALE_DIVISOR  = 1.3    # log1p(vol_ratio) / divisor maps to [0, ~1]

    # Liquidity Shock Detector — distinguishes institutional from retail volume events
    LIQ_SHOCK_ENABLED      = True
    LIQ_SHOCK_THRESHOLD    = 1.5    # minimum shock value required to apply the boost
    LIQ_SHOCK_BOOST        = 0.08   # additive boost applied to final_n (scale 0–1)

    # ── VWAP ────────────────────────────────────────────────────────────────
    VWAP_ROLL_WINDOW    = 20

    # ── ATR ─────────────────────────────────────────────────────────────────
    ATR_LENGTH          = 14
    # FIX-F: Percentile thresholds instead of hardcoded pct values
    ATR_HIST_WINDOW     = 60       # bars used to compute percentile
    # EGX-calibrated: raise ATR percentile thresholds so only extreme moves flag
    ATR_PCT_HIGH        = 85       # ≥85th percentile → HIGH risk (EGX-calibrated)
    ATR_PCT_MED         = 65       # ≥65th percentile → MED risk (EGX-calibrated)

    # [P3-G3] ATR% Filter (Hard/Soft Limits)
    ATR_PCT_FILTER_ENABLED = True
    # EGX-calibrated: loosen hard/soft ATR% limits (EGX stocks run larger ATRs)
    ATR_PCT_HARD_LIMIT      = 10.0   # ≥10% ATR → WAIT (was 8.0)
    ATR_PCT_SOFT_LIMIT      = 7.0    # ≥7% ATR + BUY → PROBE (was 5.0)
    ATR_NORMALIZE_BY_PRICE  = True   # always use atr/price (%), never raw ATR points

    # ── Whale detection ──────────────────────────────────────────────────────
    WHALE_ZSCORE_THRESH = 1.5
    WHALE_CLV_THRESH    = 0.5
    WHALE_VOL_THRESH    = 1.3
    WHALE_CLV_SIGNAL    = 0.6

    # ── CMF (Chaikin Money Flow) ──────────────────────────────────────────
    CMF_DAMPING_ENABLED = True
    CMF_DAMPING_FACTOR  = 0.70
    CMF_PERIOD          = 20

    # [P3-G6] CMF Size Boost
    CMF_SIZE_BOOST_ENABLED   = True
    CMF_SIZE_BOOST_THRESHOLD = 0.15
    CMF_SIZE_BOOST_MULT      = 1.10

    # ── VCP (Volatility Contraction Pattern) ──────────────────────────────
    VCP_MULTIPLIER_ENABLED = True
    VCP_SCORE_MULTIPLIER   = 1.15

    # ── Signal score ─────────────────────────────────────────────────────────
    SCORE_BUY           = 7
    SCORE_WATCH         = 4
    FAKE_BREAK_BODY     = 0.45
    RSI_OVERBOUGHT      = 72.0

    # ── Gating ───────────────────────────────────────────────────────────────
    LATE_ZONE_FILTER_ENABLED = True
    RSI_OB_GATE_ENABLED      = True
    RSI_OB_HARD_LIMIT        = 78.0
    RSI_OB_SOFT_LIMIT        = 72.0
    EMA50_GUARD_ENABLED      = True

    # ── SmartRank weights (EXPLICIT — all components normalised 0-1) ─────────
    # FIX-B: Each weight is applied to a 0-1 normalised sub-score.
    # Total weight budget = 1.0.  Adjust weights here, not in the formula.
    # Formula (documented in smart_rank_score()):
    #   smart_rank = Σ(weight_i × normalised_component_i) × SMART_RANK_SCALE
    #   where each normalised_component_i ∈ [0, 1]
    # Rebalanced: more weight on capital flow and structure, less on momentum.
    # EGX signals driven by institutional flows, not momentum spikes.
    # New sum: 0.30+0.25+0.20+0.10+0.10+0.05 = 1.00 — assert still passes.
    SR_W_FLOW        = 0.30   # increased — EGX is driven by institutional capital flows
    SR_W_STRUCTURE   = 0.25   # increased — technical structure is a more reliable signal
    SR_W_TIMING      = 0.20   # unchanged
    SR_W_MOMENTUM    = 0.10   # decreased — was over-promoting volatile low-quality stocks
    SR_W_REGIME      = 0.10   # decreased
    SR_W_NEURAL      = 0.05   # decreased
    # (weights must sum to 1.0 — enforced at startup)
    SMART_RANK_SCALE    = 60.0  # output range: [0, SMART_RANK_SCALE]
    SMART_RANK_SMOOTHING = 0.5  # EWM alpha: higher = faster response
    SMART_RANK_ADX_CAP  = 25.0  # max rank when ADX < ADX_SOFT_LO
    SMARTRANK_ENTRY_THRESHOLD = 20  # minimum SmartRank for add-on eligibility
    SMARTRANK_MIN_ACTIONABLE = 16.8   # "Emerging Setup" threshold

    # ── Sector configuration ──────────────────────────────────────────────────
    # Remove hard-block blacklist for EGX — use soft downgrade instead
    BLACKLISTED_SECTORS = set()

    # EGX-calibrated: sectors historically weak that should be downgraded
    WEAK_SECTOR_DOWNGRADE = {"INDUSTRIAL"}
    BLACKLISTED_SECTORS_BT = {"INDUSTRIAL"}
    PRIORITY_SECTORS = [
        "BANKS",        # Phase 1 BT: WR=47.6% — strongest sector
        "REAL_ESTATE",  # Phase 1 BT: WR=43.3%
        "SERVICES",     # Phase 1 BT: WR=42.0%
    ]
    SECTOR_FILTER_ENABLED = True
    SIZE_MULTIPLIER_FLOOR = 0.25   # global floor — never reduce below 25%

    # ── Neural adaptive weights ───────────────────────────────────────────────
    # FIX-E: Weight update now uses mean-reversion to 1.0 (neutral).
    # Old code accumulated drift; new code decays toward 1.0 each update.
    NEURAL_WEIGHT_MIN   = 0.8
    NEURAL_WEIGHT_MAX   = 1.4
    NEURAL_STEP         = 0.05
    NEURAL_DECAY        = 0.02   # decay toward 1.0 per update cycle
    NEURAL_MEM_SIZE     = 50     # rolling window for market context

    # ── Win-rate engine ───────────────────────────────────────────────────────
    # FIX-A: True empirical win rate from balanced win/loss sample.
    WINRATE_MIN_SAMPLE  = 10     # below this → show "⌛ Building"
    WINRATE_FLOOR       = 20.0
    WINRATE_CEIL        = 60.0
    WINRATE_SPARSE_PENALTY = 5.0 # per-missing-trade confidence discount

    # ── Market regime detection ───────────────────────────────────────────────
    # FIX-C: Regime now requires BOTH ADX > threshold AND EMA200 slope direction.
    # Prevents "Accumulation" false-positives in downtrending markets.
    REGIME_ADX_BULL       = 25.0
    REGIME_ADX_DIST       = 18.0
    REGIME_SLOPE_BARS     = 20   # bars used to compute EMA200 slope

    # Bear market score damping — reduces signal count in weak or bear markets
    REGIME_BEAR_DAMPING_ENABLED = True
    REGIME_BEAR_SCORE_MULT      = 0.60   # multiply raw_n by 0.60 in BEAR / DISTRIBUTION
    REGIME_NEUTRAL_SCORE_MULT   = 0.85   # multiply raw_n by 0.85 in NEUTRAL market

    REGIME_RSI_DIST_MIN   = 65.0
    REGIME_BEAR_SLOPE_THRESH = -0.002   # EMA200 slope below this → BEAR candidate
    REGIME_BEAR_RSI_MAX      = 45.0     # RSI below this confirms BEAR (not just cooling)
    
    # ── General Market Proxy ──────────────────────────────────────────────────
    # NOTE: ^EGX30 is dead on Yahoo Finance (returns HTTP 404 for all variants).
    # Best working proxy is COMI.CA (Commercial International Bank of Egypt),
    # the most liquid and institutionally tracked EGX blue chip (124 bars on YF).
    EGX30_SYMBOL          = "COMI.CA"  # Proxy for broad EGX market health
    EGX30_HEALTH_BARS     = 50        # Bars required to evaluate broad market health (EMA50)

    # ── Trade plan geometry ───────────────────────────────────────────────────
    PLAN_ENTRY_DISCOUNT  = 0.995
    PLAN_STOP_ADX_LOW    = 0.965
    PLAN_STOP_CLV_HIGH   = 0.970
    PLAN_STOP_DEFAULT    = 0.955
    PLAN_TARGET_HIGH     = 1.15
    PLAN_TARGET_DEFAULT  = 1.09
    PLAN_ANTICIPATION_HI = 5.0

    # ── Trade sizing ─────────────────────────────────────────────────────────
    ACCOUNT_SIZE         = 10_000.0
    RISK_PER_TRADE       = 0.01

    # ── Portfolio guard ───────────────────────────────────────────────────────
    # FIX-G: Guard is now a pure function returning a new annotated list.
    PORTFOLIO_MAX_PER_SECTOR    = 2
    PORTFOLIO_MAX_ATR_EXPOSURE  = 0.04  # 4% of account in ATR units

    # ── Trade outcome engine ──────────────────────────────────────────────────
    OUTCOME_LOG_FILE         = "trades_log.json"
    OUTCOME_HISTORY_FILE     = "trades_history.json"
    OUTCOME_LOOKFORWARD_DAYS = 15
    OUTCOME_MIN_BARS_NEEDED  = 3
    MAX_BARS_HELD            = 14

    # ── Backtest costs & limits ───────────────────────────────────────────
    BT_COMMISSION    = 0.00275      # EGX broker commission (0.275%)
    BT_STAMP         = 0.001        # stamp duty (0.1%)
    BT_SPREAD        = 0.002        # average spread cost (0.2%)
    BT_TOTAL_COST_PCT = BT_COMMISSION + BT_STAMP + BT_SPREAD   # ~0.575%
    BT_MAX_BARS      = 15           # default max holding period
    BT_DAILY_TOP_N   = 2            # Phase 2: only enter top-N signals per day by SmartRank
                                     # Set to 0 to disable (all allowed signals enter)
    # Phase 2b: minimum action quality for backtest entry
    # "ACCUMULATE" = SmartRank >= 40% of scale (>=24) — high conviction only
    # "PROBE"      = SmartRank >= 28% of scale (>=16.8) — includes weaker signals
    # Set to "ACCUMULATE" to filter out low-SmartRank entries
    BT_MIN_ACTION    = "PROBE"          # reverted — see BT_MIN_SMARTRANK below
    BT_MIN_SMARTRANK = 38.0             # raised from 30.0 — all 235 backtest trades were SR 30-40, only 3 above 40 achieved 67% WR vs 33% overall (March 2026)
                                         # 20.0 = 33% of SMART_RANK_SCALE (60)
                                         # raise to 24.0 to test stricter filter
                                         # set to 0.0 to disable
    BT_OOS_START     = "2025-01-01"     # Phase 4: recommended out-of-sample start date
                                         # Results before this date may be optimistically biased
    MIN_BARS_HELD            = 3
    OPTIMAL_BARS_LOW         = 7
    OPTIMAL_BARS_HIGH        = 14

    # ── Scan history & paper trading ──────────────────────────────────────────
    SCAN_HISTORY_ENABLED   = True    # auto-save daily scan CSV
    SCAN_HISTORY_KEEP_DAYS = 90      # delete scans older than 90 days

    # ── Brain mode ────────────────────────────────────────────────────────────
    BRAIN_SCORE_AGGRESSIVE = 6
    BRAIN_SCORE_NEUTRAL    = 7
    BRAIN_SCORE_DEFENSIVE  = 8

    # ── Signal accumulation ───────────────────────────────────────────────────
    ACCUM_SCORE_THRESH   = 2.0
    LEADER_QUANTUM_DELTA = 1.2

    # ── Download ──────────────────────────────────────────────────────────────
    CHUNK_SIZE           = 6
    DOWNLOAD_TIMEOUT     = 30
    MAX_DOWNLOAD_RETRIES = 2
    RETRY_BACKOFF_BASE   = 1.5
    STOOQ_MAX_WORKERS    = 8
    INVESTING_MAX_WORKERS = 8
    TD_MAX_WORKERS       = 6
    TD_REQUEST_DELAY     = 7.5   # 8 req/min = 7.5s gap
    TD_BARS              = 500

    # ── UI ────────────────────────────────────────────────────────────────────
    UI_POLL_MS     = 40
    UI_PULSE_MS    = 420

    # ── Misc ─────────────────────────────────────────────────────────────────
    CONF_SIGMOID_SCALE = 0.25
    CONF_SIGMOID_SHIFT = 15.0

    # Unified trading days — was 250 in indicators.py vs 252 in metrics.py
    TRADING_DAYS_PER_YEAR = 252

    # EGP risk-free rate (Egyptian T-bills ~12%)
    RISK_FREE_ANNUAL_PCT = 12.0

    # ── Data Guard (Module 1) ────────────────────────────────────────────
    DG_CANDLE_BAD_PCT_LIMIT  = 0.10   # reject if >10% bars have broken candles
    DG_VOL_ANOMALY_ZSCORE    = 3.0    # |Z| threshold per bar
    DG_VOLUME_ZSCORE_THRESHOLD = DG_VOL_ANOMALY_ZSCORE  # legacy alias for backtest overrides
    DG_CANDLE_SIZE_ATR_MULTIPLIER = 4.0                 # legacy backtest knob (unused by current DataGuard)
    DG_VOL_ANOMALY_PCT_LIMIT = 0.20   # reject if >20% of bars anomalous
    DG_CONFIDENCE_FULL       = 65.0   # ≥65 → full signal
    DG_CONFIDENCE_DEGRADED   = 40.0   # 40-64 → WATCH cap; <40 → rejected
    DG_IDEAL_BARS            = 200    # bar count for 100% sufficiency
    
    # ── Data Guard: Consecutive Zero Volume ──────────────────────────────
    DG_MAX_CONSECUTIVE_ZERO_VOL = 3   # flag if 3+ consecutive zero-volume days
    
    # ── Data Guard: Data Staleness ───────────────────────────────────────
    # Phase 3: Changed from calendar days to trading days (Sun-Thu only).
    # Accounts for Egyptian public holidays with 1-day/week buffer.
    DG_MAX_DATA_LAG_DAYS      = 3    # EGX trading days (was 4 calendar days)
    
    # ── Data Guard: Cross-Source Agreement ──────────────────────────────
    DG_CROSS_SOURCE_SPREAD_LIMIT = 0.05  # flag if sources disagree by more than 5%
    
    # ── Data Guard: Weights (must sum to 1.0) ─────────────────────────────
    DG_WEIGHT_CANDLE         = 0.35   # was 0.40
    DG_WEIGHT_VOLUME         = 0.25   # was 0.30
    DG_WEIGHT_BARS           = 0.25   # was 0.30
    DG_WEIGHT_ZVOL           = 0.15   # weight for consecutive-zero-volume check

    # ── Momentum Guard (Module 2) ────────────────────────────────────────
    MG_PERSISTENCE_MIN_EACH       = 2.0    # each day's momentum must clear this
    MG_LOSS_CLUSTER_WINDOW        = 5      # sessions to look back for stop-losses
    MG_LOSS_CLUSTER_TRIGGER       = 2      # stop-losses within window to trigger guard
    MG_DEFENSIVE_RANK_BOOST       = 5      # SmartRank threshold boost in defensive mode
    MG_DEFENSIVE_POSITION_SCALE   = 0.65   # position scale in defensive mode
    MG_EXEMPTION_THRESHOLD_NORMAL = 2.5    # momentum exemption in normal mode
    MG_EXEMPTION_THRESHOLD_GUARD  = 3.5    # momentum exemption in defensive mode
    MG_FATIGUE_WINDOW             = 10     # sessions to look back for breakout failures
    MG_FATIGUE_FAIL_RATE          = 0.6    # >60% failure → fatigue mode
    MG_FATIGUE_POSITION_SCALE     = 0.75   # position scale cap in fatigue mode
    # Trend structure confirmation — signal only passes when price > EMA20 AND price > EMA50
    MG_TREND_CONFIRM_ENABLED = True
    MG_TREND_CONFIRM_SPANS   = (20, 50)   # (fast_ema_span, slow_ema_span)
    # ── Alpha Monitor (Module 3) ──────────────────────────────────────
    AM_MIN_TRADES          = 10     # minimum resolved trades before warnings
    AM_LEVEL1_SHARPE       = 0.5    # Sharpe below this → Level 1
    AM_LEVEL2_SHARPE       = 0.2    # Sharpe below this → Level 2
    AM_LEVEL3_SHARPE       = 0.0    # Sharpe at/below this → Level 3
    AM_LEVEL1_EXPECTANCY   = 0.0    # expectancy below this → Level 1
    AM_LEVEL1_WINRATE      = 0.35   # win rate below this → Level 1
    AM_LEVEL2_WINRATE      = 0.25   # win rate below this → Level 2
    AM_LEVEL3_EXPECTANCY   = -0.02  # expectancy below this → Level 3

    # ── Position Manager (Module 4) ───────────────────────────────────
    PM_MAX_ADDONS_PER_POSITION = 1      # max add-ons per trade
    PM_ADDON_R                 = 0.5    # add-on size in R units
    PM_MAX_EXPOSURE_R          = 2.0    # hard ceiling: initial(1R) + addon(0.5R) = 1.5R max
    PM_ADD_MIN_PROFIT_PCT      = 3.0    # minimum open profit % to qualify
    PM_ADD_MIN_ADX             = 30.0   # minimum ADX
    PM_ADD_MIN_MOMENTUM        = 2.0    # minimum momentum score
    PM_ADDON_STOP_ATR_MULT     = 0.5    # add-on stop = current_price - (ATR × this)

    # ── Scan / Runner
    CACHE_TTL_SECONDS        = 3600
    MARKET_BREADTH_THRESHOLD = 0.50
    SCAN_MAX_WORKERS         = 8
    INDICATOR_CACHE_ENABLED  = True  # Can be disabled for debugging

    # ── Scoring
    CPI_FLOOR   = 0.1
    MOM_NORM_LO = -3.0
    MOM_NORM_HI =  6.0
    QUANTILE_NORM_ENABLED = True   # use quantile normalization for momentum when available

    # ── [P3-G2] RR Bonus ───────────────────────────────────────────────────
    RR_BONUS_ENABLED     = True
    RR_BONUS_THRESHOLD   = 3.0
    RR_BONUS_AMOUNT      = 0.05

    # ── Risk
    ATR_INTRADAY_THRESH = 1.5

    # ── Outcomes
    OUTCOME_STALE_MULTIPLIER = 2


_SR_WEIGHT_SUM = (
    K.SR_W_FLOW + K.SR_W_STRUCTURE + K.SR_W_TIMING +
    K.SR_W_MOMENTUM + K.SR_W_REGIME + K.SR_W_NEURAL
)
assert abs(_SR_WEIGHT_SUM - 1.0) < 1e-9, (
    f"SmartRank weights must sum to 1.0, got {_SR_WEIGHT_SUM}"
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTORS & SYMBOLS
# ═══════════════════════════════════════════════════════════════════════════

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


# ── Live account/risk setting accessors ──────────────────────────────────────
DATA_SOURCE_CFG: Dict[str, object] = {
    "alpha_vantage_key":  "",
    "use_yahoo":          True,
    "use_stooq":          True,
    "use_alpha_vantage":  False,
    "use_investing":      True,
    "use_twelve_data":    False,
    "twelve_data_key":    "",
    # ── Account / Risk settings (editable from UI) ───────────────────────
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
