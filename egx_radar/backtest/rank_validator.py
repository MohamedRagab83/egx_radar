from __future__ import annotations

"""Ranking power validator for EGX Radar's three-tier scoring system.

Measures the PREDICTIVE QUALITY of each ranking system — not just overall
backtest performance. The key question is: does a higher rank actually
correlate with better trade outcomes?

Four measurement dimensions:
  1. Winner-Loser Spread   — rank separation between winners and losers
  2. Rank-PnL Correlation  — Pearson and Spearman r(rank, pnl)
  3. Quartile Monotonicity — avg PnL per rank quartile (should increase Q1→Q4)
  4. False Positive Rate   — precision at high-rank thresholds
  5. Regime Consistency    — each metric broken down by market regime

Results are returned as structured dicts for both machine use and display.
"""

import math
import statistics
from typing import Dict, List, Optional, Tuple


# ── Constants ─────────────────────────────────────────────────────────────

RANKING_SYSTEMS = [
    ("smart_rank",        "SmartRank   (production)"),
    ("multi_factor_rank", "Multi-Factor (experimental)"),
    ("final_rank",        "Final Rank   (hybrid 60/40)"),
]

PRECISION_THRESHOLDS = [50.0, 60.0, 70.0, 80.0]
MIN_TRADES_FOR_ANALYSIS = 5


# ── Math Utilities ─────────────────────────────────────────────────────────


def _pearson(x: List[float], y: List[float]) -> float:
    """Pearson correlation coefficient between two lists."""
    n = len(x)
    if n < 3:
        return float("nan")
    xm = statistics.mean(x)
    ym = statistics.mean(y)
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y))
    denom = math.sqrt(
        sum((xi - xm) ** 2 for xi in x) * sum((yi - ym) ** 2 for yi in y)
    )
    return num / denom if denom > 1e-12 else float("nan")


def _spearman(x: List[float], y: List[float]) -> float:
    """Spearman rank correlation (Information Coefficient) between two lists."""
    n = len(x)
    if n < 3:
        return float("nan")
    rx = _rank_list(x)
    ry = _rank_list(y)
    return _pearson(rx, ry)


def _rank_list(values: List[float]) -> List[float]:
    """Convert values to their rank positions (1-based, handles ties by averaging)."""
    sorted_unique = sorted(set(values))
    rank_map: Dict[float, float] = {}
    idx = 1
    for v in sorted_unique:
        count = values.count(v)
        rank_map[v] = idx + (count - 1) / 2.0
        idx += count
    return [rank_map[v] for v in values]


def _safe_mean(values: List[float], default: float = float("nan")) -> float:
    return statistics.mean(values) if values else default


def _safe_stdev(values: List[float], default: float = float("nan")) -> float:
    return statistics.stdev(values) if len(values) >= 2 else default


# ── Core Analysis Functions ────────────────────────────────────────────────


def winner_loser_spread(trades: List[dict], rank_key: str) -> Dict[str, float]:
    """Compute rank spread between winners and losers.

    Spread = avg_rank(winners) - avg_rank(losers)
    Larger positive spread = rank correctly orders outcomes.
    """
    valid = [t for t in trades if rank_key in t and t[rank_key] is not None
             and "pnl_pct" in t]
    if len(valid) < MIN_TRADES_FOR_ANALYSIS:
        return {"spread": float("nan"), "winner_avg": float("nan"),
                "loser_avg": float("nan"), "n_valid": len(valid)}

    winners = [t[rank_key] for t in valid if t["pnl_pct"] > 0]
    losers = [t[rank_key] for t in valid if t["pnl_pct"] <= 0]

    w_avg = _safe_mean(winners)
    l_avg = _safe_mean(losers)
    spread = w_avg - l_avg if (not math.isnan(w_avg) and not math.isnan(l_avg)) else float("nan")

    return {
        "spread": round(spread, 3) if not math.isnan(spread) else float("nan"),
        "winner_avg": round(w_avg, 2) if not math.isnan(w_avg) else float("nan"),
        "loser_avg": round(l_avg, 2) if not math.isnan(l_avg) else float("nan"),
        "n_winners": len(winners),
        "n_losers": len(losers),
        "n_valid": len(valid),
    }


