#!/usr/bin/env python
"""Phase 1 diagnostic check"""
import sys
sys.path.insert(0, '.')

print('=== Phase 1 Critical Bug Verification ===')
print()

checks = [
    ('BUG-1  cpi=cpi_n present',   'egx_radar/backtest/engine.py', '"cpi": cpi_n',  True),
    ('BUG-3  flush=True absent',   'egx_radar/backtest/engine.py', 'flush=True',      False),
    ('BUG-4  cmf=cmf_val present', 'egx_radar/backtest/engine.py', '"cmf": cmf_val',  True),
]

all_clean = True
for label, path, pattern, should_exist in checks:
    try:
        path_win = path.replace('/', '\\')
        with open(path_win, encoding='utf-8', errors='ignore') as f:
            src = f.read()
        found = pattern in src
        ok    = (found == should_exist)
        if not ok:
            all_clean = False
        status = 'CLEAN' if ok else 'ISSUE'
        print(f'  {status} — {label}')
    except FileNotFoundError:
        print(f'  MISSING FILE — {path}')
        all_clean = False

print()
if all_clean:
    print('═══════════════════════════════════════════')
    print('Phase 1 status: ALL CLEAN')
    print('═══════════════════════════════════════════')
    print()
    print('Ready to proceed to Phase 2.')
    print('Type: /fix-phase2')
else:
    print('Phase 1 status: ISSUES DETECTED')
    print('Do not proceed until issues are resolved.')
