"""Extended backtest: 2020-2025 for more statistical significance."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.backtest.engine import run_backtest

all_trades = []
for year in range(2020, 2026):
    print(f"Running {year}...")
    try:
        t, _, _, _ = run_backtest(f'{year}-01-01', f'{year}-12-31')
        print(f"  {year}: {len(t)} trades")
        all_trades.extend(t)
    except Exception as e:
        print(f"  {year}: ERROR - {e}")

tot = len(all_trades)
print(f"\nTotal trades (2020-2025): {tot}")

if not tot:
    print("NO TRADES generated!")
else:
    wins = sum(1 for t in all_trades if t['outcome'] == 'WIN')
    losses = sum(1 for t in all_trades if t['outcome'] == 'LOSS')
    exits = sum(1 for t in all_trades if t['outcome'] == 'EXIT')
    pnl_pos = sum(1 for t in all_trades if t['pnl_pct'] > 0)
    pnls = [t['pnl_pct'] for t in all_trades]
    
    peak = 100.0; equity = 100.0; max_dd = 0
    for t in all_trades:
        a = t.get('alloc_pct', 0.1)
        equity *= 1 + a * t['pnl_pct'] / 100
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
    
    print(f"WIN: {wins}  LOSS: {losses}  EXIT: {exits}")
    print(f"Label WR:    {wins/tot*100:.1f}%")
    print(f"PnL WR:      {pnl_pos/tot*100:.1f}%")
    print(f"Avg PnL:     {sum(pnls)/len(pnls):.2f}%")
    print(f"Total Ret:   {sum(pnls):.2f}%")
    print(f"Max DD:      {max_dd:.2f}%")
    
    for i, t in enumerate(all_trades, 1):
        sym = t.get('sym', '?')
        sd = t.get('signal_date', '?')
        sr = t.get('smart_rank', 0)
        pnl = t.get('pnl_pct', 0)
        out = t.get('outcome', '?')
        bars = t.get('bars_held', 0)
        partial = t.get('partial_taken', False)
        print(f"  {i:2}. {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out:4s} bars={bars} partial={partial}")
