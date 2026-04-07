from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


# ==================================================
# 1) CONFIGURATION
# ==================================================
SECTORS: Dict[str, List[str]] = {
    "BANKS": ["COMI", "CIEB", "ADIB", "SAUD", "CNFN", "FAIT"],
    "REAL_ESTATE": ["TMGH", "PHDC", "OCDI", "HELI", "DSCW"],
    "INDUSTRIAL": ["ORAS", "SKPC", "KZPC", "AMOC", "ESRS"],
    "SERVICES": ["FWRY", "ETEL", "JUFO", "HRHO", "EGTS", "ORWE"],
    "ENERGY": ["ABUK", "MFPC", "ISPH", "EAST", "SWDY"],
}
SYMBOLS = sorted({s for sec in SECTORS.values() for s in sec})
SECTOR_BY_SYMBOL = {sym: sec for sec, syms in SECTORS.items() for sym in syms}


from egx_radar.config import settings

@dataclass(frozen=True)
class RiskConfig:
    account_size: float = 100_000.0
    risk_per_trade: float = settings.RISK_PER_TRADE_STRONG
    max_open_trades: int = settings.MAX_OPEN_TRADES
    max_sector_positions: int = settings.MAX_SECTOR_POSITIONS
    max_sector_exposure_pct: float = settings.MAX_SECTOR_EXPOSURE_PCT
    slippage_pct: float = settings.SLIPPAGE_PCT
    fee_pct: float = settings.FEE_PCT
    max_bars_hold: int = 20
    partial_exit_fraction: float = settings.PARTIAL_EXIT_FRACTION


@dataclass(frozen=True)
class EngineConfig:
    warmup_bars: int = 80
    smart_rank_accumulate: float = 70.0
    smart_rank_probe: float = 55.0
    alpha_min_score: float = 70.0
    alpha_sr_cap: float = 60.0


RISK = RiskConfig()
CFG = EngineConfig()


# ==================================================
# 2) DATA STRUCTURES
# ==================================================
@dataclass
class Snapshot:
    date: pd.Timestamp
    symbol: str
    sector: str
    close: float
    open: float
    high: float
    low: float
    volume: float
    rsi: float
    atr: float
    atr_pct: float
    ema20: float
    ema50: float
    ema200: float
    volume_ratio: float
    trend_strength: float
    structure_score: float
    smart_rank: float
    probability: float = 0.5
    sentiment_score: float = 0.5
    alpha_score: float = 0.0


@dataclass
class Trade:
    symbol: str
    sector: str
    entry_date: pd.Timestamp
    entry: float
    stop: float
    target: float
    size: int
    risk_used: float
    signal_type: str
    smart_rank: float
    probability: float
    sentiment_score: float
    alpha_score: float
    bars_held: int = 0
    status: str = "OPEN"
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl_pct: float = 0.0


# ==================================================
# 3) CORE ENGINES (INDICATORS + SMARTRANK)
# ==================================================
def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def rsi_wilder(close: pd.Series, period: int = 14) -> float:
    arr = close.to_numpy(dtype=float)
    if len(arr) < period + 2:
        return 50.0
    delta = np.diff(arr[-(period + 16):])
    gain = np.maximum(delta, 0.0)
    loss = np.maximum(-delta, 0.0)
    g = float(np.mean(gain[-period:]))
    l = float(np.mean(loss[-period:]))
    if l <= 1e-9:
        return 100.0 if g > 0 else 50.0
    rs = g / l
    return 100.0 - (100.0 / (1.0 + rs))


def atr_wilder(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period + 2:
        return 0.0
    hi = df["High"].to_numpy(dtype=float)
    lo = df["Low"].to_numpy(dtype=float)
    cl = df["Close"].to_numpy(dtype=float)
    n = min(len(df), period + 24)
    hi = hi[-n:]
    lo = lo[-n:]
    cl = cl[-n:]
    prev_close = np.roll(cl, 1)
    prev_close[0] = cl[0]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev_close), np.abs(lo - prev_close)))
    atr = float(np.mean(tr[-period:]))
    return atr if math.isfinite(atr) else 0.0


