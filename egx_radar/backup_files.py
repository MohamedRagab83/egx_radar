#!/usr/bin/env python3
"""Backup script to copy core files."""
import shutil
import os

files_to_backup = [
    (r'd:\egx radar seprated\egx_radar\core\scoring.py', r'd:\egx radar seprated\egx_radar\core\scoring.py.bak'),
    (r'd:\egx radar seprated\egx_radar\core\signals.py', r'd:\egx radar seprated\egx_radar\core\signals.py.bak'),
    (r'd:\egx radar seprated\egx_radar\core\__init__.py', r'd:\egx radar seprated\egx_radar\core\__init__.py.bak'),
]

print("Creating backups...")
print("-" * 60)

all_successful = True
for src, dst in files_to_backup:
    try:
        shutil.copy2(src, dst)
        if os.path.exists(dst):
            print(f"✓ {os.path.basename(dst)} - copied successfully")
        else:
            print(f"✗ {os.path.basename(dst)} - FAILED (file not found)")
            all_successful = False
    except FileNotFoundError:
        print(f"✗ {os.path.basename(src)} - SOURCE FILE NOT FOUND")
        all_successful = False
    except Exception as e:
        print(f"✗ Error copying {os.path.basename(src)}: {e}")
        all_successful = False

print("-" * 60)
if all_successful:
    print("All backups created successfully!")
else:
    print("Some backups failed. See errors above.")
