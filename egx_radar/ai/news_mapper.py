from __future__ import annotations

import re
from typing import Any, Iterable, Optional


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_symbol_token(sym: str) -> str:
    token = str(sym or "").upper().strip()
    if token.endswith(".CA"):
        token = token[:-3]
    return token


def map_news_to_symbol(news: dict, symbols: Iterable[str]) -> Optional[str]:
    """Map a news payload to one EGX symbol using title/content token matching."""
    title = _safe_text(news.get("title", "")).upper()
    content = _safe_text(news.get("content", "")).upper()
    blob = f"{title} {content}"

    for sym in symbols:
        token = _normalize_symbol_token(sym)
        if not token:
            continue
        pattern = rf"(^|[^A-Z0-9]){re.escape(token)}([^A-Z0-9]|$)"
        if re.search(pattern, blob):
            return token

    return None


__all__ = ["map_news_to_symbol"]
