from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import egx_radar.backtest.engine as backtest_engine
import egx_radar.core.signal_engine as signal_engine
from egx_radar.backtest.metrics import compute_metrics

DATE_FROM = "2024-01-01"
DATE_TO = "2024-12-31"
OUTPUT_PATH = Path("_news_intelligence_backtest_comparison.json")


def _summary(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = compute_metrics(trades)["overall"]
    false_breakouts = sum(
        1
        for trade in trades
        if float(trade.get("pnl_pct", 0.0) or 0.0) < 0.0 and int(trade.get("bars_held", 99) or 99) <= 3
    )
    return {
        "trades": len(trades),
        "win_rate_pct": float(metrics.get("win_rate_pct", 0.0) or 0.0),
        "max_drawdown_pct": float(metrics.get("max_drawdown_pct", 0.0) or 0.0),
        "sharpe_ratio": float(metrics.get("sharpe_ratio", 0.0) or 0.0),
        "false_breakouts": false_breakouts,
    }


def _news_payload_for_symbol(sym: str) -> List[Dict[str, Any]]:
    now = datetime.now(UTC).replace(tzinfo=None)
    text_by_symbol = {
        "COMI": "نمو قوي وزيادة الإيرادات مع تحسن الهوامش",
        "CIEB": "صفقة استحواذ تدعم التوسع",
        "TMGH": "تراجع الأرباح وضغوط تمويلية",
        "ORAS": "خسائر كبيرة وتحقيق رسمي",
    }
    text = text_by_symbol.get(str(sym or "").upper(), "")
    if not text:
        return []
    return [
        {
            "title": text,
            "content": text,
            "symbol": str(sym).upper(),
            "timestamp": now - timedelta(hours=2),
            "source": "mubasher",
        }
    ]


def _run_variant(enable_news: bool) -> List[Dict[str, Any]]:
    def _patched_fetch_symbol_news(sym: str) -> List[Dict[str, Any]]:
        return _news_payload_for_symbol(sym) if enable_news else []

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch.object(signal_engine, "_fetch_symbol_news", side_effect=_patched_fetch_symbol_news)
        )
        trades, _equity, _params, _extras = backtest_engine.run_backtest(DATE_FROM, DATE_TO)
    return trades


def main() -> int:
    baseline_trades = _run_variant(enable_news=False)
    with_news_trades = _run_variant(enable_news=True)

    baseline = _summary(baseline_trades)
    with_news = _summary(with_news_trades)

    checks = {
        "false_breakout_reduction": with_news["false_breakouts"] <= baseline["false_breakouts"],
        "drawdown_reduction": with_news["max_drawdown_pct"] <= baseline["max_drawdown_pct"],
        "no_overtrading": with_news["trades"] <= int(max(5, round(baseline["trades"] * 1.10))),
    }
    checks["approved"] = all(checks.values())

    payload = {
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "baseline_without_news": baseline,
        "with_news_intelligence": with_news,
        "validation": checks,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"News intelligence comparison saved to: {OUTPUT_PATH}")
    print(json.dumps(checks, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
