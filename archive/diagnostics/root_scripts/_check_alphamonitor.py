import sys; sys.path.insert(0, '.')
from sqlalchemy import create_engine, text
import json
from datetime import datetime

print("-" * 80)
print("STEP 1: oe_record_signal() and pnl_pct in DB")
print("-" * 80)
print()

# Read the oe_record_signal function to check if it writes pnl_pct
with open('egx_radar/outcomes/engine.py') as f:
    content = f.read()
    
# Find the function
start = content.find('def oe_record_signal(')
end = content.find('\ndef ', start + 1)
func = content[start:end]

# Check for pnl_pct writes
if 'pnl_pct' in func and 'db.save_trade_signal' in func:
    lines = func.split('\n')
    for i, line in enumerate(lines[-30:], 1):
        print(f"  {line}")
else:
    print("[NOTE] oe_record_signal() writes entry signal to DB ONLY")
    print("       pnl_pct is written LATER by oe_resolve_trade() at resolution time")
    print("       oe_save_history_batch() saves to JSON, but NOT to DB at resolution time")

print()
print("-" * 80)
print("STEP 2: Query SQLite - SELECT status, pnl_pct, result FROM trades")
print("-" * 80)
print()

engine = create_engine('sqlite:///./egx_radar.db')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT id, symbol, entry_signal, entry_price, exit_price, result, pnl_pct 
        FROM trades 
        ORDER BY id
    '''))
    
    rows = result.fetchall()
    print("Total records: {}".format(len(rows)))
    print()
    
    for row in rows:
        record_id, sym, signal, entry, exit_val, res, pnl = row
        print("  id={} sym={:10} signal={:10} entry={:8.2f} exit={:>8} result={:>8} pnl_pct={}".format(
            record_id, sym, signal, entry, 
            "{:.2f}".format(exit_val) if exit_val else "NULL",
            res if res else "NULL",
            "{:.2f}".format(pnl) if pnl else "NULL"
        ))

print()
print("-" * 80)
print("STEP 3: Check trades_history.json - show last 5 resolved trades")
print("-" * 80)
print()

with open('trades_history.json') as f:
    history = json.load(f)

print("Total resolved trades in JSON: {}".format(len(history)))
print()
print("Last 5 trades:")
print()

for i, trade in enumerate(history[-5:], 1):
    sym = trade.get('sym', '?')
    status = trade.get('status', '?')
    entry = trade.get('entry', 0.0)
    exit_p = trade.get('exit_price', '?')
    pnl = trade.get('pnl_pct', '?')
    days = trade.get('days_held', '?')
    
    print("  {}. {} {} entry={:7.2f} exit={:>7} pnl_pct={:>7} days={}".format(
        i, sym.ljust(10), status.ljust(8), entry,
        "{:.2f}".format(exit_p) if isinstance(exit_p, (int, float)) else "NULL",
        "{:.2f}".format(pnl) if isinstance(pnl, (int, float)) else "NULL",
        days
    ))

print()
print("-" * 80)
print("STEP 4: Count real CLOSED trades with pnl_pct")
print("-" * 80)
print()

# Count JSON resolved trades with pnl_pct
json_closed = [t for t in history if t.get('pnl_pct') is not None and isinstance(t.get('pnl_pct'), (int, float))]
print("Resolved trades in trades_history.json: {} (with real pnl_pct)".format(len(json_closed)))

# Count DB closed trades with pnl_pct
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM trades WHERE pnl_pct IS NOT NULL'))
    db_closed = result.fetchone()[0]

print("Resolved trades in SQLite DB: {} (with pnl_pct NOT NULL)".format(db_closed))

print()
print("SUMMARY:")
print("  JSON history: {} trades with real pnl_pct".format(len(json_closed)))
print("  SQLite DB   : {} trades with real pnl_pct".format(db_closed))

if db_closed == 0:
    print()
    print("  >> DATABASE IS NOT BEING UPDATED AT TRADE RESOLUTION TIME")
    print("  >> DB only receives initial entry signal, never the exit/outcome")
    print("  >> oe_process_open_trades() calls oe_save_history_batch() [JSON]")
    print("  >> but does NOT call db.save_resolved_trade() [database]")
