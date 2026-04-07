#!/usr/bin/env python3
"""
EGX Radar — Ablation Testing Framework
======================================
Identifies the TRUE source of edge by selectively disabling major components.

Tests run:
  0. Baseline          — all components active, production config
  1. No Regime         — detect_market_regime, apply_regime_gate disabled
  2. No SmartRank      — smart_rank replaced with simple momentum proxy
  3. No Accumulation   — evaluate_accumulation_context forced permissive
  4. No Guards         — compute_portfolio_guard + _is_high_probability_trade bypassed
  5. Raw System        — all four filters disabled simultaneously

Same dataset, same period, same execution model for all tests.
All changes are temporary (unittest.mock patch context managers).
"""

import sys
import os
import math
import logging
import contextlib
import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

# Suppress noisy logs from yfinance and the scanner internals
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
for noisy in ("yfinance", "peewee", "urllib3", "requests", "egx_radar"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

# ─────────────────────────────────────────────────────────────────────────────
# Import all modules BEFORE any patching so references are stable
# ─────────────────────────────────────────────────────────────────────────────
import egx_radar.backtest.engine as eng
import egx_radar.core.signal_engine as sig_eng
import egx_radar.core.accumulation as accum_mod
import egx_radar.core.portfolio as port_mod

from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.data_loader import load_backtest_data
from egx_radar.backtest.metrics import compute_metrics
from egx_radar.core.portfolio import GuardedResult
from egx_radar.core.signal_engine import classify_trade_type

# Capture originals BEFORE any patch is applied.  These never change.
_ORIG_EVAL_SNAPSHOT = eng.evaluate_symbol_snapshot        # from signal_engine
_ORIG_ACCUM_CTX     = accum_mod.evaluate_accumulation_context

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
DATE_FROM = "2024-01-01"
DATE_TO   = "2024-12-31"

BANNER = "=" * 72

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Download data once, cache in memory
# ─────────────────────────────────────────────────────────────────────────────
print(BANNER)
print("  EGX RADAR - ABLATION TESTING FRAMEWORK")
print(f"  Period : {DATE_FROM}  ->  {DATE_TO}")
print(f"  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(BANNER)
print()
print("Downloading market data (once for all 6 tests)...")

_CACHED_DATA: Dict[str, Any] = load_backtest_data(DATE_FROM, DATE_TO)
_SYMBOLS_LOADED = len(_CACHED_DATA)
print(f"  OK  {_SYMBOLS_LOADED} symbols loaded.\n")

if _SYMBOLS_LOADED == 0:
    sys.exit("No market data returned. Check yfinance connectivity and symbol list.")


def _mock_loader(date_from: str, date_to: str):
    """Return the pre-loaded dataset for every test run."""
    return _CACHED_DATA


# ─────────────────────────────────────────────────────────────────────────────
# Patch factories (NO REGIME)
# ─────────────────────────────────────────────────────────────────────────────
#
# Three engine-level names are patched:
#   • detect_market_regime(proxy_df) → always "STRONG"
#     (bypasses weak-market regime filters in run_backtest loop)
#   • detect_conservative_market_regime(results) → always "BULL"
#     (bypasses apply_regime_gate call and NEUTRAL/BEAR blocks)
#   • apply_regime_gate(result, regime) → passthrough identity
#     (safety net — makes damping a no-op even if somehow called)
#
_NO_REGIME_PATCHES = [
    patch.object(eng, "detect_market_regime",            return_value="STRONG"),
    patch.object(eng, "detect_conservative_market_regime", return_value="BULL"),
    patch.object(eng, "apply_regime_gate",               side_effect=lambda r, _regime: r),
]

# ─────────────────────────────────────────────────────────────────────────────
# Patch factories (NO SMARTRANK)
# ─────────────────────────────────────────────────────────────────────────────
#
# Wraps evaluate_symbol_snapshot to replace the composite SmartRank score
# with a simple momentum + volume proxy, completely independent of the
# four accumulation sub-scores.
#
# Proxy formula:
#   proxy = 50 + adaptive_mom * 2.0 + (vol_ratio - 1.0) * 8.0
#   clamped to [0, 100]
#
# A stock with flat momentum (0) and average volume (vol_ratio=1) → proxy=50.
# Positive momentum and above-average volume push it toward 90+.
# Negative momentum and thin volume push it below 50 (filtered out).
#
def _eval_no_smartrank(df_ta, sym: str, sector: str, regime: str = "BULL"):
    result = _ORIG_EVAL_SNAPSHOT(df_ta, sym, sector, regime)
    if result is None:
        return None

    adaptive_mom = result.get("adaptive_mom", 0.0)
    vol_ratio    = result.get("vol_ratio",    1.0)
    proxy        = min(max(0.0, 50.0 + adaptive_mom * 2.0 + (vol_ratio - 1.0) * 8.0), 100.0)
    proxy        = round(proxy, 2)

    result["smart_rank"] = proxy

    # Update plan classifications to be consistent with the proxy score
    if result.get("plan"):
        proxy_type = classify_trade_type(proxy)
        result["plan"]["score"]      = proxy
        result["plan"]["trade_type"] = proxy_type if proxy_type else "SKIP"
        # If proxy is high enough to trade but plan said WAIT, keep WAIT
        # (entry_ready condition is NOT changed here — only SmartRank changes)

    return result


_NO_SMARTRANK_PATCHES = [
    patch.object(eng, "evaluate_symbol_snapshot", side_effect=_eval_no_smartrank),
]

# ─────────────────────────────────────────────────────────────────────────────
# Patch factories (NO ACCUMULATION)
# ─────────────────────────────────────────────────────────────────────────────
#
# Patches evaluate_accumulation_context (in signal_engine's namespace, where
# evaluate_symbol_snapshot calls it) to return the real computed context but
# with three booleans forced to permissive values:
#
#   accumulation_detected = True   → passes the accumulation prerequisite
#   entry_ready           = True   → allows ACCUMULATE/PROBE actions
#   fake_move             = False  → removes the fake-move hard block
#
# All numeric scores (quality, structure, volume, trend) remain as computed
# from real market data — SmartRank is unchanged by this patch.
#
def _accum_bypass(df_ta, *, price, ema20, ema50, ema200,
                  ema20_slope_pct, ema50_slope_pct, ema200_slope_pct,
                  rsi, adx, avg_turnover, spread_pct,
                  avg_vol, vol_ratio, vol_zscore):
    ctx = _ORIG_ACCUM_CTX(
        df_ta,
        price=price, ema20=ema20, ema50=ema50, ema200=ema200,
        ema20_slope_pct=ema20_slope_pct, ema50_slope_pct=ema50_slope_pct,
        ema200_slope_pct=ema200_slope_pct,
        rsi=rsi, adx=adx, avg_turnover=avg_turnover, spread_pct=spread_pct,
        avg_vol=avg_vol, vol_ratio=vol_ratio, vol_zscore=vol_zscore,
    )
    ctx = dict(ctx)
    ctx["accumulation_detected"] = True
    ctx["entry_ready"]           = True
    ctx["fake_move"]             = False   # allow candidate setups including marginal ones
    return ctx


_NO_ACCUMULATION_PATCHES = [
    # Must be patched in signal_engine's namespace — that's where
    # evaluate_symbol_snapshot resolves the name at call time.
    patch.object(sig_eng, "evaluate_accumulation_context", side_effect=_accum_bypass),
]

# ─────────────────────────────────────────────────────────────────────────────
# Patch factories (NO GUARDS)
# ─────────────────────────────────────────────────────────────────────────────
#
# Two guards are bypassed:
#
#   1. compute_portfolio_guard — the sector cap / ATR exposure / position-count
#      gate.  Bypass returns every result as unblocked (is_blocked=False).
#
#   2. _is_high_probability_trade — the 10-factor quality gate with hard
#      disqualifiers (fake_move, erratic_volume, smart_rank < 50, low turnover,
#      LATE zone).  Bypass always returns True.
#
# Note: the liquidity pre-filter inside evaluate_symbol_snapshot
# (avg_turnover < K.MIN_TURNOVER_EGP) is kept as data-quality, not a guard.
#
def _guard_bypass(results, account_size=None, open_trades=None):
    return (
        [GuardedResult(r, "", False) for r in results],
        {},
        0.0,
        [],
        False,
    )


_NO_GUARDS_PATCHES = [
    patch.object(eng, "compute_portfolio_guard",    side_effect=_guard_bypass),
    patch.object(eng, "_is_high_probability_trade", return_value=True),
]

# ─────────────────────────────────────────────────────────────────────────────
# Patch factories (RAW SYSTEM — all 4 filters disabled simultaneously)
# ─────────────────────────────────────────────────────────────────────────────
_RAW_PATCHES = (
    _NO_REGIME_PATCHES
    + _NO_SMARTRANK_PATCHES
    + _NO_ACCUMULATION_PATCHES
    + _NO_GUARDS_PATCHES
)

# ─────────────────────────────────────────────────────────────────────────────
# Core runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_variant(label: str, extra_patches: list) -> Dict[str, Any]:
    """
    Apply patches, run backtest, return metrics dict.
    The data-loader mock is always included to avoid re-downloading.
    """
    print(f"  Running: {label} ...", end="", flush=True)

    try:
        with contextlib.ExitStack() as stack:
            # Always serve cached data
            stack.enter_context(
                patch.object(eng, "load_backtest_data", side_effect=_mock_loader)
            )
            # Apply ablation patches
            for cm in extra_patches:
                stack.enter_context(cm)

            trades, _equity_curve, _params, _extras = run_backtest(DATE_FROM, DATE_TO)

        if not trades:
            print(" -> 0 trades -- all signals filtered out")
            return {
                "label": label, "trades": 0,
                "win_rate": None, "profit_factor": None,
                "expectancy": None, "max_dd": None,
            }

        m = compute_metrics(trades)["overall"]
        print(
            f" -> {m['total_trades']} trades | "
            f"WR {m['win_rate_pct']:.1f}% | "
            f"PF {m['profit_factor']:.2f} | "
            f"Exp {m['expectancy_pct']:+.2f}% | "
            f"DD -{m['max_drawdown_pct']:.1f}%"
            f" | Sharpe {m['sharpe_ratio']:.2f}"
        )
        return {
            "label":          label,
            "trades":         m["total_trades"],
            "win_rate":       m["win_rate_pct"],
            "profit_factor":  m["profit_factor"],
            "expectancy":     m["expectancy_pct"],
            "max_dd":         m["max_drawdown_pct"],
            "sharpe":         m["sharpe_ratio"],
            "avg_bars":       m["avg_bars_in_trade"],
            "total_return":   m["total_return_pct"],
        }

    except Exception as exc:
        import traceback
        print(f" -> ERROR: {exc}")
        traceback.print_exc()
        return {
            "label": label, "trades": "ERR", "win_rate": "ERR",
            "profit_factor": "ERR", "expectancy": "ERR", "max_dd": "ERR",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Run all 6 variants
# ─────────────────────────────────────────────────────────────────────────────
print("Running ablation tests (same data, same execution model):\n")

RESULTS: List[Dict[str, Any]] = []

VARIANTS = [
    ("Baseline",        []),
    ("No Regime",       _NO_REGIME_PATCHES),
    ("No SmartRank",    _NO_SMARTRANK_PATCHES),
    ("No Accumulation", _NO_ACCUMULATION_PATCHES),
    ("No Guards",       _NO_GUARDS_PATCHES),
    ("Raw System",      _RAW_PATCHES),
]

for _label, _patches in VARIANTS:
    RESULTS.append(_run_variant(_label, _patches))

# ─────────────────────────────────────────────────────────────────────────────
# Output table
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(val, digits=2, signed=False, pct=False):
    if val is None or val == "ERR" or val == "N/A":
        return str(val) if val is not None else "N/A"
    if isinstance(val, str):
        return val
    suffix = "%" if pct else ""
    sign   = "+" if signed and val > 0 else ""
    return f"{sign}{val:.{digits}f}{suffix}"


baseline = RESULTS[0] if RESULTS else {}

print()
print(BANNER)
print("  ABLATION RESULTS")
print(BANNER)

col_widths = [18, 7, 10, 12, 12, 9, 8]
headers    = ["Test Variant", "Trades", "Win Rate", "Prof.Factor", "Expectancy", "Max DD", "Sharpe"]
row_fmt    = "{:<18} {:>7} {:>10} {:>12} {:>12} {:>9} {:>8}"

print(row_fmt.format(*headers))
print("-" * 80)

for r in RESULTS:
    name   = r["label"]
    trades = str(r["trades"])
    wr     = _fmt(r.get("win_rate"),      digits=1, pct=True)
    pf     = _fmt(r.get("profit_factor"), digits=2)
    ex     = _fmt(r.get("expectancy"),    digits=2, signed=True, pct=True)
    dd     = f"-{r['max_dd']:.1f}%" if isinstance(r.get("max_dd"), (int, float)) else str(r.get("max_dd", "N/A"))
    sh     = _fmt(r.get("sharpe"),        digits=2)

    # Highlight baseline with asterisk
    marker = " *" if name == "Baseline" else "  "
    print(row_fmt.format(name + marker, trades, wr, pf, ex, dd, sh))

print("-" * 80)
print("  * = Baseline (production config)")
print()

# ─────────────────────────────────────────────────────────────────────────────
# Delta vs Baseline (quantitative impact analysis)
# ─────────────────────────────────────────────────────────────────────────────
print(BANNER)
print("  DELTA vs BASELINE  (ablated - baseline)")
print(BANNER)

delta_fmt = "{:<18} {:>10} {:>12} {:>12} {:>9}"
print(delta_fmt.format("Test Variant", "dWin Rate", "dProf.Factor", "dExpectancy", "dMax DD"))
print("-" * 65)

def _delta(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a - b
    return None

bl = RESULTS[0] if RESULTS else {}

for r in RESULTS[1:]:
    name = r["label"]
    dwr  = _delta(r.get("win_rate"),      bl.get("win_rate"))
    dpf  = _delta(r.get("profit_factor"), bl.get("profit_factor"))
    dex  = _delta(r.get("expectancy"),    bl.get("expectancy"))
    ddd  = _delta(r.get("max_dd"),        bl.get("max_dd"))   # positive = worse DD

    wr_s  = f"{dwr:+.1f}%" if dwr is not None else "N/A"
    pf_s  = f"{dpf:+.2f}"  if dpf is not None else "N/A"
    ex_s  = f"{dex:+.2f}%" if dex is not None else "N/A"
    dd_s  = f"{ddd:+.1f}%" if ddd is not None else "N/A"

    print(delta_fmt.format(name, wr_s, pf_s, ex_s, dd_s))

print()

# ─────────────────────────────────────────────────────────────────────────────
# Quant analysis
# ─────────────────────────────────────────────────────────────────────────────
print(BANNER)
print("  QUANT ANALYSIS")
print(BANNER)

def _impact_score(r, bl) -> float:
    """Single composite impact metric: sum of normalised deltas (higher = more damage done by removing)."""
    if not isinstance(r.get("win_rate"), (int, float)):
        return float("inf")  # error cases sort last
    wr_delta  = (bl.get("win_rate",      0) - r.get("win_rate",      0)) / max(bl.get("win_rate",      1), 1e-9) * 100
    pf_delta  = (bl.get("profit_factor", 0) - r.get("profit_factor", 0)) / max(bl.get("profit_factor", 1), 1e-9) * 100
    ex_delta  = (bl.get("expectancy",    0) - r.get("expectancy",    0))   # already normalised per-trade %
    return wr_delta + pf_delta + ex_delta


ranked = sorted(RESULTS[1:], key=lambda r: _impact_score(r, bl), reverse=True)

print()
print("  Component Importance Ranking (most damaging to remove = most valuable):\n")
for rank, r in enumerate(ranked, 1):
    impact = _impact_score(r, bl)
    label  = r["label"]
    if isinstance(r.get("win_rate"), (int, float)):
        ex_dir = "v" if r.get("expectancy", 0) < bl.get("expectancy", 0) else "^"
        pf_dir = "v" if r.get("profit_factor", 0) < bl.get("profit_factor", 0) else "^"
        note   = f"Expectancy {ex_dir}  PF {pf_dir}"
    else:
        note = "error — check logs"
    print(f"  #{rank}  {label:<20}  impact score={impact:+.1f}   {note}")

print()
print("  Interpretation guide:")
print("    Positive impact score: removing this component HURTS performance")
print("    Negative impact score: removing this component HELPS performance")
print("    Score ~0            : component has negligible effect")
print()

# ─────────────────────────────────────────────────────────────────────────────
# Trading-volume analysis (how filters affect trade count)
# ─────────────────────────────────────────────────────────────────────────────
baseline_trades = bl.get("trades", 1) or 1
print("  Filter trade-count effect:\n")
for r in RESULTS[1:]:
    tr = r.get("trades", 0)
    if isinstance(tr, int) and isinstance(baseline_trades, int) and baseline_trades > 0:
        pct_change = (tr - baseline_trades) / baseline_trades * 100
        bar_len    = int(abs(pct_change) / 5)
        bar        = ("|" * bar_len) if pct_change >= 0 else ("." * bar_len)
        direction  = "+" if pct_change >= 0 else "-"
        bar_ascii  = bar.encode('ascii', errors='replace').decode('ascii')
        print(f"  {r['label']:<20}  {str(tr):>4} trades  ({direction}{abs(pct_change):.0f}%)")

print()

# ─────────────────────────────────────────────────────────────────────────────
# Save JSON results for external analysis
# ─────────────────────────────────────────────────────────────────────────────
out_file = os.path.join(os.path.dirname(__file__), "_ablation_results.json")
with open(out_file, "w") as f:
    json.dump({
        "run_at":   datetime.now().isoformat(),
        "date_from": DATE_FROM,
        "date_to":   DATE_TO,
        "symbols_loaded": _SYMBOLS_LOADED,
        "results":  RESULTS,
    }, f, indent=2, default=str)

print(f"  Results saved to: {out_file}")
print()
print(BANNER)
print("  ABLATION TEST COMPLETE")
print(BANNER)
