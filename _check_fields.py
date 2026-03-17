import sys; sys.path.insert(0, '.')
from egx_radar.outcomes.engine import oe_load_history
history = oe_load_history()
print(f'Total trades in history: {len(history)}')
print()
if history:
    print('Fields in first trade:')
    first = history[0]
    for key in sorted(first.keys()):
        print(f'  {key}: {first[key]}')
    print()
    print('Checking "status" field (should be WIN/LOSS/TIMEOUT):')
    closed = [t for t in history if t.get('status') in ('WIN', 'LOSS', 'TIMEOUT')]
    print(f'Trades with status WIN/LOSS/TIMEOUT: {len(closed)}')
