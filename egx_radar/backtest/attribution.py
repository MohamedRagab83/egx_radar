"""
Edge Attribution & Trade Explainability Engine
===============================================

For EVERY trade: explains WHY it was taken, WHAT signals triggered it,
WHICH filters passed, WHICH risks existed, and WHY it succeeded or failed.

Analysis only - does NOT modify any trading logic.

Phases:
  1. Signal breakdown per trade (re-evaluates snapshot at signal_date)
  2. Trade outcome classification (WIN/LOSS/BREAKEVEN + reasons)
  3. Edge analysis (win rates by trade_type, regime, smart_rank range)
  4. Failure pattern detection (top causes of losses)
  5. Edge preservation rules (what to avoid vs. prioritize)
  6. Final report and live-trading assessment
"""
from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from egx_radar.config.settings import K, SYMBOLS, get_sector
from egx_radar.core.signal_engine import evaluate_symbol_snapshot

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1 -- Signal Breakdown
# ---------------------------------------------------------------------------

def attribute_trade(
    trade: Dict[str, Any],
    all_data: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    """
    Re-evaluate evaluate_symbol_snapshot at the trade's signal_date to
    recover all signal attribution fields not stored in the trade record.

    Returns the trade dict extended with:
      signals:  accumulation_detected, volume_confirmed, higher_lows,
                trend_alignment_score, zone, adx, rsi, vol_ratio, pct_ema200,
                structure_strength_score, momentum, quantum
      filters:  timing_ok, high_quality_pass, regime
      context:  all raw snapshot fields (for debugging)
    """
    sym         = trade["sym"]
    signal_date = trade.get("signal_date", "")
    regime      = trade.get("regime", "BULL")    # stored by backtest engine

    yahoo = SYMBOLS.get(sym)
    if not yahoo or yahoo not in all_data:
        return {**trade, "_attribution_error": "symbol_not_in_data"}

    df = all_data[yahoo]
    if df is None or df.empty:
        return {**trade, "_attribution_error": "empty_dataframe"}

    # Build df_slice exactly as backtest engine does at signal_date
    try:
        sig_ts  = pd.Timestamp(signal_date)
        df_slice = df[df.index <= sig_ts].tail(260).copy()
    except Exception:
        return {**trade, "_attribution_error": "bad_signal_date"}

    if len(df_slice) < K.MIN_BARS:
        return {**trade, "_attribution_error": "insufficient_bars"}

    # Re-evaluate snapshot (read-only - no trading logic modified)
    try:
        snapshot = evaluate_symbol_snapshot(
            df_ta=df_slice,
            sym=sym,
            sector=get_sector(sym),
            regime=regime,
        )
    except Exception as exc:
        return {**trade, "_attribution_error": f"snapshot_failed: {exc}"}

    if snapshot is None:
        return {**trade, "_attribution_error": "snapshot_returned_none"}

    def fb(key: str, default: bool = False) -> bool:
        return bool(snapshot.get(key, default))

    def ff(key: str, default: float = 0.0) -> float:
        v = snapshot.get(key, default)
        try:
            f = float(v)
            return f if math.isfinite(f) else default
        except (TypeError, ValueError):
            return default

    # --- Phase 1: Signal breakdown ---
    signals = {
        "accumulation_detected":    fb("accumulation_detected"),
        "volume_confirmed":         fb("volume_confirmed"),
        "higher_lows":              fb("higher_lows"),
        "trend_alignment":          ff("trend_alignment_score") >= 50.0,
        "structure_strong":         ff("structure_strength_score") >= 50.0,
        "break_confirmed":          fb("break_confirmed"),
        "erratic_volume":           fb("erratic_volume"),
        "fake_move":                fb("fake_move"),
    }

    _raw_zone = str(snapshot.get("zone", ""))
    # Strip non-ASCII chars (zone names may carry emoji prefixes from signal engine)
    _zone_ascii = ''.join(c for c in _raw_zone if ord(c) < 128).strip()
    filters = {
        "timing_ok":          not fb("timing_blocked"),
        "high_quality_pass":  True,    # trade entered => is_high_probability_trade passed
        "regime":             regime,
        "zone":               _zone_ascii,
        "late_zone":          "LATE" in _zone_ascii.upper(),
    }

    context = {
        "adx":                      ff("adx"),
        "rsi":                      ff("rsi"),
        "vol_ratio":                ff("vol_ratio"),
        "pct_ema200":               ff("pct_ema200"),
        "momentum":                 ff("momentum"),
        "quantum":                  ff("quantum"),
        "cmf":                      ff("cmf"),
        "vol_zscore":               ff("vol_zscore"),
        "spread_pct":               ff("spread_pct"),
        "structure_strength_score": ff("structure_strength_score"),
        "accumulation_quality_score": ff("accumulation_quality_score"),
        "trend_alignment_score":    ff("trend_alignment_score"),
        "volume_quality_score":     ff("volume_quality_score"),
        "up_down_volume_ratio":     ff("up_down_volume_ratio"),
        "last_3_days_gain_pct":     ff("last_3_days_gain_pct"),
        "pct_ema200":               ff("pct_ema200"),
        "two_day_gain_pct":         ff("two_day_gain_pct"),
    }

    return {
        **trade,
        "signals": signals,
        "filters": filters,
        "context": context,
        "_attribution_ok": True,
    }


# ---------------------------------------------------------------------------
# Phase 2 -- Outcome Classification
# ---------------------------------------------------------------------------

def classify_outcome(trade: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify the trade outcome and diagnose reasons.

    Uses fields from the trade record + re-attributed signal/context fields.

    Returns the trade extended with:
      result:  "WIN" | "LOSS" | "BREAKEVEN"
      reasons: list of contributing factors
    """
    pnl_pct  = float(trade.get("pnl_pct", 0.0))
    outcome  = str(trade.get("outcome", "")).upper()

    # Raw result
    if pnl_pct > 0.5:
        result = "WIN"
    elif pnl_pct < -0.5:
        result = "LOSS"
    else:
        result = "BREAKEVEN"

    signals = trade.get("signals", {})
    filters = trade.get("filters", {})
    context = trade.get("context", {})

    reasons: List[str] = []

    # --- Positive factors (for wins) ---
    if result == "WIN":
        if signals.get("accumulation_detected"):
            reasons.append("strong_accumulation")
        if signals.get("volume_confirmed"):
            reasons.append("volume_confirmed")
        if signals.get("higher_lows"):
            reasons.append("higher_lows_structure")
        if signals.get("trend_alignment"):
            reasons.append("trend_aligned")
        if signals.get("structure_strong"):
            reasons.append("strong_structure")
        if trade.get("trade_type") == "STRONG":
            reasons.append("strong_tier_signal")
        if float(trade.get("smart_rank", 0)) >= K.TRADE_TYPE_STRONG_MIN:
            reasons.append("high_smart_rank")

    # --- Negative / risk factors (for losses + wins with risks) ---

    # Late zone entry
    if filters.get("late_zone") or "LATE" in filters.get("zone", ""):
        reasons.append("late_entry")

    # Weak volume
    if not signals.get("volume_confirmed"):
        if result == "LOSS":
            reasons.append("weak_volume")

    # Erratic or fake volume
    if signals.get("erratic_volume"):
        reasons.append("erratic_volume")

    # Fake move / false breakout
    if signals.get("fake_move"):
        reasons.append("false_breakout")

    # Overextended move
    gain_3d = float(context.get("last_3_days_gain_pct", 0.0))
    if gain_3d > K.ETF_GAIN_3D_THRESHOLD:
        reasons.append("overextended_move")

    pct_ema200 = float(context.get("pct_ema200", 0.0))
    if pct_ema200 > K.ETF_EMA200_THRESHOLD:
        reasons.append("extended_from_ema200")

    # Bad regime
    regime = filters.get("regime", "BULL")
    if regime == "NEUTRAL" and result == "LOSS":
        reasons.append("weak_regime")

    # Low ADX (no trend momentum)
    adx = float(context.get("adx", 0.0))
    if adx < 14.0 and result == "LOSS":
        reasons.append("low_adx_no_trend")

    # High volume ratio (chasing volume spike)
    vol_ratio = float(context.get("vol_ratio", 1.0))
    if vol_ratio > 3.0 and result == "LOSS":
        reasons.append("volume_spike_chase")

    # Low smart rank
    sr = float(trade.get("smart_rank", 0.0))
    if sr < K.BT_MIN_SMARTRANK + 5.0 and result == "LOSS":
        reasons.append("borderline_smart_rank")

    # No structure signals at all and resulted in loss
    if (result == "LOSS"
            and not signals.get("accumulation_detected")
            and not signals.get("higher_lows")
            and not signals.get("volume_confirmed")):
        reasons.append("missing_all_quality_signals")

    # Max duration hit without profit
    if "MAX_DURATION" in outcome or str(trade.get("outcome", "")) == "EXIT":
        if pnl_pct <= 0:
            reasons.append("max_duration_no_profit")

    if not reasons:
        reasons.append("no_specific_reason_identified")

    return {**trade, "result": result, "reasons": reasons}


# ---------------------------------------------------------------------------
# Phase 3 -- Edge Analysis
# ---------------------------------------------------------------------------

_SR_BANDS: List[Tuple[str, float, float]] = [
    ("SR < 60",    0.0,  60.0),
    ("SR 60-70",  60.0,  70.0),
    ("SR 70-80",  70.0,  80.0),
    ("SR 80-90",  80.0,  90.0),
    ("SR >= 90",  90.0, 999.0),
]


def _pct(wins: int, total: int) -> float:
    return round(wins / total * 100, 1) if total > 0 else 0.0


def _band_label(sr: float) -> str:
    for label, lo, hi in _SR_BANDS:
        if lo <= sr < hi:
            return label
    return "SR >= 90"


def aggregate_edge_stats(
    trades: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute win rates by trade_type, regime, and SmartRank band.
    Only includes trades with valid attribution and a WIN/LOSS/BREAKEVEN result.
    """
    valid = [t for t in trades if t.get("_attribution_ok") and "result" in t]

    def win_rate_for(subset: List[Dict]) -> Dict:
        if not subset:
            return {"win": 0, "loss": 0, "breakeven": 0, "total": 0, "win_rate_pct": 0.0,
                    "avg_pnl_pct": 0.0, "avg_sr": 0.0}
        wins       = sum(1 for t in subset if t["result"] == "WIN")
        losses     = sum(1 for t in subset if t["result"] == "LOSS")
        breakevens = sum(1 for t in subset if t["result"] == "BREAKEVEN")
        pnls       = [float(t.get("pnl_pct", 0.0)) for t in subset]
        srs        = [float(t.get("smart_rank", 0.0)) for t in subset]
        return {
            "win":          wins,
            "loss":         losses,
            "breakeven":    breakevens,
            "total":        len(subset),
            "win_rate_pct": _pct(wins, len(subset)),
            "avg_pnl_pct":  round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
            "avg_sr":       round(sum(srs)  / len(srs),  2) if srs  else 0.0,
        }

    # By trade type
    strong_trades = [t for t in valid if str(t.get("trade_type", "")).upper() == "STRONG"]
    medium_trades = [t for t in valid if str(t.get("trade_type", "")).upper() == "MEDIUM"]

    # By regime
    bull_trades    = [t for t in valid if t.get("filters", {}).get("regime") == "BULL"]
    neutral_trades = [t for t in valid if t.get("filters", {}).get("regime") == "NEUTRAL"]

    # By SmartRank band
    sr_bands: Dict[str, List[Dict]] = defaultdict(list)
    for t in valid:
        label = _band_label(float(t.get("smart_rank", 0.0)))
        sr_bands[label].append(t)

    # By signal quality (all signals present vs. partial)
    full_signal_trades = [
        t for t in valid
        if (t.get("signals", {}).get("accumulation_detected")
            and t.get("signals", {}).get("volume_confirmed")
            and t.get("signals", {}).get("higher_lows"))
    ]
    partial_signal_trades = [t for t in valid if t not in full_signal_trades]

    # By zone
    zone_groups: Dict[str, List[Dict]] = defaultdict(list)
    for t in valid:
        zone = t.get("filters", {}).get("zone", "UNKNOWN")
        zone_clean = zone.split("_")[0] if zone else "UNKNOWN"   # "EARLY_BREAK" -> "EARLY"
        zone_groups[zone_clean].append(t)

    return {
        "overall":          win_rate_for(valid),
        "by_trade_type": {
            "STRONG":       win_rate_for(strong_trades),
            "MEDIUM":       win_rate_for(medium_trades),
        },
        "by_regime": {
            "BULL":         win_rate_for(bull_trades),
            "NEUTRAL":      win_rate_for(neutral_trades),
        },
        "by_sr_band":       {label: win_rate_for(sr_bands[label]) for label in [b[0] for b in _SR_BANDS]},
        "by_signal_quality": {
            "all_three_signals": win_rate_for(full_signal_trades),
            "partial_signals":   win_rate_for(partial_signal_trades),
        },
        "by_zone":          {z: win_rate_for(grp) for z, grp in sorted(zone_groups.items())},
    }


# ---------------------------------------------------------------------------
# Phase 4 -- Failure Pattern Detection
# ---------------------------------------------------------------------------

def detect_failure_patterns(
    trades: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Identify the top 5 reasons for losing trades.
    Also finds winning patterns vs. losing patterns.
    """
    losses = [t for t in trades
              if t.get("_attribution_ok") and t.get("result") == "LOSS"]
    wins   = [t for t in trades
              if t.get("_attribution_ok") and t.get("result") == "WIN"]

    # Count reasons across all losses
    reason_counter: Counter = Counter()
    for t in losses:
        for r in t.get("reasons", []):
            reason_counter[r] += 1

    total_losses = len(losses)
    top_5 = [
        {
            "reason":    reason,
            "count":     count,
            "pct_of_losses": _pct(count, total_losses),
        }
        for reason, count in reason_counter.most_common(5)
    ]

    # Win patterns
    win_reason_counter: Counter = Counter()
    for t in wins:
        for r in t.get("reasons", []):
            win_reason_counter[r] += 1

    total_wins = len(wins)
    top_win_patterns = [
        {
            "reason":  reason,
            "count":   count,
            "pct_of_wins": _pct(count, total_wins),
        }
        for reason, count in win_reason_counter.most_common(5)
    ]

    # Signal presence rates: losses vs wins
    def _signal_rate(subset: List[Dict], key: str) -> float:
        if not subset:
            return 0.0
        return _pct(sum(1 for t in subset if t.get("signals", {}).get(key)), len(subset))

    signal_comparison = {
        "accumulation_detected": {
            "win_pct":  _signal_rate(wins,   "accumulation_detected"),
            "loss_pct": _signal_rate(losses, "accumulation_detected"),
        },
        "volume_confirmed": {
            "win_pct":  _signal_rate(wins,   "volume_confirmed"),
            "loss_pct": _signal_rate(losses, "volume_confirmed"),
        },
        "higher_lows": {
            "win_pct":  _signal_rate(wins,   "higher_lows"),
            "loss_pct": _signal_rate(losses, "higher_lows"),
        },
        "trend_alignment": {
            "win_pct":  _signal_rate(wins,   "trend_alignment"),
            "loss_pct": _signal_rate(losses, "trend_alignment"),
        },
        "structure_strong": {
            "win_pct":  _signal_rate(wins,   "structure_strong"),
            "loss_pct": _signal_rate(losses, "structure_strong"),
        },
    }

    # Context averages: losses vs wins
    def _avg(subset: List[Dict], key: str) -> float:
        vals = [float(t.get("context", {}).get(key, 0.0)) for t in subset]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    context_comparison = {
        "avg_adx":        {"win": _avg(wins, "adx"),        "loss": _avg(losses, "adx")},
        "avg_vol_ratio":  {"win": _avg(wins, "vol_ratio"),  "loss": _avg(losses, "vol_ratio")},
        "avg_rsi":        {"win": _avg(wins, "rsi"),         "loss": _avg(losses, "rsi")},
        "avg_pct_ema200": {"win": _avg(wins, "pct_ema200"), "loss": _avg(losses, "pct_ema200")},
        "avg_3d_gain":    {"win": _avg(wins, "last_3_days_gain_pct"),
                           "loss": _avg(losses, "last_3_days_gain_pct")},
        "avg_structure":  {"win": _avg(wins, "structure_strength_score"),
                           "loss": _avg(losses, "structure_strength_score")},
        "avg_smart_rank": {
            "win":  round(sum(float(t.get("smart_rank",0)) for t in wins) / max(len(wins),1), 1),
            "loss": round(sum(float(t.get("smart_rank",0)) for t in losses) / max(len(losses),1), 1),
        },
    }

    return {
        "total_losses":        total_losses,
        "total_wins":          total_wins,
        "top_5_loss_reasons":  top_5,
        "top_5_win_patterns":  top_win_patterns,
        "signal_comparison":   signal_comparison,
        "context_comparison":  context_comparison,
    }


# ---------------------------------------------------------------------------
# Phase 5 -- Edge Preservation Rules
# ---------------------------------------------------------------------------

def generate_edge_rules(
    edge_stats: Dict[str, Any],
    failure_patterns: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Derive concrete rules:
    - What to AVOID (removing negative expected value trades)
    - What to PRIORITIZE (concentrating on highest edge setups)
    """
    rules_avoid:     List[str] = []
    rules_prioritize: List[str] = []
    evidence:        Dict[str, Any] = {}

    overall = edge_stats.get("overall", {})
    overall_wr = overall.get("win_rate_pct", 0.0)

    # --- By trade type ---
    strong_wr = edge_stats["by_trade_type"]["STRONG"].get("win_rate_pct", 0.0)
    medium_wr = edge_stats["by_trade_type"]["MEDIUM"].get("win_rate_pct", 0.0)
    strong_n  = edge_stats["by_trade_type"]["STRONG"].get("total", 0)
    medium_n  = edge_stats["by_trade_type"]["MEDIUM"].get("total", 0)

    if medium_wr < 45.0 and medium_n >= 5:
        rules_avoid.append(
            f"MEDIUM-tier trades (SR 45-70): {medium_wr}% win rate - below breakeven threshold"
        )
        evidence["medium_tier_risk"] = f"{medium_wr}% vs overall {overall_wr}%"

    if strong_wr > 55.0 and strong_n >= 5:
        rules_prioritize.append(
            f"STRONG-tier trades (SR >= 70): {strong_wr}% win rate - primary edge"
        )
        evidence["strong_tier_edge"] = f"{strong_wr}% win rate, n={strong_n}"

    # --- By regime ---
    bull_wr    = edge_stats["by_regime"]["BULL"].get("win_rate_pct", 0.0)
    neutral_wr = edge_stats["by_regime"]["NEUTRAL"].get("win_rate_pct", 0.0)
    neutral_n  = edge_stats["by_regime"]["NEUTRAL"].get("total", 0)

    if neutral_wr < 50.0 and neutral_n >= 5:
        rules_avoid.append(
            f"NEUTRAL regime entries: {neutral_wr}% win rate - market not supportive"
        )
        evidence["neutral_regime_risk"] = f"{neutral_wr}% vs BULL {bull_wr}%"

    # --- By SmartRank band ---
    for label, lo, hi in _SR_BANDS:
        band = edge_stats["by_sr_band"].get(label, {})
        wr = band.get("win_rate_pct", 0.0)
        n  = band.get("total", 0)
        if n < 3:
            continue
        if wr < 40.0:
            rules_avoid.append(f"SmartRank band {label}: {wr}% win rate (n={n}) - negative edge")
            evidence[f"sr_band_risk_{label}"] = f"{wr}%"
        elif wr > 65.0:
            rules_prioritize.append(f"SmartRank band {label}: {wr}% win rate (n={n}) - strong edge")
            evidence[f"sr_band_edge_{label}"] = f"{wr}%"

    # --- By signal quality ---
    full_wr    = edge_stats["by_signal_quality"]["all_three_signals"].get("win_rate_pct", 0.0)
    partial_wr = edge_stats["by_signal_quality"]["partial_signals"].get("win_rate_pct", 0.0)
    full_n     = edge_stats["by_signal_quality"]["all_three_signals"].get("total", 0)

    if full_wr > partial_wr + 10.0 and full_n >= 5:
        rules_prioritize.append(
            f"Full signal confluence (accum + volume + higher_lows): {full_wr}% vs {partial_wr}% partial"
        )
        evidence["signal_confluence_edge"] = f"{full_wr}% full vs {partial_wr}% partial"

    # -- From failure patterns ---
    sc = failure_patterns.get("signal_comparison", {})
    cc = failure_patterns.get("context_comparison", {})

    vol_win  = sc.get("volume_confirmed", {}).get("win_pct",  0.0)
    vol_loss = sc.get("volume_confirmed", {}).get("loss_pct", 0.0)
    if vol_win > vol_loss + 20.0:
        rules_prioritize.append(
            f"volume_confirmed=True: {vol_win}% of wins vs {vol_loss}% of losses - key filter"
        )

    acc_win  = sc.get("accumulation_detected", {}).get("win_pct",  0.0)
    acc_loss = sc.get("accumulation_detected", {}).get("loss_pct", 0.0)
    if acc_win > acc_loss + 15.0:
        rules_prioritize.append(
            f"accumulation_detected=True: {acc_win}% of wins vs {acc_loss}% of losses"
        )

    # ADX threshold
    adx_win  = cc.get("avg_adx",  {}).get("win",  0.0)
    adx_loss = cc.get("avg_adx",  {}).get("loss", 0.0)
    if adx_win > adx_loss + 3.0:
        rules_avoid.append(
            f"Low ADX setups: avg ADX in losses={adx_loss} vs wins={adx_win} - avoid when ADX < {round(adx_loss)}"
        )

    # Extended moves
    gain_win  = cc.get("avg_3d_gain", {}).get("win",  0.0)
    gain_loss = cc.get("avg_3d_gain", {}).get("loss", 0.0)
    if gain_loss > gain_win + 1.5:
        rules_avoid.append(
            f"Chasing extended moves: avg 3-day gain at entry in losses={gain_loss}% vs wins={gain_win}%"
        )

    # Top failure reason rules
    for fr in failure_patterns.get("top_5_loss_reasons", [])[:3]:
        reason = fr["reason"]
        pct    = fr["pct_of_losses"]
        if reason == "late_entry" and pct > 15:
            rules_avoid.append(f"LATE zone entries: accounts for {pct}% of losses")
        elif reason == "weak_volume" and pct > 20:
            rules_avoid.append(f"Weak volume entries: {pct}% of losses - enforce volume_confirmed")
        elif reason == "weak_regime" and pct > 15:
            rules_avoid.append(f"NEUTRAL regime losses: {pct}% - regime filter critical")
        elif reason == "false_breakout" and pct > 15:
            rules_avoid.append(f"False breakout entries: {pct}% of losses - requires break_confirmed")

    # --- Combined rule for the highest-edge setup ---
    if strong_wr > 60.0 and full_wr > 60.0:
        rules_prioritize.append(
            "HIGHEST EDGE: STRONG-tier + volume_confirmed + higher_lows + accumulation_detected"
            f"  =>  est. {round((strong_wr + full_wr) / 2, 1)}% win rate"
        )

    return {
        "rules_avoid":      rules_avoid,
        "rules_prioritize": rules_prioritize,
        "evidence":         evidence,
    }


# ---------------------------------------------------------------------------
# Phase 6 -- Full Report Generator
# ---------------------------------------------------------------------------

def generate_report(
    attributed_trades: List[Dict[str, Any]],
    edge_stats: Dict[str, Any],
    failure_patterns: Dict[str, Any],
    edge_rules: Dict[str, Any],
    date_from: str,
    date_to: str,
    print_output: bool = True,
) -> str:
    """
    Produce the full text report from all phases.
    Returns the report as a string (and optionally prints it).
    """
    lines: List[str] = []

    def ln(s: str = "") -> None:
        lines.append(s)

    overall  = edge_stats["overall"]
    total    = overall.get("total", 0)
    valid    = sum(1 for t in attributed_trades if t.get("_attribution_ok"))
    errors   = sum(1 for t in attributed_trades if not t.get("_attribution_ok"))

    ln("=" * 72)
    ln("EDGE ATTRIBUTION & TRADE EXPLAINABILITY REPORT")
    ln(f"  Period : {date_from} to {date_to}")
    ln(f"  Trades : {len(attributed_trades)} total  |  {valid} attributed  |  {errors} errors")
    ln("=" * 72)

    # -- Phase 3: Edge analysis ---
    ln()
    ln("PHASE 3 -- EDGE ANALYSIS")
    ln("-" * 72)
    ln(f"  Overall Win Rate : {overall['win_rate_pct']}%"
       f"  (W={overall['win']} L={overall['loss']} BE={overall['breakeven']}"
       f"  total={overall['total']})")
    ln(f"  Avg PnL per trade: {overall['avg_pnl_pct']}%")
    ln()

    # By trade type
    ln("  BY TRADE TYPE:")
    for tt, data in edge_stats["by_trade_type"].items():
        if data["total"] == 0:
            continue
        ln(f"    {tt:8} trades: {data['win_rate_pct']:5.1f}% WR"
           f"  avg_pnl={data['avg_pnl_pct']:+.2f}%  n={data['total']}"
           f"  avg_SR={data['avg_sr']:.1f}")

    ln()
    ln("  BY REGIME:")
    for reg, data in edge_stats["by_regime"].items():
        if data["total"] == 0:
            continue
        ln(f"    {reg:8} regime: {data['win_rate_pct']:5.1f}% WR"
           f"  avg_pnl={data['avg_pnl_pct']:+.2f}%  n={data['total']}")

    ln()
    ln("  BY SMARTRANK BAND:")
    for label, lo, hi in _SR_BANDS:
        data = edge_stats["by_sr_band"].get(label, {})
        if data.get("total", 0) == 0:
            continue
        ln(f"    {label:12}: {data['win_rate_pct']:5.1f}% WR"
           f"  avg_pnl={data['avg_pnl_pct']:+.2f}%  n={data['total']}")

    ln()
    ln("  BY SIGNAL QUALITY (accum + volume + higher_lows all present):")
    for sq_label, sq_key in [("All 3 signals", "all_three_signals"), ("Partial signals", "partial_signals")]:
        data = edge_stats["by_signal_quality"].get(sq_key, {})
        if data.get("total", 0) == 0:
            continue
        ln(f"    {sq_label:18}: {data['win_rate_pct']:5.1f}% WR"
           f"  avg_pnl={data['avg_pnl_pct']:+.2f}%  n={data['total']}")

    ln()
    ln("  BY ENTRY ZONE (top zones):")
    zone_sorted = sorted(
        edge_stats["by_zone"].items(),
        key=lambda x: x[1].get("total", 0), reverse=True
    )[:5]
    for zone, data in zone_sorted:
        if data.get("total", 0) == 0:
            continue
        ln(f"    {zone:14}: {data['win_rate_pct']:5.1f}% WR"
           f"  avg_pnl={data['avg_pnl_pct']:+.2f}%  n={data['total']}")

    # -- Phase 4: Failure patterns ---
    ln()
    ln("PHASE 4 -- FAILURE PATTERNS")
    ln("-" * 72)
    ln(f"  Total losses: {failure_patterns['total_losses']}")
    ln()
    ln("  TOP 5 LOSS REASONS:")
    for i, fr in enumerate(failure_patterns["top_5_loss_reasons"], 1):
        ln(f"    {i}. {fr['reason']:35}  {fr['pct_of_losses']:5.1f}% of losses (n={fr['count']})")

    ln()
    ln("  TOP 5 WIN PATTERNS:")
    for i, wr in enumerate(failure_patterns["top_5_win_patterns"], 1):
        ln(f"    {i}. {wr['reason']:35}  {wr['pct_of_wins']:5.1f}% of wins  (n={wr['count']})")

    ln()
    ln("  SIGNAL PRESENCE: WINS vs LOSSES")
    ln(f"    {'Signal':30}  {'Wins%':7}  {'Losses%':8}  {'Delta':6}")
    ln(f"    {'-'*30}  {'-'*7}  {'-'*8}  {'-'*6}")
    for sig, vals in failure_patterns["signal_comparison"].items():
        wp = vals["win_pct"]
        lp = vals["loss_pct"]
        delta = wp - lp
        sign = "+" if delta >= 0 else ""
        ln(f"    {sig:30}  {wp:6.1f}%  {lp:7.1f}%  {sign}{delta:.1f}%")

    ln()
    ln("  CONTEXT AVERAGES: WINS vs LOSSES")
    ln(f"    {'Metric':25}  {'Wins':8}  {'Losses':8}  {'Delta':8}")
    ln(f"    {'-'*25}  {'-'*8}  {'-'*8}  {'-'*8}")
    for metric, vals in failure_patterns["context_comparison"].items():
        wv = vals["win"]
        lv = vals["loss"]
        delta = wv - lv
        sign = "+" if delta >= 0 else ""
        ln(f"    {metric:25}  {wv:8.2f}  {lv:8.2f}  {sign}{delta:.2f}")

    # -- Phase 5: Edge rules ---
    ln()
    ln("PHASE 5 -- EDGE PRESERVATION RULES")
    ln("-" * 72)
    ln()
    ln("  AVOID:")
    if edge_rules["rules_avoid"]:
        for rule in edge_rules["rules_avoid"]:
            ln(f"    - {rule}")
    else:
        ln("    (No clear avoidance rules derived - all segments above breakeven)")

    ln()
    ln("  PRIORITIZE:")
    if edge_rules["rules_prioritize"]:
        for rule in edge_rules["rules_prioritize"]:
            ln(f"    + {rule}")
    else:
        ln("    (No high-conviction edge identified - review sample size)")

    # -- Phase 6: Final assessment ---
    ln()
    ln("PHASE 6 -- FINAL ASSESSMENT")
    ln("-" * 72)

    wr         = overall["win_rate_pct"]
    avg_pnl    = overall["avg_pnl_pct"]
    strong_wr  = edge_stats["by_trade_type"]["STRONG"].get("win_rate_pct", 0.0)
    strong_n   = edge_stats["by_trade_type"]["STRONG"].get("total", 0)

    # Verdict logic
    if total < 20:
        verdict = "INSUFFICIENT_DATA"
        verdict_detail = f"Only {total} trades. Need >= 20 for statistical confidence."
    elif wr >= 60.0 and avg_pnl > 1.0:
        verdict = "STRONG_EDGE"
        verdict_detail = f"{wr}% WR, avg +{avg_pnl}% per trade. Edge is well-defined."
    elif wr >= 55.0 and avg_pnl > 0.0:
        verdict = "MODERATE_EDGE"
        verdict_detail = f"{wr}% WR, avg +{avg_pnl}%. Edge exists but needs refinement."
    elif wr >= 50.0:
        verdict = "MARGINAL_EDGE"
        verdict_detail = f"{wr}% WR - barely above coin flip. Requires filter improvement."
    else:
        verdict = "NO_CLEAR_EDGE"
        verdict_detail = f"{wr}% WR - below 50%. Do NOT trade live without investigation."

    ln(f"  Verdict        : {verdict}")
    ln(f"  Win Rate       : {wr}%")
    ln(f"  Avg PnL/trade  : {avg_pnl:+.2f}%")
    ln(f"  STRONG trades  : {strong_wr}% WR (n={strong_n})")
    ln()
    ln(f"  Assessment     : {verdict_detail}")
    ln()

    # Recommendation
    if verdict in ("STRONG_EDGE", "MODERATE_EDGE"):
        ln("  RECOMMENDATION: Edge is stable enough for live trading with discipline.")
        ln("  Focus capital on STRONG-tier setups with full signal confluence.")
        ln("  Enforce regime filter strictly - do not override NEUTRAL market gates.")
    elif verdict == "MARGINAL_EDGE":
        ln("  RECOMMENDATION: Paper trade / reduce position sizing until edge firms up.")
        ln("  Investigate low win-rate segments and consider removing them.")
    elif verdict == "NO_CLEAR_EDGE":
        ln("  RECOMMENDATION: Do NOT deploy capital. Diagnose root cause first.")
    else:
        ln(f"  RECOMMENDATION: Extend backtest period to >= 40 trades before assessment.")

    ln()
    ln("=" * 72)

    report_str = "\n".join(lines)
    if print_output:
        # Safe print: replace any non-ASCII chars that would crash Windows cp1252 terminals
        safe_str = report_str.encode("ascii", errors="replace").decode("ascii")
        print(safe_str)
    return report_str


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_attribution_analysis(
    date_from: str = "2023-01-01",
    date_to: str   = "2024-12-31",
    max_bars: int  = 20,
    print_output: bool = True,
) -> Dict[str, Any]:
    """
    Full pipeline: backtest -> attribute -> classify -> aggregate -> report.

    Args:
        date_from:    Start of backtest period (needs 260 days of prior data).
        date_to:      End of backtest period.
        max_bars:     Max holding period per trade (passed to run_backtest).
        print_output: Print the report to stdout.

    Returns:
        Full results dict including trades, stats, patterns, rules, report.
    """
    from egx_radar.backtest.engine  import run_backtest
    from egx_radar.backtest.data_loader import load_backtest_data

    if print_output:
        print(f"Step 1: Running backtest {date_from} to {date_to} ...")
    trades, equity_curve, missed, guard_stats = run_backtest(
        date_from, date_to, max_bars=max_bars,
        progress_callback=(lambda s: print(f"  {s}")) if print_output else None,
    )

    if print_output:
        print(f"  Backtest complete: {len(trades)} closed trades.")

    if not trades:
        return {"error": "No trades generated - check date range and data availability"}

    # Load extended history for signal re-attribution (need 260+ bars of warmup)
    # Download 2 years prior to date_from so EMA200 is properly initialised
    load_from = f"{int(date_from[:4]) - 2}{date_from[4:]}"
    if print_output:
        print(f"Step 2: Loading extended history {load_from} to {date_to} for attribution ...")
    all_data = load_backtest_data(load_from, date_to)
    if print_output:
        print(f"  Loaded {len(all_data)} tickers.")

    # Phase 1: Attribute each trade
    if print_output:
        print("Attributing signals to each trade ...")
    attributed: List[Dict] = []
    for trade in trades:
        attr = attribute_trade(trade, all_data)
        attr = classify_outcome(attr)    # Phase 2 inline
        attributed.append(attr)

    attr_ok  = sum(1 for t in attributed if t.get("_attribution_ok"))
    attr_err = len(attributed) - attr_ok
    if print_output:
        print(f"  Attributed: {attr_ok} OK,  {attr_err} errors")

    # Phase 3
    edge_stats = aggregate_edge_stats(attributed)

    # Phase 4
    failure_patterns = detect_failure_patterns(attributed)

    # Phase 5
    edge_rules = generate_edge_rules(edge_stats, failure_patterns)

    # Phase 6: Report
    report_str = generate_report(
        attributed, edge_stats, failure_patterns, edge_rules,
        date_from, date_to, print_output=print_output,
    )

    return {
        "attributed_trades": attributed,
        "equity_curve":      equity_curve,
        "guard_stats":       guard_stats,
        "edge_stats":        edge_stats,
        "failure_patterns":  failure_patterns,
        "edge_rules":        edge_rules,
        "report":            report_str,
    }


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    run_attribution_analysis(
        date_from="2022-01-01",
        date_to="2024-12-31",
        max_bars=20,
    )
