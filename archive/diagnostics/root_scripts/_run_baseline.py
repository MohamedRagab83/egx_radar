"""Quick baseline backtest."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest

print("Running baseline backtest 2024-01-01 to 2025-12-31...")
trades, eq, params, diag = run_backtest('2024-01-01', '2025-12-31')

if not trades:
    print("No trades generated!")
    sys.exit(1)

wins = [t for t in trades if t['outcome'] == 'WIN']
losses = [t for t in trades if t['outcome'] == 'LOSS']
exits = [t for t in trades if t['outcome'] == 'EXIT']
tot = len(trades)
wr = len(wins)/tot*100

pnls = [t['pnl_pct'] for t in trades]
avg_pnl = sum(pnls)/len(pnls)
total_ret = sum(pnls)

avg_win = sum(t['pnl_pct'] for t in wins)/len(wins) if wins else 0
avg_loss = sum(t['pnl_pct'] for t in losses)/len(losses) if losses else 0
pf = abs(sum(t['pnl_pct'] for t in trades if t['pnl_pct']>0) / min(sum(t['pnl_pct'] for t in trades if t['pnl_pct']<0), -0.01))

# Max DD
peak = 100.0
equity = 100.0
max_dd = 0
for t in trades:
    a = t.get('alloc_pct', 0.1)
    equity *= 1 + a * t['pnl_pct']/100
    peak = max(peak, equity)
    dd = (peak - equity) / peak * 100
    max_dd = max(max_dd, dd)

# SmartRank stats
sranks = [t.get('smart_rank', 0) for t in trades]

print(f"\n=== BASELINE RESULTS ===")
print(f"Trades:        {tot}")
print(f"  WIN:         {len(wins)} ({len(wins)/tot*100:.1f}%)")
print(f"  LOSS:        {len(losses)} ({len(losses)/tot*100:.1f}%)")
print(f"  EXIT:        {len(exits)} ({len(exits)/tot*100:.1f}%)")
print(f"Win Rate:      {wr:.1f}%")
print(f"Avg PnL:       {avg_pnl:.2f}%")
print(f"Total Return:  {total_ret:.2f}%")
print(f"Avg Win:       +{avg_win:.2f}%")
print(f"Avg Loss:      {avg_loss:.2f}%")
print(f"Profit Factor: {pf:.2f}")
print(f"Max Drawdown:  {max_dd:.2f}%")
print(f"SmartRank:     min={min(sranks):.1f} max={max(sranks):.1f} avg={sum(sranks)/len(sranks):.1f}")

json.dump({
    "trades": tot, "win_rate": round(wr, 1), "max_drawdown": round(max_dd, 2),
    "total_return": round(total_ret, 2), "profit_factor": round(pf, 2),
    "avg_win": round(avg_win, 2), "avg_loss": round(avg_loss, 2),
}, open("_baseline_results.json", "w"), indent=2)
print("\nSaved to _baseline_results.json")
