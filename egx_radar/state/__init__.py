"""Application state package (Layer 8)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.state.app_state import AppState, STATE

__all__ = ["AppState", "STATE"]
