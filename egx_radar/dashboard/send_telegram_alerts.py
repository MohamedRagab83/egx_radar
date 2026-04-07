"""Dispatch Telegram alerts for the latest scanner snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from egx_radar.dashboard.app import create_app
from egx_radar.dashboard.telegram_service import dispatch_latest_snapshot_alerts


def main() -> None:
    app = create_app("development")
    with app.app_context():
        summary = dispatch_latest_snapshot_alerts(app.db_manager)
    print(summary)


if __name__ == "__main__":
    main()
