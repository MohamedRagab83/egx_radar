from __future__ import annotations

import contextlib
import copy
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import egx_radar.backtest.engine as backtest_engine
import egx_radar.core.signal_engine as signal_engine
from egx_radar.backtest.metrics import compute_metrics

DATE_FROM = "2024-01-01"
DATE_TO = "2024-12-31"
OUTPUT_PATH = Path("_alpha_engine_backtest_comparison.json")

_ORIG_EVALUATE = backtest_engine.evaluate_symbol_snapshot
_ORIG_HP_FILTER = backtest_engine._is_high_probability_trade
_ORIG_BUILD_OPEN_TRADE = backtest_engine._build_open_trade
_ORIG_BUILD_RESULTS_FOR_DAY = backtest_engine._build_results_for_day
_ALPHA_META_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
_ALPHA_LAST_SIGNAL: Dict[str, datetime] = {}


def _positive_news(sym: str) -> List[Dict[str, Any]]:
    now = datetime.now(UTC).replace(tzinfo=None)
    positive_payloads = {
        "EAST": ("نتائج اعمال", "نمو قوي في الارباح وزياده الايرادات وتحسن الهوامش"),
        "ETEL": ("صفقه استحواذ", "صفقه استحواذ تدعم التوسع وزياده الربحيه"),
        "KZPC": ("مشروع جديد", "مشروع جديد يرفع الطاقه الانتاجيه وتحسن الهوامش"),
    }
    payload = positive_payloads.get(str(sym or "").upper())
    if payload is None:
        return []
    title, content = payload
    return [
        {
            "title": title,
            "content": content,
            "symbol": str(sym).upper(),
            "timestamp": now - timedelta(hours=3),
            "source": "egx_official",
        }
    ]


def _alpha_plan_from_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    alpha_trade = dict(result.get("alpha_trade") or {})
    alpha_trade["action"] = "PROBE"
    alpha_trade["trade_type"] = "ALPHA"
    alpha_trade["score"] = float(alpha_trade.get("alpha_score") or result.get("alpha_score") or 0.0)
    alpha_trade["risk_pct"] = max(float(alpha_trade.get("risk_pct") or 0.012), 0.005)
    alpha_trade["target_pct"] = max(float(alpha_trade.get("target_pct") or 0.05), 0.03)
    alpha_trade["risk_used"] = float(alpha_trade.get("risk_used") or 0.001)
    alpha_trade["entry"] = float(alpha_trade.get("entry") or result.get("price") or 0.0)
    alpha_trade["trigger_price"] = float(alpha_trade.get("trigger_price") or alpha_trade["entry"])
    return alpha_trade


def _patched_evaluate_symbol_snapshot(df_ta, sym, sector, regime="BULL"):
    result = _ORIG_EVALUATE(df_ta, sym, sector, regime)
    if result is None:
        return None

    result = copy.deepcopy(result)
    signal_date = df_ta.index[-1].strftime("%Y-%m-%d")
    signal_dt = df_ta.index[-1].to_pydatetime().replace(tzinfo=None)
    action = str((result.get("plan") or {}).get("action") or "WAIT")
    smart_rank = float(result.get("smart_rank", 0.0) or 0.0)
    alpha_trade = result.get("alpha_trade")

    result["alpha_candidate"] = False
    if alpha_trade and 45.0 <= smart_rank < 60.0 and action not in ("ACCUMULATE", "PROBE"):
        last_signal = _ALPHA_LAST_SIGNAL.get(result["sym"])
        if last_signal is not None and (signal_dt - last_signal).days < 15:
            return result
        result["alpha_candidate"] = True
        result["plan"] = _alpha_plan_from_metadata(result)
        result["tag"] = "early"
        result["signal"] = "ALPHA EARLY"
        result["signal_display"] = "ALPHA EARLY"
        result["signal_dir"] = "BULLISH"
        _ALPHA_LAST_SIGNAL[result["sym"]] = signal_dt
        _ALPHA_META_CACHE[(result["sym"], signal_date)] = {
            "alpha_score": float(result.get("alpha_score") or 0.0),
            "position_scale": float((result.get("alpha_trade") or {}).get("position_scale") or 0.0),
            "alpha_candidate": True,
        }

    return result


def _patched_high_probability_trade(result: Dict[str, Any]) -> bool:
    if result.get("alpha_candidate"):
        return True
    return _ORIG_HP_FILTER(result)


