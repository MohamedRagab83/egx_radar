"""Small Telegram integration helpers for the SaaS dashboard."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests

from egx_radar.database.models import TelegramAlertDelivery, User


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def get_bot_username() -> str:
    return os.environ.get("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")


def telegram_ready() -> bool:
    return bool(get_bot_token())


def _telegram_api(method: str, params: Optional[Dict[str, Any]] = None, http_method: str = "GET") -> Dict[str, Any]:
    token = get_bot_token()
    if not token:
        return {"ok": False, "description": "Missing TELEGRAM_BOT_TOKEN"}

    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if http_method.upper() == "POST":
            response = requests.post(url, json=params or {}, timeout=20)
        else:
            response = requests.get(url, params=params or {}, timeout=20)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"ok": False, "description": "Invalid Telegram response"}
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


def ensure_connect_token(db_manager, user_id: int) -> str:
    with db_manager.get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            return ""
        if not user.telegram_connect_token:
            user.telegram_connect_token = secrets.token_urlsafe(16)
            session.add(user)
        return user.telegram_connect_token or ""


def build_connect_url(token: str) -> str:
    username = get_bot_username()
    if not username or not token:
        return ""
    return f"https://t.me/{username}?start={token}"


def _extract_start_token(update: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    text = str(message.get("text") or "").strip()
    if not text.startswith("/start"):
        return None, None
    parts = text.split(maxsplit=1)
    token = parts[1].strip() if len(parts) > 1 else ""
    chat_id = str(chat.get("id")) if chat.get("id") is not None else None
    return token or None, chat_id


def connect_user_from_telegram_updates(db_manager, user_id: int) -> bool:
    with db_manager.get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None or not user.telegram_connect_token:
            return False
        connect_token = user.telegram_connect_token

    updates = _telegram_api("getUpdates")
    for update in reversed(updates.get("result", [])):
        token, chat_id = _extract_start_token(update)
        if token == connect_token and chat_id:
            with db_manager.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user is None:
                    return False
                user.telegram_chat_id = chat_id
                user.telegram_connected_at = _utc_now_naive()
                user.telegram_connect_token = None
                session.add(user)
            return True
    return False


def send_telegram_message(chat_id: str, text: str) -> bool:
    if not chat_id:
        return False
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    result = _telegram_api("sendMessage", payload, http_method="POST")
    return bool(result.get("ok"))


def send_test_message(db_manager, user_id: int) -> bool:
    with db_manager.get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None or not user.telegram_chat_id:
            return False
        return send_telegram_message(
            user.telegram_chat_id,
            "EGX Radar test alert\n\nYour Telegram connection is working.",
        )


def _snapshot_path() -> Path:
    from egx_radar.config.settings import K

    return Path(os.path.dirname(K.OUTCOME_LOG_FILE)) / "scan_snapshot.json"


def load_latest_snapshot() -> list[dict]:
    path = _snapshot_path()
    if not path.exists():
        return []
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _format_signal_message(signal: Dict[str, Any]) -> str:
    return (
        "EGX Radar Alert\n\n"
        f"Symbol: {signal.get('sym')}\n"
        f"SmartRank: {float(signal.get('smart_rank') or 0.0):.2f}\n"
        f"Entry: {signal.get('entry')}\n"
        f"Stop: {signal.get('stop')}\n"
        f"Target: {signal.get('target')}"
    )


def _eligible_snapshot_signals(snapshot: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    eligible = []
    for row in snapshot:
        action = str(row.get("action") or "").upper()
        trade_type = str(row.get("trade_type") or ("STRONG" if action == "ACCUMULATE" else "")).upper()
        if action == "ACCUMULATE" and trade_type == "STRONG":
            eligible.append(row)
    return eligible


def dispatch_latest_snapshot_alerts(db_manager, user_ids: Optional[Iterable[int]] = None) -> Dict[str, int]:
    snapshot = load_latest_snapshot()
    signals = _eligible_snapshot_signals(snapshot)
    today = _utc_now_naive().date().isoformat()

    summary = {
        "signals_seen": len(signals),
        "users_checked": 0,
        "sent": 0,
        "duplicates_skipped": 0,
    }

    if not signals:
        return summary

    with db_manager.get_session() as session:
        query = session.query(User).filter(User.telegram_chat_id.isnot(None))
        if user_ids is not None:
            user_ids = list(user_ids)
            if not user_ids:
                return summary
            query = query.filter(User.id.in_(user_ids))

        users = query.all()
        summary["users_checked"] = len(users)

        for user in users:
            for signal in signals:
                symbol = str(signal.get("sym") or "").upper()
                if not symbol:
                    continue

                exists = session.query(TelegramAlertDelivery).filter(
                    TelegramAlertDelivery.user_id == user.id,
                    TelegramAlertDelivery.symbol == symbol,
                    TelegramAlertDelivery.alert_day == today,
                ).first()
                if exists is not None:
                    summary["duplicates_skipped"] += 1
                    continue

                delivered = send_telegram_message(user.telegram_chat_id, _format_signal_message(signal))
                if not delivered:
                    continue

                session.add(TelegramAlertDelivery(
                    user_id=user.id,
                    symbol=symbol,
                    alert_day=today,
                    trade_type="STRONG",
                    action="ACCUMULATE",
                    smart_rank=float(signal.get("smart_rank") or 0.0),
                    created_at=_utc_now_naive(),
                ))
                summary["sent"] += 1

    return summary
