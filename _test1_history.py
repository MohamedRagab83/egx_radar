import sys; sys.path.insert(0, '.')
from egx_radar.outcomes.engine import oe_load_history
history = oe_load_history()
closed = [t for t in history if t.get('outcome') in ('WIN','LOSS','EXIT')]
print(f'Closed trades in history: {len(closed)}')
for t in closed[:5]:
    print(f'  {t.get("sym")} | {t.get("outcome")} | pnl={t.get("pnl_pct")} | date={t.get("exit_date")}')
