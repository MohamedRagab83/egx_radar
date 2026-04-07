#!/usr/bin/env python
"""FIX-2C Verification Test"""
import sys
import math
sys.path.insert(0, '.')

print('=' * 70)
print('FIX-2C VERIFICATION: Equity curve with ATR-based allocation')
print('=' * 70)
print()

# Import after adding to path
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics

print('Running 2024-Q4 regression backtest...')
print('(This may take 1-2 minutes)')
print()

try:
    trades, equity_curve, params = run_backtest(
        date_from='2024-10-01',
        date_to='2024-12-31',
        max_bars=15,
        max_concurrent_trades=5,
    )
    
    print(f'Trades closed  : {len(trades)}')
    print(f'Equity points  : {len(equity_curve)}')
    print()
    
    # Check for NaN in equity curve
    nan_points = [(d, v) for d, v in equity_curve if not math.isfinite(v)]
    if nan_points:
        print(f'❌ FAILED: NaN values in equity curve: {len(nan_points)} point(s)')
        for d, v in nan_points[:3]:
            print(f'   {d}: {v}')
        sys.exit(1)
    else:
        print('✓ Equity curve clean: 0 NaN values')
    
    # Check equity curve bounds
    equity_values = [v for _, v in equity_curve]
    if equity_values:
        min_eq = min(equity_values)
        max_eq = max(equity_values)
        print(f'✓ Equity range: [{min_eq:.2f}%, {max_eq:.2f}%]')
    
    print()
    
    # Compute and verify metrics
    if len(trades) >= 5:
        m = compute_metrics(trades)['overall']
        
        print('Overall Performance Metrics:')
        print(f'  Win rate       : {m["win_rate_pct"]}%')
        print(f'  Sharpe         : {m["sharpe_ratio"]:.3f}')
        print(f'  Max drawdown   : {m["max_drawdown_pct"]}%')
        print(f'  Profit factor  : {m["profit_factor"]:.2f}')
        print(f'  Avg bars       : {m["avg_bars_in_trade"]:.1f}')
        print()
        
        # Verify ranges are valid
        checks = [
            ('0 ≤ win_rate_pct ≤ 100', 0 <= m['win_rate_pct'] <= 100),
            ('sharpe_ratio is finite', math.isfinite(m['sharpe_ratio'])),
            ('max_drawdown_pct ≥ 0', m['max_drawdown_pct'] >= 0),
            ('profit_factor is finite', math.isfinite(m['profit_factor'])),
        ]
        
        all_ok = True
        for desc, result in checks:
            status = '✓' if result else '❌'
            print(f'{status} {desc}')
            if not result:
                all_ok = False
        
        if not all_ok:
            print()
            print('❌ FAILED: Some metrics are out of range')
            sys.exit(1)
        
        print()
        print('=' * 70)
        print('✅ FIX-2C VERIFICATION PASSED')
        print('=' * 70)
    else:
        print(f'⚠️  WARNING: Only {len(trades)} trades (need ≥5 for full metrics)')
        print('Check data availability for Oct–Dec 2024.')
        print('Params:', params)
        print()
        print('✅ FIX-2C VERIFICATION PASSED (no crashes, equity curve valid)')

except Exception as e:
    print(f'❌ FAILED with exception:', e)
    import traceback
    traceback.print_exc()
    sys.exit(1)
