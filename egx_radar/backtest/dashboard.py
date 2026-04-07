from __future__ import annotations

"""Console-friendly performance dashboard helpers for the EGX backtest engine."""

from typing import Any, Dict, List, Optional

from egx_radar.backtest.metrics import compute_metrics
from egx_radar.backtest.missed_trades import run_missed_trade_analysis


def build_performance_dashboard(
    trades: List[dict],
    diagnostics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metrics = compute_metrics(trades)
    missed_entries = list((diagnostics or {}).get("missed_entries") or [])
    approx_returns = [
        float(m["approx_pnl_pct"])
        for m in missed_entries
        if m.get("approx_pnl_pct") is not None
    ]

    # Full missed trade intelligence analysis
    missed_intel = run_missed_trade_analysis(missed_entries=missed_entries)
    analysis = missed_intel.get("analysis", {})

    return {
        "overall": metrics.get("overall", {}),
        "by_trade_type": metrics.get("per_trade_type", {}),
        "monthly": metrics.get("monthly", []),
        "missed_trades": {
            "count": len(missed_entries),
            "approx_avg_return_pct": round(sum(approx_returns) / len(approx_returns), 2) if approx_returns else 0.0,
            "approx_total_return_pct": round(sum(approx_returns), 2) if approx_returns else 0.0,
            "samples": missed_entries[:10],
        },
        "missed_trade_analysis": analysis,
        "missed_trade_report": missed_intel.get("text", ""),
        "metrics": metrics,
    }


def render_console_report(
    dashboard: Dict[str, Any],
    title: str = "SYSTEM PERFORMANCE",
) -> str:
    overall = dashboard.get("overall", {})
    by_type = dashboard.get("by_trade_type", {})
    missed = dashboard.get("missed_trades", {})
    monthly = dashboard.get("monthly", [])

    lines = [
        f"=== {title} ===",
        f"Total Trades: {overall.get('total_trades', 0)}",
        f"Win Rate: {overall.get('win_rate_pct', 0.0)}%",
        f"Avg Return: {overall.get('avg_return_pct', 0.0)}%",
        f"Max Drawdown: {overall.get('max_drawdown_pct', 0.0)}%",
        "",
        "--- By Type ---",
    ]

    for trade_type in ("STRONG", "MEDIUM"):
        stats = by_type.get(trade_type, {})
        lines.append(
            f"{trade_type}: count={stats.get('total_trades', 0)} | "
            f"win={stats.get('win_rate_pct', 0.0)}% | "
            f"avg_return={stats.get('avg_return_pct', 0.0)}% | "
            f"avg_risk={stats.get('avg_risk_used_pct', 0.0)}%"
        )

    lines.extend(
        [
            "",
            "--- Missed Trades ---",
            f"Trigger-ready but not filled: {missed.get('count', 0)}",
            f"Approx Avg Return If Forced In: {missed.get('approx_avg_return_pct', 0.0)}%",
            f"Approx Total Return If Forced In: {missed.get('approx_total_return_pct', 0.0)}%",
        ]
    )

    # Append full missed trade intelligence report if available
    missed_report = dashboard.get("missed_trade_report", "")
    if missed_report:
        lines.extend(["", missed_report])

    lines.extend(["", "--- Trades Per Month ---"])

    if monthly:
        for item in monthly:
            lines.append(
                f"{item.get('month', 'n/a')}: "
                f"count={item.get('trade_count', 0)} | "
                f"return={item.get('return_pct', 0.0)}% | "
                f"win={item.get('win_rate_pct', 0.0)}%"
            )
    else:
        lines.append("No closed trades.")

    return "\n".join(lines)


__all__ = [
    "build_performance_dashboard",
    "render_console_report",
]
