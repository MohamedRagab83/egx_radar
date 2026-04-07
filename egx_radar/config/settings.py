
from typing import Dict, List
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
"""Global configuration and constants for EGX Radar (Layer 1)."""


import base64
import json
import math
import os
import tempfile
import threading
from typing import Dict, List


def _resolve_runtime_path(filename: str) -> str:
    data_dir = (
        os.environ.get("EGX_RADAR_DATA_DIR", "").strip()
        or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    )
    if not data_dir:
        return filename
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)


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
    # ── Brain mode ────────────────────────────────────────────────────────────
    BRAIN_SCORE_AGGRESSIVE = 6
    BRAIN_SCORE_NEUTRAL = 7
    BRAIN_SCORE_DEFENSIVE = 8


    # ── Data quality ────────────────────────────────────────────────────────
    MIN_BARS            = 60       # hard minimum for Yahoo path
    MIN_BARS_RELAXED    = 30       # relaxed minimum for Stooq/TD fallback
    LOW_LIQ_FILTER      = 150_000.0   # legacy share-volume floor (turnover filter is primary)
    PRICE_FLOOR         = 2.0      # minimum price in EGP
    LIQUIDITY_GATE_MIN_VOLUME = 100_000.0   # legacy share-volume gate
    MIN_TURNOVER_EGP    = 3_000_000.0  # ← lowered from 7M for hybrid (wider EGX coverage)
    MAX_SPREAD_PCT      = 4.5          # daily-range proxy ceiling; not a true bid/ask spread

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
    #
    # PHASE 5 CALIBRATION: Rebalanced to reduce factor concentration.
    # Previous weights were too concentrated on flow (35%). New weights distribute
    # more evenly across orthogonal factors to improve model adaptability.
    # Flow still important but reduced from 35% → 28%.
    # Structure increased to reward technical patterns more.
    # Timing increased to reward early entry signals.
    # Momentum enabled with quantile norm for better cross-sectional ranking.
    SR_W_FLOW        = 0.28   # reduced from 0.35 (less concentration)
    SR_W_STRUCTURE   = 0.28   # increased from 0.25 (reward technical patterns)
    SR_W_TIMING      = 0.22   # increased from 0.20 (reward early entry)
    SR_W_MOMENTUM    = 0.12   # increased from 0.10 (with quantile norm)
    SR_W_REGIME      = 0.10   # unchanged
    SR_W_NEURAL      = 0.00   # AI layer disabled — weight redistributed
    # Sum check: 0.28+0.28+0.22+0.12+0.10+0.00 = 1.00 ✓

    # ── Multi-Factor Rank weights (experimental parallel scoring) ────────
    # Independent from SmartRank. Used for research/comparison only.
    MF_W_TREND       = 0.30
    MF_W_MOMENTUM    = 0.25
    MF_W_VOLUME      = 0.25
    MF_W_VOLATILITY  = 0.20

    # ── Entry Timing Filter thresholds ────────────────────────────────
    ETF_GAIN_3D_THRESHOLD     = 8.0    # max 3-day gain % before blocking
    ETF_EMA200_THRESHOLD      = 12.0   # max % above EMA200 before blocking
    ETF_MINOR_BREAK_THRESHOLD = 2.5    # max minor break % before blocking

    SMART_RANK_SCALE    = 100.0  # position score output range: [0, 100]
    SMART_RANK_SMOOTHING = 0.5  # EWM alpha: higher = faster response
    SMART_RANK_ADX_CAP  = 70.0  # cap accumulation setups when trend quality is weak
    SMARTRANK_ENTRY_THRESHOLD = 75  # STRONG trade threshold
    SMARTRANK_MIN_ACTIONABLE = 65.0  # MEDIUM trade threshold

    # ── Sector configuration ──────────────────────────────────────────────────
    # Remove hard-block blacklist for EGX — use soft downgrade instead
    BLACKLISTED_SECTORS = set()

    # EGX-calibrated: sectors historically weak that should be downgraded
    WEAK_SECTOR_DOWNGRADE = {"REAL_ESTATE", "SERVICES"}  # soft downgrade for live scanning
    # BLACKLISTED_SECTORS_BT: previously blocked REAL_ESTATE + INDUSTRIAL only in backtest.
    # Emptied for live/backtest consistency — WEAK_SECTOR_DOWNGRADE applies to both.
    BLACKLISTED_SECTORS_BT: set = set()  # unified: no backtest-only hard blocks
    PRIORITY_SECTORS = []
    SECTOR_FILTER_ENABLED = False
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

    # ── Trade plan geometry ───────────────────────────────────────────────────
    PLAN_ENTRY_DISCOUNT  = 1.0
    PLAN_STOP_ADX_LOW    = 0.965
    PLAN_STOP_CLV_HIGH   = 0.970
    PLAN_STOP_DEFAULT    = 0.955
    PLAN_TARGET_HIGH     = 1.10    # ← realistic EGX swing target: 10% (was 1.15 — too ambitious)
    PLAN_TARGET_DEFAULT  = 1.08    # ← realistic EGX breakout target: 8% (was 1.12 — few trades hit it)
    PLAN_ANTICIPATION_HI = 0.60
    MAX_STOP_LOSS_PCT    = 0.05      # ← widened: let natural support work (position trading)
    PARTIAL_TP_PCT       = 0.07      # take partial profits at +7%
    TRAILING_TRIGGER_PCT = 0.05      # activate trailing stop at +5%
    TRAILING_STOP_PCT    = 0.03      # 3% trail width
    PULLBACK_MA20_MAX_DIST_PCT = 0.02
    PULLBACK_MA50_MAX_DIST_PCT = 0.03
    MAX_3DAY_GAIN_PCT    = 5.0       # ← tightened from 10.0 (reject recent surges)
    MAX_GAP_UP_PCT       = 2.0       # ← tightened from 3.0 (reject gap-ups)
    MAX_VERTICAL_EXTENSION_PCT = 0.08
    ANTI_FAKE_ABNORMAL_VOL_RATIO = 2.5

    # ─── POSITION MANAGEMENT ─────────────────────────────
    # Partial/trailing parameters centralized here (single source of truth)
    PARTIAL_EXIT_FRACTION     = 0.50   # sell 50% of position at first TP level
    RISK_PER_TRADE_STRONG     = 0.005  # 0.5% of portfolio for STRONG signals
    RISK_PER_TRADE_MEDIUM     = 0.002  # 0.2% of portfolio for MEDIUM signals  
    SLIPPAGE_PCT              = 0.003  # modeled round-trip slippage (pro)
    FEE_PCT                   = 0.0015 # EGX + broker fees (pro)
    MAX_OPEN_TRADES           = 6      # portfolio concurrency limit (pro)
    MAX_SECTOR_POSITIONS      = 2      # max positions per sector (guard)
    MAX_SECTOR_EXPOSURE_PCT   = 0.30   # max portfolio % per sector

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
    TRADE_TYPE_STRONG_MIN           = 70.0    # ← SR >= 70 = STRONG (full conviction)
    TRADE_TYPE_MEDIUM_MIN           = 45.0    # ← SR >= 45 = MEDIUM (reduced risk)
    RISK_PER_TRADE_STRONG           = 0.005   # 0.5% risk per STRONG trade
    RISK_PER_TRADE_MEDIUM           = 0.0020  # 0.20% risk per MEDIUM trade
    TRIGGER_FILL_TOLERANCE_PCT      = 0.001   # 0.1% trigger touch tolerance

    # ── Trade sizing ─────────────────────────────────────────────────────────
    ACCOUNT_SIZE         = 10_000.0
    RISK_PER_TRADE       = 0.005     # ← halved from 0.01 (0.5% risk per trade)

    # ── Portfolio guard ───────────────────────────────────────────────────────
    # FIX-G: Guard is now a pure function returning a new annotated list.
    PORTFOLIO_MAX_PER_SECTOR    = 2
    PORTFOLIO_MAX_ATR_EXPOSURE  = 0.04  # 4% of account in ATR units
    PORTFOLIO_MAX_OPEN_TRADES   = 3        # ← HYBRID: allow 3 concurrent trades
    PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT = 0.30

    # ── Trade outcome engine ──────────────────────────────────────────────────
    OUTCOME_LOG_FILE         = _resolve_runtime_path("trades_log.json")
    OUTCOME_HISTORY_FILE     = _resolve_runtime_path("trades_history.json")
    OUTCOME_LOOKFORWARD_DAYS = 20
    OUTCOME_MIN_BARS_NEEDED  = 3
    MAX_BARS_HELD            = 20
    PARTIAL_EXIT_FRACTION    = 0.50

    # ── Backtest costs & limits ───────────────────────────────────────────
    BT_SLIPPAGE_PCT  = 0.005        # minimum slippage per round-trip
    BT_FEES_PCT      = 0.002        # broker + EGX fees per round-trip
    BT_TOTAL_COST_PCT = BT_SLIPPAGE_PCT + BT_FEES_PCT
    BT_MAX_BARS      = 20           # default max holding period
    BT_DAILY_TOP_N   = 2            # ← HYBRID: allow top 2 signals per day
                                     # Set to 0 to disable (all allowed signals enter)
    # Phase 2b: minimum action quality for backtest entry
    # "ACCUMULATE" = SmartRank >= 40% of scale (>=24) — high conviction only
    # "PROBE"      = SmartRank >= 28% of scale (>=16.8) — includes weaker signals
    # Set to "ACCUMULATE" to filter out low-SmartRank entries
    BT_MIN_ACTION    = "PROBE"       # ← quality gate handles filtering, allow wider entry
    BT_MIN_SMARTRANK = 60.0          # ← raised to 60 to match live thresholds more closely (was 40)
    BT_GAP_DOWN_MAX_PCT = 0.12       # ← new: EGX ±10% daily limit; 12% caps data errors/corp actions
    BT_OOS_START     = "2025-01-01"     # Phase 4: recommended out-of-sample start date
                                         # Results before this date may be optimistically biased
    MIN_BARS_HELD            = 3
    OPTIMAL_BARS_LOW         = 7
    OPTIMAL_BARS_HIGH        = 20

    # ── Scan history & paper trading ──────────────────────────────────────────
    SCAN_HISTORY_ENABLED   = True    # auto-save daily scan CSV
    SCAN_HISTORY_KEEP_DAYS = 90      # delete scans older than 90 days

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
    MARKET_BREADTH_THRESHOLD = 0.45
    SCAN_MAX_WORKERS         = 8
    MARKET_BULL_STACKED_MIN  = 0.35
    MARKET_BEAR_BREADTH_MAX  = 0.45
    INDICATOR_CACHE_ENABLED  = True  # Can be disabled for debugging

    # ── Trade quality gate (shared by live scan AND backtest) ─────────────
    # is_high_probability_trade() uses these thresholds in BOTH paths.
    # Changing here affects both equally — no live/backtest divergence.
    SYMBOL_COOLDOWN_DAYS       = 30      # trading-day ban after N consecutive losses
    BT_SYM_COOLDOWN_LOSSES     = 2       # consecutive losses that trigger cooldown
    HQ_MIN_TURNOVER_EGP        = 7_000_000.0  # stricter turnover gate for high-quality filter
    HQ_MEDIUM_MIN_ADX          = 14.0    # ADX floor for MEDIUM-class trades (uses ADX_SOFT_LO)

    # ── Scoring
    CPI_FLOOR   = 0.1
    MOM_NORM_LO = -3.0
    MOM_NORM_HI =  6.0
    
    # PHASE 5: Enable quantile normalization for better factor orthogonality
    # This handles EGX's skewed momentum distribution better than linear normalization
    QUANTILE_NORM_ENABLED = True

    # ── [P3-G2] RR Bonus ───────────────────────────────────────────────────
    RR_BONUS_ENABLED     = False
    RR_BONUS_THRESHOLD   = 3.0
    RR_BONUS_AMOUNT      = 0.0

    # ── Risk
    ATR_INTRADAY_THRESH = 1.5

    # ── Outcomes
    OUTCOME_STALE_MULTIPLIER = 2


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
        value = float(DATA_SOURCE_CFG.get("account_size", K.ACCOUNT_SIZE))
    if not math.isfinite(value) or value < 1_000.0:
        return float(K.ACCOUNT_SIZE)
    return value


def get_risk_per_trade() -> float:
    with _data_cfg_lock:
        value = float(DATA_SOURCE_CFG.get("risk_per_trade", K.RISK_PER_TRADE))
    if not math.isfinite(value):
        return float(K.RISK_PER_TRADE)
    return float(min(max(value, 0.0005), 0.10))


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
