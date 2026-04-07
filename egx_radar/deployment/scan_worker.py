"""Headless scan worker for Railway.

Runs the existing scanner on a timer, persists the latest scan snapshot into
ScanRun/ScanSignal rows, and relies on the existing post-scan Telegram
dispatch already wired inside egx_radar.scan.runner.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

from egx_radar.database import DatabaseManager
from egx_radar.database.models import ScanRun, ScanSignal
from egx_radar.dashboard.telegram_service import load_latest_snapshot
from egx_radar.scan import runner


log = logging.getLogger(__name__)


class _DummyValue:
    def set(self, *args, **kwargs) -> None:
        return None

    def configure(self, *args, **kwargs) -> None:
        return None

    def get(self):
        return False

    def delete(self, *args, **kwargs) -> None:
        return None

    def insert(self, *args, **kwargs) -> None:
        return None

    def get_children(self):
        return []


def _build_headless_widgets() -> Dict[str, Any]:
    dummy = _DummyValue()
    return {
        "tree": dummy,
        "pbar": dummy,
        "status_var": dummy,
        "gauge_rank": dummy,
        "gauge_flow": dummy,
        "heat_labels": {},
        "rot_labels": {},
        "flow_labels": {},
        "regime_lbl": dummy,
        "brain_lbl": dummy,
        "verdict_var": dummy,
        "verdict_frm": dummy,
        "verdict_lbl_w": dummy,
        "scan_btn": dummy,
        "guard_sector_labels": {},
        "guard_exposure_lbl": dummy,
        "guard_blocked_lbl": dummy,
        "force_refresh_var": dummy,
        "health_avg_var": dummy,
        "health_act_var": dummy,
        "health_elite_var": dummy,
        "health_sell_var": dummy,
        "health_lbl": dummy,
    }


def _noop_enqueue(*args, **kwargs) -> None:
    return None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_scan_time(snapshot: list[dict]) -> datetime:
    if not snapshot:
        return datetime.utcnow()
    raw = snapshot[0].get("scan_time")
    if not raw:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return datetime.utcnow()


def _normalize_trade_type(row: dict) -> str:
    explicit = str(row.get("trade_type") or "").strip().upper()
    if explicit:
        return explicit

    action = str(row.get("action") or "").strip().upper()
    if action == "ACCUMULATE":
        return "STRONG"
    if action == "PROBE":
        return "MEDIUM"
    if action == "WAIT":
        return "SKIP"
    return "UNCLASSIFIED"


def persist_latest_snapshot(db_manager: DatabaseManager) -> dict:
    snapshot = load_latest_snapshot()
    scan_time = _parse_scan_time(snapshot)

    with db_manager.get_session() as session:
        scan_run = ScanRun(timestamp=scan_time)
        session.add(scan_run)
        session.flush()

        for row in snapshot:
            symbol = str(row.get("sym") or row.get("symbol") or "").strip().upper()
            if not symbol:
                continue

            session.add(ScanSignal(
                scan_run_id=scan_run.id,
                symbol=symbol,
                smart_rank=_to_float(row.get("smart_rank")),
                trade_type=_normalize_trade_type(row),
                entry=_to_float(row.get("entry"), None),
                stop=_to_float(row.get("stop"), None),
                target=_to_float(row.get("target"), None),
            ))

    return {
        "scan_time": scan_time.isoformat(),
        "signals_saved": len(snapshot),
    }


def run_scan_cycle(db_manager: DatabaseManager) -> dict:
    runner._enqueue = _noop_enqueue
    widgets = _build_headless_widgets()
    runner.run_scan(widgets)
    return persist_latest_snapshot(db_manager)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EGX Radar cloud scan worker.")
    parser.add_argument("--once", action="store_true", help="Run one scan cycle, then exit.")
    parser.add_argument(
        "--persist-only",
        action="store_true",
        help="Do not run a new scan. Persist the latest scan_snapshot.json to the database and exit.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=os.environ.get("EGX_RADAR_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not os.environ.get("DATABASE_URL") and not os.environ.get("DB_TYPE"):
        raise RuntimeError("DATABASE_URL is required for the scan worker")

    interval_minutes = max(int(os.environ.get("SCAN_INTERVAL_MINUTES", "10")), 1)
    db_manager = DatabaseManager()
    db_manager.init_db()

    while True:
        try:
            if args.persist_only:
                summary = persist_latest_snapshot(db_manager)
                log.info("Persisted latest snapshot | signals=%s | scan_time=%s", summary["signals_saved"], summary["scan_time"])
                return

            summary = run_scan_cycle(db_manager)
            log.info("Scan cycle complete | signals=%s | scan_time=%s", summary["signals_saved"], summary["scan_time"])
        except Exception:
            log.exception("Scan worker cycle failed")

        if args.once:
            return

        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()
