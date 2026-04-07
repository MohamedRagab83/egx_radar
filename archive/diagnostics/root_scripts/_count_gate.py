"""Count how many signals pass vs fail the quality gate in 2023-2025."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
import egx_radar.backtest.engine as eng

# Save original gate
_orig_gate = eng._is_high_probability_trade
_pass_count = 0
_fail_count = 0
_fail_details = []

def _counting_gate(r):
    global _pass_count, _fail_count
    result = _orig_gate(r)
    if result:
        _pass_count += 1
    else:
        _fail_count += 1
        # Log what failed
        score = 0
        checks = {
            "accum_det": r.get("accumulation_detected", False),
            "higher_lows": r.get("higher_lows", False),
            "price>ema50": r.get("price", 0) > r.get("ema50", 0),
            "price>ema200": r.get("price", 0) > r.get("ema200", 0),
            "rsi_ok": 40 <= r.get("rsi", 50) <= 70,
            "vol_conf": r.get("volume_confirmed", False),
            "vol_ratio_ok": r.get("vol_ratio", 1.0) <= 2.5,
            "2day_ok": abs(r.get("two_day_gain_pct", 0)) <= 5.0,
            "struct>=50": r.get("structure_strength_score", 0) >= 50,
            "accum_q>=60": r.get("accumulation_quality_score", 0) >= 60,
        }
        hard_fail = []
        if r.get("fake_move", False):
            hard_fail.append("fake_move")
        if r.get("erratic_volume", False):
            hard_fail.append("erratic_vol")
        if "LATE" in str(r.get("zone", "")).upper():
            hard_fail.append("LATE_zone")
        
        passing = sum(1 for v in checks.values() if v)
        _fail_details.append({
            "sym": r.get("sym", "?"),
            "sr": r.get("smart_rank", 0),
            "hard_fail": hard_fail,
            "soft_score": passing,
            "checks": checks,
            "zone": r.get("zone"),
        })
    return result

eng._is_high_probability_trade = _counting_gate

from egx_radar.backtest.engine import run_backtest

for year in [2023, 2024, 2025]:
    run_backtest(f'{year}-01-01', f'{year}-12-31')

print(f"Quality Gate Stats:")
print(f"  Passed: {_pass_count}")
print(f"  Failed: {_fail_count}")
print(f"  Total candidates: {_pass_count + _fail_count}")
print()

if _fail_details:
    print(f"Failed signal details:")
    for i, d in enumerate(_fail_details, 1):
        hard = f" HARD:{','.join(d['hard_fail'])}" if d['hard_fail'] else ""
        print(f"  {i}. {d['sym']:6s} SR={d['sr']:5.1f} soft={d['soft_score']}/10 zone={d['zone']}{hard}")
        failed_checks = [k for k, v in d['checks'].items() if not v]
        if failed_checks:
            print(f"     failed: {', '.join(failed_checks)}")
