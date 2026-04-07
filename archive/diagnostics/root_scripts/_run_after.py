"""Run AFTER backtest with optimized settings and quality gate."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest

print("=" * 60)
print("AFTER OPTIMIZATION — Backtest 2023-01-01 to 2025-12-31")
print("=" * 60)
print(f"  BT_MIN_SMARTRANK:       {K.BT_MIN_SMARTRANK}")
print(f"  BT_MIN_ACTION:          {K.BT_MIN_ACTION}")
print(f"  BT_DAILY_TOP_N:         {K.BT_DAILY_TOP_N}")
print(f"  MAX_STOP_LOSS_PCT:      {K.MAX_STOP_LOSS_PCT}")
print(f"  PARTIAL_TP_PCT:         {K.PARTIAL_TP_PCT}")
print(f"  TRAILING_TRIGGER_PCT:   {K.TRAILING_TRIGGER_PCT}")
print(f"  TRAILING_STOP_PCT:      {K.TRAILING_STOP_PCT}")
print(f"  RISK_PER_TRADE:         {K.RISK_PER_TRADE}")
print(f"  PORTFOLIO_MAX_OPEN:     {K.PORTFOLIO_MAX_OPEN_TRADES}")
print(f"  MIN_TURNOVER_EGP:       {K.MIN_TURNOVER_EGP}")
print()

trades, eq, params, diag = run_backtest('2023-01-01', '2025-12-31')

if not trades:
    print("NO TRADES generated with optimized filters!")
    print("The quality gate may be too strict.")
    print()
    # Save result anyway
    json.dump({"trades": 0, "win_rate": 0, "max_drawdown": 0,
               "total_return": 0, "profit_factor": 0},
              open("_after_results.json", "w"), indent=2)
    sys.exit(0)

wins = [t for t in trades if t['outcome'] == 'WIN']
losses = [t for t in trades if t['outcome'] == 'LOSS']
exits = [t for t in trades if t['outcome'] == 'EXIT']
tot = len(trades)
wr = len(wins)/tot*100 if tot else 0

pnls = [t['pnl_pct'] for t in trades]
avg_pnl = sum(pnls)/len(pnls) if pnls else 0
total_ret = sum(pnls)

avg_win = sum(t['pnl_pct'] for t in wins)/len(wins) if wins else 0
avg_loss = sum(t['pnl_pct'] for t in losses)/len(losses) if losses else 0

pos_pnl = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0)
neg_pnl = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0)
pf = abs(pos_pnl / neg_pnl) if neg_pnl < 0 else float('inf')

# Actual PnL-based win rate (positive PnL = win)
pnl_wins = [t for t in trades if t['pnl_pct'] > 0]
pnl_wr = len(pnl_wins)/tot*100 if tot else 0

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

print(f"\n{'=' * 60}")
print(f"AFTER OPTIMIZATION RESULTS")
print(f"{'=' * 60}")
print(f"Trades:            {tot}")
print(f"  WIN:             {len(wins)} ({len(wins)/tot*100:.1f}%)" if tot else "  WIN:             0")
print(f"  LOSS:            {len(losses)} ({len(losses)/tot*100:.1f}%)" if tot else "  LOSS:            0")
print(f"  EXIT:            {len(exits)} ({len(exits)/tot*100:.1f}%)" if tot else "  EXIT:            0")
print(f"Label Win Rate:    {wr:.1f}%")
print(f"PnL Win Rate:      {pnl_wr:.1f}%  (positive PnL = win)")
print(f"Avg PnL:           {avg_pnl:.2f}%")
print(f"Total Return:      {total_ret:.2f}%")
print(f"Avg Win:           +{avg_win:.2f}%")
print(f"Avg Loss:          {avg_loss:.2f}%")
print(f"Profit Factor:     {pf:.2f}")
print(f"Max Drawdown:      {max_dd:.2f}%")
if sranks:
    print(f"SmartRank:         min={min(sranks):.1f} max={max(sranks):.1f} avg={sum(sranks)/len(sranks):.1f}")

print()
print("Individual trades:")
for i, t in enumerate(trades, 1):
    print(f"  {i}. {t['sym']:6s} | {t['signal_date']} | SR={t.get('smart_rank',0):5.1f} | "
          f"PnL={t['pnl_pct']:+6.2f}% | {t['outcome']:4s} | "
          f"Entry={t.get('entry_price',0):.2f} Exit={t.get('exit_price',0):.2f} | "
          f"Bars={t.get('hold_bars',0)}")

result = {
    "trades": tot, "win_rate": round(wr, 1), "pnl_win_rate": round(pnl_wr, 1),
    "max_drawdown": round(max_dd, 2), "total_return": round(total_ret, 2),
    "profit_factor": round(pf, 2), "avg_win": round(avg_win, 2),
    "avg_loss": round(avg_loss, 2), "avg_pnl": round(avg_pnl, 2),
}
json.dump(result, open("_after_results.json", "w"), indent=2)
print(f"\nSaved to _after_results.json")
