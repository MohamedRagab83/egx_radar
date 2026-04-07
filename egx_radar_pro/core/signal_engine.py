"""
core/signal_engine.py — EGX Radar Pro
==========================================
Signal evaluation and trade entry generation.

Two strategy modes:
- legacy: original SmartRank thresholds (for baseline comparison only)
- v2: strict filter-first engine (production edge rebuild)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd

from config.settings import CFG, RISK, SECTOR_BY_SYMBOL, Snapshot, Trade
from core.indicators import atr_wilder, ema_last, rsi_wilder, volume_ratio
from core.smart_rank import smart_rank_legacy, smart_rank_v2, smart_rank_v2_filters
from ai.probability_engine import probability_engine
from news.news_fetcher import fetch_news
from news.sentiment_engine import sentiment_score
from alpha.alpha_engine import compute_alpha_score
from risk.portfolio import sector_positions
from utils.helpers import clamp
from utils.logger import get_logger

log = get_logger(__name__)


def evaluate_snapshot(
    df_slice: pd.DataFrame,
    symbol: str,
    learning_bias: float = 0.0,
) -> Optional[Snapshot]:
    """Build and enrich one market snapshot from an OHLCV slice."""
    if len(df_slice) < CFG.warmup_bars:
        return None

    c = df_slice["Close"].astype(float)
    v = df_slice["Volume"].astype(float)

    e20 = ema_last(c, 20)
    e50 = ema_last(c, 50)
    e200 = ema_last(c, 200)
    rsi = rsi_wilder(c)
    atr = atr_wilder(df_slice)
    close = float(c.iloc[-1])

    atr_pct = atr / max(close, 1e-9)
    vol_ratio = clamp(volume_ratio(v), 0.0, 4.0)
    trend = clamp((close - e50) / max(e50, 1e-9) * 5.0, 0.0, 1.0)
    structure = clamp((0.5 * float(close > e20) + 0.5 * float(close > e50)) * 100.0, 0.0, 100.0)

    recent_high = float(df_slice["High"].astype(float).tail(CFG.v2_breakout_lookback).max())
    breakout_proximity = close / max(recent_high, 1e-9)

    snap = Snapshot(
        date=df_slice.index[-1],
        symbol=symbol,
        sector=SECTOR_BY_SYMBOL.get(symbol, "OTHER"),
        close=close,
        open=float(df_slice["Open"].iloc[-1]),
        high=float(df_slice["High"].iloc[-1]),
        low=float(df_slice["Low"].iloc[-1]),
        volume=float(v.iloc[-1]),
        rsi=round(rsi, 2),
        atr=round(atr, 4),
        atr_pct=round(atr_pct, 6),
        ema20=round(e20, 3),
        ema50=round(e50, 3),
        ema200=round(e200, 3),
        volume_ratio=round(vol_ratio, 3),
        trend_strength=round(trend, 4),
        structure_score=round(structure, 2),
        smart_rank=0.0,
        smart_rank_v2=0.0,
        breakout_proximity=round(breakout_proximity, 5),
    )

    snap.smart_rank = smart_rank_legacy(snap)
    snap.smart_rank_v2 = smart_rank_v2(snap)

    # Display-only enrichment
    now = snap.date.to_pydatetime().replace(tzinfo=None)
    news = fetch_news(symbol, snap.date)
    snap.sentiment_score = sentiment_score(news, snap, now)
    snap.alpha_score = compute_alpha_score(news, snap, now)
    snap.probability = probability_engine(snap, learning_bias)

    return snap


def _legacy_plan(snapshot: Snapshot) -> Optional[Tuple[str, dict]]:
    if snapshot.smart_rank >= CFG.smart_rank_accumulate:
        entry = snapshot.close
        stop = entry * (1.0 - min(max(snapshot.atr_pct * 1.4, 0.01), 0.03))
        target = entry * 1.08
        return "MAIN", {"entry": entry, "stop": stop, "target": target, "risk_used": RISK.risk_per_trade}

    if snapshot.smart_rank >= CFG.smart_rank_probe:
        entry = snapshot.close
        stop = entry * (1.0 - min(max(snapshot.atr_pct * 1.2, 0.01), 0.025))
        target = entry * 1.06
        return "PROBE", {
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_used": RISK.risk_per_trade * 0.65,
        }
    return None


def _v2_plan(snapshot: Snapshot, params: Optional[Dict] = None) -> Optional[Tuple[str, dict]]:
    passed, _ = smart_rank_v2_filters(snapshot, params)
    if not passed:
        return None

    p = {
        "score_threshold": CFG.v2_score_threshold,
        "stop_atr_mult": CFG.v2_stop_atr_mult,
        "min_rr": CFG.v2_min_rr,
    }
    if params:
        p.update(params)

    score = smart_rank_v2(snapshot, params)
    if score < p["score_threshold"]:
        return None

    entry = snapshot.close
    stop = entry - (snapshot.atr * p["stop_atr_mult"])
    if stop <= 0.0 or stop >= entry:
        return None

    risk_per_share = entry - stop
    target = entry + (max(p["min_rr"], 2.0) * risk_per_share)

    rr = (target - entry) / max(entry - stop, 1e-9)
    if rr < 2.0:
        return None

    return "MAIN", {
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_used": RISK.risk_per_trade,
        "smart_rank_v2": score,
    }


def generate_trade_signal(
    snapshot: Snapshot,
    regime: str,
    open_trades: List[Trade],
    use_ai: bool = True,
    use_alpha: bool = True,
    strategy: str = "legacy",
    strategy_params: Optional[Dict] = None,
) -> Optional[Tuple[str, dict]]:
    """
    Entry decision engine.

    strategy="legacy" for baseline comparison.
    strategy="v2" for strict filter-first execution.
    """
    _ = (use_ai, use_alpha)

    if regime == "BEAR":
        return None

    if sum(1 for t in open_trades if t.status == "OPEN") >= RISK.max_open_trades:
        return None

    if sector_positions(open_trades).get(snapshot.sector, 0) >= RISK.max_sector_positions:
        return None

    if strategy == "v2":
        return _v2_plan(snapshot, strategy_params)

    return _legacy_plan(snapshot)


def format_signal_log(snapshot: Snapshot, decision: str) -> str:
    """Human-readable signal formatting."""
    if snapshot.sentiment_score >= 0.55:
        sentiment_label = "Positive"
    elif snapshot.sentiment_score <= 0.45:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"

    action = "BUY" if decision in {"MAIN", "PROBE"} else "WAIT"
    signal_tag = f" [{decision}]" if action == "BUY" else ""

    return (
        f"SYMBOL: {snapshot.symbol}\n"
        f"SmartRank(legacy): {snapshot.smart_rank:.2f}\n"
        f"SmartRank(2.0):    {snapshot.smart_rank_v2:.2f} -> {action}{signal_tag}\n"
        f"\n"
        f"AI Probability : {snapshot.probability:.4f}\n"
        f"Sentiment      : {snapshot.sentiment_score:.4f} ({sentiment_label})\n"
        f"Alpha Score    : {snapshot.alpha_score:.2f}\n"
        f"\n"
        f"Decision: {action} (strategy-controlled, AI/News/Alpha display only)"
    )
