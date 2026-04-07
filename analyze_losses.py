"""Analyze backtest losses to find filter opportunities."""
import json, sys
sys.path.insert(0, '.')

with open('backtest_results.json', encoding='utf-8') as f:
    data = json.load(f)
trades = data.get('trades', [])
wins = [t for t in trades if t.get('pnl_pct', 0) > 0]
losses = [t for t in trades if t.get('pnl_pct', 0) <= 0]

print(f"Total: {len(trades)}, Wins: {len(wins)}, Losses: {len(losses)}")
print()

# Volume confirmed distribution
vol_tw = sum(1 for t in wins if t.get('volume_confirmed'))
vol_fw = sum(1 for t in wins if not t.get('volume_confirmed'))
vol_tl = sum(1 for t in losses if t.get('volume_confirmed'))
vol_fl = sum(1 for t in losses if not t.get('volume_confirmed'))
print(f"WINS  vol=True:{vol_tw}  vol=False:{vol_fw}")
print(f"LOSSES vol=True:{vol_tl}  vol=False:{vol_fl}")
print()

# FWRY analysis
fwry = [t for t in trades if t.get('sym') == 'FWRY']
fw = sum(1 for t in fwry if t.get('pnl_pct', 0) > 0)
fl = sum(1 for t in fwry if t.get('pnl_pct', 0) <= 0)
print(f"FWRY: {len(fwry)} trades, W:{fw} L:{fl}")

# INDUSTRIAL
ind = [t for t in trades if t.get('sector') == 'INDUSTRIAL']
iw = sum(1 for t in ind if t.get('pnl_pct', 0) > 0)
il = sum(1 for t in ind if t.get('pnl_pct', 0) <= 0)
print(f"INDUSTRIAL: {len(ind)} trades, W:{iw} L:{il}")
print()

# Scenario: no INDUSTRIAL
no_ind = [t for t in trades if t.get('sector') != 'INDUSTRIAL']
niw = sum(1 for t in no_ind if t.get('pnl_pct', 0) > 0)
gp = sum(t['pnl_pct'] for t in no_ind if t['pnl_pct'] > 0)
gl = abs(sum(t['pnl_pct'] for t in no_ind if t['pnl_pct'] <= 0))
tr = sum(t['pnl_pct'] for t in no_ind)
pf = gp / (gl + 1e-9)
print(f"Without INDUSTRIAL: {len(no_ind)} trades, WR={niw/len(no_ind)*100:.1f}%, PF={pf:.2f}, total={tr:.2f}%")

# Bars analysis for losses
short_losses = [t for t in losses if t.get('bars_held', 0) <= 5]
print(f"\nLosses with bars<=5: {len(short_losses)}/{len(losses)}")

# SmartRank filtering scenarios
print("\n=== SMARTRANK THRESHOLDS ===")
for min_sr in [73, 75, 77, 80]:
    ft = [t for t in trades if t.get('smart_rank', 0) >= min_sr and t.get('sector') != 'INDUSTRIAL']
    if not ft:
        continue
    w = sum(1 for t in ft if t.get('pnl_pct', 0) > 0)
    gp_ = sum(t['pnl_pct'] for t in ft if t['pnl_pct'] > 0)
    gl_ = abs(sum(t['pnl_pct'] for t in ft if t['pnl_pct'] <= 0))
    print(f"  SR>={min_sr} + no IND: {len(ft)} trades, WR={w/len(ft)*100:.1f}%, PF={gp_/(gl_+1e-9):.2f}")

# Scenario: no INDUSTRIAL + no FWRY
no_ind_fwry = [t for t in trades if t.get('sector') != 'INDUSTRIAL' and t.get('sym') != 'FWRY']
w2 = sum(1 for t in no_ind_fwry if t.get('pnl_pct', 0) > 0)
gp2 = sum(t['pnl_pct'] for t in no_ind_fwry if t['pnl_pct'] > 0)
gl2 = abs(sum(t['pnl_pct'] for t in no_ind_fwry if t['pnl_pct'] <= 0))
tr2 = sum(t['pnl_pct'] for t in no_ind_fwry)
print(f"\nWithout INDUSTRIAL + FWRY: {len(no_ind_fwry)} trades, WR={w2/len(no_ind_fwry)*100:.1f}%, PF={gp2/(gl2+1e-9):.2f}, total={tr2:.2f}%")

# Quick check: bars_held correlation with losses
print("\n=== BARS_HELD ANALYSIS ===")
for max_b in [3, 5, 7]:
    fast_exits = [t for t in losses if t.get('bars_held', 0) <= max_b]
    print(f"  Losses exiting in <={max_b} bars: {len(fast_exits)}")

# What if we filter by requiring bars_held > 3 for losses (i.e., wider stop)?
print("\n=== OPTIMAL SCENARIO ANALYSIS ===")
# No INDUSTRIAL, higher quality gate
for min_sr in [70, 73, 75]:
    ft = [t for t in trades if t.get('smart_rank', 0) >= min_sr and t.get('sector') != 'INDUSTRIAL']
    if not ft:
        continue
    w = sum(1 for t in ft if t.get('pnl_pct', 0) > 0)
    l = sum(1 for t in ft if t.get('pnl_pct', 0) <= 0)
    gp_ = sum(t['pnl_pct'] for t in ft if t['pnl_pct'] > 0)
    gl_ = abs(sum(t['pnl_pct'] for t in ft if t['pnl_pct'] <= 0))
    tr_ = sum(t['pnl_pct'] for t in ft)
    pf_ = gp_ / (gl_ + 1e-9)
    print(f"  SR>={min_sr}: {len(ft)} trades, W:{w} L:{l}, WR={w/len(ft)*100:.1f}%, PF={pf_:.2f}, total={tr_:.2f}%")
