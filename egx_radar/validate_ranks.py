"""Ranking Power Validation — validate which ranking system best predicts PnL.

Usage:
    python validate_ranks.py
    python validate_ranks.py 2024-01-01 2025-06-30
    python validate_ranks.py --from-json backtest_results.json

Runs a full backtest then measures predictive power of:
    1. smart_rank        (production accumulation system)
    2. multi_factor_rank (experimental: trend + momentum + volume + volatility)
    3. final_rank        (hybrid shadow: 60% SR + 40% MFR)

Output:
    - Formatted report to console
    - rank_validation_results.json for deeper analysis
"""

from __future__ import annotations

import sys

# Ensure UTF-8 output on all platforms (required for Windows cmd/powershell)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Parse arguments ──────────────────────────────────────────────────────

date_from = "2024-01-01"
date_to   = "2025-12-31"
from_json: str | None = None

args = sys.argv[1:]
if "--from-json" in args:
    idx = args.index("--from-json")
    from_json = args[idx + 1] if idx + 1 < len(args) else "backtest_results.json"
elif len(args) >= 2:
    date_from = args[0]
    date_to   = args[1]
elif len(args) == 1:
    # Single argument: reuse existing JSON
    if args[0].endswith(".json"):
        from_json = args[0]
    else:
        print(f"Usage: python validate_ranks.py [date_from date_to] [--from-json file.json]")
        sys.exit(1)

# ── Load or run backtest ─────────────────────────────────────────────────

if from_json:
    if not os.path.exists(from_json):
        print(f"[!] JSON file not found: {from_json}")
        sys.exit(1)
    print(f"[validate_ranks] Loading trades from {from_json}...")
    with open(from_json, encoding="utf-8") as f:
        saved = json.load(f)
    trades = saved.get("trades", [])
    print(f"[validate_ranks] Loaded {len(trades)} trades from JSON.")
else:
    print(f"[validate_ranks] Running backtest {date_from} to {date_to} ...")
    from egx_radar.backtest.engine import run_backtest
    from egx_radar.backtest.metrics import compute_metrics

    trades, equity_curve, params, extra = run_backtest(date_from, date_to)
    n_valid = len([t for t in trades if math.isfinite(t.get("pnl_pct", float("nan")))])
    print(f"[validate_ranks] Backtest complete. Trades: {len(trades)} | Closed with PnL: {n_valid}")

    if trades:
        metrics = compute_metrics(trades)
        ov = metrics.get("overall", {})
        print(f"[validate_ranks] WR: {ov.get('win_rate_pct')}%  "
              f"Sharpe: {ov.get('sharpe_ratio')}  "
              f"DD: {ov.get('max_drawdown_pct')}%")

# ── Run Rank Validation ──────────────────────────────────────────────────

from egx_radar.backtest.rank_validator import run_rank_validation, format_report

if not trades:
    print("[validate_ranks] No trades to validate. Exiting.")
    sys.exit(0)

print(f"\n[validate_ranks] Analysing ranking power across {len(trades)} trades...\n")
result = run_rank_validation(trades)

# ── Print Report ─────────────────────────────────────────────────────────

print(format_report(result))

# ── Save detailed JSON ───────────────────────────────────────────────────

output_path = "rank_validation_results.json"
try:
    def _safe_serialise(obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        raise TypeError(f"Not serialisable: {type(obj)}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=_safe_serialise)
    print(f"\n[validate_ranks] Detailed results saved to: {output_path}")
except Exception as e:
    print(f"[validate_ranks] Could not save JSON: {e}")
