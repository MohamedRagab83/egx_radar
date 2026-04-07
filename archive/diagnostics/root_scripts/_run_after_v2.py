"""Run AFTER backtest year-by-year to avoid memory issues."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.backtest.engine import run_backtest

all_trades = []
for year in [2023, 2024, 2025]:
    print(f"Running {year}...")
    t, _, _, _ = run_backtest(f'{year}-01-01', f'{year}-12-31')
    print(f"  {year}: {len(t)} trades")
    all_trades.extend(t)

tot = len(all_trades)
print(f"\nTotal trades: {tot}")

if not tot:
    print("NO TRADES generated with quality gate!")
    json.dump({"trades": 0}, open("_after_results.json", "w"), indent=2)
    sys.exit(0)

wins = [t for t in all_trades if t['outcome'] == 'WIN']
losses = [t for t in all_trades if t['outcome'] == 'LOSS']
exits = [t for t in all_trades if t['outcome'] == 'EXIT']
pnl_pos = [t for t in all_trades if t['pnl_pct'] > 0]

pnls = [t['pnl_pct'] for t in all_trades]
avg_pnl = sum(pnls) / len(pnls)
total_ret = sum(pnls)

avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0

pos_sum = sum(t['pnl_pct'] for t in all_trades if t['pnl_pct'] > 0)
neg_sum = sum(t['pnl_pct'] for t in all_trades if t['pnl_pct'] < 0)
pf = abs(pos_sum / neg_sum) if neg_sum < 0 else float('inf')

# Max DD
peak = 100.0
equity = 100.0
max_dd = 0
for t in all_trades:
    a = t.get('alloc_pct', 0.1)
    equity *= 1 + a * t['pnl_pct'] / 100
    peak = max(peak, equity)
    dd = (peak - equity) / peak * 100
    max_dd = max(max_dd, dd)

wr_label = len(wins) / tot * 100
wr_pnl = len(pnl_pos) / tot * 100

print(f"\n{'=' * 60}")
print(f"AFTER OPTIMIZATION RESULTS (2023-2025)")
print(f"{'=' * 60}")
print(f"Trades:            {tot}")
print(f"  WIN:             {len(wins)}")
print(f"  LOSS:            {len(losses)}")
print(f"  EXIT:            {len(exits)}")
print(f"Label Win Rate:    {wr_label:.1f}%")
print(f"PnL Win Rate:      {wr_pnl:.1f}%")
print(f"Avg PnL:           {avg_pnl:.2f}%")
print(f"Total Return:      {total_ret:.2f}%")
print(f"Avg Win:           +{avg_win:.2f}%")
print(f"Avg Loss:          {avg_loss:.2f}%")
print(f"Profit Factor:     {pf:.2f}")
print(f"Max Drawdown:      {max_dd:.2f}%")

sranks = [t.get('smart_rank', 0) for t in all_trades]
if sranks:
    print(f"SmartRank:         min={min(sranks):.1f} max={max(sranks):.1f} avg={sum(sranks)/len(sranks):.1f}")

print(f"\nIndividual trades:")
for i, t in enumerate(all_trades, 1):
    sym = t.get('sym', '?')
    sd = t.get('signal_date', '?')
    sr = t.get('smart_rank', 0)
    pnl = t.get('pnl_pct', 0)
    out = t.get('outcome', '?')
    bars = t.get('bars_held', 0)
    partial = t.get('partial_taken', False)
    print(f"  {i}. {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out:4s} bars={bars} partial={partial}")

result = {
    "trades": tot, "win_rate_label": round(wr_label, 1),
    "win_rate_pnl": round(wr_pnl, 1),
    "max_drawdown": round(max_dd, 2), "total_return": round(total_ret, 2),
    "profit_factor": round(pf, 2), "avg_win": round(avg_win, 2),
    "avg_loss": round(avg_loss, 2), "avg_pnl": round(avg_pnl, 2),
}
json.dump(result, open("_after_results.json", "w"), indent=2)
print(f"\nSaved to _after_results.json")