def smart_rank(snapshot: Snapshot) -> float:
    flow = _clamp(snapshot.volume_ratio / 2.2, 0.0, 1.0)
    structure = _clamp(snapshot.structure_score / 100.0, 0.0, 1.0)
    timing = _clamp((snapshot.rsi - 35.0) / 40.0, 0.0, 1.0)
    momentum = _clamp(snapshot.trend_strength, 0.0, 1.0)
    regime = 1.0 if snapshot.close > snapshot.ema200 else 0.4
    neural = 0.5
    score = (
        0.30 * flow
        + 0.25 * structure
        + 0.20 * timing
        + 0.10 * momentum
        + 0.10 * regime
        + 0.05 * neural
    ) * 100.0
    return round(_clamp(score, 0.0, 100.0), 2)


# ==================================================
# 4) MARKET ANALYSIS
# ==================================================
def detect_market_regime(universe_snaps: List[Snapshot]) -> str:
    if not universe_snaps:
        return "NEUTRAL"
    breadth_ema50 = sum(1 for s in universe_snaps if s.close > s.ema50) / len(universe_snaps)
    breadth_ema200 = sum(1 for s in universe_snaps if s.close > s.ema200) / len(universe_snaps)
    avg_rank = sum(s.smart_rank for s in universe_snaps) / len(universe_snaps)
    if breadth_ema50 >= 0.60 and breadth_ema200 >= 0.55 and avg_rank >= 52:
        return "BULL"
    if breadth_ema50 <= 0.35 or avg_rank < 42:
        return "BEAR"
    return "NEUTRAL"


def sector_strength(snaps: List[Snapshot]) -> Dict[str, float]:
    out: Dict[str, List[float]] = {}
    for s in snaps:
        out.setdefault(s.sector, []).append(s.smart_rank)
    return {k: round(float(np.mean(v)), 2) for k, v in out.items() if v}


# ==================================================
# 5) AI SYSTEM
# ==================================================
@dataclass
class LearningState:
    wins: int = 0
    losses: int = 0
    avg_pnl: float = 0.0


class LearningModule:
    def __init__(self, path: str = "pro_learning_state.json") -> None:
        self.path = Path(path)
        self.state = LearningState()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.state = LearningState(
                wins=int(raw.get("wins", 0)),
                losses=int(raw.get("losses", 0)),
                avg_pnl=float(raw.get("avg_pnl", 0.0)),
            )
        except Exception:
            self.state = LearningState()

    def record(self, pnl_pct: float) -> None:
        if pnl_pct >= 0:
            self.state.wins += 1
        else:
            self.state.losses += 1
        n = self.state.wins + self.state.losses
        self.state.avg_pnl = ((self.state.avg_pnl * (n - 1)) + pnl_pct) / max(n, 1)
        self.path.write_text(
            json.dumps({
                "wins": self.state.wins,
                "losses": self.state.losses,
                "avg_pnl": round(self.state.avg_pnl, 4),
            }, indent=2),
            encoding="utf-8",
        )


def probability_engine(snapshot: Snapshot, learning_bias: float = 0.0) -> float:
    x = (
        0.34 * (snapshot.smart_rank / 100.0)
        + 0.20 * (snapshot.structure_score / 100.0)
        + 0.16 * _clamp((snapshot.rsi - 35) / 40, 0, 1)
        + 0.10 * _clamp(snapshot.volume_ratio / 2.5, 0, 1)
        + 0.08 * _clamp(snapshot.trend_strength, 0, 1)
        - 0.10 * _clamp(snapshot.atr_pct / 0.08, 0, 1)
        + learning_bias
    )
    centered = (x - 0.50) * 6.0
    p = 1.0 / (1.0 + math.exp(-centered))
    p = p * (0.95 + 0.1 * snapshot.sentiment_score)
    return round(_clamp(p, 0.05, 0.95), 4)


def classify_decision(probability: float) -> str:
    if probability >= 0.68:
        return "STRONG"
    if probability >= 0.55:
        return "MEDIUM"
    return "WEAK"


