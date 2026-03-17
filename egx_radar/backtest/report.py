from __future__ import annotations

"""Backtest report UI: tab with controls, summary, equity curve, trades table, CSV export."""

import csv
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from egx_radar.config.settings import C, F_HEADER, F_SMALL, F_MICRO, K
from egx_radar.state.app_state import STATE

from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics

log = logging.getLogger(__name__)


def open_backtest_window(root: tk.Tk) -> None:
    """Open Backtest Toplevel: date range, Run, Export, summary, equity curve, trades table, breakdown tabs."""
    from egx_radar.ui.components import _enqueue

    win = tk.Toplevel(root)
    win.title("📊 Backtest")
    win.configure(bg=C.BG)
    win.geometry("1200x720")

    # Controls
    ctrl = tk.Frame(win, bg=C.BG, pady=8)
    ctrl.pack(fill="x", padx=14)
    tk.Label(ctrl, text="Date From:", font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 4))
    date_from_var = tk.StringVar(value="2020-01-01")
    tk.Entry(ctrl, textvariable=date_from_var, font=F_SMALL, width=12).pack(side="left", padx=(0, 12))
    tk.Label(ctrl, text="Date To:", font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 4))
    date_to_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    tk.Entry(ctrl, textvariable=date_to_var, font=F_SMALL, width=12).pack(side="left", padx=(0, 12))
    tk.Label(ctrl, text="Max Bars:", font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 4))
    max_bars_var = tk.StringVar(value=str(K.BT_MAX_BARS))
    tk.Entry(ctrl, textvariable=max_bars_var, font=F_SMALL, width=4).pack(side="left", padx=(0, 16))

    progress_var = tk.StringVar(value="Ready — set dates and click Run Backtest")
    tk.Label(ctrl, textvariable=progress_var, font=F_SMALL, fg=C.CYAN, bg=C.BG).pack(side="left", padx=8)

    def do_run() -> None:
        try:
            date_from = date_from_var.get().strip()
            date_to = date_to_var.get().strip()
            max_bars = max(int(max_bars_var.get().strip()), K.BT_MAX_BARS)
        except ValueError:
            _enqueue(lambda: messagebox.showerror("Error", "Invalid date or max bars"))
            return

        def run_in_thread() -> None:
            def progress(msg: str) -> None:
                _enqueue(lambda: progress_var.set(msg))

            _enqueue(lambda: progress_var.set("Loading data…"))
            try:
                result = run_backtest(
                    date_from=date_from,
                    date_to=date_to,
                    max_bars=max_bars,
                    max_concurrent_trades=5,
                    progress_callback=progress,
                )
                # run_backtest returns 4 values: (trades, equity_curve, params, guard_stats)
                # The original code unpacked only 3, causing ValueError on every single run.
                if len(result) == 4:
                    trades, equity_curve, params, _guard_stats = result
                else:
                    trades, equity_curve, params = result
            except Exception as exc:
                log.exception("Backtest failed: %s", exc)
                _enqueue(lambda: messagebox.showerror("Backtest Error", str(exc)))
                _enqueue(lambda: progress_var.set("Error — see message"))
                return

            metrics = compute_metrics(trades)
            with STATE._lock:
                STATE.backtest_results = {
                    "trades": trades,
                    "equity_curve": equity_curve,
                    "metrics": metrics,
                    "params": params,
                }

            def refresh() -> None:
                progress_var.set(f"Done — {len(trades)} trades")
                _refresh_summary(metrics["overall"], summary_lbl)
                _refresh_equity_canvas(equity_curve, equity_canvas)
                _refresh_trades_table(trades, trades_tree)
                _refresh_breakdown(metrics, regime_tree, sector_tree, month_tree)

            _enqueue(refresh)

        _enqueue(lambda: progress_var.set("Running backtest…"))
        threading.Thread(target=run_in_thread, daemon=True).start()

    tk.Button(ctrl, text="▶ Run Backtest", font=F_HEADER, fg=C.BG, bg=C.ACCENT,
              relief="flat", padx=12, pady=4, command=do_run).pack(side="right", padx=4)

    def do_export() -> None:
        with STATE._lock:
            data = STATE.backtest_results
        if not data or not data.get("trades"):
            messagebox.showwarning("Export", "Run a backtest first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"EGX_Radar_Backtest_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Backtest Results",
        )
        if not path:
            return
        trades = data["trades"]
        if not trades:
            messagebox.showwarning("Export", "No trades to export.")
            return
        cols = list(trades[0].keys())
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(trades)
        messagebox.showinfo("Saved ✅", f"Exported {len(trades)} trades to:\n{path}")

    tk.Button(ctrl, text="💾 Export CSV", font=F_HEADER, fg=C.TEXT, bg=C.BG3,
              relief="flat", padx=10, pady=4, command=do_export).pack(side="right")

    # Content: summary + equity curve row
    content = tk.Frame(win, bg=C.BG)
    content.pack(fill="both", expand=True, padx=14, pady=4)

    left = tk.Frame(content, bg=C.BG)
    left.pack(side="left", fill="y", padx=(0, 12))
    summary_lbl = tk.Label(
        left, text="Win Rate: —\nTotal R: —\nMax DD: —\nSharpe: —\nProfit F: —",
        font=F_SMALL, fg=C.ACCENT2, bg=C.BG2, justify="left", padx=12, pady=10,
    )
    summary_lbl.pack(anchor="w")

    equity_canvas = tk.Canvas(content, width=700, height=180, bg=C.BG2, highlightthickness=0)
    equity_canvas.pack(side="left", fill="both", expand=True)

    # Trades table
    table_frm = tk.Frame(win, bg=C.BG)
    table_frm.pack(fill="both", expand=True, padx=14, pady=4)
    cols = ("Date", "Symbol", "Signal", "Entry", "Exit", "P&L%", "Regime")
    trades_tree = ttk.Treeview(table_frm, columns=cols, show="headings", height=10)
    for c in cols:
        trades_tree.heading(c, text=c)
        trades_tree.column(c, width=90 if c != "Symbol" else 70, anchor="center")
    vsb_t = ttk.Scrollbar(table_frm, orient="vertical", command=trades_tree.yview)
    trades_tree.configure(yscrollcommand=vsb_t.set)
    vsb_t.pack(side="right", fill="y")
    trades_tree.pack(fill="both", expand=True)

    # Breakdown tabs
    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=14, pady=4)
    regime_frm = tk.Frame(nb, bg=C.BG)
    sector_frm = tk.Frame(nb, bg=C.BG)
    month_frm = tk.Frame(nb, bg=C.BG)
    nb.add(regime_frm, text="By Regime")
    nb.add(sector_frm, text="By Sector")
    nb.add(month_frm, text="By Month")

    rc = ("Regime", "Win%", "Avg R:R", "Trades")
    regime_tree = ttk.Treeview(regime_frm, columns=rc, show="headings", height=6)
    for c in rc:
        regime_tree.heading(c, text=c)
        regime_tree.column(c, width=100)
    regime_tree.pack(fill="both", expand=True)

    sc = ("Sector", "Win%", "Trades", "Avg Return%")
    sector_tree = ttk.Treeview(sector_frm, columns=sc, show="headings", height=6)
    for c in sc:
        sector_tree.heading(c, text=c)
        sector_tree.column(c, width=120)
    sector_tree.pack(fill="both", expand=True)

    mc = ("Month", "Return%", "Win%")
    month_tree = ttk.Treeview(month_frm, columns=mc, show="headings", height=6)
    for c in mc:
        month_tree.heading(c, text=c)
        month_tree.column(c, width=100)
    month_tree.pack(fill="both", expand=True)

    def _refresh_summary(overall: Dict[str, Any], lbl: tk.Label) -> None:
        o = overall or {}
        lbl.configure(
            text=(
                f"Win Rate: {o.get('win_rate_pct', '—')}%\n"
                f"Total R: {o.get('total_return_pct', '—')}%\n"
                f"Max DD: {o.get('max_drawdown_pct', '—')}%\n"
                f"Sharpe: {o.get('sharpe_ratio', '—')}\n"
                f"Profit F: {o.get('profit_factor', '—')}"
            )
        )

    def _refresh_equity_canvas(curve: List[tuple], canvas: tk.Canvas) -> None:
        canvas.delete("all")
        if not curve or len(curve) < 2:
            canvas.create_text(350, 90, text="No equity curve", fill=C.MUTED)
            return
        w, h = 700, 180
        padding = 40
        ys = [y for _, y in curve]
        y_min = min(ys)
        y_max = max(ys)
        y_range = (y_max - y_min) or 1.0
        x_step = (w - 2 * padding) / max(1, len(curve) - 1)
        points = []
        for i, (_, y) in enumerate(curve):
            px = padding + i * x_step
            ny = (y - y_min) / y_range
            py = h - padding - ny * (h - 2 * padding)
            points.append((px, py))
        peak = ys[0]
        for i in range(1, len(points)):
            y_val = curve[i][1]
            if y_val > peak:
                peak = y_val
            elif peak > y_min and i > 0:
                x0 = points[i - 1][0]
                x1 = points[i][0]
                canvas.create_rectangle(x0, 0, x1, h, fill="#2a1a1a", outline="")
        for i in range(1, len(points)):
            color = C.GREEN if curve[i][1] >= 0 else C.RED
            canvas.create_line(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1], fill=color, width=2)
        canvas.create_text(w // 2, 12, text="Cumulative return %", fill=C.MUTED, font=F_MICRO)

    def _refresh_trades_table(trades: List[dict], tree: ttk.Treeview) -> None:
        tree.delete(*tree.get_children())
        for t in trades:
            tree.insert("", tk.END, values=(
                t.get("exit_date", "—"),
                t.get("sym", "—"),
                t.get("signal_type", "—"),
                f"{t.get('entry', 0):.2f}",
                f"{t.get('exit', 0):.2f}",
                f"{t.get('pnl_pct', 0):.2f}%",
                t.get("regime", "—"),
            ))

    def _refresh_breakdown(
        metrics: Dict[str, Any],
        rt: ttk.Treeview,
        st: ttk.Treeview,
        mt: ttk.Treeview,
    ) -> None:
        for tree in (rt, st, mt):
            tree.delete(*tree.get_children())
        for reg, data in (metrics.get("per_regime") or {}).items():
            rt.insert("", tk.END, values=(
                reg,
                f"{data.get('win_rate_pct', 0)}%",
                data.get("avg_rr", 0),
                data.get("total_trades", 0),
            ))
        for sec, data in (metrics.get("per_sector") or {}).items():
            st.insert("", tk.END, values=(
                sec,
                f"{data.get('win_rate_pct', 0)}%",
                data.get("total_trades", 0),
                f"{data.get('avg_return_pct', 0)}%",
            ))
        for m in metrics.get("monthly") or []:
            mt.insert("", tk.END, values=(
                m.get("month", "—"),
                f"{m.get('return_pct', 0)}%",
                f"{m.get('win_rate_pct', 0)}%",
            ))

    # Pre-fill from last run if any
    with STATE._lock:
        data = STATE.backtest_results
    if data:
        _refresh_summary(data.get("metrics", {}).get("overall", {}), summary_lbl)
        _refresh_equity_canvas(data.get("equity_curve", []), equity_canvas)
        _refresh_trades_table(data.get("trades", []), trades_tree)
        _refresh_breakdown(data.get("metrics", {}), regime_tree, sector_tree, month_tree)
