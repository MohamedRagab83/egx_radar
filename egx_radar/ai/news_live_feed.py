from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib import request
from urllib.error import URLError
from xml.etree import ElementTree

from egx_radar.config.settings import SYMBOLS

from .news_mapper import map_news_to_symbol

log = logging.getLogger(__name__)

_CACHE_FILE = Path(__file__).with_name("news_cache.json")
_DEFAULT_REFRESH_MINUTES = 7
_MAX_CACHE_HOURS = 24

_SOURCE_PRIORITY = [
    (
        "egx_official",
        [
            "https://www.egx.com.eg/en/DisclosureNewsRss.aspx",
        ],
    ),
    (
        "mubasher",
        [
            "https://www.mubasher.info/rss/egx-news",
        ],
    ),
    (
        "investing_egypt",
        [
            "https://www.investing.com/rss/news_25.rss",
        ],
    ),
    (
        "company_announcements",
        [
            "https://www.egx.com.eg/en/DisclosureNewsRss.aspx",
        ],
    ),
]


def _read_cache() -> Dict[str, Any]:
    if not _CACHE_FILE.exists():
        return {"last_fetch": None, "items": []}
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_fetch": None, "items": []}


def _write_cache(payload: Dict[str, Any]) -> None:
    _CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_iso(ts: Any) -> Optional[datetime]:
    if isinstance(ts, datetime):
        return ts
    text = str(ts or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _normalize_headline(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(title or "").strip().lower())
    return cleaned


def _dedupe_key(item: Dict[str, Any]) -> str:
    title = _normalize_headline(item.get("title", ""))
    source = str(item.get("source", "")).lower()
    symbol = str(item.get("symbol", "")).upper()
    digest = hashlib.sha1(f"{source}|{symbol}|{title}".encode("utf-8")).hexdigest()
    return digest


def _clean_text(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", str(text or ""))
    return re.sub(r"\s+", " ", no_tags).strip()


def _parse_rss(url: str, source: str) -> List[Dict[str, Any]]:
    try:
        with request.urlopen(url, timeout=10) as response:
            payload = response.read()
    except (URLError, TimeoutError, OSError) as exc:
        log.debug("News source unavailable %s (%s)", url, exc)
        return []

    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return []

    items: List[Dict[str, Any]] = []
    for node in root.findall(".//item")[:80]:
        title = _clean_text(node.findtext("title", default=""))
        content = _clean_text(
            node.findtext("description", default="")
            or node.findtext("content:encoded", default="")
        )
        if not title:
            continue
        published_raw = node.findtext("pubDate", default="")
        ts = _parse_iso(published_raw) or datetime.utcnow()
        items.append(
            {
                "title": title,
                "content": content,
                "symbol": None,
                "timestamp": ts,
                "source": source,
            }
        )
    return items


def _prune_last_24h(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=_MAX_CACHE_HOURS)
    pruned: List[Dict[str, Any]] = []
    for item in items:
        ts = _parse_iso(item.get("timestamp")) or now
        if ts >= cutoff:
            copied = dict(item)
            copied["timestamp"] = ts
            pruned.append(copied)
    return pruned


def _symbol_whitelist() -> List[str]:
    return sorted({str(sym).upper() for sym in SYMBOLS.keys()})


def _apply_symbol_mapping(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    symbols = _symbol_whitelist()
    mapped: List[Dict[str, Any]] = []
    for item in items:
        payload = dict(item)
        sym = str(payload.get("symbol") or "").upper().strip()
        if sym.endswith(".CA"):
            sym = sym[:-3]
        if sym not in symbols:
            sym = map_news_to_symbol(payload, symbols) or ""
        if sym not in symbols:
            continue
        payload["symbol"] = sym
        mapped.append(payload)
    return mapped


def _serialize_cache_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        copied = dict(item)
        ts = _parse_iso(copied.get("timestamp")) or datetime.utcnow()
        copied["timestamp"] = ts.isoformat()
        out.append(copied)
    return out


def _deserialize_cache_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        copied = dict(item)
        copied["timestamp"] = _parse_iso(copied.get("timestamp")) or datetime.utcnow()
        out.append(copied)
    return out


def fetch_live_news(*, force: bool = False, refresh_minutes: int = _DEFAULT_REFRESH_MINUTES) -> List[Dict[str, Any]]:
    """Fetch prioritized EGX news, dedupe, and keep a rolling 24h cache."""
    cache = _read_cache()
    last_fetch = _parse_iso(cache.get("last_fetch"))
    cached_items = _prune_last_24h(_deserialize_cache_items(cache.get("items", [])))

    now = datetime.utcnow()
    if not force and last_fetch is not None:
        elapsed = (now - last_fetch).total_seconds() / 60.0
        if elapsed < float(max(1, refresh_minutes)):
            return sorted(cached_items, key=lambda x: x["timestamp"], reverse=True)

    dedupe = {_dedupe_key(item) for item in cached_items}
    incoming: List[Dict[str, Any]] = []
    for source, urls in _SOURCE_PRIORITY:
        for url in urls:
            incoming.extend(_parse_rss(url, source))

    incoming = _apply_symbol_mapping(incoming)
    for item in incoming:
        key = _dedupe_key(item)
        if key in dedupe:
            continue
        dedupe.add(key)
        cached_items.append(item)

    cached_items = _prune_last_24h(cached_items)
    cached_items.sort(key=lambda x: x["timestamp"], reverse=True)
    _write_cache(
        {
            "last_fetch": now.isoformat(),
            "items": _serialize_cache_items(cached_items),
        }
    )
    return cached_items


__all__ = ["fetch_live_news"]
