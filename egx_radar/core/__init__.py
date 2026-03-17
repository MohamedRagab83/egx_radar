"""Core computation layer: indicators, scoring, signals, risk, portfolio."""

import logging

log = logging.getLogger(__name__)

from egx_radar.core.indicators import (
    safe_clamp,
    last_val,
    compute_atr,
    compute_atr_risk,
    compute_vwap_dist,
    compute_vol_zscore,
    detect_ema_cross,
    detect_vol_divergence,
    compute_ud_ratio,
    detect_vcp,
    sharpe_from_trades,
)

from egx_radar.core.scoring import (
    _norm,
    score_capital_pressure,
    score_institutional_entry,
    score_whale_footprint,
    score_flow_anticipation,
    score_quantum,
    score_gravity,
    score_tech_signal,
    smart_rank_score,
)

from egx_radar.core.signals import (
    detect_market_regime,
    detect_phase,
    detect_predictive_zone,
    build_signal,
    build_signal_reason,
    get_signal_direction,
)

from egx_radar.core.risk import (
    build_trade_plan,
    institutional_confidence,
    compute_dynamic_stop,
)

from egx_radar.core.portfolio import (
    GuardedResult,
    compute_portfolio_guard,
)

from egx_radar.core.data_guard import DataGuard, DataGuardResult

__all__ = [
    # indicators
    "safe_clamp",
    "last_val",
    "compute_atr",
    "compute_atr_risk",
    "compute_vwap_dist",
    "compute_vol_zscore",
    "compute_ud_ratio",
    "detect_vcp",
    "detect_ema_cross",
    "detect_vol_divergence",
    "sharpe_from_trades",
    # scoring
    "_norm",
    "score_capital_pressure",
    "score_institutional_entry",
    "score_whale_footprint",
    "score_flow_anticipation",
    "score_quantum",
    "score_gravity",
    "score_tech_signal",
    "smart_rank_score",
    # signals
    "detect_market_regime",
    "detect_phase",
    "detect_predictive_zone",
    "build_signal",
    "build_signal_reason",
    "get_signal_direction",
    # risk
    "build_trade_plan",
    "institutional_confidence",
    # portfolio
    "GuardedResult",
    "compute_portfolio_guard",
    # data guard
    "DataGuard",
    "DataGuardResult",
]
