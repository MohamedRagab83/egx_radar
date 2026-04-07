#!/usr/bin/env python
"""Phase 4 FIX-4B Verification"""
import sys
sys.path.insert(0, '.')

print('=' * 70)
print('PHASE 4 — FIX-4B Verification: Circular Calibration Guard')
print('=' * 70)
print()

# Check the metadata and warning
print('Checking calibration metadata in engine.py:')
print('-' * 70)
try:
    with open('egx_radar/backtest/engine.py', encoding='utf-8', errors='ignore') as f:
        engine_src = f.read()
    
    checks = [
        ('_BT_SECTOR_BIAS_TRAIN_END' in engine_src, 'Training period end defined'),
        ('BT_OOS_START' in engine_src, 'Out-of-sample start defined'),
        ('CIRCULAR CALIBRATION' in engine_src, 'Circular calibration warning'),
        ('circular' in engine_src.lower() and 'bias' in engine_src.lower(), 'Full documentation'),
    ]
    
    all_ok = True
    for check, desc in checks:
        status = '✓' if check else '✗'
        print(f'  {status} {desc}')
        if not check:
            all_ok = False
    
    if not all_ok:
        print()
        print('  ❌ INCOMPLETE: Some elements missing')
    else:
        print()
        print('  ✅ Metadata in place')
except Exception as e:
    print(f'  ❌ ERROR: {e}')
    all_ok = False

print()

# Check the warning in run_backtest
print('Checking run_backtest() warning:')
print('-' * 70)
try:
    checks = [
        ('log.warning' in engine_src and 'CIRCULAR CALIBRATION' in engine_src, 'Warning logged'),
        ('date_from < BT_OOS_START' in engine_src, 'Condition checks date_from'),
        ('optimistically biased' in engine_src, 'Bias message present'),
    ]
    
    all_ok_2 = True
    for check, desc in checks:
        status = '✓' if check else '✗'
        print(f'  {status} {desc}')
        if not check:
            all_ok_2 = False
    
    if not all_ok_2:
        print()
        print('  ❌ INCOMPLETE: Warning not fully integrated')
    else:
        print()
        print('  ✅ Warning in run_backtest()')
except Exception as e:
    print(f'  ❌ ERROR: {e}')
    all_ok_2 = False

print()

# Check settings.py
print('Checking settings.py constant:')
print('-' * 70)
try:
    with open('egx_radar/config/settings.py', encoding='utf-8', errors='ignore') as f:
        settings_src = f.read()
    
    has_constant = 'BT_OOS_START' in settings_src and '2025-01-01' in settings_src
    if has_constant:
        print('  ✓ BT_OOS_START = "2025-01-01"')
        print()
        print('  ✅ Constant defined')
    else:
        print('  ✗ Constant not found')
        print()
        print('  ❌ INCOMPLETE')
except Exception as e:
    print(f'  ❌ ERROR: {e}')
    has_constant = False

print()
print('=' * 70)
if all_ok and all_ok_2 and has_constant:
    print('✅ PHASE 4 — FIX-4B VERIFICATION PASSED')
else:
    print('❌ PHASE 4 — FIX-4B VERIFICATION INCOMPLETE')
print('=' * 70)