# ==================================================
# 6) NEWS SYSTEM (EGX OPTIMIZED)
# ==================================================
POSITIVE_PHRASES = {
    "نمو قوي": 2.0,
    "زيادة الإيرادات": 2.0,
    "تحسن الهوامش": 1.5,
    "صفقة استحواذ": 2.5,
}
NEGATIVE_PHRASES = {
    "تراجع الأرباح": -2.0,
    "ضغوط تمويلية": -2.0,
    "ارتفاع المديونية": -2.0,
}
CRITICAL_PHRASES = {
    "خسائر كبيرة": -3.0,
    "إيقاف التداول": -3.0,
    "تحقيق رسمي": -3.0,
}


def fetch_news(symbol: str, date: pd.Timestamp) -> List[dict]:
    # In production this would call RSS/API feeds. Here we keep it deterministic/runnable.
    seed = abs(hash((symbol, str(date.date())))) % 100
    if seed < 90:
        return []
    title = "نمو قوي وزيادة الإيرادات" if seed % 2 == 0 else "تراجع الأرباح وضغوط تمويلية"
    source = "egx_official" if seed % 3 == 0 else "mubasher"
    return [{
        "title": title,
        "content": title,
        "source": source,
        "timestamp": date.to_pydatetime(),
    }]


def analyze_arabic_sentiment(text: str) -> float:
    score = 0.0
    for k, v in POSITIVE_PHRASES.items():
        if k in text:
            score += v
    for k, v in NEGATIVE_PHRASES.items():
        if k in text:
            score += v
    for k, v in CRITICAL_PHRASES.items():
        if k in text:
            score += v
    return _clamp(score, -3.0, 3.0)


def classify_news_type(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["نتائج", "أرباح", "earnings", "results"]):
        return "earnings"
    if any(x in t for x in ["توزيع", "dividend", "coupon"]):
        return "dividend"
    if any(x in t for x in ["استحواذ", "merger", "acquisition"]):
        return "acquisition"
    if any(x in t for x in ["توسع", "expansion", "project", "مشروع"]):
        return "expansion"
    return "general"


def news_strength(news: dict) -> float:
    cred = {
        "egx_official": 1.0,
        "company_announcements": 0.95,
        "mubasher": 0.82,
        "investing_egypt": 0.72,
    }.get(str(news.get("source", "")).lower(), 0.55)
    typ = classify_news_type(f"{news.get('title','')} {news.get('content','')}")
    imp = {
        "earnings": 1.0,
        "dividend": 0.82,
        "acquisition": 0.94,
        "expansion": 0.88,
        "general": 0.60,
    }[typ]
    return round(_clamp(0.55 * cred + 0.45 * imp, 0.0, 1.0), 4)


def news_decay(hours_old: float) -> float:
    if hours_old < 6:
        return 1.0
    if hours_old < 24:
        return 0.7
    if hours_old < 48:
        return 0.5
    return 0.3


def market_reaction_factor(snapshot: Snapshot, sentiment: float) -> float:
    impact = 1.0
    if sentiment > 0 and snapshot.rsi < 50:
        impact *= 0.6
    if sentiment < 0 and snapshot.rsi > 60:
        impact *= 0.6
    if snapshot.volume_ratio > 1.5:
        impact *= 1.1
    return _clamp(impact, 0.4, 1.2)


def sentiment_score(news_list: List[dict], snapshot: Snapshot, now: datetime) -> float:
    if not news_list:
        return 0.5
    total = 0.0
    for n in news_list:
        txt = f"{n.get('title','')} {n.get('content','')}"
        s = analyze_arabic_sentiment(txt)
        ts = n.get("timestamp", now)
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()
        if ts.tzinfo is not None:
            ts = ts.astimezone(UTC).replace(tzinfo=None)
        age_h = max((now - ts).total_seconds() / 3600.0, 0.0)
        total += s * news_decay(age_h) * market_reaction_factor(snapshot, s)
    norm = (total + 5.0) / 10.0
    return round(_clamp(norm, 0.0, 1.0), 4)


