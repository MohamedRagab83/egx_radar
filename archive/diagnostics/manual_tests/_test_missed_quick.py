"""Quick test: Missed Trade Intelligence System (short date range)."""
import sys, os
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.missed_trades import run_missed_trade_analysis

print(f"BT_MIN_SMARTRANK = {K.BT_MIN_SMARTRANK}")
print(f"BLACKLISTED_SECTORS_BT = {K.BLACKLISTED_SECTORS_BT}")
print()

# Short period — should complete in a few minutes
result = run_backtest(
    date_from="2024-10-01",
    date_to="2024-12-31",
    progress_callback=lambda msg: print(f"  {msg}", flush=True),
)

if len(result) == 4:
    trades, equity_curve, params, diagnostics = result
elif len(result) == 3:
    trades, equity_curve, params = result
    diagnostics = {}
else:
    raise ValueError(f"Unexpected result length: {len(result)}")

print(f"\nClosed trades: {len(trades)}")
missed_entries = diagnostics.get("missed_entries", [])
print(f"Missed entries (all types): {len(missed_entries)}")

# Breakdown by reason
reasons = {}
for m in missed_entries:
    r = m.get("reason", "trigger_miss")
    reasons[r] = reasons.get(r, 0) + 1
print(f"Breakdown by reason: {reasons}")

# Count how many have simulation results
simulated = sum(1 for m in missed_entries if "approx_pnl_pct" in m)
print(f"Simulated (counterfactual): {simulated}")
unsimulated = len(missed_entries) - simulated
print(f"Not simulated (metadata only): {unsimulated}")

# --- Run the missed trade analysis ---
print("\n" + "="*60)
report = run_missed_trade_analysis(missed_entries=missed_entries, print_report=True)

print("\n=== DONE ===")
