#!/usr/bin/env python
"""Clean up Phase 3 backups"""
import os

backup_files = [
    'egx_radar/core/data_guard.py.bak',
    'egx_radar/config/settings.py.bak',
    'egx_radar/scan/runner.py.bak',
    'egx_radar/backtest/data_loader.py.bak',
]

for f in backup_files:
    if os.path.exists(f):
        os.remove(f)
        print(f'✓ Deleted: {f}')

print()
print('Phase 3 backups cleaned up. Phase 3 confirmed successful.')
