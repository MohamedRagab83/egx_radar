"""Deep analysis of backtest results to understand real performance."""
import json
import statistics

with open("backtest_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

trades = data["trades"]
ov     = data["overall"]
params = data["params"]

print(f"{'='*60}")
print(f"  تحليل نتائج Backtest  {params['date_from']} → {params['date_to']}")
print(f"{'='*60}\n")

# Detect outliers (data anomalies)
pnls = [float(t.get("pnl_pct") or 0) for t in trades]
mean_p = statistics.mean(pnls)
stdev_p = statistics.stdev(pnls) if len(pnls) > 1 else 0

outliers = [t for t in trades if float(t.get("pnl_pct") or 0) < (mean_p - 3 * stdev_p)]
normal   = [t for t in trades if float(t.get("pnl_pct") or 0) >= (mean_p - 3 * stdev_p)]

print(f"الصفقات الكلية:           {len(trades)}")
print(f"متوسط P&L:                {mean_p:+.2f}%")
print(f"الانحراف المعياري:         {stdev_p:.2f}%")
print(f"حدود الاكتشاف (3σ):       < {(mean_p - 3*stdev_p):+.2f}%")
print()

if outliers:
    print("⚠  بيانات شاذة (احتمال خطأ في Yahoo Finance / تعليق سهم):")
    for t in outliers:
        pnl   = float(t.get("pnl_pct") or 0)
        entry = float(t.get("entry") or 0)
        exit_ = float(t.get("exit") or t.get("exit_price") or 0)
        bars  = t.get("bars_held", "?")
        print(f"  {t['sym']:8s} | {t.get('entry_date','?')} | entry={entry:.2f} → exit={exit_:.2f} | {pnl:+.2f}% في {bars} يوم")
    print()

# Stats without outliers
pnls_clean = [float(t.get("pnl_pct") or 0) for t in normal]
wins_clean  = [p for p in pnls_clean if p > 0]
losses_clean = [p for p in pnls_clean if p <= 0]
wr_clean = len(wins_clean) / len(pnls_clean) * 100 if pnls_clean else 0
avg_w = statistics.mean(wins_clean) if wins_clean else 0
avg_l = statistics.mean(losses_clean) if losses_clean else 0
pf    = (len(wins_clean)*avg_w) / (len(losses_clean)*abs(avg_l)+1e-9) if pnls_clean else 0
expectancy = statistics.mean(pnls_clean) if pnls_clean else 0

print(f"── الأداء بدون البيانات الشاذة ({len(normal)} صفقة) ──────────────")
print(f"  نسبة الربح:        {wr_clean:.1f}%")
print(f"  متوسط الربح/صفقة:  {expectancy:+.2f}%")
print(f"  متوسط الرابحة:     {avg_w:+.2f}%")
print(f"  متوسط الخاسرة:     {avg_l:+.2f}%")
print(f"  نسبة R:R:          {abs(avg_w/avg_l):.2f}" if avg_l else "  نسبة R:R: N/A")
print(f"  Profit Factor:     {pf:.2f}")
print()

# What caused REAL_ESTATE to be so bad?
re_trades = [t for t in trades if t.get("sector") == "REAL_ESTATE"]
re_pnls   = [float(t.get("pnl_pct") or 0) for t in re_trades]
print(f"── قطاع العقارات ({len(re_trades)} صفقة) ──────────────────────────")
for t in sorted(re_trades, key=lambda x: float(x.get("pnl_pct") or 0)):
    pnl = float(t.get("pnl_pct") or 0)
    print(f"  {t['sym']:8s} | {t.get('entry_date','?')} | {pnl:+7.2f}% | {t.get('status','?')}")
print()

# Stoplosses pattern
stoploss_trades = [t for t in trades if abs(float(t.get("pnl_pct") or 0) - (-5.44)) < 0.1]
print(f"── صفقات Stop-Loss (MAX_STOP=5%) — {len(stoploss_trades)} صفقة ────────────")
print(f"  هذه الصفقات وصل سعرها لوقف الخسارة (-5% + 0.44% تكاليف = -5.44%)")
print(f"  تحليل: نسبة الوقف = {len(stoploss_trades)/len(trades)*100:.0f}% من الصفقات")
print()

# Performance by equity
if data.get("equity_curve"):
    eq = [e["equity_pct"] for e in data["equity_curve"] if e["equity_pct"] != 0]
    if eq:
        print(f"── منحنى رأس المال ──────────────────────────────────────")
        print(f"  أعلى نقطة: +{max(eq):.2f}%")
        print(f"  أدنى نقطة: {min(eq):.2f}%")
        print(f"  النهاية:   {eq[-1]:+.2f}%")
        print()

# Annual simulation without outliers
print(f"── محاكاة العائد السنوي (بدون بيانات شاذة) ──────────────────")
trades_per_year = len(normal) / 2  # 2-year backtest
print(f"  صفقات فعلية/سنة في الـ backtest: {trades_per_year:.0f}")
print()

# With capital
for capital in [50_000, 100_000, 500_000]:
    equity = 100.0
    for p in pnls_clean:
        alloc = 0.10  # conservative 10% per trade with risk sizing
        equity *= (1 + alloc * p / 100)
    ann = equity - 100
    egp = capital * ann / 100
    sign = "+" if egp >= 0 else ""
    print(f"  رأس مال {capital:>9,} ج.م. → سنوي: {sign}{egp:>10,.0f} ج.م. ({ann:+.1f}%)")

print()
print("── الخلاصة ─────────────────────────────────────────────────")
if expectancy > 0:
    print(f"  ✅ النظام رابح (بدون الشاذات) | EV = {expectancy:+.2f}% / صفقة")
else:
    print(f"  ❌ النظام خاسر | EV = {expectancy:+.2f}% / صفقة")
print(f"  ⚠ البيانات الشاذة ({len(outliers)} صفقة) أثّرت بشكل كبير على النتيجة")
print(f"  ⚠ عدد الصفقات قليل جداً ({len(trades)} خلال سنتين = {len(trades)/24:.1f}/شهر)")
print(f"  ⚠ يجب مراجعة {outliers[0]['sym'] if outliers else '—'} للتأكد من صحة بيانات Yahoo Finance")