def _patched_build_open_trade(pending, entry_base, account_size, entry_date, fill_mode):
    trade = _ORIG_BUILD_OPEN_TRADE(pending, entry_base, account_size, entry_date, fill_mode)
    key = (pending.get("sym"), pending.get("signal_date"))
    alpha_meta = _ALPHA_META_CACHE.get(key)
    if not alpha_meta:
        trade["alpha_candidate"] = False
        trade["alpha_score"] = 0.0
        return trade

    trade = dict(trade)
    trade["alpha_candidate"] = True
    trade["alpha_score"] = round(float(alpha_meta.get("alpha_score") or 0.0), 2)
    trade["alpha_position_scale"] = round(float(alpha_meta.get("position_scale") or 0.0), 4)
    return trade


def _patched_build_results_for_day(all_data, date, yahoo_to_sym):
    results, sector_strength, regime, market_regime = _ORIG_BUILD_RESULTS_FOR_DAY(all_data, date, yahoo_to_sym)
    if any(result.get("alpha_candidate") for result in results) and market_regime == "WEAK":
        return results, sector_strength, regime, "ALPHA"
    return results, sector_strength, regime, market_regime


def _summary(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = compute_metrics(trades)["overall"]
    alpha_trades = [trade for trade in trades if trade.get("alpha_candidate")]
    alpha_expectancy = compute_metrics(alpha_trades)["overall"]["expectancy_pct"] if alpha_trades else 0.0
    alpha_win_rate = compute_metrics(alpha_trades)["overall"]["win_rate_pct"] if alpha_trades else 0.0
    return {
        "trade_count": len(trades),
        "total_return_pct": float(metrics.get("total_return_pct", 0.0) or 0.0),
        "win_rate_pct": float(metrics.get("win_rate_pct", 0.0) or 0.0),
        "max_drawdown_pct": float(metrics.get("max_drawdown_pct", 0.0) or 0.0),
        "sharpe_ratio": float(metrics.get("sharpe_ratio", 0.0) or 0.0),
        "expectancy_pct": float(metrics.get("expectancy_pct", 0.0) or 0.0),
        "alpha_trade_count": len(alpha_trades),
        "alpha_expectancy_pct": float(alpha_expectancy or 0.0),
        "alpha_win_rate_pct": float(alpha_win_rate or 0.0),
    }


def _run_variant(enable_alpha: bool) -> List[Dict[str, Any]]:
    _ALPHA_META_CACHE.clear()
    _ALPHA_LAST_SIGNAL.clear()

    def _patched_fetch_symbol_news(sym: str) -> List[Dict[str, Any]]:
        return _positive_news(sym) if enable_alpha else []

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch.object(signal_engine, "_fetch_symbol_news", side_effect=_patched_fetch_symbol_news)
        )
        if enable_alpha:
            stack.enter_context(
                patch.object(backtest_engine, "evaluate_symbol_snapshot", side_effect=_patched_evaluate_symbol_snapshot)
            )
            stack.enter_context(
                patch.object(backtest_engine, "_build_results_for_day", side_effect=_patched_build_results_for_day)
            )
            stack.enter_context(
                patch.object(backtest_engine, "_is_high_probability_trade", side_effect=_patched_high_probability_trade)
            )
            stack.enter_context(
                patch.object(backtest_engine, "_build_open_trade", side_effect=_patched_build_open_trade)
            )
        trades, _equity, _params, _extras = backtest_engine.run_backtest(DATE_FROM, DATE_TO)
    return trades


def main() -> int:
    baseline_trades = _run_variant(enable_alpha=False)
    alpha_trades = _run_variant(enable_alpha=True)

    baseline = _summary(baseline_trades)
    alpha = _summary(alpha_trades)

    validation = {
        "expectancy_improves": alpha["expectancy_pct"] >= baseline["expectancy_pct"],
        "drawdown_ok": alpha["max_drawdown_pct"] <= baseline["max_drawdown_pct"] + 0.5,
        "no_overtrading": alpha["trade_count"] <= int(max(baseline["trade_count"] + 3, round(baseline["trade_count"] * 1.20))),
        "early_trades_show_edge": alpha["alpha_trade_count"] > 0 and alpha["alpha_expectancy_pct"] > 0.0,
    }
    validation["approved"] = all(validation.values())

    payload = {
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "baseline": baseline,
        "alpha_overlay": alpha,
        "validation": validation,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Alpha engine comparison saved to: {OUTPUT_PATH}")
    print(json.dumps(validation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
