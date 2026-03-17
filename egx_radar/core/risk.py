"""Risk engine: trade plan construction and institutional confidence (Layer 6)."""

import logging
from typing import Optional, Tuple

from egx_radar.config.settings import (
    K,
    get_account_size,
    get_risk_per_trade,
)
from egx_radar.core.indicators import safe_clamp

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 6: RISK ENGINE — ATR-percentile sizing, dynamic thresholds
# ═══════════════════════════════════════════════════════════════════════════


def build_trade_plan(
    price: float, rsi: float, adx: float, clv: float,
    trend_acc: float, smart_rank: float, anticipation: float,
    atr_risk_label: str = "—",
    atr: Optional[float] = None,
    tech_score: int = 0,
    vol_ratio: float = 1.0,
    size_multiplier: float = 1.0,
) -> dict:
    """
    Produce an actionable trade plan.

    FIX-1: Thresholds now relative to SMART_RANK_SCALE (was hardcoded 7/5
            which is only 12% of the 60-point scale — effectively meaningless).
            New thresholds: ACCUMULATE >= 40%, PROBE >= 28%, WATCH_ONLY >= 15%.
    FIX-3: ADX soft-low gate has exception for very high tech_score + strong volume
            so strong momentum moves are not silently ignored.
    """
    _sr = K.SMART_RANK_SCALE   # 60.0

    if adx < K.ADX_SOFT_LO:
        # Relaxed gate: allow PROBE if overall evidence is strong enough
        # even when ADX is slightly below threshold (accumulation phase stocks
        # often have low ADX by design — worth probing on strong flow/anticipation)
        if tech_score >= 12 and vol_ratio > 2.0:
            action = "PROBE"
        elif smart_rank >= K.SMART_RANK_SCALE * 0.40 and anticipation > 0.5:
            # High rank + strong flow anticipation = worth probing despite low ADX
            action = "PROBE"
        else:
            action = "WAIT"
    elif adx < K.ADX_SOFT_HI:
        # FIX-1: was >= 6.0 (10% of scale) → now 22% of scale
        action = "PROBE" if smart_rank >= _sr * 0.22 else "WAIT"
    else:
        # FIX-1: was > 7 (12%) / > 5 (8%) → now 40% / 28% / 15%
        if smart_rank > _sr * 0.40 and anticipation > K.PLAN_ANTICIPATION_HI:
            action = "ACCUMULATE"
        elif smart_rank > _sr * 0.28:
            action = "PROBE"
        elif smart_rank > _sr * 0.15:
            action = "WATCH_ONLY"
        else:
            action = "WAIT"

    # Extra gate: never ACCUMULATE into HIGH-risk ATR environment
    if action == "ACCUMULATE" and atr_risk_label == "⚠️ HIGH":
        action = "PROBE"

    if adx < K.ADX_SOFT_HI:
        stop = round(price * K.PLAN_STOP_ADX_LOW, 2)
    elif clv > 0.5 and trend_acc > 0:
        stop = round(price * K.PLAN_STOP_CLV_HIGH, 2)
    else:
        stop = round(price * K.PLAN_STOP_DEFAULT, 2)

    entry  = round(price * K.PLAN_ENTRY_DISCOUNT, 2)
    target = round(
        price * (K.PLAN_TARGET_HIGH if anticipation > K.PLAN_ANTICIPATION_HI else K.PLAN_TARGET_DEFAULT),
        2,
    )

    # Guard: entry ≈ stop ⇒ RR is undefined; return WAIT to avoid div-by-zero sizing
    if abs(entry - stop) < 0.001 * price:
        return {
            "action": "WAIT", "entry": entry, "stop": stop, "target": price,
            "size": 0, "rr": float('nan'), "timeframe": "—",
            "force_wait": True, "winrate": 0.0, "winrate_na": True, "rr_invalid": True,
        }

    # ── Risk-based position sizing ────────────────────────────────────────────
    account_size = get_account_size()
    risk_amount = account_size * get_risk_per_trade()
    rps = abs(entry - stop)
    share_count = max(1, int(risk_amount / rps))

    # ── Unified multiplier application (SINGLE application point) ────────────
    _size_mult = max(K.SIZE_MULTIPLIER_FLOOR, float(size_multiplier or 1.0))
    share_count = max(1, int(share_count * _size_mult))
    rr   = round(abs(target - entry) / rps, 1)

    atr_pct = (atr / price * 100) if (atr and price > 0) else 0.0
    if adx > 35 and atr_pct > K.ATR_INTRADAY_THRESH:
        timeframe = "⚡ Intraday"
    elif adx > K.ADX_STRONG:
        timeframe = "📅 Swing (3-10d)"
    else:
        timeframe = "📆 Position (wks)"

    return {
        "action": action, "entry": entry, "stop": stop,
        "target": target, "size": share_count, "rr": rr,
        "timeframe": timeframe,
        "force_wait": action == "WAIT",
        "winrate": 0.0,   # filled by estimate_winrate() in scoring pass
        "winrate_na": action == "WAIT",
    }


def institutional_confidence(winrate: float, smart_rank: float, sector_strength: float,
                             dg_tier: str = "", mg_passed: bool = True) -> str:
    """Calculate institutional confidence label based on rank, strength, and guard results."""
    score = winrate * 0.5 + smart_rank * 5 + sector_strength * 8
    # FIX-5: guard-based penalties
    if dg_tier == "DEGRADED":
        score *= 0.85
    elif dg_tier == "REJECTED":
        score *= 0.60
    if not mg_passed:
        score *= 0.90
    if score > 90: return "🔥 ELITE"
    if score > 70: return "💎 STRONG"
    if score > 55: return "🧠 GOOD"
    if score > 40: return "⚠️ MID"
    return "❌ WEAK"


def compute_dynamic_stop(
    current_price: float, entry: float, current_stop: float, current_target: float,
    momentum: float, regime: str, is_short: bool = False
) -> Tuple[float, float, str]:
    """
    Feature 2: Dynamic Trailing Take-Profit
    Adjusts standard static stops/targets based on live trailing mathematics.
    Returns (new_stop, new_target, reason)
    """
    new_stop = current_stop
    new_target = current_target
    reason = "HELD"
    
    if is_short:
        # PnL logic reversed
        pnl_pct = ((entry - current_price) / (entry + 1e-9)) * 100
        if pnl_pct > 3.0:
            trail_stop = current_price * 1.02  # Trail 2% behind price
            if trail_stop < current_stop:
                new_stop = trail_stop
                reason = "TRAILED⬇"
            if momentum < -2.0:
                new_target = current_target * 0.98 # Expand downside target
                reason += " | EXPANDED"
    else:
        pnl_pct = ((current_price - entry) / (entry + 1e-9)) * 100
        
        # Scenario: Strongly winning, start trailing the stop up
        if pnl_pct > 3.0:
            trail_stop = current_price * 0.98  # Trail 2% below price
            if trail_stop > current_stop:
                new_stop = trail_stop
                reason = "TRAILED⬆"
                
            # If momentum is very strong, push the target higher instead of selling
            if momentum > 2.0 and regime == "MOMENTUM":
                new_target = current_target * 1.02
                reason += " | EXPANDED"
                
        # Scenario: Exhaustion while winning (Momentum death) → clamp stop aggressively
        elif pnl_pct > 1.0 and momentum < 0 and regime != "MOMENTUM":
            trail_stop = current_price * 0.99
            if trail_stop > current_stop:
                new_stop = trail_stop
                reason = "EXHAUSTION CLAMP"
    
    return round(new_stop, 3), round(new_target, 3), reason