# ==================================================
# 7) ALPHA ENGINE
# ==================================================
def compute_alpha_score(news_list: List[dict], snapshot: Snapshot, now: datetime) -> float:
    if not news_list:
        return 0.0
    raw = 0.0
    for n in news_list:
        txt = f"{n.get('title','')} {n.get('content','')}"
        sent = analyze_arabic_sentiment(txt)
        ts = n.get("timestamp", now)
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()
        if ts.tzinfo is not None:
            ts = ts.astimezone(UTC).replace(tzinfo=None)
        age_h = max((now - ts).total_seconds() / 3600.0, 0.0)
        raw += sent * news_strength(n) * news_decay(age_h) * market_reaction_factor(snapshot, sent)
    score = 50.0 + raw * (50.0 / 3.0)
    return round(_clamp(score, 0.0, 100.0), 2)


def alpha_filter(snapshot: Snapshot, alpha_score: float) -> Tuple[bool, str]:
    if alpha_score < 60:
        return False, "alpha_below_60"
    if snapshot.atr_pct > 0.06:
        return False, "atr_too_high"
    if snapshot.volume_ratio < 1.3:
        return False, "volume_too_low"
    if snapshot.rsi < 45:
        return False, "rsi_too_low"
    return True, "alpha_pass"


def build_alpha_trade(snapshot: Snapshot, alpha_score: float) -> dict:
    pullback = min(max(snapshot.atr * 0.35, snapshot.close * 0.003), snapshot.close * 0.015)
    entry = max(snapshot.low, snapshot.close - pullback)
    risk_pct = _clamp((entry - snapshot.low * 0.995) / max(entry, 1e-9), 0.008, 0.025)
    target_pct = max(0.04, risk_pct * 2.2)
    scale = min(0.20, max(0.08, (alpha_score - 60.0) / 200.0))
    return {
        "entry": round(entry, 3),
        "stop": round(entry * (1.0 - risk_pct), 3),
        "target": round(entry * (1.0 + target_pct), 3),
        "risk_pct": round(risk_pct, 4),
        "target_pct": round(target_pct, 4),
        "position_scale": round(scale, 4),
        "alpha_score": round(alpha_score, 2),
    }


# ==================================================
# 8) RISK MANAGEMENT
# ==================================================
def sector_positions(open_trades: List[Trade]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for t in open_trades:
        if t.status == "OPEN":
            out[t.sector] = out.get(t.sector, 0) + 1
    return out


def compute_position_size(entry: float, stop: float, risk_used: float, account_size: float) -> int:
    risk_amount = account_size * risk_used
    risk_per_share = max(entry - stop, entry * 0.005)
    if risk_amount <= 0:
        return 0
    return max(1, int(risk_amount / max(risk_per_share, 1e-9)))


# ==================================================
# 9) SIGNAL ENGINE
# ==================================================
def evaluate_snapshot(df_slice: pd.DataFrame, symbol: str, learning_bias: float = 0.0) -> Optional[Snapshot]:
    if len(df_slice) < CFG.warmup_bars:
        return None
    c = df_slice["Close"].astype(float)
    v = df_slice["Volume"].astype(float)
    ema20 = float(c.ewm(span=20, adjust=False).mean().iloc[-1])
    ema50 = float(c.ewm(span=50, adjust=False).mean().iloc[-1])
    ema200 = float(c.ewm(span=200, adjust=False).mean().iloc[-1])
    rsi = rsi_wilder(c)
    atr = atr_wilder(df_slice)
    close = float(c.iloc[-1])
    atr_pct = atr / max(close, 1e-9)
    avg_vol = float(v.rolling(20).mean().iloc[-1]) if len(v) >= 20 else float(v.mean())
    vol_ratio = float(v.iloc[-1]) / max(avg_vol, 1e-9)
    trend = _clamp((close - ema50) / max(ema50, 1e-9) * 5.0, 0.0, 1.0)
    structure = _clamp((0.5 * (close > ema20) + 0.5 * (close > ema50)) * 100.0, 0.0, 100.0)

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
        ema20=round(ema20, 3),
        ema50=round(ema50, 3),
        ema200=round(ema200, 3),
        volume_ratio=round(_clamp(vol_ratio, 0.0, 4.0), 3),
        trend_strength=round(trend, 4),
        structure_score=round(structure, 2),
        smart_rank=0.0,
    )
    snap.smart_rank = smart_rank(snap)

    now = snap.date.to_pydatetime().replace(tzinfo=None)
    news = fetch_news(symbol, snap.date)
    snap.sentiment_score = sentiment_score(news, snap, now)
    snap.alpha_score = compute_alpha_score(news, snap, now)
    snap.probability = probability_engine(snap, learning_bias)
    return snap


