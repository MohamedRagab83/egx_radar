#!/usr/bin/env python
"""Create Phase 4 backup"""
import shutil
import os

files_to_backup = [
    'egx_radar/backtest/engine.py',
    'egx_radar/config/settings.py',
]

for fpath in files_to_backup:
    if os.path.exists(fpath):
        shutil.copy(fpath, fpath + '.bak')
        print(f'✓ Backed up: {fpath}')

print()
print('Phase 4 backups created.')
