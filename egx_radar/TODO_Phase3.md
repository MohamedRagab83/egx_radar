# EGX Radar v1.0 - Phase 3 Implementation TODO

## STATUS: ✅ ALL 5 FEATURES IMPLEMENTED

### ✅ ALREADY DONE:
| Feature | Config | Logic | Location |
|---------|--------|-------|----------|
| P3-E1 EMA50 Guard | ✅ K.EMA50_GUARD_ENABLED | ✅ runner.py | Lines ~730 |
| P3-E2 VCP Multiplier | ✅ K.VCP_MULTIPLIER_ENABLED | ✅ scoring.py | Lines ~385 |
| P3-E3 CMF Damping | ✅ K.CMF_DAMPING_ENABLED | ✅ scoring.py | Lines ~388 |

### ✅ NOW COMPLETE:

#### 1. [P3-E3] CMF Damping ✅
- Config: CMF_DAMPING_ENABLED = True, CMF_DAMPING_FACTOR = 0.70
- Logic: scoring.py - if cmf < 0 and vol_ratio < 1.0 and vwap_dist < 0 → raw_n *= 0.70

#### 2. [P3-G2] RR Bonus ✅
- Config: RR_BONUS_ENABLED = True, RR_BONUS_THRESHOLD = 3.0, RR_BONUS_AMOUNT = 0.05
- Logic: scoring.py - AFTER weighted sum, BEFORE ×60 scaling
- Estimate RR from: RSI sweet spot, ADX strength, momentum, pct_ema200, volume

#### 3. [P3-G3] ATR% Hard + Soft Limits ✅
- Config: ATR_PCT_FILTER_ENABLED = True, ATR_PCT_HARD_LIMIT = 8.0, ATR_PCT_SOFT_LIMIT = 5.0
- Logic: runner.py - atr_pct >= 8.0 → WAIT; >= 5.0 + ACCUMULATE → PROBE

#### 4. [P3-G5] Volume Surge ✅
- Config: VOL_SURGE_ENABLED = True, VOL_SURGE_THRESHOLD = 2.5
- Logic: runner.py - vol_ratio >= 2.5 → size_multiplier *= 1.20

#### 5. [P3-G6] CMF Size Boost ✅
- Config: CMF_SIZE_BOOST_ENABLED = True, CMF_SIZE_BOOST_THRESHOLD = 0.15, CMF_SIZE_BOOST_MULT = 1.10
- Logic: runner.py - cmf >= 0.15 → size_multiplier *= 1.10

---

## Golden Rules Checklist:
- [x] NEVER touch "early" signal
- [x] NEVER delete existing code
- [x] All new features ADDITIVE
- [x] Config flags for each feature
- [x] Show before/after for each

