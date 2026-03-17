"""Run a single backtest with current settings and export CSV."""
import sys, os, csv, json
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

MARKER = os.path.join(os.path.dirname(__file__), "bt_done_marker.json")

# Remove old marker
if os.path.exists(MARKER):
    os.remove(MARKER)

try:
    from egx_radar.config.settings import K
    from egx_radar.backtest.engine import run_backtest
    from egx_radar.backtest.metrics import compute_metrics
    from datetime import datetime

    print(f"BT_MIN_SMARTRANK = {K.BT_MIN_SMARTRANK}")

    trades, equity_curve, params = run_backtest(
        date_from="2020-01-01",
        date_to="2026-03-01",
        progress_callback=lambda msg: print(f"  {msg}", flush=True),
    )

    print(f"Trades: {len(trades)}")

    csv_name = ""
    if trades:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        csv_name = f"EGX_Radar_Backtest_{ts}.csv"
        cols = list(trades[0].keys())
        with open(csv_name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(trades)
        print(f"Exported: {csv_name}")

    m = compute_metrics(trades)
    overall = m if "total_trades" in m else m.get("overall", m)
    summary = {
        "status": "done",
        "csv": csv_name,
        "sr": K.BT_MIN_SMARTRANK,
        "total_trades": overall.get("total_trades", len(trades)),
        "win_rate_pct": overall.get("win_rate_pct", 0),
        "profit_factor": overall.get("profit_factor", 0),
        "max_drawdown_pct": overall.get("max_drawdown_pct", 0),
        "sharpe_ratio": overall.get("sharpe_ratio", 0),
        "total_return_pct": overall.get("total_return_pct", 0),
    }
    with open(MARKER, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n=== Summary (SR={K.BT_MIN_SMARTRANK}) ===")
    for k, v in summary.items():
        if k not in ("status", "csv", "sr"):
            print(f"  {k}: {v}")
    print("Done.")

except Exception as e:
    import traceback
    with open(MARKER, "w") as f:
        json.dump({"status": "error", "error": traceback.format_exc()}, f, indent=2)
    raise
