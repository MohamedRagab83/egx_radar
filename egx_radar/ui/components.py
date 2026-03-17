from __future__ import annotations

"""UI primitives: Tkinter queue, gauges, heatmaps, tooltips, and export (Layer 10)."""

import csv
import logging
import math
import queue
import tkinter.messagebox as messagebox
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, ttk

from egx_radar import __version__
from egx_radar.config.settings import (
    K,
    C,
    F_BODY,
    F_HEADER,
    F_SMALL,
    F_MICRO,
    SECTORS,
    get_account_size,
    get_max_per_sector,
    get_atr_exposure,
)

log = logging.getLogger(__name__)


# ── UI event queue (FIX-H) ───────────────────────────────────────────────────
_ui_q: queue.Queue = queue.Queue()


def _enqueue(fn, *args, **kwargs):
    _ui_q.put((fn, args, kwargs))


def _pump(root: tk.Tk) -> None:
    """Drain the UI queue on the main thread. Called every UI_POLL_MS ms."""
    while True:
        try:
            fn, args, kwargs = _ui_q.get_nowait()
            fn(*args, **kwargs)
        except queue.Empty:
            break
        except Exception as exc:
            log.error("UI queue error: %s", exc)
    root.after(K.UI_POLL_MS, lambda: _pump(root))


# ── Pulse controller ──────────────────────────────────────────────────────────
class PulseController:
    def __init__(self) -> None:
        self._active   = False
        self._state    = 0
        self._frm: Optional[tk.Frame] = None
        self._lbl: Optional[tk.Label] = None
        self._base_col = C.BG

    def start(self, frm: tk.Frame, lbl: tk.Label, base_col: str) -> None:
        self._frm, self._lbl, self._base_col = frm, lbl, base_col
        if not self._active:
            self._active = True
            self._tick()

    def stop(self) -> None:
        self._active = False
        if self._frm:
            try:
                self._frm.configure(bg=self._base_col)
                if self._lbl:
                    self._lbl.configure(bg=self._base_col)
            except tk.TclError:
                pass

    def _tick(self) -> None:
        if not self._active or not self._frm:
            return
        self._state ^= 1
        col = "#113a2c" if self._state else self._base_col
        try:
            self._frm.configure(bg=col)
            if self._lbl:
                self._lbl.configure(bg=col)
            self._frm.after(K.UI_PULSE_MS, self._tick)
        except tk.TclError:
            self._active = False


_pulse = PulseController()


def _clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


# ── Gauge widget ──────────────────────────────────────────────────────────────
def draw_gauge(canvas: tk.Canvas, val: float, max_val: float, label: str, sublabel: str = "") -> None:
    canvas.delete("all")
    W, H   = 160, 110
    cx, cy = W // 2, H - 18
    R      = 58
    ratio  = _clamp01(val / (max_val + 1e-9))
    col    = C.GREEN if ratio >= 0.65 else (C.YELLOW if ratio >= 0.38 else C.RED)
    canvas.create_arc(cx-R, cy-R, cx+R, cy+R, start=0, extent=180, style="arc", width=14, outline=C.BG3)
    if ratio > 0.005:
        canvas.create_arc(cx-R, cy-R, cx+R, cy+R, start=0, extent=ratio*180, style="arc", width=14, outline=col)
    ang = math.radians(180 - ratio * 180)
    nx  = cx + (R-9) * math.cos(ang)
    ny  = cy - (R-9) * math.sin(ang)
    canvas.create_line(cx, cy, nx, ny, fill=col, width=2)
    canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=col, outline="")
    canvas.create_text(cx, cy-24, text=f"{val:.1f}", fill=col, font=("Consolas", 15, "bold"))
    canvas.create_text(cx, cy-8,  text=label,    fill=C.ACCENT2, font=("Consolas", 8, "bold"))
    if sublabel:
        canvas.create_text(cx, cy+6, text=sublabel, fill=C.MUTED, font=("Consolas", 7))


# ── UI update helpers (called from _pump, safe on main thread) ─────────────────
def _update_heatmap(heat_labels: dict, sector_strength: Dict[str, float]) -> None:
    for sec, val in sector_strength.items():
        if val > 0.6:   bg, fg = "#0a2218", C.GREEN
        elif val > 0.3: bg, fg = "#1c1a08", C.YELLOW
        else:           bg, fg = "#220a0a", C.RED
        heat_labels[sec].configure(text=f"{sec}\n{val:.2f}", bg=bg, fg=fg)


def _update_rotation_map(rot_labels: dict, scores: Dict[str, float], future: str) -> None:
    for sec, val in scores.items():
        if sec == future:  col, bg = C.GREEN,  "#061f14"
        elif val > 0.6:    col, bg = C.CYAN,   "#06131f"
        elif val > 0.35:   col, bg = C.YELLOW, "#1c1a08"
        else:              col, bg = C.MUTED,  C.BG3
        rot_labels[sec].configure(
            text=f"{'👑 ' if sec == future else ''}{sec}\n{val:.2f}", fg=col, bg=bg
        )


def _update_flow_map(flow_labels: dict, flow_scores: Dict[str, float], leader: str) -> None:
    for sec, val in flow_scores.items():
        if sec == leader: col, bg = C.GREEN,  "#061f14"
        elif val > 0.3:   col, bg = C.CYAN,   "#06131f"
        elif val > 0:     col, bg = C.YELLOW, "#1c1a08"
        else:             col, bg = C.RED,    "#220a0a"
        flow_labels[sec].configure(
            text=f"{'💰 ' if sec == leader else ''}{sec}\n{val:+.2f}", fg=col, bg=bg
        )