def rank_pnl_correlation(trades: List[dict], rank_key: str) -> Dict[str, float]:
    """Pearson and Spearman correlation between rank values and realized PnL."""
    valid = [t for t in trades if rank_key in t and t[rank_key] is not None
             and "pnl_pct" in t and math.isfinite(t.get("pnl_pct", float("nan")))]
    if len(valid) < MIN_TRADES_FOR_ANALYSIS:
        return {"pearson": float("nan"), "spearman": float("nan"),
                "n_valid": len(valid)}

    ranks = [float(t[rank_key]) for t in valid]
    pnls = [float(t["pnl_pct"]) for t in valid]

    return {
        "pearson": round(_pearson(ranks, pnls), 4),
        "spearman": round(_spearman(ranks, pnls), 4),
        "n_valid": len(valid),
    }


def quartile_analysis(trades: List[dict], rank_key: str) -> Dict[str, object]:
    """Split trades into rank quartiles, compare avg PnL per quartile.

    A well-ordered ranking system should produce monotonically increasing PnL
    as rank quartile improves (Q1 worst → Q4 best).
    """
    valid = [t for t in trades if rank_key in t and t[rank_key] is not None
             and "pnl_pct" in t and math.isfinite(t.get("pnl_pct", float("nan")))]
    if len(valid) < MAX(8, MIN_TRADES_FOR_ANALYSIS):
        return {"quartiles": [], "monotonic": None, "n_valid": len(valid)}

    sorted_by_rank = sorted(valid, key=lambda t: float(t[rank_key]))
    n = len(sorted_by_rank)
    q_size = n // 4

    quartiles = []
    labels = ["Q1 (lowest 25%)", "Q2 (25-50%)", "Q3 (50-75%)", "Q4 (top 25%)"]
    for i in range(4):
        start = i * q_size
        end = (i + 1) * q_size if i < 3 else n  # Q4 gets any remainder
        group = sorted_by_rank[start:end]
        pnls = [float(t["pnl_pct"]) for t in group]
        ranks = [float(t[rank_key]) for t in group]
        quartiles.append({
            "label": labels[i],
            "count": len(group),
            "rank_range": (round(min(ranks), 1), round(max(ranks), 1)),
            "avg_pnl": round(_safe_mean(pnls), 3),
            "win_rate": round(sum(1 for p in pnls if p > 0) / len(pnls) * 100, 1) if pnls else 0.0,
        })

    # Check for monotonic improvement (Q1 → Q4 avg PnL increasing)
    pnl_sequence = [q["avg_pnl"] for q in quartiles]
    non_nan_pnls = [p for p in pnl_sequence if not math.isnan(p)]
    monotonic = all(non_nan_pnls[i] <= non_nan_pnls[i + 1]
                    for i in range(len(non_nan_pnls) - 1)) if len(non_nan_pnls) >= 2 else None

    return {"quartiles": quartiles, "monotonic": monotonic, "n_valid": len(valid)}


def MAX(a, b):
    return max(a, b)


def false_positive_analysis(
    trades: List[dict], rank_key: str, thresholds: List[float] = None
) -> Dict[str, object]:
    """Compute precision at various rank thresholds.

    Precision = % of high-rank trades that actually won.
    High precision at high thresholds = reliable ranking system.
    """
    if thresholds is None:
        thresholds = PRECISION_THRESHOLDS

    valid = [t for t in trades if rank_key in t and t[rank_key] is not None
             and "pnl_pct" in t]
    if len(valid) < MIN_TRADES_FOR_ANALYSIS:
        return {"levels": [], "n_valid": len(valid)}

    levels = []
    for threshold in thresholds:
        above = [t for t in valid if float(t[rank_key]) >= threshold]
        if not above:
            levels.append({
                "threshold": threshold, "count": 0,
                "win_rate": float("nan"), "avg_pnl": float("nan"),
                "false_positive_rate": float("nan"),
            })
            continue
        wins = [t for t in above if t["pnl_pct"] > 0]
        pnls = [float(t["pnl_pct"]) for t in above]
        win_rate = len(wins) / len(above) * 100
        levels.append({
            "threshold": threshold,
            "count": len(above),
            "win_rate": round(win_rate, 1),
            "avg_pnl": round(_safe_mean(pnls), 3),
            "false_positive_rate": round(100 - win_rate, 1),
        })
    return {"levels": levels, "n_valid": len(valid)}


