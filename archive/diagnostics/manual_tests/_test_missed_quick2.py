"""Quick test: Missed Trade Intelligence with wider date range and lower SR threshold."""
import sys, os
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.missed_trades import run_missed_trade_analysis

# Temporarily lower threshold to generate test data
original_sr = K.BT_MIN_SMARTRANK
K.BT_MIN_SMARTRANK = 38.0
print(f"BT_MIN_SMARTRANK = {K.BT_MIN_SMARTRANK} (test override)")
print()

# 1-year range for reasonable runtime
result = run_backtest(
    date_from="2024-01-01",
    date_to="2024-12-31",
    progress_callback=lambda msg: print(f"  {msg}", flush=True),
)

# Restore
K.BT_MIN_SMARTRANK = original_sr

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

# Breakdown
reasons = {}
for m in missed_entries:
    r = m.get("reason", "trigger_miss")
    reasons[r] = reasons.get(r, 0) + 1
print(f"Breakdown by reason: {reasons}")

simulated = sum(1 for m in missed_entries if "approx_pnl_pct" in m)
print(f"Simulated (counterfactual): {simulated}")
print(f"Not simulated (metadata only): {len(missed_entries) - simulated}")

# Show first 3 missed entries for debugging
for i, m in enumerate(missed_entries[:3]):
    print(f"\n  Sample missed #{i+1}: {m}")

# --- Run the missed trade analysis ---
print("\n" + "="*60)
report = run_missed_trade_analysis(missed_entries=missed_entries, print_report=True)

print("\n=== DONE ===")
