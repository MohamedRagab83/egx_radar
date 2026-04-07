"""
Run EGX Radar full backtest and print detailed results.
Usage:  python run_backtest.py [date_from] [date_to]
Default: 2024-01-01 to 2025-12-31
"""
import sys
import logging
import json

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

date_from = sys.argv[1] if len(sys.argv) > 1 else "2024-01-01"
date_to   = sys.argv[2] if len(sys.argv) > 2 else "2025-12-31"

print(f"\n{'='*60}")
print(f"  EGX Radar Backtest  {date_from}  →  {date_to}")
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