def generate_trade_signal(
    snapshot: Snapshot,
    regime: str,
    open_trades: List[Trade],
    use_ai: bool,
    use_alpha: bool,
) -> Optional[Tuple[str, dict]]:
    # AI/News/Alpha stay computed for display, but execution is SmartRank-only.
    _ = (use_ai, use_alpha)

    if regime == "BEAR":
        return None
    if len([t for t in open_trades if t.status == "OPEN"]) >= RISK.max_open_trades:
        return None

    sec_pos = sector_positions(open_trades)
    if sec_pos.get(snapshot.sector, 0) >= RISK.max_sector_positions:
        return None

    if snapshot.smart_rank >= CFG.smart_rank_accumulate:
        entry = snapshot.close
        stop = entry * (1.0 - min(max(snapshot.atr_pct * 1.4, 0.01), 0.03))
        target = entry * 1.08
        return "MAIN", {
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_used": RISK.risk_per_trade,
        }

    if snapshot.smart_rank >= CFG.smart_rank_probe and regime != "BEAR":
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


def format_signal_log(snapshot: Snapshot, decision: str) -> str:
    sentiment_label = "Positive" if snapshot.sentiment_score >= 0.55 else "Negative" if snapshot.sentiment_score <= 0.45 else "Neutral"
    decision_text = "BUY" if decision in {"MAIN", "PROBE"} else "WAIT"
    return (
        f"SYMBOL: {snapshot.symbol}\n"
        f"SmartRank: {snapshot.smart_rank:.2f} -> {decision_text}\n\n"
        f"AI Probability: {snapshot.probability:.4f}\n"
        f"Sentiment: {snapshot.sentiment_score:.4f} ({sentiment_label})\n"
        f"Alpha Score: {snapshot.alpha_score:.2f}\n\n"
        f"Decision: {decision_text} (SmartRank only)"
    )


def print_signal_preview(market_data: Dict[str, pd.DataFrame]) -> None:
    latest = min(df.index.max() for df in market_data.values() if not df.empty)
    snaps: List[Snapshot] = []
    for sym, df in market_data.items():
        if latest not in df.index:
            continue
        snap = evaluate_snapshot(df[df.index <= latest].tail(260), sym, learning_bias=0.0)
        if snap is not None:
            snaps.append(snap)

    if not snaps:
        return

    regime = detect_market_regime(snaps)
    print("\n=== SIGNAL PREVIEW (SmartRank-driven execution) ===")
    shown = 0
    for snap in sorted(snaps, key=lambda x: x.smart_rank, reverse=True):
        sig = generate_trade_signal(snap, regime, [], use_ai=True, use_alpha=True)
        decision = sig[0] if sig is not None else "WAIT"
        if decision == "WAIT" and shown >= 5:
            continue
        print(format_signal_log(snap, decision))
        print()
        shown += 1
        if shown >= 5:
            break


# ==================================================
# 10) BACKTEST ENGINE
# ==================================================
def _close_trade(t: Trade, px: float, date: pd.Timestamp, reason: str) -> None:
    gross = (px - t.entry) / max(t.entry, 1e-9) * 100.0
    net = gross - (RISK.fee_pct * 100.0)
    t.exit_price = float(px)
    t.exit_date = date
    t.status = reason
    t.pnl_pct = float(net)


