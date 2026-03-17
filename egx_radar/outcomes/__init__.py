"""Trade outcomes and logging engine (Layer 9)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.outcomes.engine import (
    oe_load_log,
    oe_save_log,
    oe_load_history,
    oe_save_history_batch,
    _normalise_df_index,
    oe_resolve_trade,
    oe_record_signal,
    oe_process_open_trades,
    oe_save_rejections,
)

__all__ = [
    "oe_load_log",
    "oe_save_log",
    "oe_load_history",
    "oe_save_history_batch",
    "_normalise_df_index",
    "oe_resolve_trade",
    "oe_record_signal",
    "oe_process_open_trades",
    "oe_save_rejections",
]
