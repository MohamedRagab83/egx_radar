import sys; sys.path.insert(0, '.')
from egx_radar.outcomes.engine import oe_load_history
from sqlalchemy import create_engine, text

print("=" * 80)
print("VERIFICATION: DB UPDATE FOR RESOLVED TRADES")
print("=" * 80)
print()

# Check JSON history
history = oe_load_history()
closed = [t for t in history if t.get('status') in ('WIN', 'LOSS', 'TIMEOUT')]

print("[1] Closed trades in JSON history:")
print("    Total: {} (with status WIN/LOSS/TIMEOUT)".format(len(closed)))
print()

for i, t in enumerate(closed[:5], 1):
    print("    {}. {} | {} | pnl={:+.2f}% | date={}".format(
        i, t.get('sym', '?').ljust(10), t.get('status', '?').ljust(8),
        t.get('pnl_pct', 0), t.get('resolved_date', '?')
    ))

print()
print("[2] Query database for resolved trades:")
print()

engine = create_engine('sqlite:///./egx_radar.db')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT id, symbol, entry_price, exit_price, result, pnl_pct, exit_date
        FROM trades 
        WHERE exit_price IS NOT NULL AND pnl_pct IS NOT NULL
        ORDER BY id
    '''))
    
    rows = result.fetchall()
    print("    Total records with exit_price AND pnl_pct: {}".format(len(rows)))
    print()
    
    for row in rows[:10]:
        record_id, sym, entry, exit_val, res, pnl, exit_date = row
        print("    id={} {} entry={:8.2f} exit={:8.2f} result={:>8} pnl_pct={:+7.2f}% exit={}".format(
            record_id, sym.ljust(10), entry, exit_val if exit_val else 0,
            res if res else "NULL", pnl if pnl else 0, str(exit_date)[:10] if exit_date else "NULL"
        ))

print()
print("=" * 80)
print("RESULT: Check if DB now has resolved trades with pnl_pct")
print("=" * 80)
