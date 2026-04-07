"""Create Telegram alert tables and add missing user columns safely."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from egx_radar.database.manager import DatabaseManager


def main() -> None:
    db = DatabaseManager()
    db.init_db()

    inspector = inspect(db.engine)
    user_columns = {col["name"] for col in inspector.get_columns("users")}
    required_columns = {
        "telegram_chat_id": "ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(64)",
        "telegram_connect_token": "ALTER TABLE users ADD COLUMN telegram_connect_token VARCHAR(128)",
        "telegram_connected_at": "ALTER TABLE users ADD COLUMN telegram_connected_at DATETIME",
    }

    added = []
    with db.engine.begin() as connection:
        for column_name, sql in required_columns.items():
            if column_name not in user_columns:
                connection.execute(text(sql))
                added.append(column_name)

    print("Telegram alert database setup complete.")
    print(f"Added user columns: {', '.join(added) if added else 'none'}")
    print("Table ready: telegram_alert_deliveries")


if __name__ == "__main__":
    main()
