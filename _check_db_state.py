import sys; sys.path.insert(0, '.')
from egx_radar.database.manager import DatabaseManager
from sqlalchemy import text

print('=============== ACTUAL DATABASE STATE ===============')
print()

engine = DatabaseManager().engine

with engine.connect() as conn:
    # Check all trades
    result = conn.execute(text('SELECT COUNT(*) FROM trades'))
    total = result.fetchone()[0]
    print(f'Total records in trades table: {total}')
    
    # Check trades with result set
    result = conn.execute(text('SELECT COUNT(*) FROM trades WHERE result IS NOT NULL'))
    resolved = result.fetchone()[0]
    print(f'Trades with result NOT NULL: {resolved}')
    
    # Check trades with pnl_pct set
    result = conn.execute(text('SELECT COUNT(*) FROM trades WHERE pnl_pct IS NOT NULL'))
    with_pnl = result.fetchone()[0]
    print(f'Trades with pnl_pct NOT NULL: {with_pnl}')
    
    print()
    print('Record details (all trades):')
    result = conn.execute(text('''
        SELECT id, symbol, entry_price, exit_price, result, pnl_pct, exit_date
        FROM trades
        ORDER BY id
    '''))
    
    for i, row in enumerate(result.fetchall(), 1):
        record_id, sym, entry, exit_val, res, pnl, exit_date = row
        print(f'  {i}. {sym:10} entry={entry:8.2f} exit={exit_val or "NULL":>8} result={res or "NULL":>8} pnl={pnl or "NULL":>8} exit_date={exit_date or "NULL"}')
