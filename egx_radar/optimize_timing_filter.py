"""
Grid search optimization for Entry Timing Filter thresholds.
Tests 27 combinations and finds the best configuration.

Usage:  python optimize_timing_filter.py
"""
import sys
import os
import logging
import itertools
import json
import warnings

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(name)s: %(message)s")

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics

# ── Grid definition ──────────────────────────────────────────────────────
GAIN_3D_VALUES     = [6.0, 8.0, 10.0]
EMA200_VALUES      = [8.0, 10.0, 12.0]
MINOR_BREAK_VALUES = [2.0, 2.5, 3.0]

DATE_FROM = "2024-01-01"
DATE_TO   = "2025-12-31"

# ── Run grid search ─────────────────────────────────────────────────────
combos = list(itertools.product(GAIN_3D_VALUES, EMA200_VALUES, MINOR_BREAK_VALUES))
total = len(combos)
results = []

print(f"\n{'='*72}")
print(f"  Entry Timing Filter — Grid Search Optimization")
print(f"  {total} combinations | {DATE_FROM} to {DATE_TO}")
print(f"{'='*72}\n")

# Save original thresholds
orig_3d    = K.ETF_GAIN_3D_THRESHOLD
orig_ema   = K.ETF_EMA200_THRESHOLD
orig_break = K.ETF_MINOR_BREAK_THRESHOLD

for i, (g3d, ema, mb) in enumerate(combos, 1):
    # Override thresholds for this run
    K.ETF_GAIN_3D_THRESHOLD     = g3d
    K.ETF_EMA200_THRESHOLD      = ema
    K.ETF_MINOR_BREAK_THRESHOLD = mb

    label = f"3d={g3d:.0f} ema200={ema:.0f} break={mb:.1f}"
    print(f"  [{i:2d}/{total}] {label} ...", end="", flush=True)

    try:
        trades, _, _, _ = run_backtest(
            date_from=DATE_FROM,
            date_to=DATE_TO,
            progress_callback=None,
        )
        n = len(trades)
        if n >= 2:
            m = compute_metrics(trades)["overall"]
            wr   = m["win_rate_pct"]
            avg  = m["avg_return_pct"]
            pf   = m["profit_factor"]
            sr   = m["sharpe_ratio"]
            dd   = m["max_drawdown_pct"]
            tot  = m["total_return_pct"]
        else:
            wr = avg = pf = sr = dd = tot = 0.0

        results.append({
            "gain_3d": g3d,
            "ema200": ema,
            "minor_break": mb,
            "trades": n,
            "win_rate": round(wr, 1),
            "avg_pnl": round(avg, 2),
            "profit_factor": round(pf, 2),
            "sharpe": round(sr, 2),
            "max_dd": round(dd, 2),
            "total_return": round(tot, 2),
        })
        print(f"  {n:>3d} trades | WR={wr:5.1f}% | PF={pf:5.2f} | avg={avg:+6.2f}%")

    except Exception as exc:
        print(f"  ERROR: {exc}")
        results.append({
            "gain_3d": g3d, "ema200": ema, "minor_break": mb,
            "trades": 0, "win_rate": 0, "avg_pnl": 0,
            "profit_factor": 0, "sharpe": 0, "max_dd": 0, "total_return": 0,
        })

# Restore original thresholds
K.ETF_GAIN_3D_THRESHOLD     = orig_3d
K.ETF_EMA200_THRESHOLD      = orig_ema
K.ETF_MINOR_BREAK_THRESHOLD = orig_break

# ── Results table ────────────────────────────────────────────────────────
print(f"\n{'='*72}")
print(f"  FULL RESULTS TABLE")
print(f"{'='*72}\n")

header = f"  {'3d':>4s} {'ema':>4s} {'brk':>4s} | {'Trd':>4s} {'WR%':>6s} {'AvgPnL':>7s} {'PF':>5s} {'Sharpe':>7s} {'DD%':>6s} {'TotRet':>7s}"
print(header)
print(f"  {'-'*4} {'-'*4} {'-'*4}-+-{'-'*4}-{'-'*6}-{'-'*7}-{'-'*5}-{'-'*7}-{'-'*6}-{'-'*7}")

for r in results:
    print(f"  {r['gain_3d']:4.0f} {r['ema200']:4.0f} {r['minor_break']:4.1f}"
          f" | {r['trades']:4d} {r['win_rate']:6.1f} {r['avg_pnl']:+7.2f} {r['profit_factor']:5.2f}"
          f" {r['sharpe']:7.2f} {r['max_dd']:6.2f} {r['total_return']:+7.2f}")

# ── Find best configuration ─────────────────────────────────────────────
# Filter: must have > 12 trades (avoid over-filtering)
viable = [r for r in results if r["trades"] > 12]

if not viable:
    print("\n  WARNING: No configuration has > 12 trades. Relaxing to > 8.")
    viable = [r for r in results if r["trades"] > 8]

if viable:
    # Primary sort: profit factor (desc), tiebreak: win rate (desc), then trades (desc)
    best = max(viable, key=lambda r: (r["profit_factor"], r["win_rate"], r["trades"]))

    # Also find most aggressive (highest PF regardless of trade count)
    best_aggressive = max(results, key=lambda r: (r["profit_factor"], r["win_rate"]))

    # Also find most balanced (reasonable trades + good PF)
    balanced = [r for r in results if r["trades"] >= 15]
    best_balanced = max(balanced, key=lambda r: (r["profit_factor"], r["win_rate"])) if balanced else best

    print(f"\n{'='*72}")
    print(f"  OPTIMAL CONFIGURATIONS")
    print(f"{'='*72}\n")

    def show_config(label, cfg):
        print(f"  {label}:")
        print(f"    Thresholds:  gain_3d={cfg['gain_3d']:.0f}%  ema200={cfg['ema200']:.0f}%  minor_break={cfg['minor_break']:.1f}%")
        print(f"    Trades: {cfg['trades']}  |  WR: {cfg['win_rate']}%  |  PF: {cfg['profit_factor']}  |  Avg: {cfg['avg_pnl']:+.2f}%  |  Sharpe: {cfg['sharpe']}")
        print()

    show_config("BEST (PF-maximized, >12 trades)", best)
    show_config("AGGRESSIVE (highest PF, any count)", best_aggressive)
    show_config("BALANCED (>= 15 trades, best PF)", best_balanced)

    print(f"  RECOMMENDATION:")
    if best["profit_factor"] > 1.3 and best["win_rate"] >= 60:
        print(f"    Use BEST config: 3d={best['gain_3d']:.0f}  ema200={best['ema200']:.0f}  break={best['minor_break']:.1f}")
        print(f"    Strong edge with reasonable trade count.")
    elif best_balanced["profit_factor"] > 1.2:
        print(f"    Use BALANCED config: 3d={best_balanced['gain_3d']:.0f}  ema200={best_balanced['ema200']:.0f}  break={best_balanced['minor_break']:.1f}")
        print(f"    Moderate edge with higher sample size.")
    else:
        print(f"    Current defaults (3d=8, ema200=10, break=2.5) remain adequate.")
        print(f"    No clear improvement found in the grid.")

else:
    print("\n  No viable configurations found. All combinations produced too few trades.")

# ── Save results ─────────────────────────────────────────────────────────
output = {
    "grid": results,
    "best": best if viable else None,
    "best_aggressive": best_aggressive if viable else None,
    "best_balanced": best_balanced if viable else None,
}
with open("timing_grid_results.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Results saved to: timing_grid_results.json")
print(f"{'='*72}\n")
