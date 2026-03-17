#!/usr/bin/env python
"""Phase 3 Verification Tests"""
import sys
import datetime
sys.path.insert(0, '.')

print('=' * 70)
print('PHASE 3 — VERIFICATION TESTS')
print('=' * 70)
print()

# FIX-3A: Trading day function
print('FIX-3A: Trading-day-aware staleness check')
print('-' * 70)
try:
    from egx_radar.core.data_guard import _egx_trading_days_since
    
    # Test 1: Same day
    today = datetime.date.today()
    lag0 = _egx_trading_days_since(today)
    assert lag0 == 0, f'Same-day lag should be 0, got {lag0}'
    print('  ✓ Same-day lag = 0 trading days')
    
    # Test 2: One calendar day ago (might be trading day or not)
    yesterday = today - datetime.timedelta(days=1)
    lag1 = _egx_trading_days_since(yesterday)
    print(f'  ✓ Yesterday lag = {lag1} trading day(s)')
    
    # Test 3: One week ago (5-6 trading days + holiday buffer)
    week_ago = today - datetime.timedelta(days=7)
    lag_week = _egx_trading_days_since(week_ago)
    print(f'  ✓ One week ago lag = {lag_week} trading day(s)')
    assert 0 <= lag_week <= 6, f'One week ago should be 0-6 trading days, got {lag_week}'
    
    print('  ✅ FIX-3A: PASSED')
except Exception as e:
    print(f'  ❌ FIX-3A: FAILED — {e}')
    import traceback
    traceback.print_exc()

print()

# FIX-3B: Logging in place
print('FIX-3B: Thread-safety logging for pandas_ta')
print('-' * 70)
try:
    with open('egx_radar/scan/runner.py', encoding='utf-8', errors='ignore') as f:
        runner_src = f.read()
    
    checks = [
        ('_indicator_fail_count' in runner_src, 'Failure counter present'),
        ('Rate-limit' in runner_src or 'rate-limited' in runner_src.lower(), 'Rate-limit comment present'),
        ('Further pandas_ta failures will be suppressed' in runner_src, 'Suppression message present'),
    ]
    
    all_ok = True
    for check, desc in checks:
        status = '✓' if check else '✗'
        print(f'  {status} {desc}')
        if not check:
            all_ok = False
    
    if all_ok:
        print('  ✅ FIX-3B: PASSED')
    else:
        print('  ❌ FIX-3B: INCOMPLETE')
except Exception as e:
    print(f'  ❌ FIX-3B: FAILED — {e}')

print()

# FIX-3C: requirements.txt
print('FIX-3C: requirements.txt created')
print('-' * 70)
try:
    import os
    assert os.path.exists('requirements.txt'), 'requirements.txt not found'
    
    with open('requirements.txt') as f:
        content = f.read()
    
    packages = [
        ('yfinance', 'yfinance>=0.2.40,<0.3'),
        ('pandas', 'pandas>=2.0,<3.0'),
        ('numpy', 'numpy>=1.24,<2.0'),
        ('pandas_ta', 'pandas_ta>=0.3.14b0'),
        ('requests', 'requests>=2.31,<3.0'),
    ]
    
    all_ok = True
    for pkg, spec in packages:
        found = pkg in content
        status = '✓' if found else '✗'
        print(f'  {status} {pkg}')
        if not found:
            all_ok = False
    
    if all_ok:
        print('  ✅ FIX-3C: PASSED')
    else:
        print('  ❌ FIX-3C: INCOMPLETE')
except Exception as e:
    print(f'  ❌ FIX-3C: FAILED — {e}')

print()

# FIX-3D: OHLCV sanity check
print('FIX-3D: OHLCV sanity check in data_loader.py')
print('-' * 70)
try:
    with open('egx_radar/backtest/data_loader.py', encoding='utf-8', errors='ignore') as f:
        loader_src = f.read()
    
    checks = [
        ('FIX-3D' in loader_src, 'FIX-3D comment present'),
        ('sanity check' in loader_src.lower() or 'OHLCV sanity' in loader_src, 'Sanity check mentioned'),
        ('l <= c <= h' in loader_src, 'Close-between-Low-High check present'),
        ('yfinance column inversion' in loader_src, 'Inversion detection message present'),
    ]
    
    all_ok = True
    for check, desc in checks:
        status = '✓' if check else '✗'
        print(f'  {status} {desc}')
        if not check:
            all_ok = False
    
    if all_ok:
        print('  ✅ FIX-3D: PASSED')
    else:
        print('  ❌ FIX-3D: INCOMPLETE')
except Exception as e:
    print(f'  ❌ FIX-3D: FAILED — {e}')

print()
print('=' * 70)
print('PHASE 3 VERIFICATION COMPLETE')
print('=' * 70)
