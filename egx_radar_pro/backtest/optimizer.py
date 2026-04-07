"""
backtest/optimizer.py — EGX Radar Pro
========================================
Grid-search optimizer for Smart Rank 2.0 strategy parameters.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

from backtest.engine import run_backtest
from backtest.metrics import performance_metrics


def _candidate_grid() -> List[Dict[str, float]]:
    return [
        {"rsi_min": 44.0, "rsi_max": 64.0, "volume_min": 1.10, "atr_pct_max": 0.030, "score_threshold": 58.0},
        {"rsi_min": 44.0, "rsi_max": 64.0, "volume_min": 1.20, "atr_pct_max": 0.030, "score_threshold": 60.0},
        {"rsi_min": 45.0, "rsi_max": 65.0, "volume_min": 1.20, "atr_pct_max": 0.035, "score_threshold": 62.0},
        {"rsi_min": 46.0, "rsi_max": 66.0, "volume_min": 1.10, "atr_pct_max": 0.035, "score_threshold": 60.0},
        {"rsi_min": 47.0, "rsi_max": 65.0, "volume_min": 1.15, "atr_pct_max": 0.035, "score_threshold": 58.0},
        {"rsi_min": 45.0, "rsi_max": 63.0, "volume_min": 1.25, "atr_pct_max": 0.030, "score_threshold": 62.0},
        {"rsi_min": 43.0, "rsi_max": 67.0, "volume_min": 1.10, "atr_pct_max": 0.035, "score_threshold": 56.0},
        {"rsi_min": 45.0, "rsi_max": 65.0, "volume_min": 1.05, "atr_pct_max": 0.040, "score_threshold": 55.0},
    ]


def _objective(metrics: Dict[str, float]) -> float:
    """Favor expectancy and drawdown stability, then winrate."""
    return (
        2.4 * metrics["expectancy_pct"]
        + 0.8 * metrics["winrate_pct"]
        - 1.6 * metrics["drawdown_pct"]
    )


def optimize_v2(market_data: Dict[str, pd.DataFrame]) -> Dict:
    """
    Run grid search and return best Smart Rank 2.0 parameter set.

    Returns
    -------
    dict with:
      best_params, best_metrics, top_results
    """
    results: List[Dict] = []

    for params in _candidate_grid():
        trades, curve = run_backtest(
            market_data,
            use_ai=False,
            use_alpha=False,
            learning=None,
            strategy="v2",
            strategy_params=params,
        )
        metrics = performance_metrics(trades, curve)

        # Avoid overfitting to tiny sample sizes
        if metrics["trades"] < 5:
            continue

        results.append(
            {
                "params": params,
                "metrics": metrics,
                "objective": round(_objective(metrics), 4),
            }
        )

    if not results:
        raise RuntimeError("Optimizer found no valid parameter sets (all had too few trades).")

    results.sort(key=lambda x: x["objective"], reverse=True)
    return {
        "best_params": results[0]["params"],
        "best_metrics": results[0]["metrics"],
        "all_results": results,
        "top_results": results[:10],
    }
