"""Scoring engine: SmartRank component scores and composite ranking (Layer 4)."""

import logging
import math
from typing import Dict, List, Tuple

from egx_radar.config.settings import K
from egx_radar.core.indicators import safe_clamp, quantile_norm

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4: SCORING ENGINE — All component scores normalised 0-1
# ═══════════════════════════════════════════════════════════════════════════


def _norm(val: float, lo: float, hi: float) -> float:
    """Linearly normalise val ∈ [lo, hi] → [0, 1]. Clamps outside range."""
    if hi <= lo:
        return 0.0
    return safe_clamp((val - lo) / (hi - lo), 0.0, 1.0)


def score_capital_pressure(
    clv: float, trend_acc: float, vol_ratio: float,
    price: float, ema50: float, vwap_dist: float,
    ud_ratio: float = 1.0, is_vcp: bool = False
) -> float:
    """
    Capital Pressure Index, normalised 0-1.
    Raw CPI components:
      - volume contribution: min(2.0, vol_ratio * 0.9)
      - CLV contribution (if positive): clv * 2.2
      - trend acceleration (if positive): min(1.5, trend_acc * 6.0)
      - EMA50 proximity bonus: 1.2 if within 3%
      - VWAP discount bonus: min(1.0, |vwap_dist| * 4.0) if below VWAP
    Raw range: [0, ~8].  Normalised to [0, 1].
    """
    if getattr(K, "VOL_LOG_SCALE_ENABLED", True):
        # Logarithmic scaling: dampens minor retail spikes, rewards sustained volume
        vol_contrib = min(1.0, math.log1p(max(0.0, vol_ratio)) / K.VOL_LOG_SCALE_DIVISOR)
    else:
        vol_contrib = min(2.0, vol_ratio * 0.9)  # legacy linear fallback
    raw = vol_contrib
    if clv > 0:
        raw += clv * 2.2
    if trend_acc > 0:
        raw += min(1.5, trend_acc * 6.0)
    if ema50 > 0 and abs(price - ema50) / (ema50 + 1e-9) < 0.03:
        raw += 1.2
    if vwap_dist < -0.01:
        raw += min(1.0, abs(vwap_dist) * 4.0)

    # Feature 3: Micro-structure Volume Analysis
    if is_vcp:
        raw += 1.5  # Bonus for volatility contraction

    if ud_ratio < 0.7:
        raw -= 1.0  # Softened penalty for down-volume dominance in EGX
    elif ud_ratio > 1.5:
        raw += 1.0  # Bonus for strong up-volume dominance

    final_score = _norm(safe_clamp(raw, 0.0, 10.0), 0.0, 10.0)
    # Floor at config minimum so structurally sound stocks don't lose the entire 20% FLOW weight
    return max(K.CPI_FLOOR, final_score)


def score_institutional_entry(
    rsi: float, adx: float, clv: float,
    trend_acc: float, vol_ratio: float, pct_ema200: float
) -> float:
    """
    Institutional Entry Timing score, normalised 0-1.
    Raw components (max 10.0):
      2.0 if RSI 45-60 | 1.5 if ADX < 22 | 2.0 if CLV > 0.45
      2.0 if trend_acc > 0 | 1.5 if vol_ratio 1.0-1.4 | 1.0 if pct_ema200 < 18
    """
    s = 0.0
    if 45 <= rsi <= 60:          s += 2.0
    if adx < 22:                 s += 1.5
    if clv > 0.45:               s += 2.0
    if trend_acc > 0:            s += 2.0
    if 1.0 <= vol_ratio <= 1.4:  s += 1.5
    if pct_ema200 < 18:          s += 1.0
    return _norm(safe_clamp(s, 0.0, 10.0), 0.0, 10.0)


