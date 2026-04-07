"""Debug: Backtest 2020-Q2 (known to have trades) to test missed trade system."""
import sys, os
sys.stdout.reconfigure(line_buffering=True, encoding='utf-8', errors='replace')
sys.stderr.reconfigure(line_buffering=True, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from egx_radar.config.settings import K

# Use SR=38 to get some trades but also some rejects
K.BT_MIN_SMARTRANK = 38.0
print(f"BT_MIN_SMARTRANK = {K.BT_MIN_SMARTRANK}")

from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.missed_trades import run_missed_trade_analysis

# 2-year range to give indicators enough warmup (SMA200 etc.)
result = run_backtest('2020-01-01', '2021-12-31',
                      progress_callback=lambda msg: print(f"  {msg}", flush=True))

if len(result) == 4:
    trades, eq, params, diag = result
elif len(result) == 3:
    trades, eq, params = result
    diag = {}

print(f"\nTrades: {len(trades)}")
missed = diag.get('missed_entries', [])
print(f"Missed entries: {len(missed)}")

reasons = {}
for m in missed:
    r = m.get("reason", "trigger_miss")
    reasons[r] = reasons.get(r, 0) + 1
print(f"Breakdown: {reasons}")

simulated = sum(1 for m in missed if "approx_pnl_pct" in m)
print(f"Simulated: {simulated}, Metadata-only: {len(missed) - simulated}")

# Show sample entries
for i, m in enumerate(missed[:5]):
    print(f"\n  Missed #{i+1}: sym={m.get('sym')}, reason={m.get('reason')}, score={m.get('score')}, "
          f"approx_pnl={m.get('approx_pnl_pct', 'N/A')}")

if missed:
    print("\n" + "="*60)
    report = run_missed_trade_analysis(missed_entries=missed, print_report=True)
else:
    print("\nNo missed entries generated.")

print("\n=== DONE ===")
