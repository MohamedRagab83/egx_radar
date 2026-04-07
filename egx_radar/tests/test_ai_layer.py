from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import egx_radar.backtest.engine as backtest_engine
from egx_radar.ai.decision_engine import build_trade_decision
from egx_radar.ai.execution_layer import apply_execution_scaling
from egx_radar.ai.learning_engine import LearningEngine
from egx_radar.ai.probability_engine import compute_probability
from egx_radar.backtest.data_loader import load_backtest_data
from egx_radar.backtest.metrics import compute_metrics
from egx_radar.core.signal_engine import evaluate_symbol_snapshot

DATE_FROM = "2024-01-01"
DATE_TO = "2024-12-31"
SNAPSHOT_OUTPUT = Path("_ai_snapshot_results.json")
COMPARISON_OUTPUT = Path("_ai_backtest_comparison.json")

_ORIG_EVALUATE = backtest_engine.evaluate_symbol_snapshot
_ORIG_BUILD_OPEN_TRADE = backtest_engine._build_open_trade
_AI_SIGNAL_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _serialize_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sym": trade.get("sym"),
        "signal_date": trade.get("signal_date"),
        "entry_date": trade.get("entry_date"),
        "exit_date": trade.get("exit_date"),
        "smart_rank": trade.get("smart_rank"),
        "probability": trade.get("probability"),
        "trade_class": trade.get("trade_class"),
        "risk_used": trade.get("risk_used"),
        "alloc_pct": trade.get("alloc_pct"),
        "pnl_pct": trade.get("pnl_pct"),
        "outcome": trade.get("outcome"),
    }


def _enrich_signal_result(result: Dict[str, Any], signal_date: str) -> Dict[str, Any]:
    decision = build_trade_decision(result)
    enriched = dict(result)
    enriched["probability"] = decision.probability
    enriched["trade_class"] = decision.trade_class
    enriched["ai_size_multiplier"] = decision.size_multiplier
    enriched["ai_rationale"] = decision.rationale
    _AI_SIGNAL_CACHE[(enriched["sym"], signal_date)] = {
        "probability": decision.probability,
        "trade_class": decision.trade_class,
        "size_multiplier": decision.size_multiplier,
    }
    return enriched


def _patched_evaluate_symbol_snapshot(df_ta, sym, sector, regime="BULL"):
    result = _ORIG_EVALUATE(df_ta, sym, sector, regime)
    if result is None:
        return None
    signal_date = df_ta.index[-1].strftime("%Y-%m-%d")
    return _enrich_signal_result(result, signal_date)


def _patched_build_open_trade_factory(scale_execution: bool):
    def _patched_build_open_trade(pending, entry_base, account_size, entry_date, fill_mode):
        trade = _ORIG_BUILD_OPEN_TRADE(pending, entry_base, account_size, entry_date, fill_mode)
        key = (pending.get("sym"), pending.get("signal_date"))
        ai_meta = _AI_SIGNAL_CACHE.get(key)
        if not ai_meta:
            return trade

        decorated = dict(trade)
        decorated["probability"] = ai_meta["probability"]
        decorated["trade_class"] = ai_meta["trade_class"]
        decorated["ai_size_multiplier"] = ai_meta["size_multiplier"]

        if not scale_execution:
            return decorated

        scaled_plan = apply_execution_scaling(decorated, ai_meta["probability"], ai_meta["trade_class"])
        decorated["size"] = int(scaled_plan["ai_scaled_size"])
        decorated["risk_used"] = float(scaled_plan["ai_scaled_risk_used"])
        return decorated

    return _patched_build_open_trade


