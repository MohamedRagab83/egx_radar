"""UI layer: Tkinter main window, gauges, tooltips, and helpers (Layer 10)."""

import logging

log = logging.getLogger(__name__)

from egx_radar.ui.components import (
    _ui_q,
    _enqueue,
    _pump,
    PulseController,
    _pulse,
    draw_gauge,
    _update_heatmap,
    _update_rotation_map,
    _update_flow_map,
    _update_guard_bar,
    _update_regime_label,
    _update_brain_label,
    _show_tooltip,
    _destroy_tooltip,
    export_csv,
)


def main() -> None:
    from egx_radar.ui.main_window import main as _main
    _main()

__all__ = [
    "_ui_q",
    "_enqueue",
    "_pump",
    "PulseController",
    "_pulse",
    "draw_gauge",
    "_update_heatmap",
    "_update_rotation_map",
    "_update_flow_map",
    "_update_guard_bar",
    "_update_regime_label",
    "_update_brain_label",
    "_show_tooltip",
    "_destroy_tooltip",
    "export_csv",
    "main",
]
