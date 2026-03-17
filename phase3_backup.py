#!/usr/bin/env python
"""Create Phase 3 backups"""
import shutil
import os

files_to_backup = [
    'egx_radar/core/data_guard.py',
    'egx_radar/config/settings.py',
    'egx_radar/scan/runner.py',
    'egx_radar/backtest/data_loader.py',
]

for fpath in files_to_backup:
    if os.path.exists(fpath):
        shutil.copy(fpath, fpath + '.bak')
        print(f'✓ Backed up: {fpath}')
    else:
        print(f'✗ Not found: {fpath}')

print()
print('All Phase 3 backups created.')