def run_backtest(
    market_data: Dict[str, pd.DataFrame],
    use_ai: bool,
    use_alpha: bool,
    learning: Optional[LearningModule] = None,
) -> Tuple[List[Trade], List[Tuple[str, float]]]:
    all_dates = sorted({d for df in market_data.values() for d in df.index})
    open_trades: List[Trade] = []
    closed: List[Trade] = []
    equity = 100.0
    curve: List[Tuple[str, float]] = []

    for i, date in enumerate(all_dates):
        snaps: List[Snapshot] = []
        for sym, df in market_data.items():
            if date not in df.index:
                continue
            df_slice = df[df.index <= date].tail(260)
            bias = 0.0
            if learning is not None:
                n = learning.state.wins + learning.state.losses
                if n >= 10:
                    wr = learning.state.wins / max(n, 1)
                    bias = (wr - 0.5) * 0.2
            snap = evaluate_snapshot(df_slice, sym, learning_bias=bias)
            if snap is not None:
                snaps.append(snap)

        regime = detect_market_regime(snaps)

        # Update open trades
        for t in list(open_trades):
            sym_df = market_data[t.symbol]
            if date not in sym_df.index:
                continue
            row = sym_df.loc[date]
            t.bars_held += 1
            open_px = float(row["Open"])
            high = float(row["High"])
            low = float(row["Low"])
            close = float(row["Close"])

            if open_px <= t.stop:
                _close_trade(t, open_px * (1.0 - RISK.slippage_pct), date, "STOP")
            elif low <= t.stop:
                _close_trade(t, t.stop * (1.0 - RISK.slippage_pct), date, "STOP")
            elif high >= t.target:
                _close_trade(t, t.target * (1.0 - RISK.slippage_pct), date, "TARGET")
            elif t.bars_held >= RISK.max_bars_hold:
                _close_trade(t, close * (1.0 - RISK.slippage_pct), date, "TIME")
            else:
                continue

            alloc_pct = min((t.entry * t.size) / max(RISK.account_size, 1e-9), RISK.max_sector_exposure_pct)
            equity *= 1.0 + alloc_pct * (t.pnl_pct / 100.0)
            closed.append(t)
            if learning is not None:
                learning.record(t.pnl_pct)
            open_trades.remove(t)

        # Generate new entries
        if i + 1 < len(all_dates):
            next_date = all_dates[i + 1]
            taken_today: set[str] = set(t.symbol for t in open_trades)
            for s in sorted(snaps, key=lambda x: x.smart_rank, reverse=True):
                if s.symbol in taken_today:
                    continue
                sig = generate_trade_signal(s, regime, open_trades, use_ai=use_ai, use_alpha=use_alpha)
                if sig is None:
                    continue
                signal_type, plan = sig
                next_df = market_data[s.symbol]
                if next_date not in next_df.index:
                    continue
                next_open = float(next_df.loc[next_date]["Open"])
                entry = float(plan["entry"])
                stop = float(plan["stop"])
                target = float(plan["target"])
                risk_used = float(plan["risk_used"])
                size = compute_position_size(entry, stop, risk_used, RISK.account_size)
                if size <= 0:
                    continue

                open_trades.append(
                    Trade(
                        symbol=s.symbol,
                        sector=s.sector,
                        entry_date=next_date,
                        entry=next_open * (1.0 + RISK.slippage_pct),
                        stop=stop,
                        target=target,
                        size=size,
                        risk_used=risk_used,
                        signal_type=signal_type,
                        smart_rank=s.smart_rank,
                        probability=s.probability,
                        sentiment_score=s.sentiment_score,
                        alpha_score=s.alpha_score,
                    )
                )
                taken_today.add(s.symbol)
                if len(open_trades) >= RISK.max_open_trades:
                    break

        curve.append((date.strftime("%Y-%m-%d"), round(equity - 100.0, 3)))

    # Force-close remaining
    if all_dates:
        last = all_dates[-1]
        for t in list(open_trades):
            row = market_data[t.symbol].loc[last]
            _close_trade(t, float(row["Close"]) * (1.0 - RISK.slippage_pct), last, "FINAL")
            alloc_pct = min((t.entry * t.size) / max(RISK.account_size, 1e-9), RISK.max_sector_exposure_pct)
            equity *= 1.0 + alloc_pct * (t.pnl_pct / 100.0)
            closed.append(t)
            if learning is not None:
                learning.record(t.pnl_pct)
        curve[-1] = (curve[-1][0], round(equity - 100.0, 3))

    return closed, curve


