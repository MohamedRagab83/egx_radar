"""Debug: Short backtest to check why 0 trades."""
import sys, os
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from egx_radar.config.settings import K
K.BT_MIN_SMARTRANK = 38.0
print(f"BT_MIN_SMARTRANK = {K.BT_MIN_SMARTRANK}")

from egx_radar.backtest.engine import run_backtest

result = run_backtest('2024-10-01', '2024-12-31',
                      progress_callback=lambda msg: print(f"  {msg}", flush=True))

if len(result) == 4:
    trades, eq, params, diag = result
elif len(result) == 3:
    trades, eq, params = result
    diag = {}

print(f"\nTrades: {len(trades)}")
if params:
    # Print params but skip 'history' which is huge
    for k, v in params.items():
        if k == 'history':
            continue
        print(f"  param.{k}: {v}")

if diag:
    print(f"\nDiagnostics keys: {list(diag.keys())}")
    missed = diag.get('missed_entries', [])
    print(f"  missed_entries count: {len(missed)}")
    guard_stats = diag.get('guard_stats', {})
    if guard_stats:
        print(f"  guard_stats: {guard_stats}")

# Show first few trades if any
for i, t in enumerate(trades[:3]):
    print(f"\nTrade #{i+1}: {t.get('sym','')} {t.get('signal_type','')} PnL={t.get('pnl_pct',0):.2f}%")

print("\n=== DEBUG DONE ===")
