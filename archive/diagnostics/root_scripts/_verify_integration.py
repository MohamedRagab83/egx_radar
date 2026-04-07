#!/usr/bin/env python
import sys, math
sys.path.insert(0, '.')

print()
print('=' * 80)
print('VERIFICATION 2: Integration Gaps Status')
print('=' * 80)
print()

import os

GAPS = {
    'GAP-1: API → Scanner': {
        'file': 'egx_radar/dashboard/routes.py',
        'markers': ['_load_scan_snapshot', '/signals/scanner', 'get_scanner_signals()'],
    },
    'GAP-2: Outcomes → Database': {
        'file': 'egx_radar/outcomes/engine.py',
        'markers': ['_db_manager', '_get_db_manager', 'save_trade_signal'],
    },
    'GAP-3: WebSocket → Scanner': {
        'file': 'egx_radar/dashboard/websocket.py',
        'markers': ['scan_complete', 'emit_scan_complete'],
    },
    'GAP-4: market_data → Scanner': {
        'file': 'egx_radar/market_data/signals.py',
        'markers': ['smart_rank_score', 'build_signal'],
    },
}

closed_count = 0
for gap_name, cfg in GAPS.items():
    f = cfg['file']
    if not os.path.exists(f):
        print(f'  ??  {gap_name}: file not found')
        continue
    
    content = open(f, encoding='utf-8', errors='ignore').read()
    found = sum(1 for marker in cfg['markers'] if marker in content)
    total = len(cfg['markers'])
    
    if found == total:
        status = 'CLOSED'
        closed_count += 1
        detail = f'({found}/{total} markers found)'
    elif found > 0:
        status = 'PARTIAL'
        detail = f'({found}/{total} markers found)'
    else:
        status = 'OPEN'
        detail = f'(0/{total} markers found)'
    
    print(f'  {status:8}  {gap_name:<35}  {detail}')

print()
print(f'RESULT: {closed_count} gaps CLOSED, {4-closed_count} pending')
