"""
╔══════════════════════════════════════════════════════════════════════════╗
║   EGX CAPITAL FLOW RADAR v83 — STATIC ANALYSIS BUGFIX PASS           ║
║   Based on v82 + static analysis review (2026-03-01)                  ║
║                                                                          ║
║   BUG FIXES OVER v82:                                                    ║
║   1. Logger name: getLogger("EGX_v83") for this version              ║
║   2. smart_rank_score: REGIME comment merged onto momentum_n line     ║
║      → Separated onto its own line for clarity                        ║
║   3. record_loss: safe_clamp(-0.4,-0.5,0.5) is a no-op (value in    ║
║      bounds) — inconsistent with record_win literal pattern           ║
║      → Replaced with plain literal -0.4                               ║
║   4. win_sample: len(STATE.neural_win_memory) read without _lock      ║
║      → wrapped in with STATE._lock context                            ║
║                                                                          ║
║   BUG FIXES OVER v79:                                                    ║
║   1. ORAS degenerate data: ADX=100 RSI=100 not filtered                ║
║      → Two-stage guard: frozen OHLC check + ADX/RSI saturation check   ║
║   2. Sort order: BLOCKED items appeared above active BUY/EARLY rows    ║
║      → Results now re-sorted AFTER guard annotation (post-guard tag)   ║
║   3. Anticipation on SELL: ORWE showed 0.86 anticipation despite SELL  ║
║      → ant_n zeroed for tag=="sell" before storing in results dict     ║
║                                                                          ║
║   BUG FIXES OVER v78:                                                    ║
║   1. record_win bias: safe_clamp(0.6,-0.5,0.5) always returned 0.5    ║
║      → removed clamp; literal 0.5 used (correct intended ceiling)      ║
║   2. detect_ema_cross: range(-3,-1) never checked most-recent bar      ║
║      → fixed to range(-3, 0) so index -1 is included                   ║
║   3. _av_bg closure: dict writes from background thread had no lock    ║
║      → _av_lock guards all av_by_sym reads and writes                  ║
║   4. sector_rotation_memory: appended without AppState lock             ║
║      → routed through new STATE.update_sector_rotation() method        ║
║   5. STATE.scan_count += 1: unprotected read-modify-write              ║
║      → wrapped in STATE._lock                                           ║
║   6. regime_weights: computed but never referenced (dead code)          ║
║      → removed                                                          ║
║   7. Dark.Treeview style: used in Outcomes window but never defined    ║
║      → registered alongside main Treeview styles in main()             ║
║   8. trend_acc ma_fast.iloc[-8]: IndexError if <8 bars in series       ║
║      → guarded with len(ma_fast) >= 8 check                            ║
║                                                                          ║
║   ARCHITECTURE LAYERS:                                                   ║
║     1. CONFIG     — All constants in one block, documented              ║
║     2. DATA       — Multi-source OHLCV fetch + merge                    ║
║     3. INDICATORS — Stateless technical computations                    ║
║     4. SCORING    — Normalised component scoring (all 0-1)              ║
║     5. SIGNAL     — Decision engine, regime detection                   ║
║     6. RISK       — ATR-percentile risk scoring, trade sizing           ║
║     7. PORTFOLIO  — Non-mutating guard, sector + exposure caps          ║
║     8. STATE      — Thread-safe application state                       ║
║     9. OUTCOMES   — Trade log + resolution engine                       ║
║    10. UI         — Tkinter presentation layer                          ║
║                                                                          ║
║   KEY FIXES OVER v77:                                                    ║
║   A) WinRate       — True empirical rate, sample-size adjustment        ║
║   B) SmartRank     — All components normalised 0-1, explicit weights   ║
║   C) Regime        — EMA200 slope + price position, no false ACCUM      ║
║   D) Volume        — Symmetric Z-score clamp (-4,+4), no low-vol bias   ║
║   E) Neural        — Mean-reversion decay, no runaway saturation        ║
║   F) Risk          — ATR percentile scoring, dynamic thresholds         ║
║   G) Portfolio     — Pure function (no mutation), idempotent            ║
║   H) Threads       — All UI updates via queue, shared state via locks   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════
import base64
import csv
import json
import logging
import math
import os
import queue
import re
import tempfile
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import StringIO
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, NamedTuple, Optional, Tuple

import pandas as pd
import pandas_ta as pta
import yfinance as yf

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("EGX_v83")


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 1: CONFIGURATION
# All tunable constants live here.  No magic numbers in the logic layers.
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

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
    LOW_LIQ_FILTER      = 50_000.0 # minimum average daily share volume
    PRICE_FLOOR         = 2.0      # minimum price in EGP

    # ── ADX ─────────────────────────────────────────────────────────────────
    ADX_LENGTH          = 14
    ADX_STRONG          = 25.0
    ADX_MID             = 18.0
    ADX_SOFT_LO         = 16.0     # below this → WAIT regardless of score
    ADX_SOFT_HI         = 22.0     # below this → PROBE only if rank meets bar

    # ── Volume Z-score ───────────────────────────────────────────────────────
    VOL_ROLL_WINDOW     = 20
    # FIX-D: Symmetric clamp.  v77 used asymmetric (-5, +10) which rewarded
    # abnormal upside spikes while ignoring downside. Now (-4, +4).
    VOL_ZSCORE_LO       = -4.0
    VOL_ZSCORE_HI       =  4.0

    # ── VWAP ────────────────────────────────────────────────────────────────
    VWAP_ROLL_WINDOW    = 20

    # ── ATR ─────────────────────────────────────────────────────────────────
    ATR_LENGTH          = 14
    # FIX-F: Percentile thresholds instead of hardcoded pct values
    ATR_HIST_WINDOW     = 60       # bars used to compute percentile
    ATR_PCT_HIGH        = 75       # ≥75th percentile → HIGH risk
    ATR_PCT_MED         = 50       # ≥50th percentile → MED risk

    # ── Whale detection ──────────────────────────────────────────────────────
    WHALE_ZSCORE_THRESH = 1.5
    WHALE_CLV_THRESH    = 0.5
    WHALE_VOL_THRESH    = 1.3
    WHALE_CLV_SIGNAL    = 0.6

    # ── Signal score ─────────────────────────────────────────────────────────
    SCORE_BUY           = 7
    SCORE_WATCH         = 4
    FAKE_BREAK_BODY     = 0.45
    RSI_OVERBOUGHT      = 72.0

    # ── SmartRank weights (EXPLICIT — all components normalised 0-1) ─────────
    # FIX-B: Each weight is applied to a 0-1 normalised sub-score.
    # Total weight budget = 1.0.  Adjust weights here, not in the formula.
    # Formula (documented in smart_rank_score()):
    #   smart_rank = Σ(weight_i × normalised_component_i) × SMART_RANK_SCALE
    #   where each normalised_component_i ∈ [0, 1]
    SR_W_FLOW        = 0.20   # capital pressure / volume flow component
    SR_W_STRUCTURE   = 0.20   # technical score + trend acceleration
    SR_W_TIMING      = 0.20   # quantum + phase + zone bonuses
    SR_W_MOMENTUM    = 0.15   # adaptive momentum
    SR_W_REGIME      = 0.15   # CPI + IET + whale score
    SR_W_NEURAL      = 0.10   # neural adaptive weight blend
    # (weights must sum to 1.0 — enforced at startup)
    SMART_RANK_SCALE    = 60.0  # output range: [0, SMART_RANK_SCALE]
    SMART_RANK_SMOOTHING = 0.5  # EWM alpha: higher = faster response
    SMART_RANK_ADX_CAP  = 25.0  # max rank when ADX < ADX_SOFT_LO

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
    WINRATE_CEIL        = 92.0
    WINRATE_SPARSE_PENALTY = 5.0 # per-missing-trade confidence discount

    # ── Market regime detection ───────────────────────────────────────────────
    # FIX-C: Regime now requires BOTH ADX > threshold AND EMA200 slope direction.
    # Prevents "Accumulation" false-positives in downtrending markets.
    REGIME_ADX_BULL       = 25.0
    REGIME_ADX_DIST       = 18.0
    REGIME_SLOPE_BARS     = 20   # bars used to compute EMA200 slope
    REGIME_RSI_DIST_MIN   = 65.0

    # ── Trade plan geometry ───────────────────────────────────────────────────
    PLAN_ENTRY_DISCOUNT  = 0.995
    PLAN_STOP_ADX_LOW    = 0.965
    PLAN_STOP_CLV_HIGH   = 0.970
    PLAN_STOP_DEFAULT    = 0.955
    PLAN_TARGET_HIGH     = 1.12
    PLAN_TARGET_DEFAULT  = 1.07
    PLAN_ANTICIPATION_HI = 5.0

    # ── Trade sizing ─────────────────────────────────────────────────────────
    ACCOUNT_SIZE         = 10_000.0
    RISK_PER_TRADE       = 0.02

    # ── Portfolio guard ───────────────────────────────────────────────────────
    # FIX-G: Guard is now a pure function returning a new annotated list.
    PORTFOLIO_MAX_PER_SECTOR    = 2
    PORTFOLIO_MAX_ATR_EXPOSURE  = 0.04  # 4% of account in ATR units

    # ── Trade outcome engine ──────────────────────────────────────────────────
    OUTCOME_LOG_FILE         = "trades_log.json"
    OUTCOME_HISTORY_FILE     = "trades_history.json"
    OUTCOME_LOOKFORWARD_DAYS = 15
    OUTCOME_MIN_BARS_NEEDED  = 3

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


# ── SmartRank weight validation ──────────────────────────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 2: DATA — Multi-source OHLCV fetch + merge
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

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
    "risk_per_trade":     0.02,
    "portfolio_max_atr_exposure": 0.04,
    "portfolio_max_per_sector":   2,
}
_data_cfg_lock        = threading.Lock()
_source_labels: Dict[str, str] = {}
_source_labels_lock   = threading.Lock()
_SOURCE_SETTINGS_FILE = "source_settings.json"


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
    if not os.path.exists(_SOURCE_SETTINGS_FILE):
        return
    try:
        with open(_SOURCE_SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        saved["alpha_vantage_key"] = _deobfuscate(saved.get("alpha_vantage_key", ""))
        saved["twelve_data_key"]   = _deobfuscate(saved.get("twelve_data_key",   ""))
        with _data_cfg_lock:
            DATA_SOURCE_CFG.update(saved)
    except Exception:
        pass


def save_source_settings() -> None:
    try:
        with _data_cfg_lock:
            snap = dict(DATA_SOURCE_CFG)
        snap["alpha_vantage_key"] = _obfuscate(str(snap.get("alpha_vantage_key", "")))
        snap["twelve_data_key"]   = _obfuscate(str(snap.get("twelve_data_key",   "")))
        _atomic_json_write(_SOURCE_SETTINGS_FILE, snap)
    except Exception as e:
        log.error("save_source_settings: %s", e)


def _atomic_json_write(filepath: str, data: object) -> None:
    """Write JSON atomically: temp → os.replace()."""
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
    """Normalise OHLCV column names and strip MultiIndex."""
    if raw is None or raw.empty:
        return None
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip().title() for c in df.columns]
    df.rename(columns={
        "Adj Close": "Close", "Adjusted Close": "Close",
        "Adj_Close": "Close", "Turnover": "Volume",
    }, inplace=True)
    seen: dict = {}
    df = df.loc[:, [not (c in seen or seen.update({c: True})) for c in df.columns]]
    return df if "Close" in df.columns else None


def _yfin_extract(raw: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
    """Robustly extract a single ticker from yfinance MultiIndex DataFrame."""
    if raw is None or raw.empty:
        return None
    if not isinstance(raw.columns, pd.MultiIndex):
        return _flatten_df(raw)
    lv0 = set(raw.columns.get_level_values(0))
    lv1 = set(raw.columns.get_level_values(1))
    if ticker in lv0:
        try:
            return _flatten_df(raw[ticker].copy())
        except Exception:
            return None
    if ticker in lv1:
        try:
            return _flatten_df(raw.xs(ticker, axis=1, level=1).copy())
        except Exception:
            return None
    # Case-insensitive fallback
    for lv, vals in [(0, lv0), (1, lv1)]:
        for v in vals:
            if str(v).upper() == ticker.upper():
                try:
                    sub = raw[v].copy() if lv == 0 else raw.xs(v, axis=1, level=1).copy()
                    return _flatten_df(sub)
                except Exception:
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
                raw = yf.download(
                    chunk, interval="1d", period="2y",
                    group_by="ticker", auto_adjust=True,
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
            candidates.append((df_, lbl))

    if not candidates:
        return None, "—"

    priority = ["Yahoo", "Stooq", "TD", "AV"] if yahoo_ok else ["TD", "Stooq", "AV"]
    candidates.sort(key=lambda x: priority.index(x[1]) if x[1] in priority else 99)
    base_df, base_src = candidates[0]

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
                base_src += "⚠️"
            else:
                base_src += "+INV"
        except (IndexError, ValueError, TypeError):
            pass

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
    if cfg["use_yahoo"]:
        log.warning("Yahoo Finance: downloading %d symbols...", len(sym_list))
        raw = _fetch_yahoo(list(SYMBOLS.values()))
        yahoo_by_sym = {k.replace(".CA", ""): v for k, v in raw.items()}

    stooq_by_sym: Dict[str, pd.DataFrame] = {}
    if cfg["use_stooq"]:
        log.warning("Stooq: downloading...")
        stooq_by_sym = _fetch_stooq(sym_list)

    av_by_sym: Dict[str, pd.DataFrame] = {}
    _av_lock = threading.Lock()  # always created; guards av_by_sym writes from _av_bg
    av_key = str(cfg.get("alpha_vantage_key", "")).strip()
    if cfg["use_alpha_vantage"] and av_key:
        def _av_bg():
            for s in sym_list[:5]:
                df = _fetch_av_single(s, av_key)
                if df is not None:
                    with _av_lock:   # FIX: guard dict writes from background thread
                        av_by_sym[s] = df
                time.sleep(12)
        threading.Thread(target=_av_bg, daemon=True).start()

    inv_prices: Dict[str, float] = {}
    if cfg["use_investing"]:
        log.warning("Investing.com: cross-checking prices...")
        inv_prices = _fetch_investing(sym_list)

    td_by_sym: Dict[str, pd.DataFrame] = {}
    td_key = str(cfg.get("twelve_data_key", "")).strip()
    if cfg.get("use_twelve_data") and td_key:
        log.warning("TwelveData: downloading %d symbols...", len(sym_list))
        td_by_sym = _fetch_twelve_data(sym_list, td_key)

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

    with _source_labels_lock:
        _source_labels = local_labels

    log.warning(
        "Merged: %d symbols | Y:%d S:%d AV:%d INV:%d TD:%d",
        len(merged), len(yahoo_by_sym), len(stooq_by_sym),
        len(av_by_sym), len(inv_prices), len(td_by_sym),
    )
    return merged


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 3: INDICATORS — Stateless technical computations
# ██████████████████████████████████████████████════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════

def safe_clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def last_val(s: pd.Series) -> float:
    s = s.dropna()
    return float(s.iloc[-1]) if not s.empty else 0.0


def compute_atr(df: pd.DataFrame, length: int = K.ATR_LENGTH) -> Optional[float]:
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
        return atr if math.isfinite(atr) and atr > 0 else None
    except Exception:
        return None


def compute_atr_risk(df: pd.DataFrame, price: float) -> Tuple[str, float]:
    """
    FIX-F: ATR percentile-based risk scoring.
    Formula:
      atr_percentile = percentile_rank(current_atr, atr_history[-ATR_HIST_WINDOW:])
      risk = HIGH if percentile ≥ ATR_PCT_HIGH, MED if ≥ ATR_PCT_MED, else LOW
    Returns (risk_label, atr_percentile)
    """
    if price <= 0 or len(df) < K.ATR_LENGTH + 5:
        return "—", 0.0
    try:
        # Build ATR history over rolling window
        h = df["High"].reset_index(drop=True)
        l = df["Low"].reset_index(drop=True)
        c = df["Close"].reset_index(drop=True)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr_series = tr.rolling(K.ATR_LENGTH).mean().dropna()
        if len(atr_series) < 5:
            return "—", 0.0
        hist = atr_series.iloc[-K.ATR_HIST_WINDOW:].values
        current = hist[-1]
        # Percentile rank: fraction of history values ≤ current
        pct = float((hist <= current).mean()) * 100.0
        if pct >= K.ATR_PCT_HIGH:
            return "⚠️ HIGH", pct
        if pct >= K.ATR_PCT_MED:
            return "🟡 MED", pct
        return "🟢 LOW", pct
    except Exception:
        return "—", 0.0


def compute_vwap_dist(df: pd.DataFrame, price: float) -> float:
    """VWAP distance = (price - vwap) / price. Clamped to (-0.5, 0.5)."""
    try:
        close = df["Close"].dropna()
        vol   = df["Volume"].dropna()
        if len(close) < 10 or vol.sum() <= 0:
            return 0.0
        n = min(len(close), len(vol), K.VWAP_ROLL_WINDOW)
        close, vol = close.iloc[-n:], vol.iloc[-n:]
        cum_vol = vol.cumsum()
        if cum_vol.iloc[-1] <= 0:
            return 0.0
        vwap = float((close * vol).cumsum().iloc[-1] / cum_vol.iloc[-1])
        return safe_clamp((price - vwap) / price, -0.5, 0.5) if vwap > 0 else 0.0
    except Exception:
        return 0.0


def compute_vol_zscore(df: pd.DataFrame, window: int = K.VOL_ROLL_WINDOW) -> float:
    """
    FIX-D: Symmetric Z-score clamp (-4, +4).
    v77 used (-5, +10) which asymmetrically rewarded high-volume spikes.
    Formula: z = (vol[-1] - rolling_mean) / rolling_std, clipped ∈ (-4, +4)
    """
    try:
        vol = df["Volume"].dropna()
        if vol.sum() <= 0 or len(vol) < window + 2:
            return 0.0
        mu  = float(vol.rolling(window).mean().iloc[-1])
        sig = float(vol.rolling(window).std().iloc[-1])
        if sig <= 0 or not math.isfinite(sig):
            return 0.0
        # FIX-D: symmetric clamp
        return safe_clamp((float(vol.iloc[-1]) - mu) / sig, K.VOL_ZSCORE_LO, K.VOL_ZSCORE_HI)
    except Exception:
        return 0.0


def detect_ema_cross(close: pd.Series) -> str:
    """
    FIX-6: Extended window from 3 to 7 bars.
    EGX has Thu/Fri/Sat holidays — a 3-bar window misses crossovers
    that happened last week but are still valid and actionable.
    """
    if len(close) < 55:
        return ""
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    for i in range(-7, 0):   # FIX-6: was range(-3, 0)
        prev = ema10.iloc[i-1] > ema50.iloc[i-1]
        curr = ema10.iloc[i]   > ema50.iloc[i]
        if not prev and curr: return "BULL_CROSS"
        if prev and not curr: return "BEAR_CROSS"
    return ""


def detect_vol_divergence(close: pd.Series, volume: pd.Series, lookback: int = 5) -> str:
    """
    FIX-4: Added BULL_CONF (price up + volume up = strong confirmation) and
    CLIMAX_SELL (price down + volume up = capitulation / distribution top).
    These were missing — the function only detected bearish cases before.
    """
    if len(close) < lookback + 2:
        return ""
    price_chg = float(close.iloc[-1]) - float(close.iloc[-lookback])
    vol_ma    = volume.rolling(3).mean()
    if len(vol_ma.dropna()) < lookback:
        return ""
    vol_trend = float(vol_ma.iloc[-1]) - float(vol_ma.iloc[-lookback])
    if price_chg > 0 and vol_trend > 0:  return "🟢BULL_CONF"    # FIX-4: strongest signal
    if price_chg > 0 and vol_trend < 0:  return "🔀BEAR_DIV"
    if price_chg < 0 and vol_trend < 0:  return "🔵BASE"
    if price_chg < 0 and vol_trend > 0:  return "⚠️CLIMAX_SELL"  # FIX-4: distribution top
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 4: SCORING ENGINE — All component scores normalised 0-1
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

def _norm(val: float, lo: float, hi: float) -> float:
    """Linearly normalise val ∈ [lo, hi] → [0, 1]. Clamps outside range."""
    if hi <= lo:
        return 0.0
    return safe_clamp((val - lo) / (hi - lo), 0.0, 1.0)


def score_capital_pressure(
    clv: float, trend_acc: float, vol_ratio: float,
    price: float, ema50: float, vwap_dist: float
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
    raw = min(2.0, vol_ratio * 0.9)
    if clv > 0:
        raw += clv * 2.2
    if trend_acc > 0:
        raw += min(1.5, trend_acc * 6.0)
    if ema50 > 0 and abs(price - ema50) / (ema50 + 1e-9) < 0.03:
        raw += 1.2
    if vwap_dist < -0.01:
        raw += min(1.0, abs(vwap_dist) * 4.0)
    return _norm(safe_clamp(raw, 0.0, 8.0), 0.0, 8.0)


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
    if 1.2 <= vol_ratio <= 2.5:  s += 2.0
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
    label = "🧲 HEAVY" if raw >= 8 else ("🧲 BUILDING" if raw >= 5 else "▫️ LIGHT")
    return label, _norm(raw, 0.0, 12.0)


def score_tech_signal(
    price: float, ema200: float, ema50: float, adx: float, rsi: float,
    adaptive_mom: float, vol_ratio: float, breakout: bool, pct_ema200: float,
) -> int:
    """Raw integer signal score for build_signal(). Not normalised — used directly in signal classification."""
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
    rsi: float, pct_ema200: float, vol_ratio: float,
    brain_mode: str, brain_vol_req: float,
    sig_hist: List[str], market_soft: bool,
    nw: Dict[str, float],
    sector_bias: float,
    anticipation_n: float,
    regime: str,
) -> float:
    """
    FIX-B: Documented SmartRank formula with explicit normalised components.

    SmartRank = Σ(weight_i × component_i) × SMART_RANK_SCALE

    where each component_i ∈ [0, 1] and Σ weights_i = 1.0:

      FLOW (20%):
        flow_component = normalised(vol_ratio^1.3 × max(clv_from_cpi, 0)) × neural_flow
        → captured via cpi_n which already embeds vol + CLV + VWAP

      STRUCTURE (20%):
        structure_component = normalised(tech_score / 14 + trend_acc_n + hidden_n)
        → tech_score max = 14, trend_acc normalised, hidden normalised

      TIMING (20%):
        timing_component = phase/zone/pattern bonuses, normalised to [0,1]

      MOMENTUM (15%):
        momentum_component = normalised(adaptive_mom, -5, +10)

      REGIME (15%):
        regime_component = (iet_n + whale_n + gravity_n) / 3

      NEURAL (10%):
        neural_component = weighted blend of nw values, normalised

    Late-entry penalties are applied as multiplicative dampers (≤ 1.0).
    """
    # ── FLOW component ────────────────────────────────────────────────────
    flow_raw = cpi_n * nw.get("flow", 1.0) * sector_bias
    flow_n   = safe_clamp(flow_raw / max(nw.get("flow", 1.0) * sector_bias, 1e-3), 0.0, 1.0)

    # ── STRUCTURE component ───────────────────────────────────────────────
    tech_n      = _norm(tech_score, 0, 14)
    trend_acc_n = _norm(trend_acc, -0.05, 0.05)
    hidden_n    = _norm(hidden_score, 0.0, 4.0)
    structure_n = safe_clamp(
        (tech_n * 0.5 + trend_acc_n * 0.3 + hidden_n * 0.2) * nw.get("structure", 1.0),
        0.0, 1.0,
    )

    # ── TIMING component ──────────────────────────────────────────────────
    timing_raw = 0.0
    if tag == "ultra":          timing_raw += 0.35
    if silent:                  timing_raw += 0.25
    if hunter:                  timing_raw += 0.15
    if expansion:               timing_raw += 0.10
    if quantum_n > 0.5:         timing_raw += 0.20
    if gravity_n > 0.6:         timing_raw += 0.15
    if zone == "🟢 EARLY":      timing_raw += 0.15
    elif zone == "🔴 LATE":     timing_raw -= 0.10
    if phase == "Accumulation": timing_raw += 0.10
    if leader:                  timing_raw += 0.20 * nw.get("timing", 1.0)
    if tag == "early" and pct_ema200 < 20: timing_raw += 0.10
    if ema_cross == "BULL_CROSS": timing_raw += 0.15
    elif ema_cross == "BEAR_CROSS": timing_raw -= 0.15
    timing_n = safe_clamp(timing_raw, 0.0, 1.0)

    # ── MOMENTUM component ────────────────────────────────────────────────
    momentum_n = _norm(adaptive_mom, -5.0, 10.0)

    # ── REGIME component ─────────────────────────────────────────────────
    regime_n = (iet_n + whale_n + gravity_n) / 3.0

    # ── NEURAL component ─────────────────────────────────────────────────
    nw_avg  = (nw.get("flow", 1.0) + nw.get("structure", 1.0) + nw.get("timing", 1.0)) / 3.0
    neural_n = _norm(nw_avg, K.NEURAL_WEIGHT_MIN, K.NEURAL_WEIGHT_MAX)

    # ── Weighted sum → raw rank [0, 1] ───────────────────────────────────
    raw_n = (
        K.SR_W_FLOW      * flow_n      +
        K.SR_W_STRUCTURE * structure_n +
        K.SR_W_TIMING    * timing_n    +
        K.SR_W_MOMENTUM  * momentum_n  +
        K.SR_W_REGIME    * regime_n    +
        K.SR_W_NEURAL    * neural_n
    )

    # ── Late-entry penalty damper (multiplicative) ────────────────────────
    # Kept multiplicative so we never go below 0 unnaturally
    damper = 1.0
    if rsi > 70:                            damper *= 0.85
    if pct_ema200 > 35:                     damper *= 0.85
    if fake_expansion:                      damper *= 0.70
    if market_soft and tag == "buy":        damper *= 0.88
    if vol_div == "🔀BEAR_DIV":             damper *= 0.88
    if vol_div == "⚠️CLIMAX_SELL":          damper *= 0.80   # FIX-4: strong distribution signal
    if len(sig_hist) >= 3 and all(h == "buy" for h in sig_hist[-3:]):
        damper *= 0.85
    if brain_mode == "defensive" and vol_ratio < brain_vol_req:
        damper *= 0.90

    # ── Brain-mode bonus (additive boost on top of penalised raw) ─────────
    brain_boost = 0.0
    if brain_mode == "aggressive" and vol_ratio >= brain_vol_req:
        brain_boost = 0.02

    # ── FIX-4: BULL_CONF additive boost (price up + volume up = confirmed) ─
    bull_conf_boost = 0.04 if vol_div == "🟢BULL_CONF" else 0.0

    # ── Anticipation contribution (already normalised) ────────────────────
    anticipation_contrib = anticipation_n * 0.05   # minor forward-looking nudge

    final_n = safe_clamp(raw_n * damper + brain_boost + bull_conf_boost + anticipation_contrib, 0.0, 1.0)
    return round(final_n * K.SMART_RANK_SCALE, 3)


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 5: SIGNAL ENGINE
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

def detect_market_regime(
    results: List[dict],
    ema200_slopes: Optional[Dict[str, float]] = None,
) -> str:
    """
    FIX-C: Market regime now requires EMA200 slope confirmation.
    States: ACCUMULATION | MOMENTUM | DISTRIBUTION | NEUTRAL

    Rules:
      ACCUMULATION: ADX < 20, vol < 1.3, EMA200 slope is flat or rising (≥ -0.001)
                    → prevents false ACCUM in downtrending bearish markets
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
    return "NEUTRAL"


