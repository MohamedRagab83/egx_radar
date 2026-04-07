"""Test the Missed Trade Intelligence System end-to-end."""
import sys, os, csv, json
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics
from egx_radar.backtest.missed_trades import run_missed_trade_analysis
from egx_radar.backtest.dashboard import build_performance_dashboard
from datetime import datetime

print(f"BT_MIN_SMARTRANK = {K.BT_MIN_SMARTRANK}")
print(f"BLACKLISTED_SECTORS_BT = {K.BLACKLISTED_SECTORS_BT}")
print()

result = run_backtest(
    date_from="2020-01-01",
    date_to="2026-03-01",
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

# --- Run the missed trade analysis ---
report = run_missed_trade_analysis(missed_entries=missed_entries, print_report=True)
analysis = report["analysis"]

# --- Export missed trades CSV ---
if missed_entries:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    csv_name = f"Missed_Trades_{ts}.csv"
    cols = list(missed_entries[0].keys())
    # Ensure all entries have the same keys
    all_keys = set()
    for m in missed_entries:
        all_keys.update(m.keys())
    cols = sorted(all_keys)
    with open(csv_name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(missed_entries)
    print(f"\nExported missed trades: {csv_name}")

# --- Export closed trades CSV ---
if trades:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    csv_name = f"EGX_Radar_Backtest_{ts}.csv"
    cols = list(trades[0].keys())
    with open(csv_name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(trades)
    print(f"Exported backtest: {csv_name}")

# --- Build dashboard (tests integration) ---
dashboard = build_performance_dashboard(trades, diagnostics)
print(f"\nDashboard missed_trade_analysis keys: {list(dashboard.get('missed_trade_analysis', {}).keys())}")
print(f"Dashboard has report: {bool(dashboard.get('missed_trade_report'))}")

# --- Summary ---
m = compute_metrics(trades)
overall = m.get("overall", m) if "overall" in m else m
print(f"\n=== BACKTEST SUMMARY ===")
print(f"  Total trades: {overall.get('total_trades', len(trades))}")
print(f"  Win rate: {overall.get('win_rate_pct', 0)}%")
print(f"  Profit factor: {overall.get('profit_factor', 0)}")
print(f"  Max DD: {overall.get('max_drawdown_pct', 0)}%")
print(f"  Total return: {overall.get('total_return_pct', 0)}%")

# Breakdown by rejection reason
print(f"\n=== MISSED BY REASON ===")
for reason, info in analysis.get("reason_breakdown", {}).items():
    print(f"  {reason}: {info['count']} trades, WR={info['win_rate_pct']}%, avg={info['avg_return_pct']}%")

print("\nDone.")
