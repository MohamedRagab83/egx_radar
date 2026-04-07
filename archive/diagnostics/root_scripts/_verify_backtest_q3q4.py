#!/usr/bin/env python
"""
VERIFICATION 3: Backtest with wider date range
"""
import sys, math
sys.path.insert(0, '.')

print()
print('=' * 80)
print('VERIFICATION 3: Backtest Regression (2024 Q3-Q4)')
print('=' * 80)
print()

from egx_radar.backtest.engine  import run_backtest
from egx_radar.backtest.metrics import compute_metrics

print('Running backtest on 2024-07-01 to 2024-12-31 (max_bars=20)...')
print()

try:
    result = run_backtest('2024-07-01', '2024-12-31', max_bars=20)
    
    if len(result) == 4:
        trades, equity, _, guards = result
    elif len(result) == 3:
        trades, equity, _ = result
        guards = {}
    else:
        trades, equity = result
        guards = {}
    
    print(f'Backtest completed.')
    print(f'  Trades generated: {len(trades)}')
    print(f'  Equity points: {len(equity)}')
    
    # Check for NaN in equity
    nan_count = sum(1 for _, v in equity if not math.isfinite(v))
    print(f'  NaN values in equity: {nan_count}')
    
    if len(trades) >= 3:
        m = compute_metrics(trades)['overall']
        print()
        print('Metrics:')
        print(f'  Win Rate: {m["win_rate_pct"]:.2f}%')
        print(f'  Sharpe Ratio: {m["sharpe_ratio"]:.4f}')
        print(f'  Max Drawdown: {m["max_drawdown_pct"]:.2f}%')
        print(f'  Total Return: {m["total_return_pct"]:.2f}%')
        print(f'  Profit Factor: {m["profit_factor"]:.2f}')
        
        # Verify regression
        ok = (0 <= m['win_rate_pct'] <= 100 and 
              math.isfinite(m['sharpe_ratio']) and 
              nan_count == 0)
        
        print()
        if ok:
            print('✓ REGRESSION TEST PASSED')
            print('  All checks passed:')
            print(f'    - Win rate in valid range: {0 <= m["win_rate_pct"] <= 100}')
            print(f'    - Sharpe ratio is finite: {math.isfinite(m["sharpe_ratio"])}')
            print(f'    - No NaN in equity: {nan_count == 0}')
        else:
            print('✗ REGRESSION TEST FAILED')
            print(f'  Win rate valid: {0 <= m["win_rate_pct"] <= 100}')
            print(f'  Sharpe finite: {math.isfinite(m["sharpe_ratio"])}')
            print(f'  No NaN: {nan_count == 0}')
    else:
        print()
        print(f'{len(trades)} trades generated (need >= 3 for metrics)')
        print(f'Guards triggered: {guards}')
        print('REGRESSION: INCONCLUSIVE - insufficient trade data')
        
except Exception as e:
    print(f'✗ ERROR: {e}')
    import traceback
    traceback.print_exc()
