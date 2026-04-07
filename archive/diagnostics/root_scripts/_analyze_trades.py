"""Analyze all trades: PnL vs Outcome classification."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
K.BT_MIN_SMARTRANK = 0.0

from egx_radar.backtest.engine import run_backtest

trades, eq, p, d = run_backtest('2023-01-01', '2025-12-31')
print(f"Total: {len(trades)}")

for t in trades:
    sym = t["sym"]
    sr = t["smart_rank"]
    pnl = t["pnl_pct"]
    outcome = t["outcome"]
    partial = t.get("partial_taken", False)
    bars = t["bars_held"]
    regime = t.get("regime", "?")
    entry_d = t.get("entry_date", "?")
    misclass = "MISCLASSIFIED" if (outcome == "LOSS" and pnl > 0) else ""
    print(f"  {sym:6} {entry_d} SR={sr:5.1f} pnl={pnl:+6.2f}% outcome={outcome:4} partial={str(partial):5} bars={bars:2} {misclass}")

pos_pnl = sum(1 for t in trades if t["pnl_pct"] > 0)
neg_pnl = sum(1 for t in trades if t["pnl_pct"] <= 0)
wins_label = sum(1 for t in trades if t["outcome"] == "WIN")
loss_label = sum(1 for t in trades if t["outcome"] == "LOSS")
exit_label = sum(1 for t in trades if t["outcome"] == "EXIT")
misclassed = sum(1 for t in trades if t["outcome"] == "LOSS" and t["pnl_pct"] > 0)

print(f"\nBy outcome label: WIN={wins_label} LOSS={loss_label} EXIT={exit_label}")
print(f"By actual PnL:    positive={pos_pnl} negative={neg_pnl}")
print(f"Misclassified (LOSS but +PnL): {misclassed}")
print(f"Label WR:  {wins_label/max(len(trades),1)*100:.1f}%")
print(f"True WR:   {pos_pnl/max(len(trades),1)*100:.1f}%")
