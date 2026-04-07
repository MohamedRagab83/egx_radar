"""Scan SmartRank distribution across full date range."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K

# Set to 0 to see ALL trades the engine can produce
K.BT_MIN_SMARTRANK = 0.0
K.BT_MIN_ACTION = "PROBE"

from egx_radar.backtest.engine import run_backtest

print("Running backtest 2023-01 to 2025-12 with SR>=0 (no filter)...")
try:
    trades, eq, p, d = run_backtest('2023-01-01', '2025-12-31')
except Exception as ex:
    print(f"ERROR: {ex}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\nTotal trades: {len(trades)}")
if not trades:
    print("No trades!")
    sys.exit(0)

srs = [t.get("smart_rank", 0) for t in trades]
wr = sum(1 for t in trades if t["outcome"] == "WIN") / len(trades) * 100
print(f"Overall WR: {wr:.1f}%")
print(f"SR range: {min(srs):.1f} - {max(srs):.1f}, mean: {sum(srs)/len(srs):.1f}")

# WR by score bucket
print("\n--- WR by SmartRank bucket ---")
for lo, hi in [(0,20),(20,30),(30,40),(40,50),(50,60),(60,70),(70,80),(80,100)]:
    bucket = [t for t in trades if lo <= t.get("smart_rank", 0) < hi]
    if bucket:
        bwr = sum(1 for t in bucket if t["outcome"] == "WIN") / len(bucket) * 100
        avg_pnl = sum(t["pnl_pct"] for t in bucket) / len(bucket)
        print(f"  SR {lo:>3}-{hi:>3}: {len(bucket):>4} trades, WR={bwr:>5.1f}%, avg_pnl={avg_pnl:>+6.2f}%")

# Check what indicators correlate with wins
wins = [t for t in trades if t["outcome"] == "WIN"]
losses = [t for t in trades if t["outcome"] == "LOSS"]
print(f"\n--- Win vs Loss SmartRank ---")
print(f"  Avg SR of wins:   {sum(t.get('smart_rank',0) for t in wins)/max(len(wins),1):.1f}")
print(f"  Avg SR of losses: {sum(t.get('smart_rank',0) for t in losses)/max(len(losses),1):.1f}")

# Check accumulation flags (if present in trade dict)
for field in ['accumulation_detected', 'higher_lows', 'volume_confirmed', 'erratic_volume', 'fake_move']:
    vals_win = [1 for t in wins if t.get(field)]
    vals_loss = [1 for t in losses if t.get(field)]
    if vals_win or vals_loss:
        print(f"  {field}: wins={len(vals_win)}/{len(wins)}, losses={len(vals_loss)}/{len(losses)}")
