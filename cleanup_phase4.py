#!/usr/bin/env python
"""Clean up Phase 4 backups"""
import os

backup_files = [
    'egx_radar/backtest/engine.py.bak',
    'egx_radar/config/settings.py.bak',
]

for f in backup_files:
    if os.path.exists(f):
        os.remove(f)
        print(f'✓ Deleted: {f}')

print()
print('Phase 4 backups cleaned up.')
