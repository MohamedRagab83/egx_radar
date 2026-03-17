#!/usr/bin/env python
"""Phase 2 diagnostic scan"""
import sys
import inspect
import os
sys.path.insert(0, '.')

print('=' * 60)
print('PHASE 2 — Signal & Metric Consistency — DIAGNOSTIC SCAN')
print('=' * 60)
print()

print('=== FIX-2A: score_capital_pressure signature ===')
try:
    from egx_radar.core.scoring import score_capital_pressure
    params = list(inspect.signature(score_capital_pressure).parameters.keys())
    print(f'  Parameters ({len(params)}): {params}')
    if len(params) == 6:
        print('  STATUS: 6 params — needs ud_ratio, is_vcp added')
    elif len(params) == 8:
        print('  STATUS: ✓ 8 params — signature is complete')
    else:
        print(f'  STATUS: unexpected count ({len(params)}) — investigate')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('=== FIX-2A: call sites of score_capital_pressure ===')
try:
    path = 'egx_radar/backtest/engine.py'
    with open(path, encoding='utf-8', errors='ignore') as f:
        engine_src = f.read()
    
    call_lines = [line.strip() for line in engine_src.split('\n') 
                  if 'score_capital_pressure(' in line]
    print(f'  Found {len(call_lines)} call site(s) in backtest/engine.py:')
    for line in call_lines[:3]:
        print(f'    {line[:80]}...' if len(line) > 80 else f'    {line}')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('=== FIX-2B: Sharpe formula in alpha_monitor.py ===')
try:
    path = 'egx_radar/core/alpha_monitor.py'
    with open(path, encoding='utf-8', errors='ignore') as f:
        am_src = f.read()
    
    has_trades_per_year = 'trades_per_year' in am_src
    has_annuali = 'annuali' in am_src.lower()
    
    if has_trades_per_year or has_annuali:
        print('  ✓ Sharpe appears to be annualised')
        sharpe_lines = [line.strip() for line in am_src.split('\n')
                       if 'sharpe' in line.lower() and ('trades_per_year' in line or 'annuali' in line.lower())]
        for line in sharpe_lines[:2]:
            print(f'    {line[:80]}...' if len(line) > 80 else f'    {line}')
    else:
        print('  ✗ Sharpe may NOT be annualised (no trades_per_year found)')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('=== FIX-2B: Sharpe formula in backtest/metrics.py ===')
try:
    path = 'egx_radar/backtest/metrics.py'
    with open(path, encoding='utf-8', errors='ignore') as f:
        metrics_src = f.read()
    
    has_trades_per_year = 'trades_per_year' in metrics_src
    if has_trades_per_year:
        print('  ✓ Sharpe appears to be annualised in backtest/metrics.py')
        sharpe_lines = [line.strip() for line in metrics_src.split('\n')
                       if 'sharpe' in line.lower() and 'trades_per_year' in line]
        for line in sharpe_lines[:2]:
            print(f'    {line[:80]}...' if len(line) > 80 else f'    {line}')
    else:
        print('  (checking for standalone Sharpe computation)')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('=== FIX-2C: equity curve sizing in backtest/engine.py ===')
try:
    path = 'egx_radar/backtest/engine.py'
    with open(path, encoding='utf-8', errors='ignore') as f:
        engine_src = f.read()
    
    equity_lines = [line.strip() for line in engine_src.split('\n')
                   if 'equity *=' in line or ('equity' in line and '+' in line and '%' in line)]
    if equity_lines:
        print(f'  Found {len(equity_lines)} equity sizing line(s):')
        for line in equity_lines[:3]:
            print(f'    {line[:80]}...' if len(line) > 80 else f'    {line}')
    else:
        print('  (no explicit equity *= lines found)')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('=' * 60)
print('DIAGNOSTIC FINDINGS:')
print('=' * 60)
print('Before making any edits, verify the findings above.')