def regime_breakdown(trades: List[dict], rank_key: str) -> Dict[str, object]:
    """Compute winner-loser spread and correlation per market regime."""
    regimes = {}
    for t in trades:
        regime = str(t.get("regime", "UNKNOWN"))
        regimes.setdefault(regime, []).append(t)

    result = {}
    for regime, group in regimes.items():
        if len(group) < MIN_TRADES_FOR_ANALYSIS:
            result[regime] = {"skip": True, "count": len(group)}
            continue
        spread = winner_loser_spread(group, rank_key)
        corr = rank_pnl_correlation(group, rank_key)
        result[regime] = {
            "count": len(group),
            "spread": spread["spread"],
            "winner_avg": spread["winner_avg"],
            "loser_avg": spread["loser_avg"],
            "pearson_r": corr["pearson"],
            "spearman_ic": corr["spearman"],
        }
    return result


# ── Full Validation Report ─────────────────────────────────────────────────


def run_rank_validation(trades: List[dict]) -> Dict[str, object]:
    """Run all validation metrics for all three ranking systems.

    Returns a structured dict with per-system results and a comparative summary.
    """
    if not trades:
        return {"error": "No trades provided", "systems": {}, "summary": {}}

    valid_trades = [t for t in trades if math.isfinite(t.get("pnl_pct", float("nan")))]
    if len(valid_trades) < MIN_TRADES_FOR_ANALYSIS:
        return {
            "error": f"Insufficient trades ({len(valid_trades)} < {MIN_TRADES_FOR_ANALYSIS})",
            "systems": {},
            "summary": {},
        }

    results = {}
    for rank_key, label in RANKING_SYSTEMS:
        # Skip systems with no data in trades
        has_data = any(t.get(rank_key, 0) > 0 for t in valid_trades)
        if not has_data:
            results[rank_key] = {"label": label, "available": False}
            continue

        results[rank_key] = {
            "label": label,
            "available": True,
            "spread": winner_loser_spread(valid_trades, rank_key),
            "correlation": rank_pnl_correlation(valid_trades, rank_key),
            "quartiles": quartile_analysis(valid_trades, rank_key),
            "false_positives": false_positive_analysis(valid_trades, rank_key),
            "by_regime": regime_breakdown(valid_trades, rank_key),
        }

    # Comparative summary — rank the systems on each metric
    summary = _build_comparative_summary(results)
    return {"systems": results, "summary": summary, "n_trades": len(valid_trades)}


def _build_comparative_summary(results: Dict[str, object]) -> Dict[str, object]:
    """Identify which ranking system wins on each metric."""
    available = {k: v for k, v in results.items() if v.get("available")}
    if not available:
        return {}

    def _best_by(metric_fn, higher_is_better: bool):
        scores = {k: metric_fn(v) for k, v in available.items()}
        valid = {k: s for k, s in scores.items() if not math.isnan(s)}
        if not valid:
            return None, scores
        best = max(valid, key=valid.get) if higher_is_better else min(valid, key=valid.get)
        return best, scores

    # Spread — higher is better
    best_spread, spreads = _best_by(
        lambda v: v["spread"]["spread"], higher_is_better=True
    )
    # Pearson correlation — higher is better
    best_pearson, pearsons = _best_by(
        lambda v: v["correlation"]["pearson"], higher_is_better=True
    )
    # Spearman IC — higher is better
    best_spearman, spearmans = _best_by(
        lambda v: v["correlation"]["spearman"], higher_is_better=True
    )
    # False positive rate at threshold=70 — lower is better
    def _fp_at_70(v):
        for level in v["false_positives"].get("levels", []):
            if level["threshold"] == 70.0:
                return level.get("false_positive_rate", float("nan"))
        return float("nan")
    best_precision, fp_rates = _best_by(lambda v: _fp_at_70(v), higher_is_better=False)

    return {
        "best_spread": best_spread,
        "best_pearson_correlation": best_pearson,
        "best_spearman_ic": best_spearman,
        "best_precision_at_70": best_precision,
        "all_spreads": {k: round(v, 3) if not math.isnan(v) else None for k, v in spreads.items()},
        "all_pearsons": {k: round(v, 4) if not math.isnan(v) else None for k, v in pearsons.items()},
        "all_spearmans": {k: round(v, 4) if not math.isnan(v) else None for k, v in spearmans.items()},
    }


# ── Formatted Report ──────────────────────────────────────────────────────


