import sys; sys.path.insert(0, '.')
from sqlalchemy import create_engine, inspect, text

try:
    engine = create_engine('sqlite:///./egx_radar.db')
    print('[OK] Engine created')
    
    # Get table information
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print('=== SQLite Database Tables ===')
    print(f'Tables: {tables}')
    print()
    
    # Show Trade table schema
    if 'trades' in tables:
        print('=== Trades Table Schema ===')
        columns = inspector.get_columns('trades')
        for col in columns:
            print(f'  {col["name"]:25} {str(col["type"]):20}')
        print()
        print('=== Trades Table Content ===')
        with engine.connect() as conn:
            result = conn.execute(text('SELECT COUNT(*) as cnt FROM trades'))
            cnt = result.fetchone()[0]
            print(f'Total records: {cnt}')
            print()
            result = conn.execute(text('SELECT * FROM trades LIMIT 15'))
            rows = result.fetchall()
            cols = list(result.keys())
            print(f'Columns: {cols}')
            print()
            for i, row in enumerate(rows, 1):
                d = dict(zip(cols, row))
                print(f'{i:2}. {d}')
    else:
        print('ERROR: trades table not found in database')
        print(f'Available tables: {tables}')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
