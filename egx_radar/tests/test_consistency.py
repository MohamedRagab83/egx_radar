"""
Phase 2 - Live Scan vs Backtest Consistency Check
==================================================

Proves that LIVE SCAN == BACKTEST by running the same core signal computation
on the same OHLC data slice and comparing outputs.

Both paths now use evaluate_symbol_snapshot() with a dynamically computed
pre_regime. The consistency question is:

  1. Do the two regime-detection methods agree for the same market date?
  2. When they disagree, how different are the resulting signals?

Usage:
    python -m pytest egx_radar/tests/test_consistency.py -v -s
    or:
    python egx_radar/tests/test_consistency.py
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd

from egx_radar.config.settings import K, SYMBOLS, get_sector
from egx_radar.backtest.engine import detect_market_regime
from egx_radar.core.signal_engine import (
    apply_entry_timing_filter,
    evaluate_symbol_snapshot,
    is_high_probability_trade,
)

log = logging.getLogger(__name__)

# -- Test parameters ---------------------------------------------------------
DATE_FROM   = "2022-01-01"   # extend to get enough bars for EMA200 warmup
DATE_TO     = "2024-12-31"
TEST_FROM   = "2024-10-01"   # only TEST dates are sampled from here
N_SYMBOLS   = 20          # number of EGX symbols to test
N_DATES     = 10          # number of market dates to sample
DATE_STRIDE = 6           # pick every Nth trading day

# Symbols to use (first N from the watchlist, excluding the proxy index)
_ALL_SYMS = [s for s in SYMBOLS if s != K.EGX30_SYMBOL.replace(".CA", "").replace("^", "")]
TEST_SYMBOLS = list(SYMBOLS.keys())[:N_SYMBOLS]


# -- Regime helpers -----------------------------------------------------------

def compute_scan_regime(all_data: dict, date: pd.Timestamp) -> str:
    """
    Live-scan regime method: market breadth (% of symbols whose price > EMA50).
    Returns "BULL" or "NEUTRAL".
    """
    above_ema50 = 0
    total_checked = 0
    for yahoo_sym, df in all_data.items():
        if df is None or df.empty or "Close" not in df.columns:
            continue
        df_to_date = df[df.index <= date]
        close = df_to_date["Close"].dropna()
        if len(close) < 52:
            continue
        try:
            ema50_val = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
            price_val = float(close.iloc[-1])
            total_checked += 1
            if price_val > ema50_val:
                above_ema50 += 1
        except (IndexError, ValueError, TypeError):
            continue

    if total_checked == 0:
        return "BULL"   # no data -> optimistic default matches scan behavior

    breadth_ratio = above_ema50 / total_checked
    market_healthy = breadth_ratio > K.MARKET_BREADTH_THRESHOLD
    return "BULL" if market_healthy else "NEUTRAL"


def compute_bt_regime(all_data: dict, date: pd.Timestamp) -> str:
    """
    Backtest regime method: proxy index (detect_market_regime on EGX30 proxy).
    Returns "BULL" or "NEUTRAL".
    """
    proxy_df = all_data.get(K.EGX30_SYMBOL)
    if proxy_df is None or date not in proxy_df.index:
        return "BULL"   # no proxy data -> same fallback as backtest engine

    proxy_slice = proxy_df[proxy_df.index <= date].tail(260).copy()
    market_regime = detect_market_regime(proxy_slice)
    return "BULL" if market_regime == "STRONG" else "NEUTRAL"


# -- Single-symbol evaluators -------------------------------------------------

def _eval_with_regime(
    sym: str,
    df_slice: pd.DataFrame,
    regime: str,
) -> Optional[Dict[str, Any]]:
    """
    Evaluate a single symbol exactly as both live scan and backtest do:
      1. evaluate_symbol_snapshot  (shared function, deterministic)
      2. apply_entry_timing_filter (present in live scan post-Phase 1)
    Returns None if signal computation rejected the symbol.
    """
    result = evaluate_symbol_snapshot(
        df_ta=df_slice,
        sym=sym,
        sector=get_sector(sym),
        regime=regime,
    )
    if result is None:
        return None

    # Apply timing filter - mirrors scan/runner.py post-evaluate step
    plan = result.get("plan")
    if plan and plan.get("action") in ("ACCUMULATE", "PROBE"):
        zone       = result.get("zone", "")
        pct_ema200 = float(result.get("pct_ema200", 0.0))
        plan, timing_blocked, _ = apply_entry_timing_filter(plan, result, zone, pct_ema200)
        result["plan"]           = plan
        result["timing_blocked"] = timing_blocked

    # Apply is_high_probability_trade - shared gate for both paths
    plan = result.get("plan") or {}
    if plan.get("action") in ("ACCUMULATE", "PROBE"):
        if not is_high_probability_trade(result):
            plan = dict(plan)
            plan["action"]     = "WAIT"
            plan["force_wait"] = True
            plan["size"]       = 0
            result["plan"]     = plan

    return result


def run_scan_single(sym: str, df_slice: pd.DataFrame, scan_regime: str) -> Optional[Dict]:
    """Live-scan path: evaluate with scan regime."""
    return _eval_with_regime(sym, df_slice, scan_regime)


def run_backtest_single(sym: str, df_slice: pd.DataFrame, bt_regime: str) -> Optional[Dict]:
    """Backtest path: evaluate with backtest regime."""
    return _eval_with_regime(sym, df_slice, bt_regime)


# -- Core comparison function -------------------------------------------------

def compare_single_day(
    sym: str,
    df_slice: pd.DataFrame,
    scan_regime: str,
    bt_regime: str,
    date: str,
) -> Dict[str, Any]:
    """
    Compare live-scan vs backtest for a single symbol on a single day.

    Returns a dict with:
      same_signal, same_entry, same_sl, same_tp, match, regime_match, ...
    """
    scan_result = run_scan_single(sym, df_slice, scan_regime)
    bt_result   = run_backtest_single(sym, df_slice, bt_regime)

    base = {
        "sym":          sym,
        "date":         date,
        "scan_regime":  scan_regime,
        "bt_regime":    bt_regime,
        "regime_match": scan_regime == bt_regime,
    }

    # Both rejected - consistent (both say "no signal")
    if scan_result is None and bt_result is None:
        return {**base, "match": True,  "reason": "both_none",
                "same_signal": True, "same_entry": True, "same_sl": True, "same_tp": True}

    # One rejected, other didn't - inconsistency
    if scan_result is None or bt_result is None:
        return {**base, "match": False, "reason": "one_rejected",
                "same_signal": False, "same_entry": False, "same_sl": False, "same_tp": False,
                "detail": f"scan={'None' if scan_result is None else 'result'} "
                          f"bt={'None' if bt_result is None else 'result'}"}

    scan_plan = scan_result.get("plan") or {}
    bt_plan   = bt_result.get("plan") or {}

    scan_action = scan_plan.get("action", "WAIT")
    bt_action   = bt_plan.get("action",   "WAIT")

    def safe_round(x: Any) -> float:
        try:
            v = float(x)
            return round(v, 2) if math.isfinite(v) else 0.0
        except (TypeError, ValueError):
            return 0.0

    scan_entry  = safe_round(scan_plan.get("entry",  0))
    bt_entry    = safe_round(bt_plan.get("entry",    0))
    scan_stop   = safe_round(scan_plan.get("stop",   0))
    bt_stop     = safe_round(bt_plan.get("stop",     0))
    scan_target = safe_round(scan_plan.get("target", 0))
    bt_target   = safe_round(bt_plan.get("target",   0))

    same_signal = scan_action == bt_action
    same_entry  = abs(scan_entry  - bt_entry)  < 0.02   # ±0.02 EGP tolerance
    same_sl     = abs(scan_stop   - bt_stop)   < 0.02
    same_tp     = abs(scan_target - bt_target) < 0.02
    match       = same_signal and same_entry and same_sl and same_tp

    record = {
        **base,
        "match":       match,
        "reason":      "full_compare",
        "same_signal": same_signal,
        "same_entry":  same_entry,
        "same_sl":     same_sl,
        "same_tp":     same_tp,
        "scan_action": scan_action,
        "bt_action":   bt_action,
    }

    if not same_signal:
        record["signal_delta"] = f"{scan_action} -> {bt_action}"
    if not same_entry:
        record["entry_delta"]  = f"{scan_entry} vs {bt_entry}"
    if not same_sl:
        record["sl_delta"]     = f"{scan_stop} vs {bt_stop}"
    if not same_tp:
        record["tp_delta"]     = f"{scan_target} vs {bt_target}"

    return record


# -- Main test runner ---------------------------------------------------------

def run_consistency_test(
    all_data: dict,
    test_symbols: List[str],
    test_dates: List[pd.Timestamp],
) -> Dict[str, Any]:
    """
    Run compare_single_day for every (symbol, date) pair.
    Returns aggregated results and full mismatch list.
    """
    results    : List[Dict] = []
    mismatches : List[Dict] = []

    for date in test_dates:
        scan_regime = compute_scan_regime(all_data, date)
        bt_regime   = compute_bt_regime(all_data, date)

        for sym in test_symbols:
            yahoo = SYMBOLS.get(sym)
            if yahoo not in all_data:
                continue
            df = all_data[yahoo]
            if df is None or date not in df.index:
                continue

            df_slice = df[df.index <= date].tail(260).copy()
            if len(df_slice) < K.MIN_BARS:
                continue

            record = compare_single_day(
                sym, df_slice, scan_regime, bt_regime, date.strftime("%Y-%m-%d")
            )
            results.append(record)
            if not record["match"]:
                mismatches.append(record)

    # -- Aggregate stats ---------------------------------------------------
    total = len(results)
    if total == 0:
        return {"error": "No results computed - check data availability"}

    matched            = sum(1 for r in results if r["match"])
    regime_agreed      = sum(1 for r in results if r["regime_match"])
    signal_matched     = sum(1 for r in results if r["same_signal"])
    entry_matched      = sum(1 for r in results if r["same_entry"])
    sl_matched         = sum(1 for r in results if r["same_sl"])
    tp_matched         = sum(1 for r in results if r["same_tp"])

    regime_disagree    = [r for r in results if not r["regime_match"]]
    regime_disagree_mismatches = [r for r in regime_disagree if not r["match"]]

    # Signal breakdown for mismatches
    signal_mismatches  = [r for r in mismatches if not r["same_signal"]]

    # Per-date regime summary
    date_regime: Dict[str, Dict] = {}
    for date in test_dates:
        ds = date.strftime("%Y-%m-%d")
        day_results = [r for r in results if r["date"] == ds]
        if day_results:
            sr = day_results[0]["scan_regime"]
            br = day_results[0]["bt_regime"]
            date_regime[ds] = {
                "scan_regime": sr,
                "bt_regime":   br,
                "regime_match": sr == br,
                "n_symbols":   len(day_results),
                "n_matched":   sum(1 for r in day_results if r["match"]),
            }

    return {
        "summary": {
            "total_comparisons":        total,
            "consistency_score_pct":    round(matched / total * 100, 1),
            "full_matches":             matched,
            "regime_agreement_pct":     round(regime_agreed / total * 100, 1),
            "signal_match_pct":         round(signal_matched / total * 100, 1),
            "entry_match_pct":          round(entry_matched / total * 100, 1),
            "sl_match_pct":             round(sl_matched / total * 100, 1),
            "tp_match_pct":             round(tp_matched / total * 100, 1),
            "n_mismatches":             len(mismatches),
            "n_regime_disagreements":   len(regime_disagree),
            "regime_disagree_mismatches": len(regime_disagree_mismatches),
        },
        "date_regime_summary": date_regime,
        "mismatches":          mismatches,
        "signal_mismatches":   signal_mismatches,
    }


# -- Entry point (also usable as pytest) -------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    print("=" * 64)
    print("Phase 2 - Live Scan vs Backtest Consistency Check")
    print("=" * 64)

    print(f"\nDownloading data: {DATE_FROM} to {DATE_TO} ...")
    print(f"Symbols: {N_SYMBOLS}  |  Dates: {N_DATES}  |  Stride: every {DATE_STRIDE} trading days")

    from egx_radar.backtest.data_loader import load_backtest_data
    all_data = load_backtest_data(DATE_FROM, DATE_TO)
    print(f"Loaded {len(all_data)} tickers.\n")

    # Pick available trading dates from proxy or any liquid symbol
    proxy_key = K.EGX30_SYMBOL
    ref_key   = proxy_key if proxy_key in all_data else list(all_data.keys())[0]
    ref_dates = sorted(all_data[ref_key].index.tolist())

    # Pick test dates from TEST_FROM onward (data goes back to DATE_FROM for indicator warmup)
    ref_dates = sorted(all_data[ref_key].index.tolist())
    test_cutoff   = pd.Timestamp(TEST_FROM)
    eligible      = [d for d in ref_dates if d >= test_cutoff]
    if len(eligible) < N_DATES:
        print(f"WARNING: only {len(eligible)} eligible test dates from {TEST_FROM}, using all")
        test_dates = eligible
    else:
        step       = max(1, len(eligible) // N_DATES)
        test_dates = eligible[::step][:N_DATES]

    print(f"Test dates ({len(test_dates)}):")
    for d in test_dates:
        print(f"  {d.strftime('%Y-%m-%d')}")

    # Symbols subset
    test_symbols = [s for s in TEST_SYMBOLS if SYMBOLS.get(s) in all_data][:N_SYMBOLS]
    print(f"\nTest symbols ({len(test_symbols)}): {test_symbols}\n")

    # Run
    report = run_consistency_test(all_data, test_symbols, test_dates)

    if "error" in report:
        print(f"ERROR: {report['error']}")
        return

    s = report["summary"]
    print("-" * 64)
    print("RESULTS")
    print("-" * 64)
    print(f"  Total comparisons     : {s['total_comparisons']}")
    print(f"  Consistency Score     : {s['consistency_score_pct']}%   << overall match rate")
    print(f"  Regime agreement      : {s['regime_agreement_pct']}%   (scan breadth vs bt proxy)")
    print(f"  Signal match          : {s['signal_match_pct']}%")
    print(f"  Entry match           : {s['entry_match_pct']}%")
    print(f"  SL match              : {s['sl_match_pct']}%")
    print(f"  TP match              : {s['tp_match_pct']}%")
    print(f"  Full mismatches       : {s['n_mismatches']}")
    print(f"  Regime disagreements  : {s['n_regime_disagreements']}")
    print(f"  Regime-caused mismatches: {s['regime_disagree_mismatches']}")

    print()
    print("Per-date regime summary:")
    print(f"  {'Date':12}  {'Scan':7}  {'BT':7}  {'Match':6}  Syms  OK")
    print(f"  {'-'*12}  {'-'*7}  {'-'*7}  {'-'*6}  {'-'*4}  {'-'*4}")
    for ds, info in sorted(report["date_regime_summary"].items()):
        marker = "OK" if info["regime_match"] else "!!"
        print(f"  {ds}  {info['scan_regime']:7}  {info['bt_regime']:7}  {marker}      "
              f"{info['n_symbols']:3}   {info['n_matched']:3}")

    if report["mismatches"]:
        print()
        print("-" * 64)
        print(f"MISMATCH DETAIL ({len(report['mismatches'])} mismatches)")
        print("-" * 64)
        for r in report["mismatches"][:30]:   # cap at 30 lines
            regime_flag = "" if r["regime_match"] else " [REGIME DIFFERS]"
            print(f"  {r['date']}  {r['sym']:8}  scan={r.get('scan_action','?'):11}  "
                  f"bt={r.get('bt_action','?'):11}  {regime_flag}")
            for field in ("signal_delta", "entry_delta", "sl_delta", "tp_delta"):
                if field in r:
                    print(f"              {field}: {r[field]}")
        if len(report["mismatches"]) > 30:
            print(f"  ... and {len(report['mismatches']) - 30} more")
    else:
        print("\nNo mismatches found. Live scan == Backtest for all tested (symbol, date) pairs.")

    # Root-cause summary if consistency < 90%
    if s["consistency_score_pct"] < 90.0:
        print()
        print("-" * 64)
        print("ROOT CAUSE ANALYSIS (consistency < 90%)")
        print("-" * 64)
        regime_mismatch_pct = round(s["n_regime_disagreements"] / s["total_comparisons"] * 100, 1)
        regime_caused_pct   = round(s["regime_disagree_mismatches"] / max(s["n_mismatches"], 1) * 100, 1)
        print(f"  Regime disagreement rate          : {regime_mismatch_pct}%")
        print(f"  % of mismatches caused by regime  : {regime_caused_pct}%")
        print()
        if regime_caused_pct > 80:
            print("  PRIMARY CAUSE: The two regime-detection methods disagree.")
            print("  SCAN uses: EMA50 breadth across all symbols")
            print("  BACKTEST uses: detect_market_regime on proxy index (COMI.CA/^EGX30)")
            print()
            print("  RESOLUTION OPTIONS:")
            print("  A) Unify: make scan also use the proxy index (simplest)")
            print("  B) Unify: make backtest also use breadth (requires all-symbol data in backtest)")
            print("  C) Accept: treat this as a known structural difference (measure, not fix)")
        else:
            print("  PRIMARY CAUSE: Signal computation differences (not regime)")
            sig_miss = [r for r in report["mismatches"] if not r["same_signal"] and r["regime_match"]]
            print(f"  Regime-agreed signal mismatches: {len(sig_miss)}")
            for r in sig_miss[:5]:
                print(f"    {r['date']} {r['sym']}: {r.get('signal_delta','?')}")

    print()
    print("=" * 64)
    print(f"Consistency Score: {s['consistency_score_pct']}%")
    print("=" * 64)


def test_consistency_minimum():
    """pytest entry point - runs a minimal consistency check."""
    import pytest
    logging.basicConfig(level=logging.WARNING)

    try:
        from egx_radar.backtest.data_loader import load_backtest_data
        all_data = load_backtest_data("2024-11-01", "2024-12-31")
    except Exception as e:
        pytest.skip(f"Data download failed: {e}")

    proxy_key = K.EGX30_SYMBOL
    ref_key   = proxy_key if proxy_key in all_data else list(all_data.keys())[0]
    ref_dates = sorted(all_data[ref_key].index.tolist())

    ref_dates = sorted(all_data[ref_key].index.tolist())
    step       = max(1, len(ref_dates) // 5)
    test_dates = ref_dates[::step][:5]    # 5 dates

    test_symbols  = [s for s in list(SYMBOLS.keys())[:10] if SYMBOLS.get(s) in all_data]

    report = run_consistency_test(all_data, test_symbols, test_dates)
    assert "summary" in report, f"No summary in report: {report}"

    score = report["summary"]["consistency_score_pct"]
    assert score >= 90.0, (
        f"Consistency score {score}% < 90% minimum.\n"
        f"Mismatches: {json.dumps(report['mismatches'][:5], indent=2)}"
    )


if __name__ == "__main__":
    main()
