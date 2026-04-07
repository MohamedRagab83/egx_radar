#!/usr/bin/env python
"""Phase 4 Diagnostic Scan — SmartRank & Calibration Upgrades"""
import sys
import os
sys.path.insert(0, '.')

print('=' * 70)
print('PHASE 4 — SmartRank & Calibration Upgrades — DIAGNOSTIC SCAN')
print('=' * 70)
print()

# FIX-4A
print('FIX-4A: NEURAL component replacement')
print('-' * 70)
try:
    with open('egx_radar/core/scoring.py', encoding='utf-8', errors='ignore') as f:
        scoring_src = f.read()
    
    has_neural_component = 'nw_avg' in scoring_src and 'neural_n' in scoring_src
    has_quantile_norm = 'def quantile_norm' in scoring_src or 'quantile_norm(' in scoring_src
    has_momentum_series = 'momentum_series' in scoring_src
    has_cross_sectional = 'Cross-sectional momentum' in scoring_src or 'cross-sectional' in scoring_src.lower()
    
    print(f'  {"✓" if has_neural_component else "✗"} NEURAL component (nw_avg, neural_n) found')
    print(f'  {"✓" if has_quantile_norm else "✗"} quantile_norm function exists')
    print(f'  {"✓" if has_momentum_series else "✗"} momentum_series parameter present')
    print(f'  {"✓" if has_cross_sectional else "✗"} Cross-sectional logic implemented')
    
    if has_neural_component and not has_cross_sectional:
        print()
        print('  STATUS: NEURAL component uses old formula (nw_avg normalised)')
        print('          Requires upgrade to cross-sectional momentum rank')
    elif has_cross_sectional:
        print()
        print('  STATUS: ✅ Cross-sectional momentum rank already in place')
    else:
        print()
        print('  STATUS: Component structure missing')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('FIX-4B: Sector bias calibration metadata')
print('-' * 70)
try:
    with open('egx_radar/backtest/engine.py', encoding='utf-8', errors='ignore') as f:
        engine_src = f.read()
    
    has_sector_bias = '_BT_SECTOR_BIAS' in engine_src
    has_circular_warning = 'CIRCULAR CALIBRATION' in engine_src or 'circular' in engine_src.lower()
    has_bt_oos_start = 'BT_OOS_START' in engine_src
    has_train_end = '_BT_SECTOR_BIAS_TRAIN_END' in engine_src or 'TRAIN_END' in engine_src
    
    print(f'  {"✓" if has_sector_bias else "✗"} _BT_SECTOR_BIAS dict present')
    print(f'  {"✓" if has_circular_warning else "✗"} Circular calibration warning comment')
    print(f'  {"✓" if has_bt_oos_start else "✗"} BT_OOS_START constant defined')
    print(f'  {"✓" if has_train_end else "✗"} Training period end marked')
    
    if has_sector_bias and not has_circular_warning:
        print()
        print('  STATUS: Sector bias exists but lacks calibration warning')
        print('          Needs metadata about calibration period')
    elif has_circular_warning:
        print()
        print('  STATUS: ✅ Circular calibration guard already in place')
    else:
        print()
        print('  STATUS: Sector bias not found')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('FIX-4C: Signal aging penalty')
print('-' * 70)
try:
    with open('egx_radar/core/scoring.py', encoding='utf-8', errors='ignore') as f:
        scoring_src = f.read()
    
    has_aging_logic = 'aging' in scoring_src.lower() or 'stale' in scoring_src.lower()
    has_sig_hist = 'sig_hist' in scoring_src
    has_vol_ratio_check = 'vol_ratio < 1.1' in scoring_src or 'vol_ratio.*1.1' in scoring_src
    has_damper_aging = '0.88' in scoring_src and 'damper' in scoring_src
    
    print(f'  {"✓" if has_sig_hist else "✗"} sig_hist (signal history) parameter')
    print(f'  {"✓" if has_aging_logic else "✗"} Aging/staleness logic present')
    print(f'  {"✓" if has_vol_ratio_check else "✗"} Volume ratio check (1.1 threshold)')
    print(f'  {"✓" if has_damper_aging else "✗"} Aging damper (0.88 multiplier)')
    
    if has_sig_hist and not has_damper_aging:
        print()
        print('  STATUS: Signal tracking exists but no aging penalty applied')
        print('          Needs damper *= 0.88 for persistent unconfirmed signals')
    elif has_damper_aging:
        print()
        print('  STATUS: ✅ Signal aging penalty already implemented')
    else:
        print()
        print('  STATUS: Signal history tracking not found')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('=' * 70)
print('DIAGNOSTIC COMPLETE')
print('=' * 70)
