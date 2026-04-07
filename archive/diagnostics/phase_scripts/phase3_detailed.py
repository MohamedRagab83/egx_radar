#!/usr/bin/env python
"""Phase 3 Detailed Diagnostic"""
import sys
import os
sys.path.insert(0, '.')

print('=' * 70)
print('PHASE 3 — DETAILED ACTION PLAN')
print('=' * 70)
print()

# FIX-3A detailed
print('FIX-3A: Trading-day-aware staleness check')
print('-' * 70)
print('File: egx_radar/core/data_guard.py')
print()
print('ACTION: Add _egx_trading_days_since() function')
print('  - Takes a date, returns count of EGX trading days (Sun-Thu) since that date')
print('  - Accounts for public holidays with a 1-day/week buffer')
print()
print('THEN: Update evaluate() method')
print('  - Replace calendar-day lag check with trading-day lag check')
print('  - Use: trading_lag = _egx_trading_days_since(last_date)')
print()
print('UPDATE settings: DG_MAX_DATA_LAG_DAYS = 3 (trading days, not 4)')
print()

# FIX-3B detailed
print('FIX-3B: Thread-safety logging for pandas_ta')
print('-' * 70)
print('File: egx_radar/ui/scan_runner.py (or equivalent)')
print()
print('ACTION: Find except block that silently handles pandas_ta failures')
print('  - Currently sets adx_val=0.0, rsi_val=50.0 with no log')
print('  - Add rate-limited warning log')
print('  - Limit to 3 failures, then suppress subsequent failures')
print()

# FIX-3C detailed
print('FIX-3C: Create requirements.txt')
print('-' * 70)
print('LOCATION: Project root (d:\\egx radar seprated\\requirements.txt)')
print()
print('FILE CONTENTS:')
print('  - yfinance>=0.2.40,<0.3')
print('  - pandas>=2.0,<3.0')
print('  - numpy>=1.24,<2.0')
print('  - pandas_ta>=0.3.14b0  (with warning about thread-safety)')
print('  - requests>=2.31,<3.0')
print()

# FIX-3D detailed
print('FIX-3D: OHLCV sanity check')
print('-' * 70)
print('Files: egx_radar/data/fetchers.py and egx_radar/backtest/data_loader.py')
print()
print('ACTION: Add sanity check at end of _flatten() function')
print('  - Verify Close is between Low and High on last bar')
print('  - If not, log warning and return None (reject bad data)')
print('  - Catches silent yfinance API inversions')
print()

# Check for scan_runner
print('FILE INVENTORY CHECK:')
print('-' * 70)
ui_files = []
for root, dirs, files in os.walk('egx_radar/ui'):
    for f in files:
        if f.endswith('.py'):
            ui_files.append(f)

print(f'UI files found: {", ".join(sorted(ui_files))}')
if 'scan_runner.py' not in ui_files:
    print('  ⚠️  scan_runner.py not found, checking for scanner modules...')
    for f in ui_files:
        if 'scan' in f.lower() or 'runner' in f.lower():
            print(f'    Found: {f}')

print()
print('=' * 70)
