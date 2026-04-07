"""Run BEFORE/AFTER comparison backtest for high-probability optimization."""
import sys, os, json, csv, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.tracking_dashboard import build_tracking_dashboard

DATE_FROM = "2020-01-01"
DATE_TO   = "2026-02-28"

def run_and_report(label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Settings:")
    print(f"    BT_MIN_SMARTRANK     = {K.BT_MIN_SMARTRANK}")
    print(f"    RISK_PER_TRADE       = {K.RISK_PER_TRADE}")
    print(f"    MAX_OPEN_TRADES      = {K.PORTFOLIO_MAX_OPEN_TRADES}")
    print(f"    MIN_TURNOVER_EGP     = {K.MIN_TURNOVER_EGP}")
    print(f"    PARTIAL_TP_PCT       = {K.PARTIAL_TP_PCT}")
    print(f"    TRAILING_TRIGGER_PCT = {K.TRAILING_TRIGGER_PCT}")
    print(f"    MAX_STOP_LOSS_PCT    = {K.MAX_STOP_LOSS_PCT}")
    print(f"    BT_DAILY_TOP_N       = {K.BT_DAILY_TOP_N}")
    print(f"    BT_MIN_ACTION        = {K.BT_MIN_ACTION}")

    t0 = time.time()
    trades, equity_curve, params, diag = run_backtest(DATE_FROM, DATE_TO)
    elapsed = time.time() - t0
    print(f"\n  Backtest completed in {elapsed:.1f}s")
    print(f"  Trades: {len(trades)}")

    if not trades:
        print("  No trades generated.")
        return {}, []

    # Build dashboard
    dash = build_tracking_dashboard(trades, title=label)

    # Core metrics
    cm = dash["core_metrics"]
    print(f"\n  --- Core Metrics ---")
    print(f"  Win Rate:       {cm['win_rate']:.1f}%")
    print(f"  Avg Return:     {cm['avg_return']:.2f}%")
    print(f"  Total Return:   {cm['total_return']:.2f}%")
    print(f"  Max Drawdown:   {cm['max_drawdown']:.2f}%")
    print(f"  Profit Factor:  {cm['profit_factor']:.2f}")
    print(f"  Expectancy:     {cm['expectancy']:.2f}%")
    print(f"  Sharpe Ratio:   {cm['sharpe_ratio']:.2f}")

    # Risk
    risk = dash["risk"]
    print(f"\n  --- Risk ---")
    print(f"  Max Single Loss: {risk['max_single_loss']:.2f}%")
    print(f"  Worst Streak:    {risk['worst_losing_streak']['length']} trades ({risk['worst_losing_streak']['total_pnl']:.2f}%)")

    # Health & Verdict
    print(f"\n  Health Score: {dash['health_score']:.1f}/100")
    v = dash["verdict"]
    print(f"  Verdict: {'READY' if v['ready'] else 'NOT READY'}")
    for r in v.get("reasons", []):
        print(f"    - {r}")

    # Trade quality breakdown
    wins = [t for t in trades if t.get("outcome") == "WIN"]
    losses = [t for t in trades if t.get("outcome") == "LOSS"]
    exits = [t for t in trades if t.get("outcome") == "EXIT"]
    print(f"\n  --- Trade Quality ---")
    print(f"  WIN:  {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
    print(f"  LOSS: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")
    print(f"  EXIT: {len(exits)} ({len(exits)/len(trades)*100:.1f}%)")

    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    print(f"  Avg Win:  +{avg_win:.2f}%")
    print(f"  Avg Loss: {avg_loss:.2f}%")

    # SmartRank distribution
    sranks = [t.get("smart_rank", 0) for t in trades]
    print(f"\n  --- SmartRank Distribution ---")
    print(f"  Min: {min(sranks):.1f}  Max: {max(sranks):.1f}  Avg: {sum(sranks)/len(sranks):.1f}")

    return dash, trades


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "before"

    if mode == "before":
        print("Running BEFORE (baseline) backtest...")
        dash, trades = run_and_report("BEFORE (Baseline)")
        # Save results
        with open("_baseline_results.json", "w") as f:
            json.dump({
                "trades": len(trades),
                "win_rate": dash.get("core_metrics", {}).get("win_rate", 0),
                "max_drawdown": dash.get("core_metrics", {}).get("max_drawdown", 0),
                "total_return": dash.get("core_metrics", {}).get("total_return", 0),
                "profit_factor": dash.get("core_metrics", {}).get("profit_factor", 0),
                "sharpe": dash.get("core_metrics", {}).get("sharpe_ratio", 0),
                "health": dash.get("health_score", 0),
            }, f, indent=2)
        print("\nBaseline saved to _baseline_results.json")

    elif mode == "after":
        print("Running AFTER (optimized) backtest...")
        dash, trades = run_and_report("AFTER (High-Probability)")
        with open("_optimized_results.json", "w") as f:
            json.dump({
                "trades": len(trades),
                "win_rate": dash.get("core_metrics", {}).get("win_rate", 0),
                "max_drawdown": dash.get("core_metrics", {}).get("max_drawdown", 0),
                "total_return": dash.get("core_metrics", {}).get("total_return", 0),
                "profit_factor": dash.get("core_metrics", {}).get("profit_factor", 0),
                "sharpe": dash.get("core_metrics", {}).get("sharpe_ratio", 0),
                "health": dash.get("health_score", 0),
            }, f, indent=2)
        print("\nOptimized saved to _optimized_results.json")

    elif mode == "compare":
        if not os.path.exists("_baseline_results.json") or not os.path.exists("_optimized_results.json"):
            print("ERROR: Run 'before' and 'after' first")
            sys.exit(1)
        with open("_baseline_results.json") as f:
            before = json.load(f)
        with open("_optimized_results.json") as f:
            after = json.load(f)

        print("\n" + "="*60)
        print("  BEFORE vs AFTER COMPARISON")
        print("="*60)
        print(f"{'Metric':<20} {'BEFORE':>12} {'AFTER':>12} {'Change':>12}")
        print("-"*60)
        for key, label in [
            ("trades", "Trades"),
            ("win_rate", "Win Rate %"),
            ("max_drawdown", "Max DD %"),
            ("total_return", "Total Return %"),
            ("profit_factor", "Profit Factor"),
            ("sharpe", "Sharpe Ratio"),
            ("health", "Health Score"),
        ]:
            b = before.get(key, 0)
            a = after.get(key, 0)
            if isinstance(b, float):
                delta = a - b
                sign = "+" if delta > 0 else ""
                print(f"{label:<20} {b:>12.2f} {a:>12.2f} {sign}{delta:>11.2f}")
            else:
                delta = a - b
                sign = "+" if delta > 0 else ""
                print(f"{label:<20} {b:>12} {a:>12} {sign}{delta:>11}")

        print("\n" + "="*60)
        wr_ok = after["win_rate"] >= 60
        dd_ok = after["max_drawdown"] < 5
        print(f"  Win Rate >= 60%:   {'YES' if wr_ok else 'NO'} ({after['win_rate']:.1f}%)")
        print(f"  Drawdown < 5%:     {'YES' if dd_ok else 'NO'} ({after['max_drawdown']:.2f}%)")
        if wr_ok and dd_ok:
            print(f"\n  VERDICT: SYSTEM IS READY")
        else:
            print(f"\n  VERDICT: NEEDS MORE WORK")
        print("="*60)
