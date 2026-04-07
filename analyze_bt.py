"""Analyze backtest results in detail."""
import json

with open("backtest_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

trades = data["trades"]
trades_sorted = sorted(trades, key=lambda x: float(x.get("pnl_pct") or 0))

print("=== أسوأ 10 صفقات ===")
for t in trades_sorted[:10]:
    sym    = t.get("sym", "?")
    date   = t.get("entry_date", t.get("date","?"))
    pnl    = float(t.get("pnl_pct") or 0)
    bars   = t.get("bars_held", 0)
    ttype  = t.get("trade_type", "?")
    sector = t.get("sector", "?")
    status = t.get("status", "?")
    entry  = float(t.get("entry") or 0)
    exit_p = float(t.get("exit_price") or 0)
    stop   = float(t.get("stop") or 0)
    print(f"  {sym:8s} | {date} | pnl={pnl:+7.2f}% | bars={bars:2d} | {status:8s} | {ttype:8s} | {sector} | entry={entry:.2f} exit={exit_p:.2f} stop={stop:.2f}")

print()
print("=== أفضل 10 صفقات ===")
for t in trades_sorted[-10:]:
    sym    = t.get("sym", "?")
    date   = t.get("entry_date", t.get("date","?"))
    pnl    = float(t.get("pnl_pct") or 0)
    bars   = t.get("bars_held", 0)
    ttype  = t.get("trade_type", "?")
    sector = t.get("sector", "?")
    print(f"  {sym:8s} | {date} | pnl={pnl:+7.2f}% | bars={bars:2d} | {ttype:8s} | {sector}")

print()
worst = trades_sorted[0]
print("=== تفاصيل أسوأ صفقة ===")
for k, v in worst.items():
    print(f"  {k}: {v}")
