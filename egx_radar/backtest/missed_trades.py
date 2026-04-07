from __future__ import annotations

"""Missed Trade Intelligence System.

Analyzes all trades that were generated as signals but never entered,
classifying them as correctly rejected (bad trades) or incorrectly
rejected (missed opportunities).

Usage:
    from egx_radar.backtest.missed_trades import run_missed_trade_analysis
    report = run_missed_trade_analysis(missed_entries)
    print(report["text"])
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quality scoring thresholds (based on SmartRank / score)
# ---------------------------------------------------------------------------
_QUALITY_HIGH = 75.0
_QUALITY_MEDIUM = 65.0


def _classify_quality(score: float) -> str:
    """Classify a missed trade by its SmartRank score."""
    if score >= _QUALITY_HIGH:
        return "HIGH"
    if score >= _QUALITY_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _classify_outcome(pnl_pct: float) -> str:
    """Classify a missed trade by its simulated outcome."""
    return "MISSED_WIN" if pnl_pct > 0 else "MISSED_LOSS"


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_missed_trades(missed_entries: List[dict]) -> Dict[str, Any]:
    """Compute full analytics on a list of missed trade entries.

    Each entry is expected to have at least:
        sym, sector, signal_date, score (SmartRank),
        approx_pnl_pct (simulated P&L), approx_outcome,
        reason (why missed), trade_type.

    Returns a dict with all metrics, breakdowns, and recommendations.
    """
    if not missed_entries:
        return _empty_analysis()

    total = len(missed_entries)

    # --- Classification ---------------------------------------------------
    for m in missed_entries:
        pnl = float(m.get("approx_pnl_pct") or 0.0)
        score = float(m.get("score", m.get("smart_rank", 0.0)))
        m["classification"] = _classify_outcome(pnl)
        m["quality"] = _classify_quality(score)

    wins = [m for m in missed_entries if m["classification"] == "MISSED_WIN"]
    losses = [m for m in missed_entries if m["classification"] == "MISSED_LOSS"]

    win_count = len(wins)
    loss_count = len(losses)
    win_pct = round(win_count / total * 100, 1) if total else 0.0
    loss_pct = round(loss_count / total * 100, 1) if total else 0.0

    all_pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in missed_entries]
    avg_return = round(sum(all_pnls) / total, 2) if total else 0.0
    total_pnl = round(sum(all_pnls), 2)

    win_pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in wins]
    loss_pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in losses]
    avg_win_return = round(sum(win_pnls) / len(win_pnls), 2) if win_pnls else 0.0
    avg_loss_return = round(sum(loss_pnls) / len(loss_pnls), 2) if loss_pnls else 0.0

    # --- Quality breakdown ------------------------------------------------
    by_quality: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_quality[m["quality"]].append(m)

    quality_breakdown: Dict[str, Dict[str, Any]] = {}
    for q in ("HIGH", "MEDIUM", "LOW"):
        group = by_quality.get(q, [])
        n = len(group)
        w = sum(1 for m in group if m["classification"] == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        quality_breakdown[q] = {
            "count": n,
            "win_count": w,
            "loss_count": n - w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
            "total_pnl_pct": round(sum(pnls), 2),
        }

    # --- By rejection reason ----------------------------------------------
    by_reason: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_reason[m.get("reason", "unknown")].append(m)

    reason_breakdown: Dict[str, Dict[str, Any]] = {}
    for reason, group in by_reason.items():
        n = len(group)
        w = sum(1 for m in group if m.get("classification") == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        reason_breakdown[reason] = {
            "count": n,
            "win_count": w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
        }

    # --- By sector --------------------------------------------------------
    by_sector: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_sector[m.get("sector", "UNKNOWN")].append(m)

    sector_breakdown: Dict[str, Dict[str, Any]] = {}
    for sector, group in by_sector.items():
        n = len(group)
        w = sum(1 for m in group if m.get("classification") == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        sector_breakdown[sector] = {
            "count": n,
            "win_count": w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
        }

    # --- By trade type ----------------------------------------------------
    by_type: Dict[str, List[dict]] = defaultdict(list)
    for m in missed_entries:
        by_type[m.get("trade_type", "UNCLASSIFIED")].append(m)

    type_breakdown: Dict[str, Dict[str, Any]] = {}
    for ttype, group in by_type.items():
        n = len(group)
        w = sum(1 for m in group if m.get("classification") == "MISSED_WIN")
        pnls = [float(m.get("approx_pnl_pct") or 0.0) for m in group]
        type_breakdown[ttype] = {
            "count": n,
            "win_count": w,
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(pnls) / n, 2) if n else 0.0,
        }

    # --- Decision engine & recommendations --------------------------------
    recommendations = _generate_recommendations(
        total=total,
        win_count=win_count,
        loss_count=loss_count,
        win_pct=win_pct,
        avg_return=avg_return,
        quality_breakdown=quality_breakdown,
    )

    return {
        "total_missed": total,
        "missed_wins": win_count,
        "missed_losses": loss_count,
        "missed_wins_pct": win_pct,
        "missed_losses_pct": loss_pct,
        "avg_return_pct": avg_return,
        "avg_win_return_pct": avg_win_return,
        "avg_loss_return_pct": avg_loss_return,
        "total_pnl_impact_pct": total_pnl,
        "quality_breakdown": quality_breakdown,
        "reason_breakdown": reason_breakdown,
        "sector_breakdown": sector_breakdown,
        "type_breakdown": type_breakdown,
        "recommendations": recommendations,
        "entries": missed_entries,
    }


def _generate_recommendations(
    total: int,
    win_count: int,
    loss_count: int,
    win_pct: float,
    avg_return: float,
    quality_breakdown: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Decision engine: generate actionable insights from missed trade data."""
    insights: List[str] = []
    action = "KEEP_FILTERS"  # default

    high = quality_breakdown.get("HIGH", {})
    medium = quality_breakdown.get("MEDIUM", {})
    high_win_rate = high.get("win_rate_pct", 0.0)
    high_count = high.get("count", 0)
    medium_win_rate = medium.get("win_rate_pct", 0.0)

    # Rule 1: If most missed trades are losses → filters are working
    if loss_count > win_count and win_pct < 35:
        insights.append(
            f"System correctly filters most bad trades "
            f"({loss_count}/{total} missed were losses, {win_pct}% win rate)."
        )

    # Rule 2: HIGH quality missed wins > 20% → consider loosening entry rules
    if high_count > 0 and high_win_rate > 20:
        insights.append(
            f"WARNING: {high.get('win_count', 0)} HIGH-quality trades were missed "
            f"(win rate {high_win_rate}%). Consider loosening entry trigger rules."
        )
        action = "REVIEW_ENTRY_RULES"

    # Rule 3: HIGH quality missed wins > 50% → strong signal to loosen
    if high_count >= 3 and high_win_rate > 50:
        insights.append(
            f"STRONG: HIGH-quality missed trades have {high_win_rate}% win rate. "
            f"Entry triggers may be too tight."
        )
        action = "LOOSEN_ENTRY_RULES"

    # Rule 4: Average return of missed trades is positive → leaving money on table
    if avg_return > 0:
        insights.append(
            f"Avg missed trade return is +{avg_return}% — "
            f"system is leaving potential profit on the table."
        )
        if action == "KEEP_FILTERS":
            action = "REVIEW_ENTRY_RULES"

    # Rule 5: Average return negative → filters are protecting capital
    if avg_return < 0:
        insights.append(
            f"Avg missed trade return is {avg_return}% — "
            f"filters are protecting capital effectively."
        )

    # Rule 6: MEDIUM quality has decent win rate → might be worth investigating
    if medium.get("count", 0) >= 3 and medium_win_rate > 40:
        insights.append(
            f"MEDIUM-quality missed trades have {medium_win_rate}% win rate. "
            f"Some could be recoverable with adjusted triggers."
        )

    if not insights:
        insights.append("Not enough data to generate meaningful recommendations.")

    # Conclusion
    if action == "KEEP_FILTERS":
        conclusion = "النظام بيحميك — الفلاتر شغالة صح. (System is protecting you.)"
    elif action == "LOOSEN_ENTRY_RULES":
        conclusion = "النظام بيضيع فرص كتير — لازم تراجع شروط الدخول. (System is missing opportunities — review entry rules.)"
    else:
        conclusion = "في فرص بتتضيع — محتاج مراجعة بسيطة. (Some opportunities are lost — needs minor review.)"

    return {
        "action": action,
        "conclusion": conclusion,
        "insights": insights,
    }


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def format_missed_trade_report(analysis: Dict[str, Any]) -> str:
    """Format a human-readable text report from the analysis dict."""
    if not analysis or analysis.get("total_missed", 0) == 0:
        return "=== MISSED TRADE ANALYSIS ===\n\nNo missed trades to analyze.\n"

    lines = [
        "=== MISSED TRADE ANALYSIS ===",
        "",
        f"Total Missed: {analysis['total_missed']}",
        f"Missed Wins: {analysis['missed_wins']} ({analysis['missed_wins_pct']}%)",
        f"Missed Losses: {analysis['missed_losses']} ({analysis['missed_losses_pct']}%)",
        "",
        f"Avg Missed Return: {analysis['avg_return_pct']}%",
        f"Avg Win Return: {analysis['avg_win_return_pct']}%",
        f"Avg Loss Return: {analysis['avg_loss_return_pct']}%",
        f"Total PnL Impact: {analysis['total_pnl_impact_pct']}%",
        "",
        "--- By Quality ---",
    ]

    for q in ("HIGH", "MEDIUM", "LOW"):
        qd = analysis["quality_breakdown"].get(q, {})
        lines.extend([
            f"{q}:",
            f"    count: {qd.get('count', 0)}",
            f"    win rate: {qd.get('win_rate_pct', 0.0)}%",
            f"    avg return: {qd.get('avg_return_pct', 0.0)}%",
            f"    total PnL: {qd.get('total_pnl_pct', 0.0)}%",
        ])

    lines.extend(["", "--- By Rejection Reason ---"])
    for reason, rd in analysis.get("reason_breakdown", {}).items():
        lines.append(
            f"{reason}: count={rd['count']} | "
            f"win rate={rd['win_rate_pct']}% | "
            f"avg return={rd['avg_return_pct']}%"
        )

    lines.extend(["", "--- By Sector ---"])
    for sector, sd in sorted(
        analysis.get("sector_breakdown", {}).items(),
        key=lambda x: x[1].get("count", 0),
        reverse=True,
    ):
        lines.append(
            f"{sector}: count={sd['count']} | "
            f"win rate={sd['win_rate_pct']}% | "
            f"avg return={sd['avg_return_pct']}%"
        )

    recs = analysis.get("recommendations", {})
    lines.extend([
        "",
        "--- Recommendations ---",
        f"Action: {recs.get('action', 'N/A')}",
    ])
    for insight in recs.get("insights", []):
        lines.append(f"  * {insight}")
    lines.extend([
        "",
        "--- Conclusion ---",
        recs.get("conclusion", ""),
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Top-level callable
# ---------------------------------------------------------------------------

def run_missed_trade_analysis(
    missed_entries: Optional[List[dict]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    print_report: bool = False,
) -> Dict[str, Any]:
    """Run a complete missed-trade intelligence analysis.

    Args:
        missed_entries: List of missed trade dicts (from backtest diagnostics).
            If None, extracted from *diagnostics*.
        diagnostics: The diagnostics dict returned by run_backtest() as 4th element.
        print_report: If True, print the text report to stdout.

    Returns:
        Dict with keys: analysis (full metrics), text (formatted report).
    """
    if missed_entries is None and diagnostics is not None:
        missed_entries = list(diagnostics.get("missed_entries") or [])
    if missed_entries is None:
        missed_entries = []

    analysis = analyze_missed_trades(missed_entries)
    text = format_missed_trade_report(analysis)

    if print_report:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('utf-8', errors='replace').decode('ascii', errors='replace'))

    return {
        "analysis": analysis,
        "text": text,
    }


# ---------------------------------------------------------------------------
# Empty result
# ---------------------------------------------------------------------------

def _empty_analysis() -> Dict[str, Any]:
    empty_quality = {
        q: {"count": 0, "win_count": 0, "loss_count": 0,
            "win_rate_pct": 0.0, "avg_return_pct": 0.0, "total_pnl_pct": 0.0}
        for q in ("HIGH", "MEDIUM", "LOW")
    }
    return {
        "total_missed": 0,
        "missed_wins": 0,
        "missed_losses": 0,
        "missed_wins_pct": 0.0,
        "missed_losses_pct": 0.0,
        "avg_return_pct": 0.0,
        "avg_win_return_pct": 0.0,
        "avg_loss_return_pct": 0.0,
        "total_pnl_impact_pct": 0.0,
        "quality_breakdown": empty_quality,
        "reason_breakdown": {},
        "sector_breakdown": {},
        "type_breakdown": {},
        "recommendations": {
            "action": "NO_DATA",
            "conclusion": "No missed trades to analyze.",
            "insights": [],
        },
        "entries": [],
    }


__all__ = [
    "run_missed_trade_analysis",
    "analyze_missed_trades",
    "format_missed_trade_report",
]
