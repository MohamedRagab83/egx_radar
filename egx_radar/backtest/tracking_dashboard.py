from __future__ import annotations

"""
Trade Tracking Dashboard — real-time system quality evaluation.

Answers: "هل أنا جاهز أدخل فلوس… ولا لسه بدري؟"

Reads REAL trade data from backtest results and/or CSV logs.
All metrics are computed dynamically — no hardcoded values.
"""

import csv
import logging
import math
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from egx_radar.backtest.metrics import compute_metrics
from egx_radar.config.settings import K

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────
# PART 1 & 2: Core Metrics + Progress Tracking
# ─────────────────────────────────────────────────────────────────────────

_TRADE_THRESHOLD_INSUFFICIENT = 20
_TRADE_THRESHOLD_PRELIMINARY = 50


def _progress_status(trade_count: int) -> Tuple[str, str]:
    """Return (status_label, status_icon) based on trade count."""
    if trade_count < _TRADE_THRESHOLD_INSUFFICIENT:
        return "INSUFFICIENT DATA", "🔴"
    elif trade_count < _TRADE_THRESHOLD_PRELIMINARY:
        return "PRELIMINARY", "⚠️"
    else:
        return "STATISTICALLY SIGNIFICANT", "✅"


# ─────────────────────────────────────────────────────────────────────────
# PART 3: Trade Classification (STRONG / MEDIUM)
# ─────────────────────────────────────────────────────────────────────────

