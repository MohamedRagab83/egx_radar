"""
Run EGX Radar full backtest and print detailed results.
Usage:  python run_backtest.py [date_from] [date_to]
Default: 2024-01-01 to 2025-12-31
"""
import sys
import logging
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

date_from = sys.argv[1] if len(sys.argv) > 1 else "2024-01-01"
date_to   = sys.argv[2] if len(sys.argv) > 2 else "2025-12-31"

print(f"\n{'='*60}")
print(f"  EGX Radar Backtest  {date_from}  to  {date_to}")
print(f"{'='*60}")
print("جاري تحميل البيانات (قد يستغرق بعض الوقت)...\n")

from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.dashboard import build_performance_dashboard, render_console_report
from egx_radar.backtest.metrics import compute_metrics

def progress(msg):
    print(f"  ⟳ {msg}")

trades, equity_curve, params, diagnostics = run_backtest(
    date_from=date_from,
    date_to=date_to,
    progress_callback=progress,
)

print(f"\n{'='*60}")
print(f"  انتهى الـ backtest — {len(trades)} صفقة مغلقة")
print(f"{'='*60}\n")

if not trades:
    print("⚠ لا توجد صفقات. تحقق من البيانات والرموز.")
    sys.exit(0)

metrics = compute_metrics(trades)
ov = metrics["overall"]

print("── الإحصائيات الرئيسية ──────────────────────────────────")
print(f"  إجمالي الصفقات:        {ov['total_trades']}")
print(f"  نسبة الربح (Win Rate): {ov['win_rate_pct']}%")
print(f"  متوسط العائد/صفقة:     {ov['avg_return_pct']:+.2f}%")
print(f"  العائد الكلي:          {ov['total_return_pct']:+.2f}%")
print(f"  أقصى تراجع (Max DD):   {ov['max_drawdown_pct']:.2f}%")
print(f"  Sharpe Ratio:          {ov['sharpe_ratio']:.2f}")
print(f"  Profit Factor:         {ov['profit_factor']:.2f}")
print(f"  متوسط مدة الصفقة:      {ov['avg_bars_in_trade']:.1f} يوم")
print(f"  أكبر ربح:              {ov['largest_win_pct']:+.2f}%")
print(f"  أكبر خسارة:            {ov['largest_loss_pct']:+.2f}%")
print()

# Win/Loss/Timeout breakdown
from collections import Counter
status_counts = Counter(t.get("status", "?") for t in trades)
print("── توزيع النتائج ──────────────────────────────────────────")
for k in ["WIN", "LOSS", "TIMEOUT", "MISSED"]:
    if k in status_counts:
        pct = status_counts[k] / len(trades) * 100
        print(f"  {k:10s}: {status_counts[k]:4d} ({pct:.1f}%)")
print()

# Per regime
if metrics.get("per_regime"):
    print("── حسب حالة السوق ────────────────────────────────────────")
    for reg, data in sorted(metrics["per_regime"].items()):
        print(f"  {reg:10s}: {data['total_trades']:4d} صفقة | WR={data['win_rate_pct']:5.1f}% | RR={data['avg_rr']:.2f}")
    print()

# Per sector
if metrics.get("per_sector"):
    print("── حسب القطاع ────────────────────────────────────────────")
    sectors_sorted = sorted(metrics["per_sector"].items(), key=lambda x: x[1]["avg_return_pct"], reverse=True)
    for sec, data in sectors_sorted[:8]:
        print(f"  {sec:20s}: {data['total_trades']:3d} صفقة | WR={data['win_rate_pct']:5.1f}% | avg={data['avg_return_pct']:+.2f}%")
    print()

# Per trade type
if metrics.get("per_trade_type"):
    print("── حسب نوع الصفقة ─────────────────────────────────────────")
    for tt, data in sorted(metrics["per_trade_type"].items()):
        r = data.get("avg_risk_used_pct", 0.0)
        print(f"  {tt:15s}: {data['total_trades']:3d} | WR={data['win_rate_pct']:5.1f}% | avg={data['avg_return_pct']:+.2f}% | RR={data['avg_rr']:.2f}")
    print()

# Monthly breakdown
if metrics.get("monthly"):
    print("── الأداء الشهري ─────────────────────────────────────────")
    positive_months = 0
    for m in metrics["monthly"]:
        sign = "▲" if m["return_pct"] >= 0 else "▼"
        positive_months += (1 if m["return_pct"] >= 0 else 0)
        print(f"  {m['month']}  {sign}  {m['return_pct']:+7.2f}%  |  {m['trade_count']:3d} صفقة  |  WR={m['win_rate_pct']:5.1f}%")
    total_months = len(metrics["monthly"])
    pct_pos = positive_months / total_months * 100 if total_months else 0
    print(f"\n  أشهر رابحة: {positive_months}/{total_months} ({pct_pos:.0f}%)")
    print()

