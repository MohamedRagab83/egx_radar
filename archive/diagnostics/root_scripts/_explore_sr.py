"""Explore SmartRank distribution and WR by score bucket."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K

# Lower threshold to see distribution
K.BT_MIN_SMARTRANK = 25.0

from egx_radar.backtest.engine import run_backtest

print("Running backtest 2024-06 to 2025-06 with SR>=25...")
try:
    trades, eq, p, d = run_backtest('2024-06-01', '2025-06-30')
except Exception as ex:
    print(f"ERROR: {ex}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"Trades with SR>=25: {len(trades)}")
if not trades:
    print("No trades!")
    sys.exit(0)

srs = [t.get("smart_rank", 0) for t in trades]
wr = sum(1 for t in trades if t["outcome"] == "WIN") / len(trades) * 100
print(f"WR: {wr:.1f}%")
print(f"SR range: {min(srs):.1f} - {max(srs):.1f}, mean: {sum(srs)/len(srs):.1f}")

# WR by score bucket
for lo, hi in [(25,35),(35,50),(50,65),(65,80),(80,100)]:
    bucket = [t for t in trades if lo <= t.get("smart_rank", 0) < hi]
    if bucket:
        bwr = sum(1 for t in bucket if t["outcome"] == "WIN") / len(bucket) * 100
        print(f"  SR {lo}-{hi}: {len(bucket)} trades, WR={bwr:.1f}%")

# Also check available fields for filtering
if trades:
    t = trades[0]
    print(f"\nAvailable fields in trade dict:")
    for k in sorted(t.keys()):
        print(f"  {k}: {type(t[k]).__name__} = {t[k]}")