# ==================================================
# 11) VALIDATION SYSTEM
# ==================================================
def performance_metrics(trades: List[Trade], curve: List[Tuple[str, float]]) -> Dict[str, float]:
    if not trades:
        return {
            "trades": 0,
            "return_pct": 0.0,
            "winrate_pct": 0.0,
            "drawdown_pct": 0.0,
            "sharpe": 0.0,
            "expectancy_pct": 0.0,
        }
    pnl = np.array([t.pnl_pct for t in trades], dtype=float)
    wins = float(np.mean(pnl > 0) * 100.0)
    expectancy = float(np.mean(pnl))
    eq = np.array([v for _, v in curve], dtype=float) + 100.0
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / np.maximum(peak, 1e-9)
    drawdown = float(abs(dd.min()) * 100.0)
    rets = np.diff(eq) / np.maximum(eq[:-1], 1e-9)
    sharpe = 0.0
    if len(rets) > 5 and np.std(rets) > 1e-9:
        sharpe = float((np.mean(rets) / np.std(rets)) * math.sqrt(252))
    return {
        "trades": int(len(trades)),
        "return_pct": float(round(eq[-1] - 100.0, 2)),
        "winrate_pct": float(round(wins, 2)),
        "drawdown_pct": float(round(drawdown, 2)),
        "sharpe": float(round(sharpe, 2)),
        "expectancy_pct": float(round(expectancy, 2)),
    }


def validate_system(market_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
    learning = LearningModule()
    baseline_trades, baseline_curve = run_backtest(market_data, use_ai=False, use_alpha=False, learning=None)
    ai_trades, ai_curve = run_backtest(market_data, use_ai=True, use_alpha=False, learning=learning)
    alpha_trades, alpha_curve = run_backtest(market_data, use_ai=True, use_alpha=True, learning=learning)

    if not (len(baseline_trades) == len(ai_trades) == len(alpha_trades)):
        raise RuntimeError(
            "Execution parity failed: trade counts differ across baseline/ai/alpha runs. "
            "Decisions must remain SmartRank-only."
        )

    baseline = performance_metrics(baseline_trades, baseline_curve)
    ai = performance_metrics(ai_trades, ai_curve)
    alpha = performance_metrics(alpha_trades, alpha_curve)

    return {
        "baseline": baseline,
        "ai": ai,
        "alpha": alpha,
    }


# ==================================================
# 12) MAIN EXECUTION
# ==================================================
def _synthetic_ohlcv(symbol: str, start: str = "2023-01-01", bars: int = 320) -> pd.DataFrame:
    rng = np.random.default_rng(abs(hash(symbol)) % (2**32 - 1))
    dates = pd.bdate_range(start=start, periods=bars)
    drift = 0.0006 + (abs(hash(symbol)) % 5) * 0.0001
    vol = 0.012 + (abs(hash(symbol)) % 7) * 0.001
    prices = [20.0 + (abs(hash(symbol)) % 80)]
    for _ in range(1, bars):
        ret = rng.normal(drift, vol)
        prices.append(max(1.0, prices[-1] * (1.0 + ret)))
    close = np.array(prices)
    open_ = close * (1.0 + rng.normal(0, 0.002, bars))
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.004, 0.003, bars)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.004, 0.003, bars)))
    volume = rng.integers(150_000, 2_200_000, bars)
    return pd.DataFrame({
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates)


def load_market_data(symbols: Iterable[str]) -> Dict[str, pd.DataFrame]:
    data: Dict[str, pd.DataFrame] = {}
    for sym in symbols:
        data[sym] = _synthetic_ohlcv(sym)
    return data


def pretty_print_results(results: Dict[str, Dict[str, float]]) -> None:
    print("\n=== EGX PRO SYSTEM VALIDATION ===")
    cols = ["trades", "return_pct", "winrate_pct", "drawdown_pct", "sharpe", "expectancy_pct"]
    for name in ["baseline", "ai", "alpha"]:
        row = results[name]
        print(f"\n{name.upper()}")
        for c in cols:
            print(f"  {c:14}: {row[c]}")


def main() -> None:
    # Keep runtime bounded for quick production health checks.
    universe = SYMBOLS[:14]
    market_data = load_market_data(universe)
    print_signal_preview(market_data)
    results = validate_system(market_data)
    pretty_print_results(results)

    out = Path("egx_radar_pro_results.json")
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
