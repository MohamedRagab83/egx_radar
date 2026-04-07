"""Signal engine: market regime, phase, zones and raw signals (Layer 5)."""

import logging
import math
from typing import Dict, List, Optional, Tuple

from egx_radar.config.settings import K

log = logging.getLogger(__name__)


def score_tech_signal(
    price: float, ema200: float, ema50: float, adx: float, rsi: float,
    adaptive_mom: float, vol_ratio: float, breakout: bool, pct_ema200: float,
) -> int:
    """Raw integer signal score for build_signal(). Not normalised — used directly in signal classification."""
    score = 0
    if price > ema200:           score += 3
    elif price > ema200 * 0.97:  score += 1
    if price > ema50:            score += 1
    if adx > K.ADX_STRONG:       score += 2
    elif adx > K.ADX_MID:        score += 1
    if 55 < rsi < 70:            score += 3
    elif 48 <= rsi <= 55:        score += 1
    if adaptive_mom > 2:         score += 3
    elif adaptive_mom > 0:       score += 2
    elif adaptive_mom > -1:      score += 1
    if vol_ratio > 1.5:          score += 2
    elif vol_ratio > 1.2:        score += 1
    if breakout:                 score += 2
    if pct_ema200 > 35:          score -= 2
    return max(0, score)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 5: SIGNAL ENGINE
# ═══════════════════════════════════════════════════════════════════════════


def detect_market_regime(
    results: List[dict],
    ema200_slopes: Optional[Dict[str, float]] = None,
) -> str:
    """
    FIX-C: Market regime now requires EMA200 slope confirmation.
    States: ACCUMULATION | MOMENTUM | DISTRIBUTION | NEUTRAL

    Rules:
      ACCUMULATION: ADX < 20, vol < 1.3, EMA200 slope is flat or rising (≥ -0.001)
                    → prevents false ACCUM in downtrending bearish markets
      MOMENTUM:     ADX > 25, vol > 1.4
      DISTRIBUTION: RSI > 65, ADX > REGIME_ADX_DIST, EMA200 slope falling (< 0)
      NEUTRAL:      everything else
    """
    if not results:
        return "NEUTRAL"

    n       = len(results)
    avg_adx = sum(r["adx"]       for r in results) / n
    avg_rsi = sum(r["rsi"]       for r in results) / n
    avg_vol = sum(r["vol_ratio"] for r in results) / n

    # EMA200 slope: average across all symbols with valid slope
    avg_slope = 0.0
    if ema200_slopes:
        valid_slopes = [v for v in ema200_slopes.values() if math.isfinite(v)]
        if valid_slopes:
            avg_slope = sum(valid_slopes) / len(valid_slopes)

    if avg_adx < 20 and avg_vol < 1.3 and avg_slope >= -0.001:
        # FIX-C: Require non-negative EMA200 slope to confirm ACCUMULATION
        return "ACCUMULATION"
    if avg_adx > K.REGIME_ADX_BULL and avg_vol > 1.4:
        return "MOMENTUM"
    if avg_rsi > K.REGIME_RSI_DIST_MIN and avg_adx > K.REGIME_ADX_DIST and avg_slope < 0:
        # FIX-C: Distribution only when EMA200 is falling
        return "DISTRIBUTION"
    # BEAR: broad market below EMA200 with falling slope — clear downtrend
    # Different from DISTRIBUTION (which is a topping pattern at high RSI)
    if avg_slope < K.REGIME_BEAR_SLOPE_THRESH and avg_rsi < K.REGIME_BEAR_RSI_MAX:
        return "BEAR"
    return "NEUTRAL"


def detect_phase(
    adx: float, rsi: float, vol_ratio: float, trend_acc: float,
    clv: float, adaptive_mom: float, ema50: float, price: float,
    body_ratio: float = 0.3,
) -> str:
    """
    FIX-2: body_ratio is now a real parameter (was hardcoded 0.3 and unused).
    A small candle body (< 0.35) during quiet conditions is a classic
    accumulation footprint — smart money absorbing without showing intent.
    """
    hidden = 0.0
    if adx < 20 and 45 < rsi < 60:      hidden += 1.5
    if vol_ratio < 1.2 and clv > 0.4:   hidden += 1.0
    if trend_acc > 0:                    hidden += 1.0
    if body_ratio < 0.35:               hidden += 0.5   # FIX-2: real body signal
    if hidden > K.ACCUM_SCORE_THRESH:
        return "Accumulation"
    if adaptive_mom > 1.5 and adx > K.ADX_MID and price > ema50:
        return "Expansion"
    return "Exhaustion"


def detect_predictive_zone(rsi: float, adaptive_mom: float, pct_ema200: float, vol_ratio: float) -> str:
    """Determine predictive early/mid/late zone. EGX-calibrated thresholds.

    Wider RSI band and relaxed momentum threshold to avoid over-classifying
    normal EGX market conditions as LATE.
    """
    s = 0
    if 45 <= rsi <= 65:    s += 2   # was 48-60 — wider RSI band for EGX
    if adaptive_mom > -1:  s += 2   # was >0 — allow slightly negative momentum
    if pct_ema200 < 20:    s += 1   # was <15 — EGX stocks often run 15-20% above EMA200
    if vol_ratio < 1.6:    s += 1   # was <1.4 — EGX volume is spikier
    if s >= 5: return "🟢 EARLY"
    if s >= 3: return "🟡 MID"
    return "🔴 LATE"


