"""Diagnostic: which quality checks eliminate the most trades?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K

# Temporarily disable quality gate and lower SR to see all candidates
orig_sr = K.BT_MIN_SMARTRANK
K.BT_MIN_SMARTRANK = 0.0

# Monkey-patch the quality gate to log rejections
import egx_radar.backtest.engine as eng

_original_fn = eng._is_high_probability_trade
_rejection_counts = {}
_rejected_details = []

def _logging_quality_gate(r):
    sym = r.get("sym", "?")
    sr = r.get("smart_rank", 0)
    
    checks = [
        ("accumulation_detected", r.get("accumulation_detected", False) == True),
        ("higher_lows", r.get("higher_lows", False) == True),
        ("price>ema50", r.get("price", 0) > r.get("ema50", 0)),
        ("price>ema200", r.get("price", 0) > r.get("ema200", 0)),
        ("rsi_45_65", 45 <= r.get("rsi", 50) <= 65),
        ("vol_ratio<1.8", r.get("vol_ratio", 1.0) <= 1.8),
        ("no_erratic_vol", not r.get("erratic_volume", False)),
        ("no_fake_move", not r.get("fake_move", False)),
        ("2day_gain<5", abs(r.get("two_day_gain_pct", 0)) <= 5.0),
        ("3day_gain<max", abs(r.get("last_3_days_gain_pct", 0)) <= K.MAX_3DAY_GAIN_PCT),
        ("gap_up<max", abs(r.get("gap_up_pct", 0)) <= K.MAX_GAP_UP_PCT),
        ("volume_confirmed", r.get("volume_confirmed", False) == True),
        ("struct_score>=60", r.get("structure_strength_score", 0) >= 60),
        ("accum_score>=70", r.get("accumulation_quality_score", 0) >= 70),
        ("trend_score>=50", r.get("trend_alignment_score", 0) >= 50),
        ("not_LATE_zone", "LATE" not in str(r.get("zone", "")).upper()),
    ]
    
    failed = [name for name, passed in checks if not passed]
    
    if failed:
        for f in failed:
            _rejection_counts[f] = _rejection_counts.get(f, 0) + 1
        _rejected_details.append({
            "sym": sym, "sr": sr,
            "failed": failed,
            "values": {
                "accum_det": r.get("accumulation_detected"),
                "higher_lows": r.get("higher_lows"),
                "rsi": round(r.get("rsi", 0), 1),
                "vol_ratio": round(r.get("vol_ratio", 0), 2),
                "struct_score": round(r.get("structure_strength_score", 0), 1),
                "accum_score": round(r.get("accumulation_quality_score", 0), 1),
                "trend_score": round(r.get("trend_alignment_score", 0), 1),
                "zone": r.get("zone"),
                "volume_confirmed": r.get("volume_confirmed"),
                "erratic": r.get("erratic_volume"),
                "fake_move": r.get("fake_move"),
            }
        })
    
    return len(failed) == 0

eng._is_high_probability_trade = _logging_quality_gate

from egx_radar.backtest.engine import run_backtest

all_candidates = []
for year in [2023, 2024, 2025]:
    print(f"Scanning {year}...")
    t, _, _, _ = run_backtest(f'{year}-01-01', f'{year}-12-31')
    all_candidates.extend(t)

K.BT_MIN_SMARTRANK = orig_sr

print(f"\n{'='*60}")
print(f"QUALITY GATE REJECTION ANALYSIS")
print(f"{'='*60}")
print(f"Trades that passed gate: {len(all_candidates)}")
print(f"Total rejections logged: {len(_rejected_details)}")
print()

print("Rejection counts by check (most restrictive first):")
for check, count in sorted(_rejection_counts.items(), key=lambda x: -x[1]):
    print(f"  {check:25s}: {count} rejections")

print(f"\nRejected trade details (first 20):")
for i, d in enumerate(_rejected_details[:20], 1):
    print(f"  {i}. {d['sym']:6s} SR={d['sr']:5.1f} failed: {', '.join(d['failed'])}")
    v = d['values']
    print(f"     accum={v['accum_det']} hl={v['higher_lows']} rsi={v['rsi']} vol_r={v['vol_ratio']} "
          f"struct={v['struct_score']} accum_q={v['accum_score']} trend={v['trend_score']} "
          f"zone={v['zone']} vol_conf={v['volume_confirmed']}")
