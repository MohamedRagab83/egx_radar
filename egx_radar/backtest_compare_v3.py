"""
EGX Radar v0.8.3 — Backtest Comparison v3 (Fixed)
===================================================
Fixes applied in this run:
  Problem 1 — Sharpe: uses sharpe_from_trades() (no sqrt(252) annualisation on trade returns)
  Problem 2 — DEGRADED: engine_with_guards.py now has corrected DEGRADED logic
  Problem 3 — AlphaMonitor: debug prints to confirm evaluate_from_trades() receives data

Symbols : ESRS, HELI, DSCW, PHDC, FWRY, HRHO, ISPH, AMOC, COMI, CNFN
Period  : 2025-09-01 → 2026-03-01
Output  : C:\\tmp\\backtest_results_v3.txt
"""
from __future__ import annotations

import os
import sys
import time
import logging
from datetime import datetime

# Force UTF-8 stdout on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── suppress noisy library logs ──────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
for noisy in ("egx_radar.backtest.engine", "egx_radar.backtest.engine_with_guards",
              "egx_radar.core", "egx_radar.state", "egx_radar.data"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ── add project root to path ──────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, os.path.dirname(PROJECT_ROOT))

# ── imports ───────────────────────────────────────────────────────────────────
from egx_radar.backtest.engine            import run_backtest as run_no_guards
from egx_radar.backtest.engine_with_guards import run_backtest as run_with_guards
from egx_radar.backtest.metrics           import compute_metrics, sharpe_from_trades

DATE_FROM = "2025-09-01"
DATE_TO   = "2026-03-01"
MAX_BARS  = 10
MAX_CONCURRENT = 5

OUTPUT_FILE = r"C:\tmp\backtest_results_v3.txt"

# ── helpers ───────────────────────────────────────────────────────────────────
def progress(msg: str) -> None:
    print(f"  {msg}", flush=True)


def fmt_banner(title: str) -> str:
    line = "=" * 60
    return f"\n{line}\n  {title}\n{line}"


def fmt_metrics(m: dict, sharpe_corrected: float) -> str:
    ov = m.get("overall", {})
    lines = [
        f"  Total Trades        : {ov.get('total_trades', 0)}",
        f"  Win Rate            : {ov.get('win_rate_pct', 0.0):.1f}%",
        f"  Total Return        : {ov.get('total_return_pct', 0.0):.2f}%",
        f"  Max Drawdown        : {ov.get('max_drawdown_pct', 0.0):.2f}%",
        f"  Profit Factor       : {ov.get('profit_factor', 0.0):.2f}",
        f"  Avg R:R             : {ov.get('avg_rr', 0.0):.2f}",
        f"  Avg Bars in Trade   : {ov.get('avg_bars_in_trade', 0.0):.1f}",
        f"  Largest Win         : {ov.get('largest_win_pct', 0.0):.2f}%",
        f"  Largest Loss        : {ov.get('largest_loss_pct', 0.0):.2f}%",
        "",
        f"  [OLD Sharpe (live formula)] : {ov.get('sharpe_ratio', 0.0):.4f}  ← uses sqrt(252), INFLATED",
        f"  [CORRECTED Sharpe (trade)] : {sharpe_corrected:.4f}              ← no annualisation",
    ]
    return "\n".join(lines)


def fmt_guard_stats(gs: dict) -> str:
    lines = [f"  {k:<35}: {v}" for k, v in gs.items()]
    return "\n".join(lines)


