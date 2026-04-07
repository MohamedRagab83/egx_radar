import sys; sys.path.insert(0, '.')
from egx_radar.database.manager import DatabaseManager
db = DatabaseManager()
with db.get_session() as session:
    from egx_radar.database.models import Trade
    trades = session.query(Trade).filter(
        Trade.result.isnot(None)
    ).limit(10).all()
    print(f'Resolved trades in DB: {len(trades)}')
    for t in trades:
        print(f'  {t.symbol} | {t.result} | pnl={t.pnl_pct} | exit={t.exit_date}')
