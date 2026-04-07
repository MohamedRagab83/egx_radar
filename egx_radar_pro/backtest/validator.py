"""
backtest/validator.py — EGX Radar Pro
=========================================
Validation and diagnosis toolkit.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict

import numpy as np
import pandas as pd

from ai.learning import LearningModule
from backtest.engine import run_backtest
from backtest.metrics import performance_metrics
from backtest.optimizer import optimize_v2
from core.signal_engine import evaluate_snapshot
from utils.logger import get_logger

log = get_logger(__name__)


def validate_system(
    market_data: Dict[str, pd.DataFrame],
    strategy: str = "legacy",
    strategy_params: Dict | None = None,
) -> Dict[str, Dict[str, float]]:
    """
    Run three-mode parity validation for a given strategy.

    Execution must be identical across baseline/ai/alpha modes because
    AI/News/Alpha remain display-only.
    """
    baseline_trades, baseline_curve = run_backtest(
        market_data,
        use_ai=False,
        use_alpha=False,
        learning=None,
        strategy=strategy,
        strategy_params=strategy_params,
    )

    learning = LearningModule()
    ai_trades, ai_curve = run_backtest(
        market_data,
        use_ai=True,
        use_alpha=False,
        learning=learning,
        strategy=strategy,
        strategy_params=strategy_params,
    )

    alpha_trades, alpha_curve = run_backtest(
        market_data,
        use_ai=True,
        use_alpha=True,
        learning=learning,
        strategy=strategy,
        strategy_params=strategy_params,
    )

    counts = (len(baseline_trades), len(ai_trades), len(alpha_trades))
    if not (counts[0] == counts[1] == counts[2]):
        raise RuntimeError(
            f"EXECUTION PARITY FAILED for strategy='{strategy}'.\n"
            f"  baseline={counts[0]} ai={counts[1]} alpha={counts[2]}"
        )

    return {
        "baseline": performance_metrics(baseline_trades, baseline_curve),
        "ai": performance_metrics(ai_trades, ai_curve),
        "alpha": performance_metrics(alpha_trades, alpha_curve),
    }


def diagnose_failure(market_data: Dict[str, pd.DataFrame]) -> Dict:
    """Return a data-driven diagnosis for why legacy mode loses edge."""
    trades, curve = run_backtest(market_data, strategy="legacy", use_ai=False, use_alpha=False)
    metrics = performance_metrics(trades, curve)

    pnls = np.array([t.pnl_pct for t in trades], dtype=float) if trades else np.array([], dtype=float)
    sr = np.array([t.smart_rank for t in trades], dtype=float) if trades else np.array([], dtype=float)
    exits = dict(Counter([t.status for t in trades]))

    # Reconstruct filter quality at signal time to expose weak entries
    sampled = 0
    trend_fail = 0
    rsi_outside = 0
    vol_low = 0
    atr_high = 0

    for t in trades:
        df = market_data[t.symbol]
        pos = df.index.get_loc(t.entry_date)
        if isinstance(pos, slice) or pos <= 0:
            continue
        signal_date = df.index[pos - 1]
        snap = evaluate_snapshot(df[df.index <= signal_date].tail(260), t.symbol, learning_bias=0.0)
        if snap is None:
            continue

        sampled += 1
        if not (snap.close > snap.ema50 and snap.close > snap.ema200):
            trend_fail += 1
        if not (45.0 <= snap.rsi <= 65.0):
            rsi_outside += 1
        if not (snap.volume_ratio > 1.2):
            vol_low += 1
        if not (snap.atr_pct <= 0.03):
            atr_high += 1

    sr_buckets = []
    for a, b in [(55, 60), (60, 65), (65, 70), (70, 75), (75, 100)]:
        if len(sr) == 0:
            continue
        idx = (sr >= a) & (sr < b)
        c = int(idx.sum())
        if c == 0:
            continue
        sr_buckets.append(
            {
                "bucket": f"{a}-{b}",
                "count": c,
                "winrate_pct": round(float((pnls[idx] > 0).mean() * 100.0), 2),
                "expectancy_pct": round(float(pnls[idx].mean()), 4),
            }
        )

    return {
        "legacy_metrics": metrics,
        "legacy_exit_mix": exits,
        "entry_quality": {
            "sampled_entries": sampled,
            "trend_fail_pct": round(100.0 * trend_fail / max(sampled, 1), 2),
            "rsi_outside_45_65_pct": round(100.0 * rsi_outside / max(sampled, 1), 2),
            "volume_ratio_le_1_2_pct": round(100.0 * vol_low / max(sampled, 1), 2),
            "atr_pct_gt_3_pct": round(100.0 * atr_high / max(sampled, 1), 2),
        },
        "legacy_smart_rank_buckets": sr_buckets,
    }


def validate_old_vs_new(market_data: Dict[str, pd.DataFrame]) -> Dict:
    """
    Compare legacy strategy vs Smart Rank 2.0 with optimizer-selected params.

    Raises RuntimeError if the new strategy fails to improve all required metrics.
    """
    old_trades, old_curve = run_backtest(
        market_data,
        use_ai=False,
        use_alpha=False,
        learning=None,
        strategy="legacy",
    )
    old_metrics = performance_metrics(old_trades, old_curve)

    opt = optimize_v2(market_data)
    viable = [
        r for r in opt["all_results"]
        if r["metrics"]["expectancy_pct"] > old_metrics["expectancy_pct"]
        and r["metrics"]["drawdown_pct"] < old_metrics["drawdown_pct"]
        and r["metrics"]["winrate_pct"] > old_metrics["winrate_pct"]
    ]
    if not viable:
        raise RuntimeError("No Smart Rank 2.0 parameter set improved expectancy, drawdown, and winrate together.")

    viable.sort(key=lambda x: x["objective"], reverse=True)
    new_params = viable[0]["params"]

    new_trades, new_curve = run_backtest(
        market_data,
        use_ai=False,
        use_alpha=False,
        learning=None,
        strategy="v2",
        strategy_params=new_params,
    )
    new_metrics = performance_metrics(new_trades, new_curve)

    improved = {
        "expectancy": new_metrics["expectancy_pct"] > old_metrics["expectancy_pct"],
        "drawdown": new_metrics["drawdown_pct"] < old_metrics["drawdown_pct"],
        "winrate": new_metrics["winrate_pct"] > old_metrics["winrate_pct"],
    }

    if not all(improved.values()):
        raise RuntimeError(
            "Smart Rank 2.0 did not satisfy mandatory improvement gates. "
            f"Improvements={improved}"
        )

    parity = validate_system(market_data, strategy="v2", strategy_params=new_params)

    return {
        "old": old_metrics,
        "new": new_metrics,
        "new_params": new_params,
        "optimizer_top": opt["top_results"],
        "improved": improved,
        "parity_v2": parity,
    }