def score_whale_footprint(
    adx: float, clv: float, trend_acc: float, vol_ratio: float, rsi: float
) -> float:
    """
    Whale Footprint score, normalised 0-1.
    Raw max: 9.0.
    """
    s = 0.0
    if adx < 25:                 s += 1.5
    if clv > 0.55:               s += 2.5
    if trend_acc > 0:            s += 2.0
    if vol_ratio > 0.9:          s += 2.0  # Calibrated for lower EGX liquidity
    if rsi < 68:                 s += 1.0
    return _norm(safe_clamp(s, 0.0, 9.0), 0.0, 9.0)


def score_flow_anticipation(
    rsi: float, adx: float, clv: float,
    trend_acc: float, vol_ratio: float, pct_ema200: float
) -> float:
    """
    Flow Anticipation score (forward-looking), normalised 0-1.
    Raw max: 10.5.
    """
    s = 0.0
    if 47 <= rsi <= 60:          s += 2.0
    if adx < 22:                 s += 1.5
    if clv > 0.45:               s += 2.5
    if trend_acc > 0:            s += 2.0
    if 0.9 <= vol_ratio <= 1.3:  s += 1.5
    if pct_ema200 < 18:          s += 1.0
    return _norm(safe_clamp(s, 0.0, 10.5), 0.0, 10.5)


def score_quantum(rsi: float, momentum: float, trend_acc: float, clv: float, vol_ratio: float) -> float:
    """
    Quantum flow convergence score, normalised 0-1.
    Raw max: 5.5.
    """
    q = 0.0
    if 48 <= rsi <= 60:       q += 1.5
    if 0.3 < momentum < 2.0:  q += 1.5
    if trend_acc > 0:         q += 1.0
    if clv > 0.4:             q += 1.0
    if vol_ratio < 1.3:       q += 0.5
    return _norm(safe_clamp(q, 0.0, 5.5), 0.0, 5.5)


def score_gravity(clv: float, trend_acc: float, vol_ratio: float, rsi: float, adaptive_mom: float) -> Tuple[str, float]:
    """Money Flow Gravity. Returns (label, normalised_score 0-1)."""
    g = vol_ratio * 1.2 + clv * 2.5 + trend_acc * 4.0
    if 48 <= rsi <= 62:   g += 2.0
    if adaptive_mom > 0:  g += 1.5
    raw = safe_clamp(g, 0.0, 12.0)
    label = "🧲 HEAVY" if raw >= 8 else ("🧲 BUILDING" if raw >= 5 else "▫️ LIGHT")
    return label, _norm(raw, 0.0, 12.0)


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