# Top symbols
if metrics.get("per_symbol"):
    print("── أفضل 10 رموز ──────────────────────────────────────────")
    sym_sorted = sorted(metrics["per_symbol"].items(), key=lambda x: x[1]["avg_return_pct"], reverse=True)
    for sym, data in sym_sorted[:10]:
        print(f"  {sym:8s}: {data['total_trades']:3d} | WR={data['win_rate_pct']:5.1f}% | avg={data['avg_return_pct']:+.2f}% | best={data['best_trade_pct']:+.2f}%")
    print()

# Missed trades
d = diagnostics or {}
missed = d.get("missed_entries", [])
if missed:
    missed_pnls = [float(m.get("approx_pnl_pct", 0)) for m in missed if m.get("approx_pnl_pct") is not None]
    print(f"── صفقات فائتة: {len(missed)} ─────────────────────────────────")
    if missed_pnls:
        print(f"  متوسط العائد التقديري: {sum(missed_pnls)/len(missed_pnls):+.2f}%")
        print(f"  مجموع العائد التقديري: {sum(missed_pnls):+.2f}%")
    from collections import Counter as _C
    reasons = _C(m.get("reason", "?") for m in missed)
    for r, n in reasons.most_common(5):
        print(f"  سبب: {r}: {n}")
    print()

# Save full results to JSON
results_path = "backtest_results.json"
with open(results_path, "w", encoding="utf-8") as f:
    json.dump({"params": params, "overall": ov, "monthly": metrics.get("monthly", []),
               "per_sector": metrics.get("per_sector", {}), "per_trade_type": metrics.get("per_trade_type", {}),
               "equity_curve": [{"date": d, "equity_pct": e} for d, e in equity_curve],
               "trades": trades}, f, indent=2, default=str)
print(f"النتائج الكاملة محفوظة في: {results_path}")

# ── 3-Way Ranking System comparison ──────────────────────────────────
hybrid_trades = [t for t in trades if t.get("final_rank", 0) > 0]
if hybrid_trades:
    print(f"\n{'='*70}")
    print(f"  SmartRank vs Multi-Factor vs Final Rank  ({len(hybrid_trades)} trades)")
    print(f"{'='*70}")

    wins_h = [t for t in hybrid_trades if t.get("pnl_pct", 0) > 0]
    losses_h = [t for t in hybrid_trades if t.get("pnl_pct", 0) <= 0]

    sr_win_avg = sum(t.get("smart_rank", 0) for t in wins_h) / len(wins_h) if wins_h else 0
    sr_loss_avg = sum(t.get("smart_rank", 0) for t in losses_h) / len(losses_h) if losses_h else 0
    mf_win_avg = sum(t.get("multi_factor_rank", 0) for t in wins_h) / len(wins_h) if wins_h else 0
    mf_loss_avg = sum(t.get("multi_factor_rank", 0) for t in losses_h) / len(losses_h) if losses_h else 0
    fr_win_avg = sum(t.get("final_rank", 0) for t in wins_h) / len(wins_h) if wins_h else 0
    fr_loss_avg = sum(t.get("final_rank", 0) for t in losses_h) / len(losses_h) if losses_h else 0

    print(f"\n  {'Metric':<20s} {'SmartRank':>12s} {'MF Rank':>12s} {'Final Rank':>12s}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12}")
    print(f"  {'Avg (winners)':<20s} {sr_win_avg:>12.2f} {mf_win_avg:>12.2f} {fr_win_avg:>12.2f}")
    print(f"  {'Avg (losers)':<20s} {sr_loss_avg:>12.2f} {mf_loss_avg:>12.2f} {fr_loss_avg:>12.2f}")
    print(f"  {'Spread (W-L)':<20s} {sr_win_avg - sr_loss_avg:>12.2f} {mf_win_avg - mf_loss_avg:>12.2f} {fr_win_avg - fr_loss_avg:>12.2f}")

    # Correlations between the three ranks
    if len(hybrid_trades) >= 3:
        sr_vals = [t.get("smart_rank", 0) for t in hybrid_trades]
        mf_vals = [t.get("multi_factor_rank", 0) for t in hybrid_trades]
        fr_vals = [t.get("final_rank", 0) for t in hybrid_trades]

        sr_mean = sum(sr_vals) / len(sr_vals)
        mf_mean = sum(mf_vals) / len(mf_vals)
        fr_mean = sum(fr_vals) / len(fr_vals)

        # SR vs MF correlation
        cov_sr_mf = sum((s - sr_mean) * (m - mf_mean) for s, m in zip(sr_vals, mf_vals)) / len(sr_vals)
        sr_std = (sum((s - sr_mean) ** 2 for s in sr_vals) / len(sr_vals)) ** 0.5
        mf_std = (sum((m - mf_mean) ** 2 for m in mf_vals) / len(mf_vals)) ** 0.5
        corr_sr_mf = cov_sr_mf / (sr_std * mf_std) if sr_std > 0 and mf_std > 0 else 0.0

        # SR vs Final correlation
        cov_sr_fr = sum((s - sr_mean) * (f - fr_mean) for s, f in zip(sr_vals, fr_vals)) / len(sr_vals)
        fr_std = (sum((f - fr_mean) ** 2 for f in fr_vals) / len(fr_vals)) ** 0.5
        corr_sr_fr = cov_sr_fr / (sr_std * fr_std) if sr_std > 0 and fr_std > 0 else 0.0

        print(f"\n  {'Correlations:':<20s}")
        print(f"  {'SR vs MF':<20s} {corr_sr_mf:>12.3f}")
        print(f"  {'SR vs Final':<20s} {corr_sr_fr:>12.3f}")
        print(f"  {'Rank averages:':<20s}")
        print(f"  {'SmartRank avg':<20s} {sr_mean:>12.2f}")
        print(f"  {'MF Rank avg':<20s} {mf_mean:>12.2f}")
        print(f"  {'Final Rank avg':<20s} {fr_mean:>12.2f}")

    # Top 10 trades: side-by-side (all 3 ranks)
    print(f"\n  {'Sym':<8s} {'SR':>6s} {'MF':>6s} {'Final':>6s} {'PnL%':>8s} {'Result':>8s}")
    print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")
    for t in sorted(hybrid_trades, key=lambda x: x.get("pnl_pct", 0), reverse=True)[:10]:
        sr = t.get("smart_rank", 0)
        mf = t.get("multi_factor_rank", 0)
        fr = t.get("final_rank", 0)
        pnl = t.get("pnl_pct", 0)
        result = "WIN" if pnl > 0 else "LOSS"
        print(f"  {t.get('sym', '?'):<8s} {sr:>6.1f} {mf:>6.1f} {fr:>6.1f} {pnl:>+8.2f} {result:>8s}")
    print()
