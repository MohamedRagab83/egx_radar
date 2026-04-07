"""Run full backtest 2020-01-01 to 2026-03-17 and print raw metrics."""
import sys, os, math
sys.path.insert(0, os.path.abspath('.'))

from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics

print("Running backtest 2020-01-01 → 2026-03-17 ...")
print("(This may take a few minutes)\n")

trades, equity, params = run_backtest(
    "2020-01-01", "2026-03-17", max_bars=15
)

print(f"Trades completed: {len(trades)}")
print(f"Equity points:    {len(equity)}")
print(f"Params:           {params}")
print()

if len(trades) >= 1:
    m = compute_metrics(trades)
    overall = m.get("overall", m)
    print("═══════════════════════════════════════")
    print("         RAW BACKTEST METRICS          ")
    print("═══════════════════════════════════════")
    for k, v in overall.items():
        print(f"  {k:30s}: {v}")
    print("═══════════════════════════════════════")
else:
    print("NO TRADES — check settings")