def _update_guard_bar(guard_slbl, guard_elbl, guard_blbl,
                      sector_counts, total_exp, blocked_syms) -> None:
    cap     = get_max_per_sector()
    max_pct = get_atr_exposure() * 100
    acct    = get_account_size()
    for sec, count in sector_counts.items():
        if count >= cap:     col, bg = C.RED,    "#220a0a"
        elif count == cap-1: col, bg = C.YELLOW, "#1c1a08"
        elif count > 0:      col, bg = C.GREEN,  "#062016"
        else:                col, bg = C.MUTED,  C.BG3
        guard_slbl[sec].configure(text=f"{sec}\n{count}/{cap}", fg=col, bg=bg)
    pct = (total_exp / (acct + 1e-9)) * 100
    exp_col = C.RED if pct >= max_pct else (C.YELLOW if pct >= max_pct * 0.75 else C.GREEN)
    guard_elbl.configure(text=f"ATR Exp: {pct:.1f}% / {max_pct:.0f}%  (حساب: {acct:,.0f} ج.م)", fg=exp_col)
    if blocked_syms:
        guard_blbl.configure(text=f"🛡️ Blocked: {', '.join(blocked_syms)}", fg=C.RED)
    else:
        guard_blbl.configure(text="🛡️ Blocked: —", fg=C.MUTED)


def _update_regime_label(lbl: tk.Label, regime: str) -> None:
    icons = {
        "ACCUMULATION": ("📦 ACCUMULATION", C.CYAN),
        "MOMENTUM":     ("🚀 MOMENTUM",      C.GREEN),
        "DISTRIBUTION": ("📤 DISTRIBUTION",  C.RED),
        "NEUTRAL":      ("📊 NEUTRAL",        C.MUTED),
    }
    txt, col = icons.get(regime, ("📊 NEUTRAL", C.MUTED))
    lbl.configure(text=txt, fg=col)


def _update_brain_label(lbl: tk.Label, mode: str) -> None:
    if mode == "aggressive":  lbl.configure(text="🧠🔥 AGGRESSIVE", fg=C.GREEN)
    elif mode == "defensive": lbl.configure(text="🧠🛡️ DEFENSIVE",  fg=C.YELLOW)
    else:                     lbl.configure(text="🧠 NEUTRAL",       fg=C.MUTED)


# ── Tooltip ───────────────────────────────────────────────────────────────────
_tooltip_win: Optional[tk.Toplevel] = None


def _show_tooltip(event, tree: ttk.Treeview, cols: tuple) -> None:
    global _tooltip_win
    item = tree.identify_row(event.y)
    if not item:
        return
    raw_vals = tree.item(item, "values")
    if not raw_vals or len(raw_vals) < len(cols):
        return
    v = dict(zip(cols, raw_vals))
    tip = (
        f"  Symbol  : {v.get('Symbol','—')}  Sector: {v.get('Sector','—')}\n"
        f"  Price   : {v.get('Price','—')}  ADX: {v.get('ADX','—')}  RSI: {v.get('RSI','—')}\n"
        f"  CPI     : {v.get('🧠CPI','—')}  IET: {v.get('🏛️IET','—')}  Whale: {v.get('🐳Whale','—')}\n"
        f"  Signal  : {v.get('Signal','—')}  Dir: {v.get('Direction','—')}\n"
        f"  Conf    : {v.get('Confidence%','—')}  Timeframe: {v.get('Timeframe','—')}\n"
        f"  Action  : {v.get('Action','—')}  Entry: {v.get('Entry','—')}  Stop: {v.get('Stop','—')}\n"
        f"  Target  : {v.get('Target','—')}  R:R: {v.get('R:R','—')}  WinRate: {v.get('WinRate%','—')}\n"
        f"  ATR Risk: {v.get('ATR Risk','—')}  VWAP%: {v.get('VWAP%','—')}\n"
        f"  Reason  : {v.get('Signal Reason','—')}\n"
        f"  🛡️Guard : {v.get('🛡️Guard','—')}"
    )
    _destroy_tooltip()
    tw = tk.Toplevel()
    tw.wm_overrideredirect(True)
    tw.wm_geometry(f"+{event.x_root+12}+{event.y_root+10}")
    tk.Label(tw, text=tip, justify="left", font=("Consolas", 9),
             bg="#1a2a3a", fg=C.CYAN, relief="flat", padx=8, pady=6,
             bd=1, highlightbackground=C.ACCENT, highlightthickness=1).pack()
    _tooltip_win = tw


def _destroy_tooltip(*_) -> None:
    global _tooltip_win
    if _tooltip_win:
        try:
            _tooltip_win.destroy()
        except tk.TclError:
            pass
        _tooltip_win = None


def export_csv(tree: ttk.Treeview, cols: tuple) -> None:
    rows = [tree.item(k)["values"] for k in tree.get_children("")]
    if not rows:
        messagebox.showwarning("Export", "No data to export!")
        return
    now  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        initialfile=f"EGX_Radar_v{__version__.replace('.', '')}_{now}.csv",
        filetypes=[("CSV files", "*.csv")],
        title="Save Radar Results",
    )
    if not path:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows([cols, *rows])
    messagebox.showinfo("Saved ✅", f"File saved:\n{path}")


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
]