def _classify_trades(trades: List[dict]) -> Dict[str, Dict[str, Any]]:
    """Split trades into STRONG / MEDIUM / other and compute per-class stats."""
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        tt = t.get("trade_type", "UNCLASSIFIED")
        buckets[tt].append(t)

    result: Dict[str, Dict[str, Any]] = {}
    for label in ("STRONG", "MEDIUM", "UNCLASSIFIED"):
        group = buckets.get(label, [])
        n = len(group)
        wins = sum(1 for t in group if t.get("pnl_pct", 0) > 0)
        avg_ret = sum(t.get("pnl_pct", 0.0) for t in group) / n if n else 0.0
        result[label] = {
            "count": n,
            "win_rate_pct": round(wins / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(avg_ret, 2),
        }
    return result


# ─────────────────────────────────────────────────────────────────────────
# PART 4: Equity Tracking — curve, drawdown, losing streaks
# ─────────────────────────────────────────────────────────────────────────

def _build_equity_curve(trades: List[dict]) -> List[Tuple[str, float]]:
    """Build equity curve from trade sequence."""
    if not trades:
        return [("start", 100.0)]

    # Use real equity_after if available (from the backtest engine)
    if all(t.get("equity_after") is not None for t in trades):
        curve = [("start", 100.0)]
        for t in trades:
            date_str = t.get("exit_date", "")
            curve.append((date_str, float(t["equity_after"])))
        return curve

    # Fallback: reconstruct from alloc_pct * pnl_pct
    equity = 100.0
    curve = [("start", equity)]
    for t in trades:
        alloc = float(t.get("alloc_pct", 0.20))
        equity *= (1 + alloc * t.get("pnl_pct", 0.0) / 100)
        date_str = t.get("exit_date", "")
        curve.append((date_str, round(equity, 4)))
    return curve


def _compute_drawdown_series(equity_curve: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """Compute drawdown % at each equity point."""
    peak = 0.0
    dd_series = []
    for date_str, eq in equity_curve:
        peak = max(peak, eq)
        dd = (peak - eq) / peak * 100 if peak > 0 else 0.0
        dd_series.append((date_str, round(dd, 2)))
    return dd_series


def _worst_losing_streak(trades: List[dict]) -> Dict[str, Any]:
    """Find the worst consecutive losing streak."""
    max_streak = 0
    current_streak = 0
    streak_pnl = 0.0
    max_streak_pnl = 0.0
    max_streak_start = ""
    max_streak_end = ""
    current_start = ""

    for t in trades:
        if t.get("pnl_pct", 0) <= 0:
            if current_streak == 0:
                current_start = t.get("entry_date", "")
            current_streak += 1
            streak_pnl += t.get("pnl_pct", 0.0)
            if current_streak > max_streak:
                max_streak = current_streak
                max_streak_pnl = streak_pnl
                max_streak_start = current_start
                max_streak_end = t.get("exit_date", "")
        else:
            current_streak = 0
            streak_pnl = 0.0

    return {
        "length": max_streak,
        "total_pnl_pct": round(max_streak_pnl, 2),
        "start_date": max_streak_start,
        "end_date": max_streak_end,
    }


# ─────────────────────────────────────────────────────────────────────────
# PART 5: Risk Monitoring
# ─────────────────────────────────────────────────────────────────────────

def _compute_risk_metrics(
    trades: List[dict],
    equity_curve: List[Tuple[str, float]],
) -> Dict[str, Any]:
    """Compute risk metrics and generate alerts."""
    if not trades:
        return {
            "max_loss_pct": 0.0,
            "consecutive_losses": 0,
            "current_drawdown_pct": 0.0,
            "alerts": [],
        }

    pnls = [t.get("pnl_pct", 0.0) for t in trades]
    max_loss = min(pnls) if pnls else 0.0

    # Current consecutive losses (from the end of the trade list)
    consec = 0
    for t in reversed(trades):
        if t.get("pnl_pct", 0) <= 0:
            consec += 1
        else:
            break

    # Current drawdown
    if equity_curve:
        peak = max(eq for _, eq in equity_curve)
        current_eq = equity_curve[-1][1]
        current_dd = (peak - current_eq) / peak * 100 if peak > 0 else 0.0
    else:
        current_dd = 0.0

    alerts = []
    if current_dd > 5.0:
        alerts.append(f"DRAWDOWN ALERT: Current drawdown is {current_dd:.1f}% (> 5%)")
    if consec >= 3:
        alerts.append(f"STREAK ALERT: {consec} consecutive losses")
    if max_loss < -8.0:
        alerts.append(f"LOSS ALERT: Worst single trade was {max_loss:.1f}%")

    return {
        "max_loss_pct": round(max_loss, 2),
        "consecutive_losses": consec,
        "current_drawdown_pct": round(current_dd, 2),
        "alerts": alerts,
    }


# ─────────────────────────────────────────────────────────────────────────
# PART 6: Trade Distribution (monthly)
# ─────────────────────────────────────────────────────────────────────────

def _monthly_distribution(trades: List[dict]) -> List[Dict[str, Any]]:
    """Compute trades per month and returns per month."""
    by_month: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        exit_d = t.get("exit_date", "")
        if len(exit_d) >= 7:
            by_month[exit_d[:7]].append(t)

    result = []
    for month in sorted(by_month.keys()):
        group = by_month[month]
        n = len(group)
        total_ret = sum(t.get("pnl_pct", 0.0) for t in group)
        wins = sum(1 for t in group if t.get("pnl_pct", 0) > 0)
        result.append({
            "month": month,
            "trade_count": n,
            "total_return_pct": round(total_ret, 2),
            "avg_return_pct": round(total_ret / n, 2) if n else 0.0,
            "win_rate_pct": round(wins / n * 100, 1) if n else 0.0,
        })
    return result


# ─────────────────────────────────────────────────────────────────────────
# PART 7: System Health Score
# ─────────────────────────────────────────────────────────────────────────

def _compute_health_score(
    win_rate_pct: float,
    avg_return_pct: float,
    max_drawdown_pct: float,
) -> float:
    """
    Compute normalized system health score (0–100).

    health = win_rate_norm * 0.3 + return_norm * 0.3 + dd_norm * 0.4

    win_rate_norm:  0% → 0, 100% → 100
    return_norm:    clamp avg_return to [-10, +10], map to 0–100
    dd_norm:        0% DD → 100, 20%+ DD → 0
    """
    wr_norm = max(0.0, min(100.0, win_rate_pct))

    # Map avg_return: -10% → 0, 0% → 50, +10% → 100
    clamped_ret = max(-10.0, min(10.0, avg_return_pct))
    ret_norm = (clamped_ret + 10.0) / 20.0 * 100.0

    # Map drawdown: 0% → 100, 20% → 0
    clamped_dd = max(0.0, min(20.0, max_drawdown_pct))
    dd_norm = (1 - clamped_dd / 20.0) * 100.0

    raw = wr_norm * 0.3 + ret_norm * 0.3 + dd_norm * 0.4
    return round(max(0.0, min(100.0, raw)), 1)


# ─────────────────────────────────────────────────────────────────────────
# PART 10: Final Decision Engine
# ─────────────────────────────────────────────────────────────────────────

def _final_verdict(
    total_trades: int,
    win_rate_pct: float,
    max_drawdown_pct: float,
    profit_factor: float,
    health_score: float,
) -> Dict[str, Any]:
    """Determine if the system is ready for real-money trading."""
    reasons = []
    passed = True

    if total_trades < _TRADE_THRESHOLD_PRELIMINARY:
        reasons.append(f"Need {_TRADE_THRESHOLD_PRELIMINARY}+ trades (have {total_trades})")
        passed = False

    if win_rate_pct < 55.0:
        reasons.append(f"Win rate {win_rate_pct:.1f}% < 55% required")
        passed = False

    if max_drawdown_pct > 5.0:
        reasons.append(f"Max drawdown {max_drawdown_pct:.1f}% > 5% limit")
        passed = False

    if profit_factor < 1.2:
        reasons.append(f"Profit factor {profit_factor:.2f} < 1.2 required")
        passed = False

    if health_score < 60:
        reasons.append(f"Health score {health_score:.0f} < 60 required")
        passed = False

    if passed:
        verdict = "READY FOR REAL MONEY"
        verdict_ar = "جاهز تدخل فلوس حقيقية!"
        icon = "✅"
    else:
        verdict = "NOT READY"
        verdict_ar = "لسه بدري — الأسباب أدناه."
        icon = "🔴"

    return {
        "verdict": verdict,
        "verdict_ar": verdict_ar,
        "icon": icon,
        "passed": passed,
        "reasons": reasons,
    }


# ─────────────────────────────────────────────────────────────────────────
# CSV Loader — read backtest CSV trades into trade dicts
# ─────────────────────────────────────────────────────────────────────────

def load_trades_from_csv(csv_path: str) -> List[dict]:
    """
    Load trades from a backtest CSV file.
    Expected columns: sym,sector,signal_type,regime,entry_date,entry,stop,
                      target,bars_held,is_short,smart_rank,exit_date,exit,
                      pnl_pct,rr,outcome
    """
    if not os.path.exists(csv_path):
        log.warning("CSV file not found: %s", csv_path)
        return []

    trades = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trade = {
                "sym": row.get("sym", ""),
                "sector": row.get("sector", ""),
                "signal_type": row.get("signal_type", ""),
                "regime": row.get("regime", ""),
                "entry_date": row.get("entry_date", ""),
                "entry": _safe_float(row.get("entry", 0)),
                "stop": _safe_float(row.get("stop", 0)),
                "target": _safe_float(row.get("target", 0)),
                "bars_held": int(row.get("bars_held", 0) or 0),
                "smart_rank": _safe_float(row.get("smart_rank", 0)),
                "exit_date": row.get("exit_date", ""),
                "exit": _safe_float(row.get("exit", 0)),
                "pnl_pct": _safe_float(row.get("pnl_pct", 0)),
                "rr": _safe_float(row.get("rr", 0)),
                "outcome": row.get("outcome", ""),
                "trade_type": _classify_trade_type(
                    _safe_float(row.get("smart_rank", 0))
                ),
            }
            trades.append(trade)
    return trades


def _safe_float(val: Any) -> float:
    try:
        v = float(val)
        return v if math.isfinite(v) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _classify_trade_type(smart_rank: float) -> str:
    if smart_rank >= K.SMARTRANK_ENTRY_THRESHOLD:
        return "STRONG"
    elif smart_rank >= K.SMARTRANK_MIN_ACTIONABLE:
        return "MEDIUM"
    return "UNCLASSIFIED"


# ─────────────────────────────────────────────────────────────────────────
# PART 8 & 9: Main Dashboard Builder + Console Output
# ─────────────────────────────────────────────────────────────────────────

def build_tracking_dashboard(
    trades: List[dict],
    title: str = "TRADING SYSTEM DASHBOARD",
) -> Dict[str, Any]:
    """
    Build the complete tracking dashboard from a list of closed trades.
    Returns a dict with all metrics, classifications, risk data, and verdict.
    """
    metrics = compute_metrics(trades)
    overall = metrics.get("overall", {})

    total_trades = overall.get("total_trades", 0)
    win_rate = overall.get("win_rate_pct", 0.0)
    avg_return = overall.get("avg_return_pct", 0.0)
    total_return = overall.get("total_return_pct", 0.0)
    max_dd = overall.get("max_drawdown_pct", 0.0)
    pf = overall.get("profit_factor", 0.0)
    expectancy = overall.get("expectancy_pct", 0.0)
    sharpe = overall.get("sharpe_ratio", 0.0)

    # PART 2: Progress
    status_label, status_icon = _progress_status(total_trades)

    # PART 3: Classification
    classification = _classify_trades(trades)

    # PART 4: Equity
    equity_curve = _build_equity_curve(trades)
    drawdown_series = _compute_drawdown_series(equity_curve)
    losing_streak = _worst_losing_streak(trades)

    # PART 5: Risk
    risk = _compute_risk_metrics(trades, equity_curve)

    # PART 6: Monthly
    monthly = _monthly_distribution(trades)

    # PART 7: Health
    health_score = _compute_health_score(win_rate, avg_return, max_dd)

    # PART 10: Verdict
    verdict = _final_verdict(total_trades, win_rate, max_dd, pf, health_score)

    return {
        "title": title,
        "core_metrics": {
            "total_trades": total_trades,
            "win_rate_pct": win_rate,
            "avg_return_pct": avg_return,
            "total_return_pct": total_return,
            "max_drawdown_pct": max_dd,
            "profit_factor": pf,
            "expectancy_pct": expectancy,
            "sharpe_ratio": sharpe,
            "largest_win_pct": overall.get("largest_win_pct", 0.0),
            "largest_loss_pct": overall.get("largest_loss_pct", 0.0),
        },
        "progress": {
            "trades_completed": total_trades,
            "status": status_label,
            "icon": status_icon,
        },
        "classification": classification,
        "equity_curve": equity_curve,
        "drawdown_series": drawdown_series,
        "losing_streak": losing_streak,
        "risk": risk,
        "monthly": monthly,
        "health_score": health_score,
        "verdict": verdict,
        "full_metrics": metrics,
    }


def format_dashboard_report(dashboard: Dict[str, Any]) -> str:
    """
    Format the dashboard as a console-friendly report string.

    PART 8: Output format.
    """
    cm = dashboard["core_metrics"]
    prog = dashboard["progress"]
    cls = dashboard["classification"]
    risk = dashboard["risk"]
    streak = dashboard["losing_streak"]
    monthly = dashboard["monthly"]
    health = dashboard["health_score"]
    verdict = dashboard["verdict"]
    title = dashboard.get("title", "TRADING SYSTEM DASHBOARD")

    lines = [
        f"===== {title} =====",
        "",
        f"Trades: {cm['total_trades']}",
        f"Status: {prog['status']} {prog['icon']}",
        "",
        f"Win Rate: {cm['win_rate_pct']}%",
        f"Avg Return: {cm['avg_return_pct']}%",
        f"Total Return: {cm['total_return_pct']}%",
        f"Max Drawdown: {cm['max_drawdown_pct']}%",
        f"Profit Factor: {cm['profit_factor']}",
        f"Expectancy: {cm['expectancy_pct']}%",
        f"Sharpe Ratio: {cm['sharpe_ratio']}",
        "",
        "--- By Type ---",
    ]

    for label in ("STRONG", "MEDIUM"):
        s = cls.get(label, {})
        lines.append(
            f"{label}: {s.get('count', 0)} trades | "
            f"{s.get('win_rate_pct', 0.0)}% win | "
            f"{s.get('avg_return_pct', 0.0):+.2f}%"
        )

    lines.extend([
        "",
        "--- Risk ---",
        f"Max Loss: {cm['largest_loss_pct']}%",
        f"Losing Streak: {streak['length']} trades ({streak['total_pnl_pct']}%)",
        f"Current DD: {risk['current_drawdown_pct']}%",
        f"Consec. Losses (now): {risk['consecutive_losses']}",
    ])

    if risk["alerts"]:
        lines.append("")
        lines.append("--- Alerts ---")
        for alert in risk["alerts"]:
            lines.append(f"  >> {alert}")

    lines.extend([
        "",
        "--- Monthly ---",
    ])
    if monthly:
        for m in monthly:
            lines.append(
                f"  {m['month']}: {m['trade_count']} trades | "
                f"{m['total_return_pct']:+.1f}% return | "
                f"{m['win_rate_pct']}% win"
            )
    else:
        lines.append("  No trades yet.")

    lines.extend([
        "",
        f"--- Health Score: {health}/100 ---",
        "",
        "--- Verdict ---",
        f"{verdict['icon']} {verdict['verdict']}",
    ])

    if verdict["reasons"]:
        for r in verdict["reasons"]:
            lines.append(f"  - {r}")

    lines.extend([
        "",
        f"  {verdict['verdict_ar']}",
        "",
        "=" * (len(title) + 12),
    ])

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# PART 9: Integration entry point
# ─────────────────────────────────────────────────────────────────────────

def run_dashboard(
    trades: Optional[List[dict]] = None,
    csv_path: Optional[str] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    print_report: bool = True,
) -> Dict[str, Any]:
    """
    Main entry point for the Trade Tracking Dashboard.

    Args:
        trades:      List of closed trade dicts (from run_backtest or paper trading).
        csv_path:    Path to a backtest CSV file to load trades from.
        diagnostics: Optional diagnostics dict from the backtest engine.
        print_report: If True, print the formatted report to console.

    Returns:
        Complete dashboard dict with all metrics, equity, risk, and verdict.
    """
    # Merge trades from all sources
    all_trades: List[dict] = []

    if trades:
        all_trades.extend(trades)

    if csv_path:
        csv_trades = load_trades_from_csv(csv_path)
        all_trades.extend(csv_trades)

    # Sort by exit_date for correct equity curve construction
    all_trades.sort(key=lambda t: t.get("exit_date", ""))

    dashboard = build_tracking_dashboard(all_trades)

    text = format_dashboard_report(dashboard)
    dashboard["text"] = text

    if print_report:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode("utf-8", errors="replace").decode("ascii", errors="replace"))

    return dashboard


__all__ = [
    "run_dashboard",
    "build_tracking_dashboard",
    "format_dashboard_report",
    "load_trades_from_csv",
]
