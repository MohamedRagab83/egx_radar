#!/usr/bin/env python
"""Phase 3 Diagnostic Scan — Data Infrastructure & Resilience"""
import sys
import os
sys.path.insert(0, '.')

print('=' * 70)
print('PHASE 3 — Data Infrastructure & Resilience — DIAGNOSTIC SCAN')
print('=' * 70)
print()

# FIX-3A
print('FIX-3A: Trading-day-aware staleness check')
print('-' * 70)
try:
    with open('egx_radar/core/data_guard.py', encoding='utf-8', errors='ignore') as f:
        dg_src = f.read()
    
    has_egx_trading_days = '_egx_trading_days_since' in dg_src
    if has_egx_trading_days:
        print('  ✓ Function _egx_trading_days_since found')
    else:
        print('  ✗ Function _egx_trading_days_since NOT found — needs to be added')
    
    has_trading_lag = 'trading_lag' in dg_src
    if has_trading_lag:
        print('  ✓ Trading lag variable found in evaluate()')
    else:
        print('  ✗ Trading lag NOT found — staleness check still uses calendar days')
    
    has_dg_max_lag = 'DG_MAX_DATA_LAG_DAYS' in dg_src
    if has_dg_max_lag:
        print('  ✓ DG_MAX_DATA_LAG_DAYS constant exists in settings')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('FIX-3B: Thread-safety logging for pandas_ta failures')
print('-' * 70)
try:
    import subprocess
    for path in ['egx_radar/ui/scan_runner.py', 'egx_radar/ui/main_window.py']:
        if os.path.exists(path):
            with open(path, encoding='utf-8', errors='ignore') as f:
                src = f.read()
            
            has_rate_limited_logging = 'Rate-limit' in src or '_fail_count' in src
            if path == 'egx_radar/ui/scan_runner.py':
                has_pta_try = 'pandas_ta' in src and 'except Exception' in src
                if has_pta_try:
                    print(f'  ✓ {path}: Has pandas_ta try block')
                    if has_rate_limited_logging:
                        print(f'    ✓ Rate-limited logging already in place')
                    else:
                        print(f'    ✗ Logging not rate-limited — needs improvement')
                else:
                    print(f'  ✗ {path}: No pandas_ta exception handling found')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('FIX-3C: requirements.txt')
print('-' * 70)
req_exists = os.path.exists('requirements.txt')
if req_exists:
    print('  ✓ requirements.txt exists')
    with open('requirements.txt') as f:
        content = f.read()
    checks = [
        ('yfinance', 'yfinance' in content),
        ('pandas', 'pandas' in content),
        ('numpy', 'numpy' in content),
        ('pandas_ta', 'pandas_ta' in content),
    ]
    for pkg, found in checks:
        status = '✓' if found else '✗'
        print(f'    {status} {pkg}')
else:
    print('  ✗ requirements.txt NOT found — needs to be created')

print()
print('FIX-3D: OHLCV sanity check in _flatten')
print('-' * 70)
try:
    with open('egx_radar/data/fetchers.py', encoding='utf-8', errors='ignore') as f:
        fetchers_src = f.read()
    
    has_sanity_check = 'sanity' in fetchers_src.lower() or 'High.*Low.*Close' in fetchers_src or 'OHLCV' in fetchers_src
    if has_sanity_check:
        print('  ✓ OHLCV sanity check appears to be in place in fetchers.py')
    else:
        print('  ✗ No OHLCV sanity check found in fetchers.py — needs to be added')
except Exception as e:
    print(f'  ERROR: {e}')

try:
    with open('egx_radar/backtest/data_loader.py', encoding='utf-8', errors='ignore') as f:
        loader_src = f.read()
    
    has_sanity_check = 'sanity' in loader_src.lower() or 'High.*Low.*Close' in loader_src
    if has_sanity_check:
        print('  ✓ OHLCV sanity check appears to be in place in data_loader.py')
    else:
        print('  ✗ No OHLCV sanity check found in data_loader.py — needs to be added')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('=' * 70)
print('DIAGNOSTIC COMPLETE')
print('=' * 70)
