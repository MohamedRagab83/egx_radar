from __future__ import annotations

from typing import Any, Dict, Mapping

from egx_radar.config.settings import K, get_account_size, get_risk_per_trade


def _snapshot_get(snapshot: Any, key: str, default: float = 0.0) -> float:
    if isinstance(snapshot, Mapping):
        value = snapshot.get(key, default)
    else:
        value = getattr(snapshot, key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def build_alpha_trade(snapshot: Any, alpha_score: float) -> Dict[str, object]:
    """Construct a small, pullback-based early trade plan capped at 20% of normal risk."""
    price = max(_snapshot_get(snapshot, "price", 0.0), 1e-9)
    atr = _snapshot_get(snapshot, "atr", 0.0)
    base_low = _snapshot_get(snapshot, "base_low", price * (1.0 - K.MAX_STOP_LOSS_PCT))

    pullback_buffer = min(max(atr * 0.35, price * 0.003), price * 0.015)
    entry = max(base_low, price - pullback_buffer)
    risk_pct = min(max((entry - (base_low * 0.995)) / max(entry, 1e-9), 0.008), 0.025)
    stop = entry * (1.0 - risk_pct)
    target = entry * (1.0 + max(0.04, risk_pct * 2.2))

    position_scale = min(0.20, max(0.08, (float(alpha_score) - 60.0) / 200.0))
    normal_risk = float(get_risk_per_trade())
    scaled_risk = min(normal_risk * position_scale, normal_risk * 0.20)
    max_notional = float(get_account_size()) * float(K.PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT) * position_scale

    return {
        "action": "ALPHA_PROBE",
        "entry": round(entry, 3),
        "trigger_price": round(entry, 3),
        "stop": round(stop, 3),
        "target": round(target, 3),
        "target_pct": round((target - entry) / max(entry, 1e-9), 4),
        "risk_pct": round((entry - stop) / max(entry, 1e-9), 4),
        "risk_used": round(scaled_risk, 4),
        "position_scale": round(position_scale, 4),
        "alpha_score": round(float(alpha_score), 2),
        "trade_type": "ALPHA",
        "timeframe": "Early News Alpha",
        "max_position_notional": round(max_notional, 2),
        "why_now": "News-led early setup with pullback entry and reduced size.",
    }


__all__ = ["build_alpha_trade"]