else:
    print("\n  (Hybrid final_rank not available in trades — run backtest with updated engine)")

# ── Entry Timing Filter Impact ──────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  Entry Timing Filter Analysis")
print(f"{'='*60}")

# Count timing-blocked signals from missed entries diagnostics
missed = (diagnostics or {}).get("missed_entries", [])
timing_blocked_missed = [m for m in missed if m.get("timing_blocked")]

# Also check if any executed trades were somehow timing_blocked (shouldn't happen)
timing_blocked_trades = [t for t in trades if t.get("timing_blocked")]

# Count from missed entries that have timing-related rejection
timing_reason_missed = [m for m in missed
                        if any(kw in str(m.get("reason", ""))
                               for kw in ("timing", "3day_gain", "ema200_dist", "zone_late"))]

total_blocked = len(timing_blocked_missed) + len(timing_reason_missed)
# Deduplicate in case both paths match the same entry
if total_blocked == 0:
    # Timing filter blocks signals INSIDE signal generation (action becomes WAIT),
    # so they never reach the backtest's missed_entries tracking.
    # We detect impact by comparing trade count with expected baseline.
    print(f"\n  Note: Timing filter operates inside signal_engine.py.")
    print(f"  Blocked signals become WAIT before reaching the backtest engine.")
    print(f"  Impact is measured by comparing total trade count and quality metrics")
    print(f"  against the pre-filter baseline.\n")

print(f"  Executed Trades:     {len(trades)}")
print(f"  Win Rate:            {ov['win_rate_pct']:.1f}%")
print(f"  Avg Return/Trade:    {ov['avg_return_pct']:+.2f}%")
print(f"  Total Return:        {ov['total_return_pct']:+.2f}%")
print(f"  Profit Factor:       {ov['profit_factor']:.2f}")
print(f"  Sharpe Ratio:        {ov['sharpe_ratio']:.2f}")
print(f"  Max Drawdown:        {ov['max_drawdown_pct']:.2f}%")

# Per-status breakdown for timing analysis
wins = [t for t in trades if t.get("pnl_pct", 0) > 0]
losses = [t for t in trades if t.get("pnl_pct", 0) <= 0]
avg_win = sum(t.get("pnl_pct", 0) for t in wins) / len(wins) if wins else 0
avg_loss = sum(t.get("pnl_pct", 0) for t in losses) / len(losses) if losses else 0
print(f"\n  Wins:  {len(wins)} (avg {avg_win:+.2f}%)")
print(f"  Losses: {len(losses)} (avg {avg_loss:+.2f}%)")

# Check if any trades have timing_blocked field (diagnostic)
has_timing_field = sum(1 for t in trades if "timing_blocked" in t)
print(f"\n  Trades with timing_blocked field: {has_timing_field}/{len(trades)}")

# Missed entries breakdown
if missed:
    reason_counts = {}
    for m in missed:
        r = m.get("reason", "unknown")
        reason_counts[r] = reason_counts.get(r, 0) + 1
    print(f"\n  Missed Entries: {len(missed)}")
    print(f"  {'Reason':<35s} {'Count':>6s}")
    print(f"  {'-'*35} {'-'*6}")
    for r, n in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {r:<35s} {n:>6d}")

print(f"\n{'='*60}")
print(f"  Compare these metrics against prior baseline to measure timing filter impact.")
print(f"{'='*60}\n")