def build_signal(
    price: float, ema200: float, ema50: float, adx: float, rsi: float,
    adaptive_mom: float, vol_ratio: float, breakout: bool, pct_ema200: float,
    phase: str, brain_score_req: int = K.BRAIN_SCORE_NEUTRAL, vol_div: str = "",
) -> Tuple[str, str, int]:
    """Build the final raw signal, tag, and technical score."""
    score = score_tech_signal(
        price, ema200, ema50, adx, rsi, adaptive_mom, vol_ratio, breakout, pct_ema200
    )

    if phase == "Accumulation":
        if 48 <= rsi <= 62:                      score += 3
        elif 40 <= rsi < 48 or 62 < rsi <= 70:  score += 1
    elif phase == "Expansion":
        if 55 < rsi < 70:                        score += 3
        elif 48 <= rsi <= 55:                    score += 1

    zone = detect_predictive_zone(rsi, adaptive_mom, pct_ema200, vol_ratio)
    # ── ultra signal strict guards ────────────────────────────────────────────
    # BT: ultra WR=5% when firing in LATE zone — downgrade to buy, never wait.
    _ultra_ok = (
        adaptive_mom > 0.8
        and vol_ratio > 1.15
        and zone != "🔴 LATE"
        and adaptive_mom > 0.0
        and vol_div not in ("BEAR_DIV", "🔀BEAR_DIV")
    )

    if phase == "Accumulation" and adaptive_mom > 0.8 and vol_ratio > 1.15:
        raw_sig, raw_tag = ("🧠 ULTRA EARLY", "ultra") if _ultra_ok else ("🔥 BUY", "buy")
    elif phase == "Expansion" and adx > K.ADX_MID and adaptive_mom > 1.5:
        raw_sig, raw_tag = "🚀 EARLY", "early"
    else:
        score_watch_adj = max(K.SCORE_WATCH, brain_score_req - 3)
        if score >= brain_score_req:
            raw_sig, raw_tag = "🔥 BUY",   "buy"
        elif score >= score_watch_adj:
            raw_sig, raw_tag = "👀 WATCH", "watch"
        else:
            raw_sig, raw_tag = "❌ SELL",  "sell"

    if raw_tag in ("buy", "ultra", "early") and rsi > K.RSI_OVERBOUGHT:
        raw_sig  = "👀 WATCH ⚠️OB"
        raw_tag  = "watch"

    return raw_sig, raw_tag, score


def build_signal_reason(
    rsi: float, adx: float, pct_ema200: float, phase: str,
    vol_div: str, ema_cross: str, adaptive_mom: float,
    clv: float, vol_ratio: float, tag: str = "",
) -> str:
    passed: List[str] = []
    failed: List[str] = []

    # Phase
    if phase == "Accumulation":    passed.append("Accum phase")
    elif phase == "Expansion":     passed.append("Expansion phase")
    else:                          failed.append("No clear phase")

    # ADX
    if adx > 30:                   passed.append(f"ADX strong ({adx:.0f})")
    elif adx < 18:                 failed.append(f"ADX weak ({adx:.0f})")

    # RSI
    if 48 <= rsi <= 62:            passed.append("RSI healthy")
    elif rsi > K.RSI_OVERBOUGHT:   failed.append(f"RSI overbought ({rsi:.0f})")
    elif rsi < 35:                 failed.append(f"RSI oversold ({rsi:.0f})")
    else:                          failed.append(f"RSI neutral ({rsi:.0f})")

    # Volume
    if vol_div == "🟢BULL_CONF":   passed.append("Vol confirmed")
    elif vol_div == "🔀BEAR_DIV":  failed.append("Bear vol div")
    elif vol_div == "⚠️CLIMAX_SELL": failed.append("Climax sell")

    # Momentum
    if adaptive_mom > 2:           passed.append("Strong mom")
    elif adaptive_mom < -1:        failed.append("Weak mom")

    # EMA cross
    if ema_cross == "BULL_CROSS":  passed.append("Bull EMA cross")
    elif ema_cross == "BEAR_CROSS": failed.append("Bear EMA cross")

    # Distance from EMA200
    if pct_ema200 > 30:            failed.append(f"Extended {pct_ema200:.0f}% vs EMA200")
    elif pct_ema200 < 0:           failed.append("Below EMA200")

    # Build output: show up to 2 passed + up to 2 failed
    parts = passed[:2] + [f"✗{f}" for f in failed[:2]]
    return " | ".join(parts) if parts else "Mixed signals"


def get_signal_direction(tag: str) -> str:
    """Determine the text direction (Bullish/Bearish/Neutral) from the signal tag."""
    if tag in ("buy", "ultra", "early"):
        return "📈 BULLISH"
    if tag == "sell":
        return "📉 BEARISH"
    return "⏸️ NEUTRAL"
