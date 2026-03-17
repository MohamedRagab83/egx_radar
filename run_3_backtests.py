"""Run 3 backtests with different BT_MIN_SMARTRANK values and compare results."""
import csv
import json
import sys
import os
import traceback

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

PROGRESS_FILE = os.path.join(r"d:\egx radar seprated", "bt_progress.json")

def _save_progress(data):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, default=str)

progress = {"status": "starting", "runs_done": 0, "results": [], "error": None}
_save_progress(progress)

try:
    from egx_radar.config.settings import K
    from egx_radar.backtest.engine import run_backtest
    from egx_radar.backtest.metrics import compute_metrics

    RUNS = [
        (r"d:\egx radar seprated\backtest_SR0.csv",  0.0),
        (r"d:\egx radar seprated\backtest_SR20.csv", 20.0),
        (r"d:\egx radar seprated\backtest_SR24.csv", 24.0),
    ]

    results_table = []

    for idx, (csv_name, sr_val) in enumerate(RUNS):
        K.BT_MIN_SMARTRANK = sr_val
        progress["status"] = f"running SR={sr_val} ({idx+1}/3)"
        _save_progress(progress)
        print(f"\nRUN: BT_MIN_SMARTRANK = {sr_val}", flush=True)

        trades, equity_curve, params = run_backtest(
            date_from="2020-01-01",
            date_to="2026-03-01",
            progress_callback=lambda msg: print(f"  {msg}", flush=True),
        )
        print(f"  Trades returned: {len(trades)}", flush=True)

        if trades:
            cols = list(trades[0].keys())
            with open(csv_name, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(trades)

        m = compute_metrics(trades)
        overall = m if "total_trades" in m else m.get("overall", m)
        row = {
            "sr": sr_val,
            "trades": overall.get("total_trades", len(trades)),
            "wr": overall.get("win_rate_pct", 0.0),
            "pf": overall.get("profit_factor", 0.0),
            "dd": overall.get("max_drawdown_pct", 0.0),
            "sharpe": overall.get("sharpe_ratio", 0.0),
            "total_ret": overall.get("total_return_pct", 0.0),
        }
        results_table.append(row)
        progress["runs_done"] = idx + 1
        progress["results"].append(row)
        _save_progress(progress)

    K.BT_MIN_SMARTRANK = 20.0
    progress["status"] = "done"
    _save_progress(progress)

except Exception as e:
    progress["status"] = "error"
    progress["error"] = traceback.format_exc()
    _save_progress(progress)
    raise

# Print comparison table
print(f"\n{'='*80}")
print("COMPARISON TABLE")
print(f"{'='*80}")
print(f"| {'Run':>3} | {'BT_MIN_SMARTRANK':>16} | {'Trades':>6} | {'Win Rate':>8} | {'PF':>6} | {'Max DD':>8} | {'Sharpe':>6} | {'Total Ret':>10} |")
print(f"|{'---':->5}|{'---':->18}|{'---':->8}|{'---':->10}|{'---':->8}|{'---':->10}|{'---':->8}|{'---':->12}|")
for i, r in enumerate(results_table, 1):
    print(f"| {i:>3} | {r['sr']:>16.1f} | {r['trades']:>6} | {r['wr']:>7.1f}% | {r['pf']:>6.2f} | {r['dd']:>7.2f}% | {r['sharpe']:>6.2f} | {r['total_ret']:>9.2f}% |")
print()