def format_report(validation_result: Dict[str, object]) -> str:
    """Render a readable text report from run_rank_validation() output."""
    lines = []

    if "error" in validation_result:
        return f"[Rank Validator] {validation_result['error']}"

    n = validation_result.get("n_trades", 0)
    systems = validation_result.get("systems", {})
    summary = validation_result.get("summary", {})
    W = 72

    lines.append("=" * W)
    lines.append(f"  EGX Radar — Ranking Power Validation Report ({n} trades)")
    lines.append("=" * W)

    # ── Section 1: Winner-Loser Spread ───────────────────────────
    lines.append("")
    lines.append("  1. WINNER-LOSER RANK SPREAD")
    lines.append("     (higher spread = ranking correctly separates winners from losers)")
    lines.append("")
    lines.append(f"  {'System':<30s} {'Winner Avg':>12s} {'Loser Avg':>12s} {'Spread':>10s}")
    lines.append(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*10}")
    for rank_key, _ in RANKING_SYSTEMS:
        v = systems.get(rank_key, {})
        if not v.get("available"):
            lines.append(f"  {v.get('label', rank_key):<30s}  (no data)")
            continue
        sp = v["spread"]
        label = v["label"]
        best_tag = " <-- BEST" if rank_key == summary.get("best_spread") else ""
        lines.append(
            f"  {label:<30s} {_fmt(sp['winner_avg']):>12s} {_fmt(sp['loser_avg']):>12s} "
            f"{_fmt(sp['spread']):>10s}{best_tag}"
        )

    # ── Section 2: PnL Correlation ───────────────────────────────
    lines.append("")
    lines.append("  2. RANK-TO-PNL CORRELATION")
    lines.append("     (Pearson = linear fit; Spearman IC = rank ordering quality)")
    lines.append("")
    lines.append(f"  {'System':<30s} {'Pearson r':>12s} {'Spearman IC':>14s}")
    lines.append(f"  {'-'*30} {'-'*12} {'-'*14}")
    for rank_key, _ in RANKING_SYSTEMS:
        v = systems.get(rank_key, {})
        if not v.get("available"):
            continue
        corr = v["correlation"]
        label = v["label"]
        best_p = " <-- BEST" if rank_key == summary.get("best_pearson_correlation") else ""
        lines.append(
            f"  {label:<30s} {_fmt(corr['pearson']):>12s} {_fmt(corr['spearman']):>14s}{best_p}"
        )

    # ── Section 3: Quartile Analysis ─────────────────────────────
    lines.append("")
    lines.append("  3. QUARTILE ANALYSIS")
    lines.append("     (Q1=lowest rank, Q4=highest rank; PnL should increase Q1->Q4)")
    lines.append("")
    for rank_key, _ in RANKING_SYSTEMS:
        v = systems.get(rank_key, {})
        if not v.get("available"):
            continue
        q_result = v["quartiles"]
        monotonic = q_result.get("monotonic")
        label = v["label"]
        mono_tag = "  [monotonic]" if monotonic is True else ("  [NOT monotonic]" if monotonic is False else "")
        lines.append(f"  {label}{mono_tag}")
        quartiles = q_result.get("quartiles", [])
        if not quartiles:
            lines.append("     (insufficient data for quartile analysis)")
            continue
        lines.append(f"    {'Quartile':<20s} {'Count':>6s} {'Rank Range':>16s} {'Avg PnL%':>10s} {'Win%':>8s}")
        lines.append(f"    {'-'*20} {'-'*6} {'-'*16} {'-'*10} {'-'*8}")
        for q in quartiles:
            rr = q.get("rank_range", (0, 0))
            lines.append(
                f"    {q['label']:<20s} {q['count']:>6d} "
                f"[{rr[0]:5.1f} - {rr[1]:5.1f}] "
                f"{q['avg_pnl']:>+10.3f} {q['win_rate']:>7.1f}%"
            )
        lines.append("")

    # ── Section 4: False Positive Rates ──────────────────────────
    lines.append("  4. FALSE POSITIVE ANALYSIS  (precision at rank thresholds)")
    lines.append("     (What % of high-rank signals actually won?)")
    lines.append("")
    header = f"  {'Threshold':<12s}"
    for rank_key, _ in RANKING_SYSTEMS:
        v = systems.get(rank_key, {})
        if v.get("available"):
            header += f" {v['label'][:18]:>22s}"
    lines.append(header)
    n_available = sum(1 for rk, _ in RANKING_SYSTEMS if systems.get(rk, {}).get("available", False))
    lines.append(f"  {'-'*12}{'  ----------------------' * n_available}")

    # Row per threshold
    for thresh in PRECISION_THRESHOLDS:
        row = f"  {f'rank >= {thresh:.0f}':<12s}"
        for rank_key, _ in RANKING_SYSTEMS:
            v = systems.get(rank_key, {})
            if not v.get("available"):
                continue
            fp_data = v["false_positives"]
            level = next((l for l in fp_data.get("levels", []) if l["threshold"] == thresh), None)
            if level and level["count"] > 0:
                row += f"  {level['win_rate']:>6.1f}% win ({level['count']:>3d} trades)"
            else:
                row += f"  {'no trades':>18s}"
        best_tag = ""
        if thresh == 70.0 and summary.get("best_precision_at_70"):
            best_key = summary.get("best_precision_at_70")
            best_label = systems.get(best_key, {}).get("label", best_key)
            best_tag = f"  <-- {best_label}"
        lines.append(row + best_tag)

    # ── Section 5: Regime Consistency ────────────────────────────
    lines.append("")
    lines.append("  5. REGIME CONSISTENCY")
    lines.append("     (spread across market regimes; consistent = reliable)")
    lines.append("")
    # Collect all regimes from any system
    all_regimes: set = set()
    for rank_key, _ in RANKING_SYSTEMS:
        v = systems.get(rank_key, {})
        if v.get("available"):
            all_regimes.update(v.get("by_regime", {}).keys())

    for regime in sorted(all_regimes):
        lines.append(f"  Regime: {regime}")
        lines.append(f"    {'System':<30s} {'Count':>6s} {'Spread':>10s} {'IC':>10s}")
        lines.append(f"    {'-'*30} {'-'*6} {'-'*10} {'-'*10}")
        for rank_key, _ in RANKING_SYSTEMS:
            v = systems.get(rank_key, {})
            if not v.get("available"):
                continue
            rd = v.get("by_regime", {}).get(regime, {})
            label = v["label"]
            if rd.get("skip"):
                lines.append(f"    {label:<30s} {rd['count']:>6d}  (too few trades)")
            else:
                lines.append(
                    f"    {label:<30s} {rd.get('count',0):>6d} "
                    f"{_fmt(rd.get('spread')):>10s} "
                    f"{_fmt(rd.get('spearman_ic')):>10s}"
                )
        lines.append("")

    # ── Section 6: Comparative Summary ───────────────────────────
    lines.append("=" * W)
    lines.append("  COMPARATIVE SUMMARY")
    lines.append("=" * W)
    lines.append("")

    best_map = {
        "Winner-Loser Spread":     summary.get("best_spread"),
        "Pearson Correlation":     summary.get("best_pearson_correlation"),
        "Spearman IC":             summary.get("best_spearman_ic"),
        "Precision at rank >= 70": summary.get("best_precision_at_70"),
    }
    label_map = {k: v.get("label", k) for k, v in systems.items() if v.get("available")}
    score_counter: Dict[str, int] = {k: 0 for k in label_map}

    for metric, winner in best_map.items():
        winner_label = label_map.get(winner, "N/A") if winner else "N/A"
        lines.append(f"  Best {metric:<28s}: {winner_label}")
        if winner and winner in score_counter:
            score_counter[winner] += 1

    lines.append("")
    lines.append("  Overall score (wins across all metrics):")
    for rank_key, score in sorted(score_counter.items(), key=lambda x: -x[1]):
        label = label_map.get(rank_key, rank_key)
        bar = "=" * score + "-" * (4 - score)
        lines.append(f"    [{bar}] {score}/4  {label}")

    # Recommendation
    lines.append("")
    best_overall = max(score_counter, key=score_counter.get, default=None)
    if best_overall and score_counter[best_overall] > 0:
        best_label = label_map.get(best_overall, best_overall)
        if best_overall == "smart_rank":
            lines.append("  RECOMMENDATION: Current production SmartRank leads — maintain status quo.")
        elif best_overall == "final_rank" and score_counter[best_overall] >= 3:
            lines.append("  RECOMMENDATION: Final Rank leads consistently — consider A/B testing.")
        elif best_overall == "multi_factor_rank" and score_counter[best_overall] >= 3:
            lines.append("  RECOMMENDATION: Multi-Factor leads — re-evaluate hybrid blend weights.")
        else:
            lines.append(f"  RECOMMENDATION: No clear winner ({best_label} leads narrowly).")
            lines.append("                   Extend backtest period before concluding.")

    lines.append("")
    lines.append("=" * W)
    return "\n".join(lines)


def _fmt(value: object) -> str:
    """Format a number for the report table; handle NaN gracefully."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "    N/A"
    if isinstance(value, float):
        return f"{value:+.3f}" if abs(value) < 100 else f"{value:.2f}"
    return str(value)