def smart_rank_score(
    cpi_n: float, iet_n: float, whale_n: float, gravity_n: float,
    quantum_n: float, tech_score: int, trend_acc: float, hidden_score: float,
    adaptive_mom: float, phase: str, zone: str, tag: str,
    silent: bool, hunter: bool, expansion: bool, fake_expansion: bool,
    leader: bool, ema_cross: str, vol_div: str,
    rsi: float, adx: float, pct_ema200: float, vol_ratio: float,
    brain_mode: str, brain_vol_req: float,
    sig_hist: List[str], market_soft: bool,
    nw: Dict[str, float],
    sector_bias: float,
    anticipation_n: float,
    regime: str,
    cmf: float,
    vwap_dist: float,
    vcp_detected: bool,
    price: float,
    clv: float,
    liq_shock: float = 0.0,
    momentum_series=None,   # optional pd.Series of recent cross-sectional momentum values
) -> float:
    """
    FIX-B: Documented SmartRank formula with explicit normalised components.

    SmartRank = Σ(weight_i × component_i) × SMART_RANK_SCALE

    where each component_i ∈ [0, 1] and Σ weights_i = 1.0:

      FLOW (20%):
        flow_component = normalised(vol_ratio^1.3 × max(clv_from_cpi, 0)) × neural_flow
        → captured via cpi_n which already embeds vol + CLV + VWAP

      STRUCTURE (20%):
        structure_component = normalised(tech_score / 14 + trend_acc_n + hidden_n)
        → tech_score max = 14, trend_acc normalised, hidden normalised

      TIMING (20%):
        timing_component = phase/zone/pattern bonuses, normalised to [0,1]

      MOMENTUM (15%):
        momentum_component = normalised(adaptive_mom, -5, +10)

      REGIME (15%):
        regime_component = (iet_n + whale_n + gravity_n) / 3

      NEURAL (10%):
        neural_component = weighted blend of nw values, normalised

    Late-entry penalties are applied as multiplicative dampers (≤ 1.0).
    """
    # ── FLOW component ────────────────────────────────────────────────────
    # FIX-2.3: Apply neural flow weight and sector bias as real multipliers.
    # Previous code divided out the same factors it multiplied in, yielding
    # flow_n == cpi_n regardless of neural weight or sector bias.
    flow_n = safe_clamp(cpi_n * nw.get("flow", 1.0) * sector_bias, 0.0, 1.0)

    # ── STRUCTURE component ───────────────────────────────────────────────
    tech_n      = _norm(tech_score, 0, 14)
    trend_acc_n = _norm(trend_acc, -0.05, 0.05)
    hidden_n    = _norm(hidden_score, 0.0, 4.0)
    structure_n = safe_clamp(
        (tech_n * 0.5 + trend_acc_n * 0.3 + hidden_n * 0.2) * nw.get("structure", 1.0),
        0.0, 1.0,
    )

    # ── TIMING component ──────────────────────────────────────────────────
    timing_raw = 0.0
    if tag == "ultra":          timing_raw += 0.35
    if silent:                  timing_raw += 0.25
    if hunter:                  timing_raw += 0.15
    if expansion:               timing_raw += 0.10
    if quantum_n > 0.5:         timing_raw += 0.20
    if gravity_n > 0.6:         timing_raw += 0.15
    if zone == "🟢 EARLY":      timing_raw += 0.15
    elif zone == "🔴 LATE":     timing_raw -= 0.10
    if phase == "Accumulation": timing_raw += 0.10
    if leader:                  timing_raw += 0.20 * nw.get("timing", 1.0)
    if tag == "early" and pct_ema200 < 20: timing_raw += 0.10
    if ema_cross == "BULL_CROSS": timing_raw += 0.15
    elif ema_cross == "BEAR_CROSS": timing_raw -= 0.15
    timing_n = safe_clamp(timing_raw, 0.0, 1.0)

    # ── MOMENTUM component ────────────────────────────────────────────────
    # Use quantile normalization when a cross-sectional series is available.
    # This handles EGX's skewed momentum distribution better than linear norm.
    if (
        getattr(K, "QUANTILE_NORM_ENABLED", True)
        and momentum_series is not None
        and len(momentum_series.dropna()) >= 5
    ):
        momentum_n = quantile_norm(adaptive_mom, momentum_series)
    else:
        momentum_n = _norm(adaptive_mom, K.MOM_NORM_LO, K.MOM_NORM_HI)

    # ── REGIME component ─────────────────────────────────────────────────
    regime_n = (iet_n + whale_n + gravity_n) / 3.0

    # ── NEURAL component ─────────────────────────────────────────────────
    nw_avg  = (nw.get("flow", 1.0) + nw.get("structure", 1.0) + nw.get("timing", 1.0)) / 3.0
    neural_n = _norm(nw_avg, K.NEURAL_WEIGHT_MIN, K.NEURAL_WEIGHT_MAX)

    # ── Weighted sum → raw rank [0, 1] ───────────────────────────────────
    raw_n = (
        K.SR_W_FLOW      * flow_n      +
        K.SR_W_STRUCTURE * structure_n +
        K.SR_W_TIMING    * timing_n    +
        K.SR_W_MOMENTUM  * momentum_n  +
        K.SR_W_REGIME    * regime_n    +
        K.SR_W_NEURAL    * neural_n
    )

    # Market regime damping — generate fewer signals in bear or neutral markets
    if getattr(K, "REGIME_BEAR_DAMPING_ENABLED", True):
        if regime in ("DISTRIBUTION", "BEAR"):
            raw_n *= K.REGIME_BEAR_SCORE_MULT
        elif regime == "NEUTRAL":
            raw_n *= K.REGIME_NEUTRAL_SCORE_MULT

    # [P3-E3] CMF Damping
    if K.CMF_DAMPING_ENABLED and cmf < 0 and vol_ratio < 1.0 and vwap_dist < 0:
        raw_n *= K.CMF_DAMPING_FACTOR

    # [P3-E2] VCP Score Multiplier
    if vcp_detected:
        raw_n *= K.VCP_SCORE_MULTIPLIER

    # ── Late-entry penalty damper (multiplicative) ────────────────────────
    # Kept multiplicative so we never go below 0 unnaturally

    # Feature: Momentum Acceleration Exemption
    # If a stock demonstrates extreme confirmed momentum, ignore certain late-entry dampers.
    acceleration_condition = (
        adaptive_mom > 2.5 and
        vol_ratio > 1.8 and
        vol_div != "🔀BEAR_DIV" and
        tag != "sell"
    )

    damper = 1.0

    if not acceleration_condition:
        if rsi > 70:                            damper *= 0.85
        if pct_ema200 > 35:                     damper *= 0.85
        if market_soft and tag == "buy":        damper *= 0.88
        if len(sig_hist) >= 3 and all(h == "buy" for h in sig_hist[-3:]):
            damper *= 0.85

    # Always apply these structural/distribution penalties
    if fake_expansion:                      damper *= 0.70
    if vol_div == "🔀BEAR_DIV":             damper *= 0.88
    if vol_div == "⚠️CLIMAX_SELL":          damper *= 0.80   # FIX-4: strong distribution signal
    if brain_mode == "defensive" and vol_ratio < brain_vol_req:
        damper *= 0.90

    # Cap the total damping if acceleration is true
    if acceleration_condition:
        damper = max(0.90, damper)

    # ── Brain-mode bonus (additive boost on top of penalised raw) ─────────
    brain_boost = 0.0
    if brain_mode == "aggressive" and vol_ratio >= brain_vol_req:
        brain_boost = 0.02

    # ── FIX-4: BULL_CONF additive boost (price up + volume up = confirmed) ─
    bull_conf_boost = 0.04 if vol_div == "🟢BULL_CONF" else 0.0

    # ── Anticipation contribution (already normalised) ────────────────────
    anticipation_contrib = anticipation_n * 0.05   # minor forward-looking nudge

    final_n = safe_clamp(raw_n * damper + brain_boost + bull_conf_boost + anticipation_contrib, 0.0, 1.0)

    # Liquidity Shock boost — reward genuine institutional directional moves
    if getattr(K, "LIQ_SHOCK_ENABLED", True) and liq_shock >= K.LIQ_SHOCK_THRESHOLD:
        final_n = min(1.0, final_n + K.LIQ_SHOCK_BOOST)

    # [P3-G2] RR Bonus - apply AFTER weighted sum, BEFORE ×60 scaling
    # Compute estimated RR from available parameters (before build_trade_plan)
    estimated_rr = 0.0
    if 45 <= rsi <= 60:                              # Sweet spot RSI
        estimated_rr += 1.0
    if adx >= 25:                                    # Strong trend
        estimated_rr += 1.0
    if adaptive_mom > 0:                             # Positive momentum
        estimated_rr += 0.5
    if pct_ema200 < 15:                              # Room to run
        estimated_rr += 0.5
    if vol_ratio >= 1.2:                             # Volume confirmation
        estimated_rr += 0.5

    if K.RR_BONUS_ENABLED and estimated_rr >= K.RR_BONUS_THRESHOLD:
        final_n += K.RR_BONUS_AMOUNT

    # FIX-2.1: Clamp to [0, 1] so SmartRank never exceeds SMART_RANK_SCALE.
    final_n = min(1.0, final_n)

    return round(final_n * K.SMART_RANK_SCALE, 3)
