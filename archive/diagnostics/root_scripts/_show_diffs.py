import sys
from difflib import unified_diff

print("=" * 80)
print("DIFF 1: egx_radar/database/manager.py")
print("=" * 80)
print()

with open('egx_radar/database/manager.py.bak') as f:
    original = f.readlines()

with open('egx_radar/database/manager.py') as f:
    updated = f.readlines()

diff = unified_diff(original, updated, lineterm='', fromfile='manager.py.bak', tofile='manager.py')
for line in list(diff)[:150]:  # Show first 150 lines of diff
    print(line)

print()
print()
print("=" * 80)
print("DIFF 2: egx_radar/outcomes/engine.py")
print("=" * 80)
print()

with open('egx_radar/outcomes/engine.py.bak') as f:
    original = f.readlines()

with open('egx_radar/outcomes/engine.py') as f:
    updated = f.readlines()

diff = unified_diff(original, updated, lineterm='', fromfile='engine.py.bak', tofile='engine.py')
for line in list(diff)[:200]:  # Show first 200 lines of diff
    print(line)
