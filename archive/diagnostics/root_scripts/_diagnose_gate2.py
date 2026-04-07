"""Diagnostic: analyze what quality gate does to the 14 BEFORE trades."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
import egx_radar.backtest.engine as eng

# Temporarily remove quality gate
original_fn = eng._is_high_probability_trade
eng._is_high_probability_trade = lambda r: True  # pass everything

# Also lower SR filter and action to get the old 14-trade baseline
K.BT_MIN_SMARTRANK = 0.0
K.BT_MIN_ACTION = "PROBE"
K.BT_DAILY_TOP_N = 5

from egx_radar.backtest.engine import run_backtest

all_trades = []
for year in [2023, 2024, 2025]:
    print(f"Running {year}...")
    t, _, _, _ = run_backtest(f'{year}-01-01', f'{year}-12-31')
    all_trades.extend(t)

print(f"\nWith NO gate: {len(all_trades)} trades")

# Now test each trade against the quality gate checks
eng._is_high_probability_trade = original_fn  # restore

# But first, let's understand: the `allowed` filter already ran. The signal details
# are stored in each trade. Let me check what fields are available:
if all_trades:
    t0 = all_trades[0]
    print(f"\nAvailable fields in trade: {sorted(t0.keys())}")

# The problem is that trades don't contain the raw signal data like
# accumulation_detected, rsi, etc. Those are checked BEFORE the trade is created.
# We need to look at the signal evaluation results.

# Let's take a different approach: read what the BEFORE results were from _analyze_trades.py
print("\nBEFORE trades (from previous analysis with outcome fix applied):")
for i, t in enumerate(all_trades, 1):
    sym = t.get('sym', '?')
    sd = t.get('signal_date', '?')
    sr = t.get('smart_rank', 0)
    pnl = t.get('pnl_pct', 0)
    out = t.get('outcome', '?')
    bars = t.get('bars_held', 0)
    partial = t.get('partial_taken', False)
    print(f"  {i}. {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out:4s} bars={bars} partial={partial}")

wins = sum(1 for t in all_trades if t['outcome'] == 'WIN')
losses = sum(1 for t in all_trades if t['outcome'] == 'LOSS')
pnl_pos = sum(1 for t in all_trades if t['pnl_pct'] > 0)
tot = len(all_trades)
if tot:
    print(f"\nLabel WR: {wins/tot*100:.1f}%  PnL WR: {pnl_pos/tot*100:.1f}%")