def alpha_monitor_summary(trades: list, gs: dict) -> str:
    l1 = gs.get("AlphaMonitor L1", 0)
    l2 = gs.get("AlphaMonitor L2", 0)
    l3 = gs.get("AlphaMonitor L3 (pause)", 0)
    total_days_warned = l1 + l2 + l3
    lines = [
        f"  AlphaMonitor L1 days (warn)  : {l1}",
        f"  AlphaMonitor L2 days (reduce): {l2}",
        f"  AlphaMonitor L3 days (pause) : {l3}",
        f"  Total days with warning      : {total_days_warned}",
    ]
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    lines: list[str] = []
    def out(s: str = "") -> None:
        print(s, flush=True)
        lines.append(s)

    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out(fmt_banner(f"EGX Radar v0.8.3 — Backtest Comparison v3 — {run_ts}"))
    out(f"  Date range : {DATE_FROM} → {DATE_TO}")
    out(f"  Max bars   : {MAX_BARS}")
    out(f"  Max slots  : {MAX_CONCURRENT}")
    out()

    # ── Backtest A — No Guards ────────────────────────────────────────────────
    out(fmt_banner("BACKTEST A — No Guards (baseline)"))
    print("\n[Running Backtest A — No Guards]...", flush=True)
    t0 = time.time()
    result_a = run_no_guards(
        DATE_FROM, DATE_TO, MAX_BARS, MAX_CONCURRENT,
        progress_callback=progress,
    )
    elapsed_a = time.time() - t0

    # engine.py returns 3-tuple (trades, equity_curve, params)
    if len(result_a) == 3:
        trades_a, equity_a, params_a = result_a
        guard_stats_a: dict = {}
    else:
        trades_a, equity_a, params_a, guard_stats_a = result_a

    metrics_a = compute_metrics(trades_a)
    returns_a = [t["pnl_pct"] for t in trades_a]
    sharpe_a_corrected = sharpe_from_trades(returns_a)

    out(f"\n  Completed in {elapsed_a:.1f}s  |  {len(trades_a)} closed trades")
    out(fmt_metrics(metrics_a, sharpe_a_corrected))

    # ── Backtest B — With Guards ──────────────────────────────────────────────
    out()
    out(fmt_banner("BACKTEST B — With Guards (DataGuard + MomentumGuard + AlphaMonitor)"))
    print("\n[Running Backtest B — With Guards]...", flush=True)
    t1 = time.time()
    trades_b, equity_b, params_b, guard_stats_b = run_with_guards(
        DATE_FROM, DATE_TO, MAX_BARS, MAX_CONCURRENT,
        progress_callback=progress,
    )
    elapsed_b = time.time() - t1

    metrics_b = compute_metrics(trades_b)
    returns_b = [t["pnl_pct"] for t in trades_b]
    sharpe_b_corrected = sharpe_from_trades(returns_b)

    out(f"\n  Completed in {elapsed_b:.1f}s  |  {len(trades_b)} closed trades")
    out(fmt_metrics(metrics_b, sharpe_b_corrected))

    out()
    out("  --- Guard Statistics ---")
    out(fmt_guard_stats(guard_stats_b))

    out()
    out("  --- AlphaMonitor Activity ---")
    out(alpha_monitor_summary(trades_b, guard_stats_b))

    # ── Delta Comparison ─────────────────────────────────────────────────────
    out()
    out(fmt_banner("DELTA: B vs A (positive = guards improved, negative = guards hurt)"))

    ov_a = metrics_a.get("overall", {})
    ov_b = metrics_b.get("overall", {})

    delta_trades = len(trades_b) - len(trades_a)
    delta_wr     = ov_b.get("win_rate_pct", 0) - ov_a.get("win_rate_pct", 0)
    delta_ret    = ov_b.get("total_return_pct", 0) - ov_a.get("total_return_pct", 0)
    delta_dd     = ov_b.get("max_drawdown_pct", 0) - ov_a.get("max_drawdown_pct", 0)
    delta_pf     = ov_b.get("profit_factor", 0) - ov_a.get("profit_factor", 0)
    delta_sharpe = sharpe_b_corrected - sharpe_a_corrected

    out(f"  Trades (B-A)        : {delta_trades:+d}   {'⚠ guards ADDED trades' if delta_trades > 0 else '✓ guards REDUCED trades' if delta_trades < 0 else '→ same trade count'}")
    out(f"  Win Rate (B-A)      : {delta_wr:+.1f}%")
    out(f"  Total Return (B-A)  : {delta_ret:+.2f}%")
    out(f"  Max Drawdown (B-A)  : {delta_dd:+.2f}%  {'✓ better' if delta_dd < 0 else '⚠ worse'}")
    out(f"  Profit Factor (B-A) : {delta_pf:+.2f}")
    out(f"  Corrected Sharpe(B-A): {delta_sharpe:+.4f}")

    # ── Validation Checks ─────────────────────────────────────────────────────
    out()
    out(fmt_banner("VALIDATION CHECKS"))

    def check(label: str, condition: bool, pass_msg: str, fail_msg: str) -> None:
        icon = "✓ PASS" if condition else "✗ FAIL"
        msg  = pass_msg if condition else fail_msg
        out(f"  [{icon}] {label}")
        out(f"          {msg}")

    check(
        "Sharpe A in realistic range (0.3 – 2.5)",
        0.3 <= sharpe_a_corrected <= 2.5,
        f"Sharpe A = {sharpe_a_corrected:.4f}  ✓ realistic",
        f"Sharpe A = {sharpe_a_corrected:.4f}  still outside expected range (prev bug may persist)",
    )
    check(
        "Trades B ≤ Trades A (guards filter, not add)",
        len(trades_b) <= len(trades_a),
        f"B={len(trades_b)} ≤ A={len(trades_a)}  ✓ DEGRADED fix working",
        f"B={len(trades_b)} > A={len(trades_a)}  ✗ DEGRADED still adding trades",
    )
    am_days = guard_stats_b.get("AlphaMonitor L1", 0) + guard_stats_b.get("AlphaMonitor L2", 0) + guard_stats_b.get("AlphaMonitor L3 (pause)", 0)
    check(
        "AlphaMonitor shows at least some warnings",
        am_days > 0,
        f"{am_days} days triggered warnings  ✓ feed loop working",
        f"0 warning days — evaluate_from_trades() received no data OR AM_MIN_TRADES not reached",
    )

    # ── AlphaMonitor root cause note ─────────────────────────────────────────
    out()
    out("  --- AlphaMonitor Diagnosis ---")
    from egx_radar.config.settings import K
    out(f"  K.AM_MIN_TRADES = {K.AM_MIN_TRADES}  (AlphaMonitor only fires after this many closed trades)")
    if am_days == 0 and len(trades_b) >= K.AM_MIN_TRADES:
        out("  ⚠  Enough trades were closed but 0 warnings fired.")
        out("     Check evaluate_from_trades() thresholds or trade outcome format.")
    elif am_days == 0:
        out(f"  → Only {len(trades_b)} closed trades during period.")
        out(f"     AlphaMonitor needs {K.AM_MIN_TRADES} to start evaluating.")
        out("     Timing note: evaluate_from_trades() is called at the START of each day,")
        out("     with the PREVIOUS day's closed trades. On first K.AM_MIN_TRADES days it")
        out("     will always return level=0. This is expected behaviour.")

    out()
    out(fmt_banner("END OF REPORT"))
    out()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n✓ Results written to: {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    main()