def _quality_distribution(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    exposure_by_class = {"STRONG": 0.0, "MEDIUM": 0.0, "WEAK": 0.0}
    total_exposure = 0.0
    for trade in trades:
        trade_class = str(trade.get("trade_class", "WEAK")).upper()
        exposure = float(trade.get("alloc_pct", 0.0) or 0.0)
        exposure_by_class[trade_class] = exposure_by_class.get(trade_class, 0.0) + exposure
        total_exposure += exposure

    if total_exposure <= 0:
        return {
            "strong_exposure_pct": 0.0,
            "medium_exposure_pct": 0.0,
            "weak_exposure_pct": 0.0,
        }

    return {
        "strong_exposure_pct": round(exposure_by_class.get("STRONG", 0.0) / total_exposure * 100.0, 2),
        "medium_exposure_pct": round(exposure_by_class.get("MEDIUM", 0.0) / total_exposure * 100.0, 2),
        "weak_exposure_pct": round(exposure_by_class.get("WEAK", 0.0) / total_exposure * 100.0, 2),
    }


def _metrics_summary(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = compute_metrics(trades)
    overall = metrics["overall"]
    return {
        "trades": len(trades),
        "win_rate_pct": overall["win_rate_pct"],
        "total_return_pct": overall["total_return_pct"],
        "max_drawdown_pct": overall["max_drawdown_pct"],
        "sharpe_ratio": overall["sharpe_ratio"],
        "profit_factor": overall["profit_factor"],
        "expectancy_pct": overall["expectancy_pct"],
        "quality_distribution": _quality_distribution(trades),
        "sample_trades": [_serialize_trade(trade) for trade in trades[:10]],
    }


def generate_snapshot_dataset(date_from: str = DATE_FROM, date_to: str = DATE_TO) -> Dict[str, Any]:
    all_data = load_backtest_data(date_from, date_to)
    snapshots: List[Dict[str, Any]] = []

    for yahoo_symbol, df in all_data.items():
        if df is None or df.empty:
            continue
        sym = backtest_engine._yahoo_to_sym().get(yahoo_symbol)
        if not sym:
            continue
        sector = backtest_engine.get_sector(sym)

        for date in df.index:
            df_slice = df[df.index <= date].tail(260).copy()
            snapshot = evaluate_symbol_snapshot(df_slice, sym, sector, regime="BULL")
            if snapshot is None:
                continue
            probability = compute_probability(snapshot)
            decision = build_trade_decision(snapshot, probability=probability)
            snapshots.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "sym": sym,
                    "sector": sector,
                    "smart_rank": snapshot.get("smart_rank"),
                    "probability": decision.probability,
                    "trade_class": decision.trade_class,
                    "signal": snapshot.get("signal"),
                    "tag": snapshot.get("tag"),
                    "action": (snapshot.get("plan") or {}).get("action"),
                    "atr_pct": snapshot.get("atr_pct"),
                    "volume_ratio": snapshot.get("volume_ratio"),
                    "structure_score": snapshot.get("structure_score"),
                }
            )

    payload = {
        "date_from": date_from,
        "date_to": date_to,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
    }
    SNAPSHOT_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _run_backtest_variant(scale_execution: bool, date_from: str, date_to: str) -> List[Dict[str, Any]]:
    _AI_SIGNAL_CACHE.clear()
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch.object(backtest_engine, "evaluate_symbol_snapshot", side_effect=_patched_evaluate_symbol_snapshot)
        )
        stack.enter_context(
            patch.object(backtest_engine, "_build_open_trade", side_effect=_patched_build_open_trade_factory(scale_execution))
        )
        trades, _equity_curve, _params, _extras = backtest_engine.run_backtest(date_from, date_to)
    return trades


def run_backtest_comparison(date_from: str = DATE_FROM, date_to: str = DATE_TO) -> Dict[str, Any]:
    baseline_trades = _run_backtest_variant(scale_execution=False, date_from=date_from, date_to=date_to)
    ai_trades = _run_backtest_variant(scale_execution=True, date_from=date_from, date_to=date_to)

    learning_engine = LearningEngine()
    for trade in ai_trades:
        learning_engine.record_outcome(
            symbol=str(trade.get("sym", "")),
            probability=float(trade.get("probability", 0.5) or 0.5),
            trade_class=str(trade.get("trade_class", "WEAK")),
            pnl_pct=float(trade.get("pnl_pct", 0.0) or 0.0),
            outcome=str(trade.get("outcome", "EXIT")),
            smart_rank=float(trade.get("smart_rank", 0.0) or 0.0),
            signal_date=str(trade.get("signal_date", "")),
        )

    baseline_summary = _metrics_summary(baseline_trades)
    ai_summary = _metrics_summary(ai_trades)

    validation = {
        "sharpe_ok": ai_summary["sharpe_ratio"] >= baseline_summary["sharpe_ratio"] - 0.10,
        "max_drawdown_ok": ai_summary["max_drawdown_pct"] <= baseline_summary["max_drawdown_pct"],
        "win_rate_ok": ai_summary["win_rate_pct"] >= baseline_summary["win_rate_pct"] - 5.0,
        "quality_ok": (
            ai_summary["quality_distribution"]["strong_exposure_pct"]
            >= baseline_summary["quality_distribution"]["strong_exposure_pct"]
            and ai_summary["quality_distribution"]["weak_exposure_pct"]
            <= baseline_summary["quality_distribution"]["weak_exposure_pct"]
        ),
    }
    validation["approved"] = all(validation.values())

    payload = {
        "date_from": date_from,
        "date_to": date_to,
        "baseline": baseline_summary,
        "ai_version": ai_summary,
        "validation": validation,
    }
    COMPARISON_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    snapshot_payload = generate_snapshot_dataset()
    comparison_payload = run_backtest_comparison()

    print(f"AI snapshot dataset saved to: {SNAPSHOT_OUTPUT}")
    print(f"Snapshots generated: {snapshot_payload['snapshot_count']}")
    print(f"AI comparison saved to: {COMPARISON_OUTPUT}")
    print(json.dumps(comparison_payload["validation"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())