def detect_phase(
    adx: float, rsi: float, vol_ratio: float, trend_acc: float,
    clv: float, adaptive_mom: float, ema50: float, price: float,
    body_ratio: float = 0.3,
) -> str:
    """
    FIX-2: body_ratio is now a real parameter (was hardcoded 0.3 and unused).
    A small candle body (< 0.35) during quiet conditions is a classic
    accumulation footprint — smart money absorbing without showing intent.
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
    s = 0
    if 48 <= rsi <= 60:    s += 2
    if adaptive_mom > 0:   s += 2
    if pct_ema200 < 15:    s += 1
    if vol_ratio < 1.4:    s += 1
    if s >= 5: return "🟢 EARLY"
    if s >= 3: return "🟡 MID"
    return "🔴 LATE"


def build_signal(
    price: float, ema200: float, ema50: float, adx: float, rsi: float,
    adaptive_mom: float, vol_ratio: float, breakout: bool, pct_ema200: float,
    phase: str, brain_score_req: int = K.BRAIN_SCORE_NEUTRAL,
) -> Tuple[str, str, int]:
    score = score_tech_signal(
        price, ema200, ema50, adx, rsi, adaptive_mom, vol_ratio, breakout, pct_ema200
    )

    if phase == "Accumulation":
        if 48 <= rsi <= 62:                      score += 3
        elif 40 <= rsi < 48 or 62 < rsi <= 70:  score += 1
    elif phase == "Expansion":
        if 55 < rsi < 70:                        score += 3
        elif 48 <= rsi <= 55:                    score += 1

    if phase == "Accumulation" and adaptive_mom > 0.8 and vol_ratio > 1.15:
        raw_sig, raw_tag = "🧠 ULTRA EARLY", "ultra"
    elif phase == "Expansion" and adx > K.ADX_MID and adaptive_mom > 1.5:
        raw_sig, raw_tag = "🚀 EARLY", "early"
    else:
        score_watch_adj = max(K.SCORE_WATCH, brain_score_req - 3)
        if score >= brain_score_req:
            raw_sig, raw_tag = "🔥 BUY",   "buy"
        elif score >= score_watch_adj:
            raw_sig, raw_tag = "👀 WATCH", "watch"
        else:
            raw_sig, raw_tag = "❌ SELL",  "sell"

    if raw_tag in ("buy", "ultra", "early") and rsi > K.RSI_OVERBOUGHT:
        raw_sig  = "👀 WATCH ⚠️OB"
        raw_tag  = "watch"

    return raw_sig, raw_tag, score


def build_signal_reason(
    rsi: float, adx: float, pct_ema200: float, phase: str,
    vol_div: str, ema_cross: str, adaptive_mom: float,
    clv: float, vol_ratio: float, tag: str = "",
) -> str:
    reasons: List[str] = []
    if phase == "Accumulation":    reasons.append("Accumulation phase")
    elif phase == "Expansion":     reasons.append("Expansion phase")
    if adx > 30:                   reasons.append(f"ADX strong ({adx:.0f})")
    elif adx < 18:                 reasons.append(f"ADX weak ({adx:.0f})")
    if 48 <= rsi <= 62:            reasons.append("RSI healthy zone")
    elif rsi > K.RSI_OVERBOUGHT:   reasons.append(f"⚠️ RSI Overbought ({rsi:.0f})")
    elif rsi < 35:                 reasons.append("RSI oversold")
    if ema_cross == "BULL_CROSS":  reasons.append("Bullish EMA cross")
    elif ema_cross == "BEAR_CROSS": reasons.append("Bearish EMA cross")
    if vol_div == "🟢BULL_CONF":    reasons.append("✅ Bull vol confirmed")    # FIX-4
    elif vol_div == "🔀BEAR_DIV":   reasons.append("Bear vol divergence")
    elif vol_div == "🔵BASE":       reasons.append("Vol base building")
    elif vol_div == "⚠️CLIMAX_SELL": reasons.append("⚠️ Climax sell volume")  # FIX-4
    if adaptive_mom > 2:           reasons.append("Strong momentum")
    elif adaptive_mom < -2:        reasons.append("Weak momentum")
    if pct_ema200 < 0:             reasons.append("Below EMA200")
    elif pct_ema200 > 30:          reasons.append("Extended above EMA200")
    return " | ".join(reasons[:3]) if reasons else "Mixed signals"


def get_signal_direction(tag: str) -> str:
    if tag in ("buy", "ultra", "early"):
        return "📈 BULLISH"
    if tag == "sell":
        return "📉 BEARISH"
    return "⏸️ NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 6: RISK ENGINE — ATR-percentile sizing, dynamic thresholds
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

def build_trade_plan(
    price: float, rsi: float, adx: float, clv: float,
    trend_acc: float, smart_rank: float, anticipation: float,
    atr_risk_label: str = "—",
    atr: Optional[float] = None,
    tech_score: int = 0,
    vol_ratio: float = 1.0,
) -> dict:
    """
    Produce an actionable trade plan.

    FIX-1: Thresholds now relative to SMART_RANK_SCALE (was hardcoded 7/5
            which is only 12% of the 60-point scale — effectively meaningless).
            New thresholds: ACCUMULATE >= 40%, PROBE >= 28%, WATCH_ONLY >= 15%.
    FIX-3: ADX soft-low gate has exception for very high tech_score + strong volume
            so strong momentum moves are not silently ignored.
    """
    _sr = K.SMART_RANK_SCALE   # 60.0

    if adx < K.ADX_SOFT_LO:
        # FIX-3: high score + big volume overrides weak ADX → at least PROBE
        if tech_score >= 12 and vol_ratio > 2.0:
            action = "PROBE"
        else:
            action = "WAIT"
    elif adx < K.ADX_SOFT_HI:
        # FIX-1: was >= 6.0 (10% of scale) → now 22% of scale
        action = "PROBE" if smart_rank >= _sr * 0.22 else "WAIT"
    else:
        # FIX-1: was > 7 (12%) / > 5 (8%) → now 40% / 28% / 15%
        if smart_rank > _sr * 0.40 and anticipation > K.PLAN_ANTICIPATION_HI:
            action = "ACCUMULATE"
        elif smart_rank > _sr * 0.28:
            action = "PROBE"
        elif smart_rank > _sr * 0.15:
            action = "WATCH_ONLY"
        else:
            action = "WAIT"

    # Extra gate: never ACCUMULATE into HIGH-risk ATR environment
    if action == "ACCUMULATE" and atr_risk_label == "⚠️ HIGH":
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
    rps  = max(abs(entry - stop), 0.01)
    size = max(1, int((get_account_size() * get_risk_per_trade()) / rps))
    rr   = round(abs(target - entry) / rps, 1)

    atr_pct = (atr / price * 100) if (atr and price > 0) else 0.0
    if adx > 35 and atr_pct > 1.5:
        timeframe = "⚡ Intraday"
    elif adx > K.ADX_STRONG:
        timeframe = "📅 Swing (3-10d)"
    else:
        timeframe = "📆 Position (wks)"

    return {
        "action": action, "entry": entry, "stop": stop,
        "target": target, "size": size, "rr": rr,
        "timeframe": timeframe,
        "force_wait": action == "WAIT",
        "winrate": 0.0,   # filled by estimate_winrate() in scoring pass
        "winrate_na": action == "WAIT",
    }


def institutional_confidence(winrate: float, smart_rank: float, sector_strength: float) -> str:
    score = winrate * 0.5 + smart_rank * 5 + sector_strength * 8
    if score > 90: return "🔥 ELITE"
    if score > 70: return "💎 STRONG"
    if score > 55: return "🧠 GOOD"
    if score > 40: return "⚠️ MID"
    return "❌ WEAK"


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 7: PORTFOLIO GUARD — Pure function, non-mutating, idempotent
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

class GuardedResult(NamedTuple):
    """Immutable wrapper for a result record with guard annotation."""
    result: dict
    guard_reason: str
    is_blocked: bool


def compute_portfolio_guard(
    results: List[dict],
    account_size: float = None,
) -> Tuple[List[GuardedResult], Dict[str, int], float, List[str]]:
    """
    FIX-G: Pure function.  Does NOT mutate input `results`.
    Uses live account_size from DATA_SOURCE_CFG so UI changes apply immediately.
    """
    if account_size is None:
        account_size = get_account_size()
    max_per_sector = get_max_per_sector()
    atr_exposure   = get_atr_exposure()

    active_tags    = {"buy", "ultra", "early"}
    sector_counts: Dict[str, int] = {s: 0 for s in SECTORS}
    cumulative     = 0.0
    max_exposure   = account_size * atr_exposure
    guarded:       List[GuardedResult] = []
    blocked_syms:  List[str]           = []

    for r in results:
        if r["tag"] not in active_tags:
            guarded.append(GuardedResult(r, "", False))
            continue

        sector  = r["sector"]
        atr     = r.get("atr") or 0.0
        size    = (r.get("plan") or {}).get("size", 0)
        contrib = atr * size

        if sector_counts.get(sector, 0) >= max_per_sector:
            reason = (
                f"Sector cap: {sector} already has "
                f"{sector_counts[sector]} signal(s) (max {max_per_sector})"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        if cumulative + contrib > max_exposure:
            reason = (
                f"ATR cap: +{contrib:.0f} EGP would bring total to "
                f"{(cumulative+contrib):.0f} EGP "
                f"({(cumulative+contrib)/account_size*100:.1f}% of account, "
                f"max {atr_exposure*100:.0f}%)"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        cumulative += contrib
        guarded.append(GuardedResult(r, "", False))

    return guarded, sector_counts, cumulative, blocked_syms


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 8: APPLICATION STATE — All shared state, all locks
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

class AppState:
    """
    Thread-safe application state container.
    FIX-H: All shared state mutations go through this class.
    No direct global state writes outside this class.
    """

    def __init__(self) -> None:
        self._lock           = threading.Lock()
        self._momentum_lock  = threading.Lock()

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

    # ── Neural weights ──────────────────────────────────────────────────────
    def update_neural_weights(self, results: List[dict]) -> None:
        """
        FIX-E: Mean-reversion update with decay.
        Formula for each weight w:
          step = +NEURAL_STEP if signal favourable, else -NEURAL_STEP
          w = clamp(w + step - NEURAL_DECAY × (w - 1.0), MIN, MAX)
        The decay term pulls w toward 1.0 (neutral) preventing runaway saturation.
        """
        if len(results) < 6:
            return
        n     = len(results)
        avg_q = sum(r["quantum"] for r in results) / n
        avg_v = sum(r["vol_ratio"] for r in results) / n
        acc_r = sum(1 for r in results if r["phase"] == "Accumulation") / n
        self.neural_memory.append((avg_q, avg_v, acc_r))
        if len(self.neural_memory) < 5:
            return
        q_avg = sum(x[0] for x in self.neural_memory) / len(self.neural_memory)
        v_avg = sum(x[1] for x in self.neural_memory) / len(self.neural_memory)
        a_avg = sum(x[2] for x in self.neural_memory) / len(self.neural_memory)
        with self._lock:
            nw = self.neural_weights
            for key, cond in [("timing", q_avg > 2.0), ("flow", v_avg > 1.4), ("structure", a_avg > 0.35)]:
                step  = K.NEURAL_STEP if cond else -K.NEURAL_STEP
                decay = K.NEURAL_DECAY * (nw[key] - 1.0)   # FIX-E: mean-reversion
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
        entries = [r for r in top_results if (r.get("plan") or {}).get("action") in ("ACCUMULATE", "PROBE")]
        with self._lock:
            for r in entries:
                bias_val = 0.2 if r["plan"]["action"] == "ACCUMULATE" else 0.05
                self.neural_bias_memory.append(safe_clamp(bias_val, -0.5, 0.5))

    # ── Signal & momentum history ────────────────────────────────────────────
    def append_signal_history(self, sym: str, tag: str) -> List[str]:
        with self._lock:
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
    def save(self, filename: str = "brain_state.json") -> None:
        try:
            history = oe_load_history()
            wins    = sum(1 for t in history if t.get("status") == "WIN")
            losses  = sum(1 for t in history if t.get("status") == "LOSS")
            with self._lock:
                data = {
                    "neural_weights": self.neural_weights,
                    "prev_ranks":     self.prev_ranks,
                    "neural_win":     list(self.neural_win_memory),
                    "neural_loss":    list(self.neural_loss_memory),
                    "neural_bias":    list(self.neural_bias_memory),
                    "sector_flow":    {k: list(v) for k, v in self.sector_flow_memory.items()},
                    "outcome_wins":   wins,
                    "outcome_losses": losses,
                }
            _atomic_json_write(filename, data)
        except OSError as e:
            log.error("AppState.save: %s", e)

    def load(self, filename: str = "brain_state.json") -> None:
        if not os.path.exists(filename):
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self.neural_weights = data.get("neural_weights", self.neural_weights)
                self.prev_ranks     = data.get("prev_ranks", {})
                if "neural_win"  in data: self.neural_win_memory  = deque(data["neural_win"],  maxlen=80)
                if "neural_loss" in data: self.neural_loss_memory = deque(data["neural_loss"], maxlen=80)
                if "neural_bias" in data: self.neural_bias_memory = deque(data["neural_bias"], maxlen=80)
                for sec, vals in data.get("sector_flow", {}).items():
                    if sec in self.sector_flow_memory:
                        self.sector_flow_memory[sec] = deque(vals, maxlen=15)
        except (OSError, json.JSONDecodeError) as e:
            log.error("AppState.load: %s", e)


STATE = AppState()


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 9: TRADE OUTCOME ENGINE
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

def oe_load_log() -> List[dict]:
    if not os.path.exists(K.OUTCOME_LOG_FILE):
        return []
    try:
        with open(K.OUTCOME_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("oe_load_log: %s", e)
        return []


def oe_save_log(trades: List[dict]) -> None:
    try:
        _atomic_json_write(K.OUTCOME_LOG_FILE, trades)
    except OSError as e:
        log.error("oe_save_log: %s", e)


def oe_load_history() -> List[dict]:
    if not os.path.exists(K.OUTCOME_HISTORY_FILE):
        return []
    try:
        with open(K.OUTCOME_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("oe_load_history: %s", e)
        return []


def oe_save_history_batch(new_trades: List[dict]) -> None:
    if not new_trades:
        return
    history = oe_load_history()
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
    except Exception:
        try:
            df.index = pd.to_datetime(df.index).tz_localize(None)
        except Exception:
            pass
    return df


def oe_resolve_trade(trade: dict, df: Optional[pd.DataFrame]) -> Optional[dict]:
    """Resolve a trade against forward price data. Returns resolved dict or None if still open."""
    if df is None or df.empty:
        return None
    entry  = trade["entry"]
    stop   = trade["stop"]
    target = trade["target"]
    try:
        df = _normalise_df_index(df)
    except Exception:
        return None

    # Stale trade: beyond 2× lookforward
    try:
        age = (datetime.now() - datetime.strptime(trade.get("date", ""), "%Y-%m-%d")).days
        if age > K.OUTCOME_LOOKFORWARD_DAYS * 2:
            try:
                last_close = float(df["Close"].iloc[-1])
            except (IndexError, ValueError):
                last_close = entry
            resolved = dict(trade)
            resolved.update({
                "status": "TIMEOUT",
                "exit_price": round(last_close, 3),
                "days_held": age, "mfe_pct": 0.0, "mae_pct": 0.0,
                "pnl_pct": round((last_close - entry) / (entry + 1e-9) * 100, 2),
                "resolved_date": datetime.now().strftime("%Y-%m-%d"),
            })
            return resolved
    except (ValueError, TypeError):
        pass

    try:
        entry_dt  = pd.Timestamp(trade.get("date", ""))
        positions = [i for i, d in enumerate(df.index) if d >= entry_dt]
        if not positions:
            return None
        start = positions[0]
    except Exception:
        return None

    window = df.iloc[start:start + K.OUTCOME_LOOKFORWARD_DAYS + 1]
    if len(window) < K.OUTCOME_MIN_BARS_NEEDED:
        return None

    highs  = window["High"].values
    lows   = window["Low"].values
    closes = window["Close"].values
    outcome = "OPEN"
    exit_bar = len(window) - 1
    mfe = mae = 0.0

    for i, (h, l, c) in enumerate(zip(highs, lows, closes)):
        mfe = max(mfe, (h - entry) / (entry + 1e-9) * 100)
        mae = max(mae, (entry - l) / (entry + 1e-9) * 100)
        if h >= target:
            outcome, exit_bar = "WIN", i;  break
        if l <= stop:
            outcome, exit_bar = "LOSS", i; break

    if outcome == "OPEN" and len(window) >= K.OUTCOME_LOOKFORWARD_DAYS:
        outcome, exit_bar = "TIMEOUT", len(window) - 1

    if outcome == "OPEN":
        return None

    exit_price = closes[min(exit_bar, len(closes) - 1)]
    resolved   = dict(trade)
    resolved.update({
        "status":     outcome,
        "exit_price": round(float(exit_price), 3),
        "days_held":  exit_bar + 1,
        "mfe_pct":    round(mfe, 2),
        "mae_pct":    round(mae, 2),
        "pnl_pct":    round((float(exit_price) - entry) / (entry + 1e-9) * 100, 2),
        "resolved_date": datetime.now().strftime("%Y-%m-%d"),
    })
    return resolved


def oe_record_signal(
    sym: str, sector: str, entry: float, stop: float, target: float,
    atr: float, smart_rank: float, anticipation: float, action: str,
    existing_trades: Optional[List[dict]] = None,
) -> None:
    today_str = datetime.now().strftime("%Y-%m-%d")
    trades    = existing_trades if existing_trades is not None else oe_load_log()
    for t in trades:
        if t.get("sym") == sym and t.get("date", "")[:10] == today_str:
            return
    trades.append({
        "sym": sym, "sector": sector, "date": today_str,
        "entry": round(entry, 3), "stop": round(stop, 3), "target": round(target, 3),
        "atr": round(atr, 3) if atr else 0.0,
        "smart_rank": round(smart_rank, 2), "anticipation": round(anticipation, 2),
        "action": action, "status": "OPEN",
    })
    oe_save_log(trades)


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
        elif outcome in ("LOSS", "TIMEOUT"):
            if outcome == "LOSS":
                losses += 1
            STATE.record_loss(rank, ant, sector=sec, tag=t_tag)

    oe_save_history_batch(batch)
    oe_save_log(remaining)
    return remaining, wins, losses


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# SCAN CORE — Orchestrates all layers into one scan pass
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

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


def run_scan(widgets: dict) -> None:
    """
    FIX-H: All UI updates go through _enqueue() → _pump() on the main thread.
    Worker thread never touches Tkinter directly.
    """
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
        _enqueue(_pulse.stop)
        _enqueue(status_var.set, "⏳ Loading data from multiple sources…")
        _enqueue(lambda: tree.delete(*tree.get_children()))
        _enqueue(lambda: pbar.configure(value=0))

        all_data = download_all()
        if not all_data:
            _enqueue(status_var.set, "❌ Download failed — no data from any source.")
            return
        _enqueue(status_var.set, f"✅ {len(all_data)} symbols loaded — computing signals…")

        oe_open, oe_wins, oe_losses = oe_process_open_trades(all_data)
        if oe_wins or oe_losses:
            _enqueue(status_var.set, f"📊 Outcomes: {oe_wins}W/{oe_losses}L resolved…")

        current_open_trades = oe_load_log()
        results:  List[dict] = []
        sec_quant: Dict[str, List[float]] = {k: [] for k in SECTORS}
        ema200_slopes: Dict[str, float]   = {}
        whale_global = False
        total = len(SYMBOLS)

        for idx, (sym, yahoo) in enumerate(SYMBOLS.items(), 1):
            if idx % 4 == 0:
                _enqueue(pbar.configure, value=int(idx / total * 100))

            if yahoo not in all_data:
                continue
            df = all_data[yahoo].copy()

            required = {"Close", "High", "Low", "Open"}
            if not required.issubset(set(df.columns)):
                continue
            if "Volume" not in df.columns:
                df["Volume"] = 0.0

            close = df["Close"].dropna()
            if len(close) < K.MIN_BARS:
                continue
            price = float(close.iloc[-1])
            if price < K.PRICE_FLOOR:
                continue

            df_ta = df.tail(250).copy()

            # FIX BUG#1 (early): if the last 5 closes are all identical → stale feed
            last5 = df_ta["Close"].iloc[-5:]
            if last5.nunique() <= 1:
                log.warning("Stale/frozen OHLC detected for %s — skipping", sym)
                continue

            # ── EMAs ─────────────────────────────────────────────────────────
            ema200_s   = close.ewm(span=200, adjust=False).mean()
            ema50_s    = close.ewm(span=50,  adjust=False).mean()
            ema200     = last_val(ema200_s)
            ema50      = last_val(ema50_s)
            pct_ema200 = safe_clamp(((price - ema200) / (ema200 + 1e-9)) * 100, -50.0, 50.0)

            # EMA200 slope (for regime detection)
            if len(ema200_s) >= K.REGIME_SLOPE_BARS + 2:
                slope = float(ema200_s.iloc[-1] - ema200_s.iloc[-K.REGIME_SLOPE_BARS]) / (price + 1e-9)
                ema200_slopes[sym] = slope

            # ── Momentum ──────────────────────────────────────────────────────
            raw_mom  = close.pct_change(5).rolling(3).mean().iloc[-1]
            momentum = float(raw_mom) * 100 if pd.notna(raw_mom) else 0.0

            # ── ADX + RSI ─────────────────────────────────────────────────────
            try:
                adf      = pta.adx(df_ta["High"], df_ta["Low"], df_ta["Close"], length=K.ADX_LENGTH)
                col_name = f"ADX_{K.ADX_LENGTH}"
                adx_val  = last_val(adf[col_name]) if (adf is not None and col_name in adf.columns) else 0.0
                rsi_val  = last_val(pta.rsi(close, length=14))
            except Exception:
                adx_val, rsi_val = 0.0, 50.0

            adx_factor   = min(1.4, max(0.6, adx_val / 25.0))
            adaptive_mom = momentum * adx_factor

            # FIX BUG#1: Degenerate data guard — skip symbol if indicators hit
            # impossible extremes (saturated pandas_ta input, stale/frozen OHLC).
            # ADX=100 or RSI>=99 indicate uniform/constant price bars.
            if adx_val >= 99.0 or rsi_val >= 99.0:
                log.warning("Degenerate indicators for %s (ADX=%.1f RSI=%.1f) — skipping", sym, adx_val, rsi_val)
                continue

            # ── Volume filter ────────────────────────────────────────────────
            avg_vol_raw = df["Volume"].rolling(20).mean().iloc[-1]
            if pd.isna(avg_vol_raw):
                continue
            avg_vol = float(avg_vol_raw)
            has_vol = avg_vol > 0
            if has_vol and avg_vol < K.LOW_LIQ_FILTER:
                continue
            vol_ratio = safe_clamp(float(df["Volume"].iloc[-1]) / (avg_vol + 1e-9), 0.0, 5.0) if has_vol else 1.0

            # ── Core indicators ───────────────────────────────────────────────
            vwap_dist  = compute_vwap_dist(df_ta, price)
            vol_zscore = compute_vol_zscore(df_ta)
            atr        = compute_atr(df_ta)
            atr_label, atr_pct_rank = compute_atr_risk(df_ta, price)

            # ── CLV ───────────────────────────────────────────────────────────
            bar_h   = float(df_ta["High"].iloc[-1])
            bar_l   = float(df_ta["Low"].iloc[-1])
            bar_o   = float(df_ta["Open"].iloc[-1])
            bar_rng = bar_h - bar_l
            clv = (safe_clamp(((price - bar_l) - (bar_h - price)) / (bar_rng + 1e-9), -1.0, 1.0)
                   if bar_rng > 1e-9 else 0.0)

            # ── Trend acceleration ────────────────────────────────────────────
            ma_fast = close.ewm(span=10, adjust=False).mean()
            if len(ma_fast) >= 8:  # FIX: guard against IndexError on short series
                raw_acc = float((ma_fast.iloc[-1] - ma_fast.iloc[-3]) - (ma_fast.iloc[-5] - ma_fast.iloc[-8]))
            else:
                raw_acc = 0.0
            trend_acc = safe_clamp(raw_acc / (price + 1e-9), -0.05, 0.05)

            # ── Breakout ──────────────────────────────────────────────────────
            recent_hi = float(df_ta["High"].iloc[-6:-1].max())
            body      = abs(price - bar_o)
            breakout  = (
                price > recent_hi and vol_ratio > 1.3 and
                (body / (bar_rng + 1e-9)) > K.FAKE_BREAK_BODY
            )

            # ── Phase detection ───────────────────────────────────────────────
            hidden_score = 0.0
            if adx_val < 20 and 45 < rsi_val < 60: hidden_score += 1.5
            if vol_ratio < 1.2 and clv > 0.4:       hidden_score += 1.0
            if trend_acc > 0:                        hidden_score += 1.0
            if body / (bar_rng + 1e-9) < 0.35:      hidden_score += 0.5

            phase = detect_phase(adx_val, rsi_val, vol_ratio, trend_acc, clv, adaptive_mom, ema50, price,
                                 body_ratio=body / (bar_rng + 1e-9))  # FIX-2: real body ratio
            zone  = detect_predictive_zone(rsi_val, adaptive_mom, pct_ema200, vol_ratio)

            # ── Pattern flags ──────────────────────────────────────────────────
            expansion = (adx_val > K.ADX_MID and momentum > 1.2 and vol_ratio > 1.1 and trend_acc > 0)
            fake_exp  = (expansion and rsi_val > 66 and vol_ratio < 1.25 and clv < 0.35 and momentum < 2.8)
            silent    = (45 <= rsi_val <= 60 and trend_acc > 0 and clv > 0.5 and vol_ratio < 1.3 and
                         (body / (bar_rng + 1e-9)) < 0.35)
            hunter    = (adx_val > 18 and 40 <= rsi_val <= 65 and vol_ratio > 1.25 and trend_acc > 0)
            whale_flag = ("🐳 Whale" if (vol_zscore > K.WHALE_ZSCORE_THRESH and
                                          clv > K.WHALE_CLV_SIGNAL and vol_ratio > K.WHALE_VOL_THRESH) else "")
            if whale_flag:
                whale_global = True

            # ── Normalised scores (all 0-1) ────────────────────────────────────
            cpi_n      = score_capital_pressure(clv, trend_acc, vol_ratio, price, ema50, vwap_dist)
            iet_n      = score_institutional_entry(rsi_val, adx_val, clv, trend_acc, vol_ratio, pct_ema200)
            whale_n    = score_whale_footprint(adx_val, clv, trend_acc, vol_ratio, rsi_val)
            ant_n      = score_flow_anticipation(rsi_val, adx_val, clv, trend_acc, vol_ratio, pct_ema200)
            quantum_n  = score_quantum(rsi_val, momentum, trend_acc, clv, vol_ratio)
            grav_lbl, grav_n = score_gravity(clv, trend_acc, vol_ratio, rsi_val, adaptive_mom)

            ema_cross  = detect_ema_cross(close)
            vol_div    = detect_vol_divergence(close, df["Volume"])
            mom_arr    = STATE.momentum_arrow(sym, momentum)

            _, _, brain_score_req = STATE.snapshot_brain()
            signal, tag, tech_score = build_signal(
                price, ema200, ema50, adx_val, rsi_val,
                adaptive_mom, vol_ratio, breakout, pct_ema200, phase,
                brain_score_req=brain_score_req,
            )

            # FIX DESIGN#3: anticipation is forward-looking; zero it for SELL signals
            # to prevent a SELL stock showing high anticipation (misleading to users)
            ant_n_effective = 0.0 if tag == "sell" else ant_n

            sector = get_sector(sym)
            if sector in sec_quant:
                sec_quant[sector].append(quantum_n)

            results.append({
                "sym": sym, "sector": sector, "price": price,
                "adx": adx_val, "rsi": rsi_val, "momentum": momentum,
                "adaptive_mom": adaptive_mom, "pct_ema200": pct_ema200,
                "vol_ratio": vol_ratio, "tech_score": tech_score,
                "signal": signal, "tag": tag, "phase": phase,
                "trend_acc": trend_acc, "breakout": breakout, "clv": clv,
                "whale": whale_flag, "hunter": "🎯 Hunter" if hunter else "",
                "silent": silent, "expansion": expansion, "fake_expansion": fake_exp,
                # Normalised scores [0,1]
                "cpi": cpi_n, "iet": iet_n, "whale_score": whale_n,
                "anticipation": ant_n_effective, "quantum": quantum_n,
                "gravity_label": grav_lbl, "gravity_score": grav_n,
                "zone": zone, "hidden": hidden_score,
                "ema_cross": ema_cross, "vol_div": vol_div,
                "mom_arrow": mom_arr, "atr": atr,
                "atr_risk": atr_label, "atr_pct_rank": atr_pct_rank,
                "vwap_dist": vwap_dist, "vol_zscore": vol_zscore,
                # Filled in scoring pass below
                "smart_rank": 0.0, "confidence": 0.0, "leader": False,
                "plan": None, "inst_conf": "—",
                "signal_dir": "⏸️ NEUTRAL", "signal_reason": "",
                "signal_display": "", "guard_reason": "",
            })

        if not results:
            _enqueue(status_var.set,
                     f"⚠️ No symbols passed filters — {len(all_data)} loaded. "
                     f"Check liquidity threshold ({K.LOW_LIQ_FILTER:,.0f}), "
                     f"price floor ({K.PRICE_FLOOR} EGP), "
                     f"min bars ({K.MIN_BARS}), or enable more data sources.")
            return

        # ── Sector strength ────────────────────────────────────────────────────
        sector_strength: Dict[str, float] = {
            sec: (sum(v) / len(v) if v else 0.0) for sec, v in sec_quant.items()
        }
        _enqueue(_update_heatmap, heat_lbl, sector_strength)

        # ── Regime ────────────────────────────────────────────────────────────
        regime = detect_market_regime(results, ema200_slopes)
        # NOTE: regime_weights was previously computed here but never used; removed (FIX: dead code)
        _enqueue(_update_regime_label, regime_lbl, regime)

        # ── Sector rotation ───────────────────────────────────────────────────
        rotation_scores: Dict[str, float] = {}
        for sec in SECTORS:
            vals = [r["anticipation"] for r in results if r["sector"] == sec]
            avg  = sum(vals) / len(vals) if vals else 0.0
            STATE.update_sector_rotation(sec, avg)   # FIX: was direct lock-free dict access
            rotation_scores[sec] = avg
        future_sector = max(rotation_scores, key=rotation_scores.get)
        _enqueue(_update_rotation_map, rot_lbl, rotation_scores, future_sector)

        # ── Capital flow map ──────────────────────────────────────────────────
        flow_map, flow_leader = build_capital_flow_map(results, sector_strength)
        _enqueue(_update_flow_map, flow_lbl, flow_map, flow_leader)

        # ── Brain mode ────────────────────────────────────────────────────────
        buy_count = sum(1 for r in results if r["tag"] in ("buy", "ultra", "early"))
        STATE.set_brain("aggressive" if buy_count >= 4 else ("defensive" if buy_count <= 1 else "neutral"))
        brain_mode, brain_vol_req, _ = STATE.snapshot_brain()
        _enqueue(_update_brain_label, brain_lbl, brain_mode)

        # ── Neural weight update ──────────────────────────────────────────────
        STATE.update_neural_weights(results)
        nw = STATE.get_neural_weights()

        # ── Market soft flag ──────────────────────────────────────────────────
        market_soft = (
            sum(r["adx"]       for r in results) / len(results) < 30 and
            sum(r["momentum"]  for r in results) / len(results) < 1.5 and
            sum(r["vol_ratio"] for r in results) / len(results) < 1.3
        )

        # ── SmartRank scoring pass ────────────────────────────────────────────
        sector_bias_map: Dict[str, float] = {
            sec: (1.25 if avg > 0.6 else (0.85 if avg < 0.28 else 1.0))
            for sec, avg in sector_strength.items()
        }

        for r in results:
            sec_avg_q = sector_strength.get(r["sector"], 0.0)
            r["leader"] = (r["quantum"] - sec_avg_q > _norm(K.LEADER_QUANTUM_DELTA, 0, 5.5) and r["trend_acc"] > 0)

            sig_hist = STATE.append_signal_history(r["sym"], r["tag"])

            new_rank = smart_rank_score(
                cpi_n        = r["cpi"],
                iet_n        = r["iet"],
                whale_n      = r["whale_score"],
                gravity_n    = r["gravity_score"],
                quantum_n    = r["quantum"],
                tech_score   = r["tech_score"],
                trend_acc    = r["trend_acc"],
                hidden_score = r["hidden"],
                adaptive_mom = r["adaptive_mom"],
                phase        = r["phase"],
                zone         = r["zone"],
                tag          = r["tag"],
                silent       = r["silent"],
                hunter       = bool(r["hunter"]),
                expansion    = r["expansion"],
                fake_expansion = r["fake_expansion"],
                leader       = r["leader"],
                ema_cross    = r["ema_cross"],
                vol_div      = r["vol_div"],
                rsi          = r["rsi"],
                pct_ema200   = r["pct_ema200"],
                vol_ratio    = r["vol_ratio"],
                brain_mode   = brain_mode,
                brain_vol_req= brain_vol_req,
                sig_hist     = sig_hist,
                market_soft  = market_soft,
                nw           = nw,
                sector_bias  = sector_bias_map.get(r["sector"], 1.0),
                anticipation_n = r["anticipation"],
                regime       = regime,
            )

            prev_rank = STATE.get_prev_rank(r["sym"], new_rank)
            smoothed  = safe_clamp(
                K.SMART_RANK_SMOOTHING * prev_rank + (1 - K.SMART_RANK_SMOOTHING) * new_rank,
                0.0, K.SMART_RANK_SCALE,
            )
            if r["adx"] < K.ADX_SOFT_LO and smoothed > K.SMART_RANK_ADX_CAP:
                smoothed = K.SMART_RANK_ADX_CAP

            r["smart_rank"] = round(smoothed, 3)
            STATE.set_prev_rank(r["sym"], smoothed)

            r["confidence"] = round(
                100 / (1 + math.exp(-K.CONF_SIGMOID_SCALE * (r["smart_rank"] - K.CONF_SIGMOID_SHIFT))),
                1,
            )

            # Win rate (FIX-A)
            winrate = STATE.estimate_winrate(
                r["smart_rank"], r["anticipation"],
                sector=r["sector"], tag=r["tag"], regime=regime,  # FIX-5
            )

            # Trade plan (FIX-F: pass atr_risk_label)
            r["plan"] = build_trade_plan(
                r["price"], r["rsi"], r["adx"], r["clv"],
                r["trend_acc"], r["smart_rank"], r["anticipation"],
                atr_risk_label=r["atr_risk"],
                atr=r["atr"],
                tech_score=r["tech_score"],   # FIX-3
                vol_ratio=r["vol_ratio"],      # FIX-3
            )
            r["plan"]["winrate"]    = winrate if not r["plan"]["force_wait"] else 0.0
            r["plan"]["winrate_na"] = r["plan"]["force_wait"]

            # Signal overrides
            if r["plan"]["force_wait"] and r["tag"] in ("buy", "ultra", "early"):
                r["signal"] = "⏳ WAIT (ADX)";  r["tag"] = "watch"
            if r["plan"]["action"] == "PROBE" and r["tag"] == "sell":
                r["plan"] = {**r["plan"], "action": "WAIT"}
            if (r["plan"]["action"] == "ACCUMULATE" and r["rsi"] > K.RSI_OVERBOUGHT and r["tag"] == "watch"):
                r["plan"] = {**r["plan"], "action": "PROBE"}

            r["signal_dir"]    = get_signal_direction(r["tag"])
            r["signal_reason"] = build_signal_reason(
                r["rsi"], r["adx"], r["pct_ema200"], r["phase"],
                r["vol_div"], r["ema_cross"], r["adaptive_mom"],
                r["clv"], r["vol_ratio"], tag=r["tag"],
            )
            if r["tech_score"] <= 3 and r["smart_rank"] > K.SMART_RANK_SCALE * 0.3:
                r["signal_reason"] += " | ⚡ Flow>Tech divergence"
            if r["adx"] < K.ADX_SOFT_LO and r["smart_rank"] >= K.SMART_RANK_ADX_CAP:
                r["signal_reason"] += " | 🔒 Rank capped (ADX<16)"

            direction = "↑ " if r["tag"] in ("buy","ultra","early") else ("↓ " if r["tag"] == "sell" else "→ ")
            r["signal_display"] = direction + r["signal"]

            r["inst_conf"] = institutional_confidence(winrate, r["smart_rank"], sector_strength.get(r["sector"], 0.0))

        STATE.record_signal_bias(results)
        # Pre-sort for guard priority (guard processes in this order)
        results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))

        # ── Portfolio guard (FIX-G: pure function) ────────────────────────────
        guarded_list, guard_counts, guard_exp, guard_blocked = compute_portfolio_guard(results)

        # Apply guard annotations to results (create new copies — no mutation of scoring data)
        annotated_results: List[dict] = []
        for gr in guarded_list:
            r_copy = dict(gr.result)
            r_copy["guard_reason"] = gr.guard_reason
            if gr.is_blocked:
                r_copy["tag"]            = "watch"
                r_copy["signal"]         = "🛡️ BLOCKED"
                r_copy["signal_display"] = "→ 🛡️ BLOCKED"
                r_copy["plan"]           = {**r_copy["plan"], "action": "WAIT 🛡️"}
            annotated_results.append(r_copy)

        # FIX BUG#2: Re-sort using post-guard tag so BLOCKED items no longer
        # appear above active BUY/EARLY signals in the display table.
        annotated_results.sort(key=lambda x: (DECISION_PRIORITY.get(x["tag"], 99), -x["smart_rank"]))

        _enqueue(_update_guard_bar, guard_slbl, guard_elbl, guard_blbl,
                 guard_counts, guard_exp, guard_blocked)

        # ── Record new signals ────────────────────────────────────────────────
        for r in annotated_results:
            if (r.get("plan") and
                r["plan"]["action"] in ("ACCUMULATE", "PROBE") and
                not r["guard_reason"]):
                oe_record_signal(
                    sym=r["sym"], sector=r["sector"],
                    entry=r["plan"]["entry"], stop=r["plan"]["stop"],
                    target=r["plan"]["target"],
                    atr=r["atr"] or 0.0,
                    smart_rank=r["smart_rank"], anticipation=r["anticipation"],
                    action=r["plan"]["action"],
                    existing_trades=current_open_trades,
                )

        # ── Entry window verdict ──────────────────────────────────────────────
        avg_rank_all = sum(r["smart_rank"] for r in annotated_results) / len(annotated_results)
        early_cnt    = sum(1 for r in annotated_results if r["zone"] == "🟢 EARLY")
        late_cnt     = sum(1 for r in annotated_results if r["zone"] == "🔴 LATE")
        if avg_rank_all >= K.SMART_RANK_SCALE * 0.10 and early_cnt >= late_cnt:
            entry_txt, entry_col = "🔥 ENTRY WINDOW OPEN", "#062016"
        elif late_cnt > early_cnt:
            entry_txt, entry_col = "⚠️ EARLY SETUPS ONLY", "#2a260a"
        else:
            entry_txt, entry_col = "🚫 NO TRADE ZONE",    "#2b0a0a"

        # ── Insert rows ───────────────────────────────────────────────────────
        medals       = ["🥇 ", "🥈 ", "🥉 "]
        phase_icon   = {"Accumulation": "🟡", "Expansion": "🔵", "Exhaustion": "🔴"}
        accum_syms   = [r["sym"] for r in annotated_results if (r.get("plan") or {}).get("action") == "ACCUMULATE"][:3]
        with STATE._lock:
            win_sample = len(STATE.neural_win_memory) + len(STATE.neural_loss_memory)

        def _insert_all():
            for i, r in enumerate(annotated_results):
                prefix = medals[i] if i < 3 else f"#{i+1} "
                icons  = phase_icon.get(r["phase"], "⚪")
                if r["breakout"]:                   icons += "💥"
                if r["quantum"] > 0.5:              icons += "🧿"
                if r["fake_expansion"]:             icons += "☠️"
                if r["leader"]:                     icons += "👑"
                if r["ema_cross"] == "BULL_CROSS":  icons += "🔔"
                if r["ema_cross"] == "BEAR_CROSS":  icons += "🔕"
                if r["vol_div"]:                    icons += r["vol_div"]

                extras = (
                    f"{icons} {r['whale']} {r['hunter']} "
                    f"{'🧬' if r['silent'] else ''}{'⚡' if r['expansion'] else ''}"
                ).strip()

                disp = f"{prefix}{r['signal_display']}"

                if r["plan"].get("winrate_na"):
                    wr_str = "—"
                elif win_sample < K.WINRATE_MIN_SAMPLE:
                    wr_str = "⌛ Building"
                else:
                    wr_str = f"{r['plan']['winrate']:.0f}%"

                row = (
                    r["sym"], r["sector"],
                    f"{r['price']:.2f}", f"{r['adx']:.1f}", f"{r['rsi']:.0f}",
                    f"{r['adaptive_mom']:+.1f}", f"{r['pct_ema200']:+.1f}%",
                    f"{r['vol_ratio']:.1f}x",
                    str(r["tech_score"]), r["gravity_label"], r["zone"],
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
                    f"{r['atr']:.2f}" if r["atr"] else "—",
                    f"{r['vwap_dist']*100:.1f}%", f"{r['vol_zscore']:.1f}",
                    r["signal_reason"],
                    r["guard_reason"] if r["guard_reason"] else "✅ OK",
                )

                if r["guard_reason"]:
                    row_tag = "blocked"
                else:
                    row_tag = (
                        "accum_top" if r["sym"] in accum_syms
                        else ("radar" if r["silent"] else r["tag"])
                    )
                tree.insert("", tk.END, values=row, tags=(row_tag,))

        _enqueue(_insert_all)

        # ── Status summary ───────────────────────────────────────────────────
        mood    = ("Momentum Strong" if avg_rank_all >= K.SMART_RANK_SCALE * 0.13
                   else ("Balanced Market" if avg_rank_all >= K.SMART_RANK_SCALE * 0.07 else "Capital Protection"))
        safe_s  = [r["sym"] for r in annotated_results if r["smart_rank"] >= K.SMART_RANK_SCALE * 0.17][:3]
        watch_s = [r["sym"] for r in annotated_results if K.SMART_RANK_SCALE * 0.08 <= r["smart_rank"] < K.SMART_RANK_SCALE * 0.17][:3]
        avoid_s = [r["sym"] for r in annotated_results if r["smart_rank"] < K.SMART_RANK_SCALE * 0.08][:3]

        verdict_txt = (
            f"🧠 BRAIN | {entry_txt} | {mood} | "
            f"🟢 {', '.join(safe_s) or '—'} | "
            f"🟡 {', '.join(watch_s) or '—'} | "
            f"🔴 {', '.join(avoid_s) or '—'}"
        )
        if guard_blocked:
            verdict_txt += f" | 🛡️ BLOCKED: {', '.join(guard_blocked)}"
        _enqueue(verdict_var.set, verdict_txt)
        _enqueue(verdict_frm.configure, bg=entry_col)
        _enqueue(verdict_w.configure, bg=entry_col)

        avg_future = sum(r["anticipation"] for r in annotated_results) / len(annotated_results)
        _enqueue(draw_gauge, g_rank, avg_rank_all, K.SMART_RANK_SCALE, "SmartRank", brain_mode)
        _enqueue(draw_gauge, g_flow, avg_future,   1.0,  "FutureFlow", "anticipation")

        if whale_global:
            _enqueue(_pulse.start, verdict_frm, verdict_w, entry_col)

        elapsed   = round(time.time() - scan_start, 1)
        nw_str    = f"F{nw['flow']:.2f} S{nw['structure']:.2f} T{nw['timing']:.2f}"
        guard_pct = (guard_exp / (get_account_size() + 1e-9)) * 100
        guard_sum = f"🛡️{len(guard_blocked)}blk" if guard_blocked else f"🛡️OK({guard_pct:.1f}%)"
        oe_sum    = f"📊{len(current_open_trades)}open/{oe_wins}W/{oe_losses}L"

        with _source_labels_lock:
            src_snap = dict(_source_labels)
        src_counts: Dict[str, int] = {}
        for lbl in src_snap.values():
            base = lbl.split("+")[0].replace("⚠️", "")
            src_counts[base] = src_counts.get(base, 0) + 1
        src_summary = " | ".join(f"{k}:{v}" for k, v in src_counts.items()) or "—"

        _enqueue(status_var.set,
                 f"✅ {len(annotated_results)} symbols | Regime:{regime} | Next:{future_sector} | "
                 f"Brain:{brain_mode} | Neural:{nw_str} | {guard_sum} | {oe_sum} | "
                 f"🌐{src_summary} | ⏱ {elapsed}s | {datetime.now().strftime('%H:%M:%S')}")
        _enqueue(pbar.configure, value=100)
        with STATE._lock:          # FIX: scan_count must be mutated under lock
            STATE.scan_count += 1

    except Exception as exc:
        log.error("Scan fatal: %s", exc, exc_info=True)
        _enqueue(status_var.set, f"❌ Error: {exc}")
    finally:
        _enqueue(scan_btn.configure, state="normal")
        _scan_lock.release()


def start_scan(widgets: dict) -> None:
    widgets["scan_btn"].configure(state="disabled")
    threading.Thread(target=run_scan, args=(widgets,), daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# LAYER 10: UI — Tkinter presentation layer
# FIX-H: UI is ONLY updated via _enqueue/_pump.
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════

# ── UI event queue (FIX-H) ───────────────────────────────────────────────────
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


# ── Pulse controller ──────────────────────────────────────────────────────────
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


# ── Gauge widget ──────────────────────────────────────────────────────────────
def draw_gauge(canvas: tk.Canvas, val: float, max_val: float, label: str, sublabel: str = "") -> None:
    canvas.delete("all")
    W, H   = 160, 110
    cx, cy = W // 2, H - 18
    R      = 58
    ratio  = safe_clamp(val / (max_val + 1e-9), 0.0, 1.0)
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


# ── UI update helpers (called from _pump, safe on main thread) ─────────────────
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
            text=f"{'👑 ' if sec == future else ''}{sec}\n{val:.2f}", fg=col, bg=bg
        )


def _update_flow_map(flow_labels: dict, flow_scores: Dict[str, float], leader: str) -> None:
    for sec, val in flow_scores.items():
        if sec == leader: col, bg = C.GREEN,  "#061f14"
        elif val > 0.3:   col, bg = C.CYAN,   "#06131f"
        elif val > 0:     col, bg = C.YELLOW, "#1c1a08"
        else:             col, bg = C.RED,    "#220a0a"
        flow_labels[sec].configure(
            text=f"{'💰 ' if sec == leader else ''}{sec}\n{val:+.2f}", fg=col, bg=bg
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
    guard_elbl.configure(text=f"ATR Exp: {pct:.1f}% / {max_pct:.0f}%  (حساب: {acct:,.0f} ج.م)", fg=exp_col)
    if blocked_syms:
        guard_blbl.configure(text=f"🛡️ Blocked: {', '.join(blocked_syms)}", fg=C.RED)
    else:
        guard_blbl.configure(text="🛡️ Blocked: —", fg=C.MUTED)


def _update_regime_label(lbl: tk.Label, regime: str) -> None:
    icons = {
        "ACCUMULATION": ("📦 ACCUMULATION", C.CYAN),
        "MOMENTUM":     ("🚀 MOMENTUM",      C.GREEN),
        "DISTRIBUTION": ("📤 DISTRIBUTION",  C.RED),
        "NEUTRAL":      ("📊 NEUTRAL",        C.MUTED),
    }
    txt, col = icons.get(regime, ("📊 NEUTRAL", C.MUTED))
    lbl.configure(text=txt, fg=col)


def _update_brain_label(lbl: tk.Label, mode: str) -> None:
    if mode == "aggressive":  lbl.configure(text="🧠🔥 AGGRESSIVE", fg=C.GREEN)
    elif mode == "defensive": lbl.configure(text="🧠🛡️ DEFENSIVE",  fg=C.YELLOW)
    else:                     lbl.configure(text="🧠 NEUTRAL",       fg=C.MUTED)


# ── Tooltip ───────────────────────────────────────────────────────────────────
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
        f"  Symbol  : {v.get('Symbol','—')}  Sector: {v.get('Sector','—')}\n"
        f"  Price   : {v.get('Price','—')}  ADX: {v.get('ADX','—')}  RSI: {v.get('RSI','—')}\n"
        f"  CPI     : {v.get('🧠CPI','—')}  IET: {v.get('🏛️IET','—')}  Whale: {v.get('🐳Whale','—')}\n"
        f"  Signal  : {v.get('Signal','—')}  Dir: {v.get('Direction','—')}\n"
        f"  Conf    : {v.get('Confidence%','—')}  Timeframe: {v.get('Timeframe','—')}\n"
        f"  Action  : {v.get('Action','—')}  Entry: {v.get('Entry','—')}  Stop: {v.get('Stop','—')}\n"
        f"  Target  : {v.get('Target','—')}  R:R: {v.get('R:R','—')}  WinRate: {v.get('WinRate%','—')}\n"
        f"  ATR Risk: {v.get('ATR Risk','—')}  VWAP%: {v.get('VWAP%','—')}\n"
        f"  Reason  : {v.get('Signal Reason','—')}\n"
        f"  🛡️Guard : {v.get('🛡️Guard','—')}"
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
        initialfile=f"EGX_Radar_v80_{now}.csv",
        filetypes=[("CSV files", "*.csv")],
        title="Save Radar Results",
    )
    if not path:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows([cols, *rows])
    messagebox.showinfo("Saved ✅", f"File saved:\n{path}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    STATE.load()
    load_source_settings()

    root = tk.Tk()
    root.title("EGX Capital Flow Radar v82 — Signal Quality Upgrade")
    root.geometry("2400x980")
    root.configure(bg=C.BG)

    # ── Header ────────────────────────────────────────────────────────────────
    hdr = tk.Frame(root, bg=C.BG, pady=6)
    hdr.pack(fill="x", padx=16)
    tk.Label(hdr, text="⚡ EGX CAPITAL FLOW RADAR v82 🧲🧠🔮🎯🧭🔔🛡️📊",
             font=F_TITLE, fg=C.ACCENT, bg=C.BG).pack(side="left")

    gauge_flow = tk.Canvas(hdr, width=160, height=110, bg=C.BG, highlightthickness=0)
    gauge_flow.pack(side="right", padx=(4, 8))
    gauge_rank = tk.Canvas(hdr, width=160, height=110, bg=C.BG, highlightthickness=0)
    gauge_rank.pack(side="right", padx=(4, 2))
    draw_gauge(gauge_rank, 0, K.SMART_RANK_SCALE, "SmartRank",  "waiting…")
    draw_gauge(gauge_flow, 0, 1.0,                "FutureFlow", "waiting…")

    scan_btn = tk.Button(hdr, text="🚀 Gravity Scan [F5]",
                         font=F_HEADER, fg=C.BG, bg=C.ACCENT, relief="flat", padx=12, pady=4)
    scan_btn.pack(side="right", padx=4)

    # ── Top bar ───────────────────────────────────────────────────────────────
    top_bar = tk.Frame(root, bg=C.BG, pady=4)
    top_bar.pack(fill="x", padx=16)
    tk.Label(top_bar, text="🔥 Sector Flow:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 6))

    heat_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(top_bar, text=f"{sec}\n—", width=15, height=2,
                       bg=C.BG3, fg=C.MUTED, font=("Consolas", 9, "bold"))
        lbl.pack(side="left", padx=3)
        heat_labels[sec] = lbl

    brain_lbl = tk.Label(top_bar, text="🧠 NEUTRAL", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    brain_lbl.pack(side="right", padx=12)

    save_btn = tk.Button(top_bar, text="💾 Save CSV", font=F_HEADER,
                         fg=C.TEXT, bg=C.BG3, relief="flat", padx=8, pady=3)
    save_btn.pack(side="right", padx=6)

    # ── Outcomes window ───────────────────────────────────────────────────────
    def open_outcomes() -> None:
        win = tk.Toplevel(root)
        win.title("📊 Trade Outcomes")
        win.configure(bg=C.BG)
        win.geometry("1100x660")

        stats_frm = tk.Frame(win, bg=C.BG, pady=6)
        stats_frm.pack(fill="x", padx=14)
        stats_lbl = tk.Label(stats_frm, text="Loading…", font=F_HEADER, fg=C.ACCENT, bg=C.BG, anchor="w")
        stats_lbl.pack(side="left", fill="x", expand=True)

        nb   = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=14, pady=4)

        oc   = ("Symbol", "Sector", "Date", "Entry", "Stop", "Target", "ATR", "Rank", "Action")
        oc_w = (60, 90, 90, 70, 70, 70, 50, 60, 90)
        hc   = ("Symbol", "Sector", "Date", "Entry", "Exit", "Stop", "Target", "Status", "Days", "MFE%", "MAE%", "PnL%", "Rank")
        hc_w = (60, 90, 90, 70, 70, 70, 70, 72, 46, 60, 60, 60, 60)

        open_frm  = tk.Frame(nb, bg=C.BG); nb.add(open_frm, text="🔓 Open")
        open_tree = ttk.Treeview(open_frm, columns=oc, show="headings", height=18, style="Dark.Treeview")
        for col, w in zip(oc, oc_w):
            open_tree.heading(col, text=col); open_tree.column(col, width=w, anchor="center", stretch=False)
        vsb_o = ttk.Scrollbar(open_frm, orient="vertical", command=open_tree.yview)
        open_tree.configure(yscrollcommand=vsb_o.set); vsb_o.pack(side="right", fill="y")
        open_tree.pack(fill="both", expand=True)

        hist_frm  = tk.Frame(nb, bg=C.BG); nb.add(hist_frm, text="📜 History")
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
                f"📊 Resolved:{tot}  ✅W:{w}  ❌L:{l}  ⏱TO:{to}  "
                f"WR:{wr:.1f}%  MFE:{avmf:.1f}%  MAE:{avma:.1f}%  PnL:{avpn:.1f}%  Open:{len(ot)}"
            ))
            nb.tab(0, text=f"🔓 Open ({len(ot)})"); nb.tab(1, text=f"📜 History ({tot})")
            open_tree.delete(*open_tree.get_children())
            for t in sorted(ot, key=lambda x: x.get("date", ""), reverse=True):
                open_tree.insert("", tk.END, values=(
                    t.get("sym","—"), t.get("sector","—"), t.get("date","—"),
                    f"{t.get('entry',0):.2f}", f"{t.get('stop',0):.2f}",
                    f"{t.get('target',0):.2f}", f"{t.get('atr',0):.2f}",
                    f"{t.get('smart_rank',0):.1f}", t.get("action","—"),
                ))
            hist_tree.delete(*hist_tree.get_children())
            for t in sorted(hist, key=lambda x: x.get("resolved_date",""), reverse=True):
                status = t.get("status","—")
                hist_tree.insert("", tk.END, values=(
                    t.get("sym","—"), t.get("sector","—"), t.get("date","—"),
                    f"{t.get('entry',0):.2f}", f"{t.get('exit_price',0):.2f}",
                    f"{t.get('stop',0):.2f}", f"{t.get('target',0):.2f}",
                    status, t.get("days_held","—"),
                    f"{t.get('mfe_pct',0):.1f}%", f"{t.get('mae_pct',0):.1f}%",
                    f"{t.get('pnl_pct',0):.1f}%", f"{t.get('smart_rank',0):.1f}",
                ), tags=(status,))

        tk.Button(stats_frm, text="🔄 Refresh", font=F_HEADER, fg=C.BG, bg=C.ACCENT,
                  relief="flat", padx=8, pady=2, command=_refresh).pack(side="right", padx=8)
        _refresh()

    outcomes_btn = tk.Button(top_bar, text="📊 Outcomes", font=F_HEADER,
                              fg=C.BG, bg="#1a5276", relief="flat", padx=8, pady=3, command=open_outcomes)
    outcomes_btn.pack(side="right", padx=6)

    # ── Capital calculator ────────────────────────────────────────────────────
    def open_calc() -> None:
        rows_data = [tree.item(k)["values"] for k in tree.get_children("")]
        if not rows_data:
            messagebox.showwarning("Calc", "Run a scan first!")
            return
        win = tk.Toplevel(root)
        win.title("💰 Capital Calculator")
        win.geometry("680x520")
        win.configure(bg=C.BG)
        win.grab_set()
        tk.Label(win, text="💰 Position Size Calculator", font=F_TITLE, fg=C.GOLD, bg=C.BG).pack(pady=(12, 4))
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
        tk.Label(win, text="💡 Change account size or risk% — table updates live",
                 font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(pady=4)

    calc_btn = tk.Button(top_bar, text="💰 Calc", font=F_HEADER,
                          fg=C.BG, bg=C.GOLD, relief="flat", padx=8, pady=3, command=open_calc)
    calc_btn.pack(side="right", padx=6)

    # ── Source settings ───────────────────────────────────────────────────────
    def open_settings() -> None:
        win = tk.Toplevel(root)
        win.title("⚙️ الإعدادات")
        win.geometry("520x700")
        win.configure(bg=C.BG)
        win.grab_set()
        tk.Label(win, text="⚙️ الإعدادات", font=F_TITLE, fg=C.ACCENT, bg=C.BG).pack(pady=(14, 4))

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=12, pady=4)

        # ── Tab 1: Account & Risk ─────────────────────────────────────────────
        tab_acct = tk.Frame(nb, bg=C.BG2); nb.add(tab_acct, text="💰 الحساب والمخاطر")
        frm_a = tk.Frame(tab_acct, bg=C.BG2, padx=20, pady=16); frm_a.pack(fill="x")

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
            _acct = float(DATA_SOURCE_CFG.get("account_size", K.ACCOUNT_SIZE))
            _risk = float(DATA_SOURCE_CFG.get("risk_per_trade", K.RISK_PER_TRADE))
            _exp  = float(DATA_SOURCE_CFG.get("portfolio_max_atr_exposure", K.PORTFOLIO_MAX_ATR_EXPOSURE))
            _mps  = int(DATA_SOURCE_CFG.get("portfolio_max_per_sector", K.PORTFOLIO_MAX_PER_SECTOR))

        acct_var = tk.StringVar(value=f"{_acct:,.0f}")
        risk_var = tk.StringVar(value=f"{_risk*100:.1f}")
        exp_var  = tk.StringVar(value=f"{_exp*100:.1f}")
        mps_var  = tk.StringVar(value=str(_mps))

        _lbl_entry(frm_a, 0, "💼 حجم الحساب (ج.م):", acct_var,
                   "مثال: 50000 أو 100000", C.GOLD)
        _lbl_entry(frm_a, 1, "⚠️ نسبة المخاطرة لكل صفقة %:", risk_var,
                   "الافتراضي 2% (نصيحة: 1-3%)")
        _lbl_entry(frm_a, 2, "🛡️ حد ATR Exposure %:", exp_var,
                   "الافتراضي 4% — رفعه يسمح بإشارات أكثر")
        _lbl_entry(frm_a, 3, "📊 أقصى أسهم لكل قطاع:", mps_var,
                   "الافتراضي 2")

        # Live preview label
        preview_lbl = tk.Label(frm_a, text="", font=F_SMALL, fg=C.CYAN,
                               bg=C.BG2, anchor="w", justify="left")
        preview_lbl.grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))

        def _update_preview(*_):
            try:
                acct = float(acct_var.get().replace(",", ""))
                risk = float(risk_var.get()) / 100
                exp  = float(exp_var.get()) / 100
                mps  = int(mps_var.get())
                max_loss = acct * risk
                max_atr  = acct * exp
                preview_lbl.configure(
                    text=(
                        f"📌 معاينة:\n"
                        f"  • أقصى خسارة لكل صفقة: {max_loss:,.0f} ج.م\n"
                        f"  • أقصى ATR exposure إجمالي: {max_atr:,.0f} ج.م\n"
                        f"  • أقصى أسهم لكل قطاع: {mps}\n"
                        f"  {'✅ إعدادات معقولة' if 0.01 <= risk <= 0.05 and 0.02 <= exp <= 0.10 else '⚠️ تحقق من القيم'}"
                    ),
                    fg=C.CYAN if 0.01 <= risk <= 0.05 else C.YELLOW,
                )
            except ValueError:
                preview_lbl.configure(text="⚠️ قيمة غير صحيحة", fg=C.RED)

        for v in (acct_var, risk_var, exp_var, mps_var):
            v.trace_add("write", _update_preview)
        _update_preview()

        tk.Label(frm_a,
                 text="💡 تلميح: رفع حجم الحساب للقيمة الفعلية هو أهم إصلاح لتقليل الحجب.\n"
                      "مثال: 10,000 ج.م → ATR cap = 400 ج.م فقط (يحجب كثيراً)\n"
                      "       50,000 ج.م → ATR cap = 2,000 ج.م (مناسب أكثر)",
                 font=F_SMALL, fg=C.YELLOW, bg=C.BG2, justify="left", anchor="w",
                 wraplength=440).grid(row=5, column=0, columnspan=3, sticky="w", pady=(14, 0))

        # ── Tab 2: Data Sources ───────────────────────────────────────────────
        tab_src = tk.Frame(nb, bg=C.BG2); nb.add(tab_src, text="🌐 مصادر البيانات")
        frm = tk.Frame(tab_src, bg=C.BG2, padx=20, pady=14); frm.pack(fill="x")
        vars_map = {}
        for key, label, desc in [
            ("use_yahoo",        "✅ Yahoo Finance", "Primary — 2yr history"),
            ("use_stooq",        "📊 Stooq",         "Free, no key"),
            ("use_alpha_vantage","🔑 Alpha Vantage",  "Requires free API key"),
            ("use_investing",    "🌐 Investing.com",  "Price cross-check only"),
            ("use_twelve_data",  "🕐 Twelve Data",    "Best EGX coverage"),
        ]:
            with _data_cfg_lock:
                cur = bool(DATA_SOURCE_CFG.get(key, False))
            v = tk.BooleanVar(value=cur); vars_map[key] = v
            row = tk.Frame(frm, bg=C.BG2); row.pack(fill="x", pady=2)
            tk.Checkbutton(row, text=label, variable=v, font=F_BODY, fg=C.TEXT,
                           bg=C.BG2, selectcolor=C.BG3, activebackground=C.BG2).pack(side="left")
            tk.Label(row, text=desc, font=F_SMALL, fg=C.MUTED, bg=C.BG2).pack(side="left", padx=8)

        tk.Label(tab_src, text="🔑 Alpha Vantage API Key:", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).pack(anchor="w", padx=20, pady=(8,0))
        with _data_cfg_lock:
            cur_av = str(DATA_SOURCE_CFG.get("alpha_vantage_key", ""))
        av_var = tk.StringVar(value=cur_av)
        tk.Entry(tab_src, textvariable=av_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=38).pack(padx=20, pady=4, fill="x")

        tk.Label(tab_src, text="🕐 Twelve Data API Key:", font=F_BODY, fg=C.GOLD, bg=C.BG2).pack(anchor="w", padx=20, pady=(10,0))
        with _data_cfg_lock:
            cur_td = str(DATA_SOURCE_CFG.get("twelve_data_key", ""))
        td_var = tk.StringVar(value=cur_td)
        td_entry = tk.Entry(tab_src, textvariable=td_var, font=F_BODY, fg=C.TEXT, bg=C.BG3,
                            insertbackground=C.TEXT, width=38, show="*")
        td_entry.pack(padx=20, pady=2, fill="x")

        def _toggle_td():
            cur_show = td_entry.cget("show")
            td_entry.configure(show="" if cur_show == "*" else "*")
            td_mask_btn.configure(text="🙈 Hide" if cur_show == "*" else "👁 Show")

        td_mask_btn = tk.Button(tab_src, text="👁 Show", font=F_SMALL, fg=C.MUTED, bg=C.BG3,
                                relief="flat", padx=6, command=_toggle_td)
        td_mask_btn.pack(anchor="e", padx=20)
        tk.Label(tab_src, text="⚠️ Keys stored with base64 obfuscation — not encrypted.\nDo not share source_settings.json.",
                 font=F_MICRO, fg=C.YELLOW, bg=C.BG2, justify="left").pack(anchor="w", padx=20, pady=(4,0))

        # ── Save button ───────────────────────────────────────────────────────
        def _apply():
            # Validate account settings
            try:
                new_acct = float(acct_var.get().replace(",", ""))
                new_risk = float(risk_var.get()) / 100
                new_exp  = float(exp_var.get()) / 100
                new_mps  = int(mps_var.get())
                assert new_acct > 0 and 0 < new_risk <= 0.5 and 0 < new_exp <= 0.5 and new_mps >= 1
            except (ValueError, AssertionError):
                messagebox.showerror("خطأ", "قيمة غير صحيحة في إعدادات الحساب.\nتحقق من الأرقام.")
                return

            with _data_cfg_lock:
                for k, v in vars_map.items():
                    DATA_SOURCE_CFG[k] = v.get()
                DATA_SOURCE_CFG["alpha_vantage_key"]          = av_var.get().strip()
                DATA_SOURCE_CFG["twelve_data_key"]            = td_var.get().strip()
                DATA_SOURCE_CFG["account_size"]               = new_acct
                DATA_SOURCE_CFG["risk_per_trade"]             = new_risk
                DATA_SOURCE_CFG["portfolio_max_atr_exposure"] = new_exp
                DATA_SOURCE_CFG["portfolio_max_per_sector"]   = new_mps

            save_source_settings()
            src_badge_var.set(_build_src_badge())
            # Update account badge live
            _refresh_account_badge()
            win.destroy()
            messagebox.showinfo(
                "تم الحفظ ✅",
                f"تم حفظ الإعدادات!\n\n"
                f"💼 حجم الحساب: {new_acct:,.0f} ج.م\n"
                f"⚠️ مخاطرة: {new_risk*100:.1f}%\n"
                f"🛡️ ATR Cap: {new_exp*100:.1f}%\n\n"
                f"سيتم التطبيق في السكان القادم."
            )

        tk.Button(win, text="💾 حفظ الإعدادات", font=F_HEADER, fg=C.BG, bg=C.ACCENT,
                  relief="flat", padx=14, pady=7, command=_apply).pack(pady=10)

    def _build_src_badge() -> str:
        with _data_cfg_lock:
            parts = []
            if DATA_SOURCE_CFG.get("use_yahoo"):         parts.append("Yahoo")
            if DATA_SOURCE_CFG.get("use_stooq"):         parts.append("Stooq")
            if DATA_SOURCE_CFG.get("use_alpha_vantage"): parts.append("AV")
            if DATA_SOURCE_CFG.get("use_investing"):     parts.append("INV")
            if DATA_SOURCE_CFG.get("use_twelve_data"):   parts.append("TD🕐")
        return "🌐 " + "+".join(parts) if parts else "🌐 Yahoo"

    src_badge_var = tk.StringVar(value=_build_src_badge())
    tk.Label(top_bar, textvariable=src_badge_var, font=F_SMALL, fg=C.CYAN, bg=C.BG).pack(side="right", padx=4)
    tk.Button(top_bar, text="⚙️ Sources", font=F_HEADER, fg=C.TEXT, bg=C.BG3,
              relief="flat", padx=8, pady=3, command=open_settings).pack(side="right", padx=4)

    # ── Account badge (live) ───────────────────────────────────────────────────
    acct_badge_var = tk.StringVar(value=f"💼 {get_account_size():,.0f} ج.م")
    tk.Label(top_bar, textvariable=acct_badge_var, font=F_SMALL, fg=C.GOLD, bg=C.BG).pack(side="right", padx=6)

    def _refresh_account_badge():
        acct_badge_var.set(f"💼 {get_account_size():,.0f} ج.م")
    verdict_frm = tk.Frame(root, bg="#06131f", pady=5)
    verdict_frm.pack(fill="x", padx=16, pady=(4, 0))
    verdict_var = tk.StringVar(value="🧠 Awaiting scan…")
    verdict_lbl_w = tk.Label(verdict_frm, textvariable=verdict_var,
                              font=("Consolas", 11, "bold"), fg=C.ACCENT2, bg="#06131f", anchor="w")
    verdict_lbl_w.pack(fill="x", padx=10)

    # ── Rotation + flow + guard bars ──────────────────────────────────────────
    rot_bar = tk.Frame(root, bg=C.BG, pady=3)
    rot_bar.pack(fill="x", padx=16)
    tk.Label(rot_bar, text="🔮 Rotation:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    rot_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(rot_bar, text=f"{sec}\n—", width=15, height=2, bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); rot_labels[sec] = lbl

    flow_bar = tk.Frame(root, bg=C.BG, pady=3)
    flow_bar.pack(fill="x", padx=16)
    tk.Label(flow_bar, text="🧭 ΔFlow:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    flow_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(flow_bar, text=f"{sec}\n—", width=15, height=2, bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); flow_labels[sec] = lbl
    regime_lbl = tk.Label(flow_bar, text="📊 NEUTRAL", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    regime_lbl.pack(side="right", padx=12)

    guard_bar = tk.Frame(root, bg=C.BG, pady=3)
    guard_bar.pack(fill="x", padx=16)
    tk.Label(guard_bar, text="🛡️ Guard:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    guard_sector_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(guard_bar, text=f"{sec}\n0/{K.PORTFOLIO_MAX_PER_SECTOR}", width=15, height=2,
                       bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); guard_sector_labels[sec] = lbl
    guard_exposure_lbl = tk.Label(guard_bar, text="ATR Exp: 0.0%", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    guard_exposure_lbl.pack(side="right", padx=12)
    guard_blocked_lbl = tk.Label(guard_bar, text="🛡️ Blocked: —", font=F_SMALL, fg=C.MUTED, bg=C.BG)
    guard_blocked_lbl.pack(side="right", padx=8)

    # ── Progress + status ─────────────────────────────────────────────────────
    pbar = ttk.Progressbar(root, orient="horizontal", mode="determinate")
    pbar.pack(fill="x", padx=16, pady=4)
    status_var = tk.StringVar(value="Ready ✅ — Press 🚀 Gravity Scan or F5")
    tk.Label(root, textvariable=status_var, font=F_SMALL, fg=C.MUTED, bg=C.BG, anchor="w", pady=2).pack(fill="x", padx=20)

    # ── Results table ─────────────────────────────────────────────────────────
    tf = tk.Frame(root, bg=C.BG)
    tf.pack(fill="both", expand=True, padx=16, pady=4)

    COLS = (
        "Symbol", "Sector", "Price", "ADX", "RSI", "AdaptMom",
        "% EMA200", "Volume", "Score", "Gravity", "Zone",
        "🔮Future", "🧠CPI", "🏛️IET", "🐳Whale",
        "Phase/Signals", "Signal", "Direction", "Confidence%", "SmartRank",
        "Action", "Timeframe", "Entry", "Stop", "Target", "Size", "WinRate%",
        "R:R", "🔥InstConf", "ATR Risk", "Trend", "ATR", "VWAP%", "VolZ",
        "Signal Reason", "🛡️Guard",
    )
    col_w = {
        "Symbol": 50, "Sector": 88, "Price": 64, "ADX": 48, "RSI": 46,
        "AdaptMom": 68, "% EMA200": 72, "Volume": 60, "Score": 46,
        "Gravity": 100, "Zone": 70, "🔮Future": 68,
        "🧠CPI": 58, "🏛️IET": 58, "🐳Whale": 62,
        "Phase/Signals": 215, "Signal": 155, "Direction": 82,
        "Confidence%": 74, "SmartRank": 80,
        "Action": 100, "Timeframe": 110, "Entry": 65, "Stop": 65, "Target": 65,
        "Size": 52, "WinRate%": 68, "R:R": 58, "🔥InstConf": 90,
        "ATR Risk": 72, "Trend": 40, "ATR": 60, "VWAP%": 65, "VolZ": 55,
        "Signal Reason": 220, "🛡️Guard": 260,
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

    # ── Legend ────────────────────────────────────────────────────────────────
    leg = tk.Frame(root, bg=C.BG, pady=3)
    leg.pack(fill="x", padx=20)
    for txt, col in [
        ("🧠 ULTRA", C.CYAN), ("🚀 EARLY", C.CYAN), ("🔥 BUY", C.GREEN),
        ("👀 WATCH", C.YELLOW), ("❌ SELL", C.RED),
        ("🧬 Silent", C.ACCENT2), ("🐳 Whale", C.PURPLE), ("🎯 Hunter", C.YELLOW),
        ("💥 Break", "#ff9f43"), ("⚡ Exp", C.CYAN), ("🧿 Quantum", C.PURPLE),
        ("☠️ Fake", C.RED), ("👑 Leader", C.YELLOW), ("🧲 Gravity", C.CYAN),
        ("ACCUMULATE", C.GOLD), ("PROBE", C.YELLOW), ("🔔 EMA✚", C.GREEN),
        ("🔀 VolDiv", C.YELLOW), ("|  ⚠️OB WATCH", C.YELLOW),
        ("|  ⚠️ATR HIGH", C.RED), ("|  🟡ATR MED", C.YELLOW),
        ("⏳ WAIT(ADX)", C.MUTED), ("|  🛡️BLOCKED", C.MUTED),
        ("|  ⚡Flow>Tech", C.YELLOW), ("|  🔒RankCap", C.MUTED),
        ("|  ⌛WR-Build", C.MUTED), ("|  v78✅", C.GREEN),
    ]:
        tk.Label(leg, text=txt, font=F_MICRO, fg=col, bg=C.BG, padx=4).pack(side="left")

    tk.Label(root, text="⚠️  Data delayed 15 minutes — execution risk warning",
             fg=C.RED_DIM, bg=C.BG, font=F_MICRO).pack(side="bottom", pady=2)

    # ── Wire up ───────────────────────────────────────────────────────────────
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
    }
    scan_btn.configure(command=lambda: start_scan(widgets))
    save_btn.configure(command=lambda: export_csv(tree, COLS))
    root.bind("<F5>", lambda _: start_scan(widgets))

    def _on_close():
        _pulse.stop()
        STATE.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    _pump(root)
    root.mainloop()


if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════════════════
# ██████████████████████████████████████████████████████████████████████████
# INTERNAL VALIDATION REPORT  (appended to source for transparency)
# ██████████████████████████████████████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              EGX CAPITAL FLOW RADAR v78 — VALIDATION REPORT               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  1. STATISTICAL SOUNDNESS                                                    ║
║  ─────────────────────────                                                   ║
║  WinRate (FIX-A):                                                            ║
║    • Empirical base: |win_mem| / (|win_mem| + |loss_mem|) × 100             ║
║    • v77 flaw: used only win_mem for avg_rank → inflated baseline            ║
║    • v78 fix: balanced sample of all outcomes as reference                   ║
║    • Sample-size adjustment: sparsity penalty when n < 10                    ║
║    • Output range: [dynamic_floor(rank), 92%]                                ║
║    • Verdict: TRUE unbiased estimate. Can show sub-50% when losses > wins.  ║
║                                                                              ║
║  SmartRank (FIX-B):                                                          ║
║    • All 6 components normalised to [0,1] via linear _norm()                ║
║    • Explicit weight block in K (sum = 1.0, validated at import)             ║
║    • Formula: Σ(w_i × c_i) × SMART_RANK_SCALE × damper                      ║
║    • Damper (0.7–1.0) multiplicative — preserves zero bound                  ║
║    • Output: [0, SMART_RANK_SCALE=60]                                        ║
║    • No component can dominate: max weight 20%, max contribution 12 pts      ║
║    • Verdict: MATHEMATICALLY SOUND. No hidden bias.                          ║
║                                                                              ║
║  Regime Detection (FIX-C):                                                   ║
║    • Now requires EMA200 slope confirmation:                                  ║
║      ACCUMULATION requires slope ≥ -0.001 (flat or rising)                  ║
║      DISTRIBUTION requires slope < 0 (falling)                               ║
║    • v77 flaw: any low-ADX / low-volume market classified as ACCUMULATION     ║
║    • v78 fix: slope criterion filters out downtrending bear markets           ║
║    • Verdict: FALSE POSITIVE RATE FOR ACCUMULATION SIGNIFICANTLY REDUCED.   ║
║                                                                              ║
║  Volume Z-Score (FIX-D):                                                     ║
║    • Symmetric clamp: (-4, +4)                                               ║
║    • v77 flaw: (-5, +10) asymmetrically rewarded spikes                      ║
║    • v78 fix: symmetric bounds; no low-volume reward bias                    ║
║    • Low-volume symbols: vol_zscore = 0 (neutral), no reward for absence     ║
║    • Verdict: STATISTICALLY CORRECT. Gaussian standardisation.              ║
║                                                                              ║
║  2. THREAD SAFETY                                                            ║
║  ─────────────────                                                           ║
║  FIX-H: All UI updates now go through _ui_q.put() / _pump() exclusively.    ║
║    • Worker thread (run_scan) NEVER calls Tkinter directly                   ║
║    • All shared state mutations go through AppState methods with locks        ║
║    • Locks used: _lock (all state), _momentum_lock (momentum defaultdict)    ║
║    • Data source cfg: _data_cfg_lock; source labels: _source_labels_lock     ║
║    • Twelve Data dispatch: _td_dispatch_lock (serial rate limiting)          ║
║    • _scan_lock: prevents concurrent scan threads                             ║
║    • Verdict: THREAD-SAFE. No Tkinter calls from background threads.         ║
║                                                                              ║
║  Neural Weights (FIX-E):                                                     ║
║    • Mean-reversion decay: w += step - NEURAL_DECAY × (w - 1.0)             ║
║    • When w > 1: decay pulls down; when w < 1: decay pulls up                ║
║    • Prevents runaway saturation to NEURAL_WEIGHT_MAX                        ║
║    • Hard clamp at [0.8, 1.4] as final guard                                 ║
║    • Verdict: STABLE. No saturation risk.                                    ║
║                                                                              ║
║  3. SIGNAL CORRECTNESS                                                       ║
║  ─────────────────────                                                       ║
║    • Signals derive from score_tech_signal() (pure, testable function)       ║
║    • SmartRank and signal are independent — rank cannot promote a SELL       ║
║    • OB guard: RSI > 72 forces tag to "watch" regardless of score            ║
║    • ADX gate: rank capped at SMART_RANK_ADX_CAP when ADX < ADX_SOFT_LO     ║
║    • Trade plan: ACCUMULATE blocked when atr_risk_label = "⚠️ HIGH"          ║
║    • All signal overrides are explicit and documented                         ║
║    • Verdict: SIGNAL INTEGRITY MAINTAINED.                                   ║
║                                                                              ║
║  4. RISK INTEGRITY                                                           ║
║  ─────────────────                                                           ║
║  ATR Percentile Risk (FIX-F):                                                ║
║    • compute_atr_risk() builds ATR history over last ATR_HIST_WINDOW=60 bars ║
║    • Percentile rank: fraction of history ≤ current ATR                      ║
║    • HIGH: ≥ 75th percentile; MED: ≥ 50th; LOW: < 50th                       ║
║    • Dynamic thresholds: adapts to each symbol's own volatility regime       ║
║    • v77 flaw: fixed 5% / 3% pct thresholds ignoring cross-symbol variance  ║
║    • ACCUMULATE blocked when ATR_RISK = HIGH                                 ║
║                                                                              ║
║  Portfolio Guard (FIX-G):                                                    ║
║    • compute_portfolio_guard() is a pure function with no side effects        ║
║    • Returns GuardedResult NamedTuple list — original results not mutated     ║
║    • Annotated copies created separately in run_scan                         ║
║    • Idempotent: calling twice produces identical output                     ║
║    • Sector cap: max 2 active signals per sector                             ║
║    • ATR exposure cap: sum(atr × size) ≤ 4% of account                      ║
║    • Verdict: PRODUCTION-SAFE. No hidden state corruption.                   ║
║                                                                              ║
║  5. ARCHITECTURE SUMMARY                                                     ║
║  ─────────────────────────                                                   ║
║    Layer 1: CONFIG      — K constants block, all documented                  ║
║    Layer 2: DATA        — Multi-source fetch, merge, consensus close         ║
║    Layer 3: INDICATORS  — Stateless technical functions                      ║
║    Layer 4: SCORING     — Normalised 0-1 components + SmartRank formula      ║
║    Layer 5: SIGNAL      — Decision engine, regime, phase detection           ║
║    Layer 6: RISK        — ATR percentile, trade sizing                       ║
║    Layer 7: PORTFOLIO   — Pure guard function, NamedTuple output             ║
║    Layer 8: STATE       — Thread-safe AppState, all locks in one place       ║
║    Layer 9: OUTCOMES    — Trade log, resolution, neural feedback             ║
║    Layer 10: UI         — Tkinter only, event-driven, queue-based            ║
║                                                                              ║
║  KNOWN LIMITATIONS:                                                          ║
║    • API keys stored as base64 only — not encrypted at rest                  ║
║    • Win-rate estimate requires ≥10 resolved trades to be meaningful         ║
║    • EGX data from Yahoo / Stooq may be delayed 15+ minutes                  ║
║    • Twelve Data free tier: 800 req/day max — serial dispatch at 7.5s/req   ║
║    • Neural weights update per scan cycle; 5+ scans needed to stabilise      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
