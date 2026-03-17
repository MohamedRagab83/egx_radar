"""Tkinter main window and layout wiring (Layer 10)."""

import logging
from typing import Dict

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from egx_radar.config.settings import (
    K,
    C,
    F_TITLE,
    F_HEADER,
    F_BODY,
    F_SMALL,
    F_MICRO,
    SECTORS,
    DATA_SOURCE_CFG,
    _data_cfg_lock,
    get_account_size,
)
from egx_radar.state.app_state import STATE
from egx_radar.ui.components import (
    _enqueue,
    _pump,
    _pulse,
    draw_gauge,
    _show_tooltip,
    _destroy_tooltip,
    export_csv,
)
from egx_radar.outcomes.engine import oe_load_log, oe_load_history
from egx_radar.data.fetchers import load_source_settings, save_source_settings
from egx_radar.backtest import open_backtest_window
from egx_radar import __version__

log = logging.getLogger(__name__)


def main() -> None:
    from egx_radar.scan.runner import start_scan, request_shutdown

    STATE.load()
    load_source_settings()

    root = tk.Tk()
    root.title(f"EGX Capital Flow Radar v{__version__} — Signal Quality Upgrade")
    root.geometry("2400x980")
    root.configure(bg=C.BG)

    # ── Header ────────────────────────────────────────────────────────────────
    hdr = tk.Frame(root, bg=C.BG, pady=6)
    hdr.pack(fill="x", padx=16)
    tk.Label(hdr, text=f"⚡ EGX CAPITAL FLOW RADAR v{__version__} 🧲🧠🔮🎯🧭🔔🛡️📊",
             font=F_TITLE, fg=C.ACCENT, bg=C.BG).pack(side="left")

    gauge_flow = tk.Canvas(hdr, width=160, height=110, bg=C.BG, highlightthickness=0)
    gauge_flow.pack(side="right", padx=(4, 8))
    gauge_rank = tk.Canvas(hdr, width=160, height=110, bg=C.BG, highlightthickness=0)
    gauge_rank.pack(side="right", padx=(4, 2))
    draw_gauge(gauge_rank, 0, K.SMART_RANK_SCALE, "SmartRank",  "waiting…")
    draw_gauge(gauge_flow, 0, 1.0,                "FutureFlow", "waiting…")

    scan_btn = tk.Button(hdr, text="🚀 Gravity Scan [F5]",
                         font=F_HEADER, fg=C.BG, bg=C.ACCENT, relief="flat", padx=12, pady=4)
    scan_btn.pack(side="right", padx=4)

    force_refresh_var = tk.BooleanVar(value=False)
    tk.Checkbutton(hdr, text="Force Refresh", variable=force_refresh_var,
                   font=F_BODY, fg=C.MUTED, bg=C.BG, selectcolor=C.BG3,
                   activebackground=C.BG).pack(side="right", padx=8)

    # ── Top bar ───────────────────────────────────────────────────────────────
    top_bar = tk.Frame(root, bg=C.BG, pady=4)
    top_bar.pack(fill="x", padx=16)
    tk.Label(top_bar, text="🔥 Sector Flow:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0, 6))

    heat_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(top_bar, text=f"{sec}\n—", width=15, height=2,
                       bg=C.BG3, fg=C.MUTED, font=("Consolas", 9, "bold"))
        lbl.pack(side="left", padx=3)
        heat_labels[sec] = lbl

    brain_lbl = tk.Label(top_bar, text="🧠 NEUTRAL", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    brain_lbl.pack(side="right", padx=12)

    save_btn = tk.Button(top_bar, text="💾 Save CSV", font=F_HEADER,
                         fg=C.TEXT, bg=C.BG3, relief="flat", padx=8, pady=3)
    save_btn.pack(side="right", padx=6)

    # ── Outcomes window ───────────────────────────────────────────────────────
    def open_outcomes() -> None:
        win = tk.Toplevel(root)
        win.title("📊 Trade Outcomes")
        win.configure(bg=C.BG)
        win.geometry("1100x660")

        stats_frm = tk.Frame(win, bg=C.BG, pady=6)
        stats_frm.pack(fill="x", padx=14)
        stats_lbl = tk.Label(stats_frm, text="Loading…", font=F_HEADER, fg=C.ACCENT, bg=C.BG, anchor="w")
        stats_lbl.pack(side="left", fill="x", expand=True)

        nb   = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=14, pady=4)

        oc   = ("Symbol", "Sector", "Date", "Entry", "Stop", "Target", "ATR", "Rank", "Action")
        oc_w = (60, 90, 90, 70, 70, 70, 50, 60, 90)
        hc   = ("Symbol", "Sector", "Date", "Entry", "Exit", "Stop", "Target", "Status", "Days", "MFE%", "MAE%", "PnL%", "Rank")
        hc_w = (60, 90, 90, 70, 70, 70, 70, 72, 46, 60, 60, 60, 60)

        open_frm  = tk.Frame(nb, bg=C.BG); nb.add(open_frm, text="🔓 Open")
        open_tree = ttk.Treeview(open_frm, columns=oc, show="headings", height=18, style="Dark.Treeview")
        for col, w in zip(oc, oc_w):
            open_tree.heading(col, text=col); open_tree.column(col, width=w, anchor="center", stretch=False)
        vsb_o = ttk.Scrollbar(open_frm, orient="vertical", command=open_tree.yview)
        open_tree.configure(yscrollcommand=vsb_o.set); vsb_o.pack(side="right", fill="y")
        open_tree.pack(fill="both", expand=True)

        hist_frm  = tk.Frame(nb, bg=C.BG); nb.add(hist_frm, text="📜 History")
        hist_tree = ttk.Treeview(hist_frm, columns=hc, show="headings", height=18, style="Dark.Treeview")
        for col, w in zip(hc, hc_w):
            hist_tree.heading(col, text=col); hist_tree.column(col, width=w, anchor="center", stretch=False)
        hist_tree.tag_configure("WIN",     background="#0a2218", foreground=C.GREEN)
        hist_tree.tag_configure("LOSS",    background="#220a0a", foreground=C.RED)
        hist_tree.tag_configure("TIMEOUT", background="#1c1a08", foreground=C.YELLOW)
        vsb_h = ttk.Scrollbar(hist_frm, orient="vertical", command=hist_tree.yview)
        hist_tree.configure(yscrollcommand=vsb_h.set); vsb_h.pack(side="right", fill="y")
        hist_tree.pack(fill="both", expand=True)

        def _refresh():
            ot = oe_load_log(); hist = oe_load_history()
            tot  = len(hist); w = sum(1 for t in hist if t.get("status") == "WIN")
            l    = sum(1 for t in hist if t.get("status") == "LOSS")
            to   = sum(1 for t in hist if t.get("status") == "TIMEOUT")
            wr   = (w / tot * 100) if tot else 0.0
            avmf = (sum(t.get("mfe_pct", 0) for t in hist) / tot) if tot else 0.0
            avma = (sum(t.get("mae_pct", 0) for t in hist) / tot) if tot else 0.0
            avpn = (sum(t.get("pnl_pct", 0) for t in hist) / tot) if tot else 0.0
            stats_lbl.configure(text=(
                f"📊 Resolved:{tot}  ✅W:{w}  ❌L:{l}  ⏱TO:{to}  "
                f"WR:{wr:.1f}%  MFE:{avmf:.1f}%  MAE:{avma:.1f}%  PnL:{avpn:.1f}%  Open:{len(ot)}"
            ))
            nb.tab(0, text=f"🔓 Open ({len(ot)})"); nb.tab(1, text=f"📜 History ({tot})")
            open_tree.delete(*open_tree.get_children())
            for t in sorted(ot, key=lambda x: x.get("date", ""), reverse=True):
                open_tree.insert("", tk.END, values=(
                    t.get("sym","—"), t.get("sector","—"), t.get("date","—"),
                    f"{t.get('entry',0):.2f}", f"{t.get('stop',0):.2f}",
                    f"{t.get('target',0):.2f}", f"{t.get('atr',0):.2f}",
                    f"{t.get('smart_rank',0):.1f}", t.get("action","—"),
                ))
            hist_tree.delete(*hist_tree.get_children())
            for t in sorted(hist, key=lambda x: x.get("resolved_date",""), reverse=True):
                status = t.get("status","—")
                hist_tree.insert("", tk.END, values=(
                    t.get("sym","—"), t.get("sector","—"), t.get("date","—"),
                    f"{t.get('entry',0):.2f}", f"{t.get('exit_price',0):.2f}",
                    f"{t.get('stop',0):.2f}", f"{t.get('target',0):.2f}",
                    status, t.get("days_held","—"),
                    f"{t.get('mfe_pct',0):.1f}%", f"{t.get('mae_pct',0):.1f}%",
                    f"{t.get('pnl_pct',0):.1f}%", f"{t.get('smart_rank',0):.1f}",
                ), tags=(status,))

        tk.Button(stats_frm, text="🔄 Refresh", font=F_HEADER, fg=C.BG, bg=C.ACCENT,
                  relief="flat", padx=8, pady=2, command=_refresh).pack(side="right", padx=8)
        _refresh()

    outcomes_btn = tk.Button(top_bar, text="📊 Outcomes", font=F_HEADER,
                              fg=C.BG, bg="#1a5276", relief="flat", padx=8, pady=3, command=open_outcomes)
    outcomes_btn.pack(side="right", padx=6)

    backtest_btn = tk.Button(top_bar, text="📊 Backtest", font=F_HEADER,
                             fg=C.BG, bg="#1a5c4d", relief="flat", padx=8, pady=3,
                             command=lambda: open_backtest_window(root))
    backtest_btn.pack(side="right", padx=6)

    # ── Capital calculator ────────────────────────────────────────────────────
    def open_calc() -> None:
        rows_data = [tree.item(k)["values"] for k in tree.get_children("")]
        if not rows_data:
            messagebox.showwarning("Calc", "Run a scan first!")
            return
        win = tk.Toplevel(root)
        win.title("💰 Capital Calculator")
        win.geometry("680x520")
        win.configure(bg=C.BG)
        win.grab_set()
        tk.Label(win, text="💰 Position Size Calculator", font=F_TITLE, fg=C.GOLD, bg=C.BG).pack(pady=(12, 4))
        inp_frm = tk.Frame(win, bg=C.BG2, padx=16, pady=10)
        inp_frm.pack(fill="x", padx=16, pady=4)
        tk.Label(inp_frm, text="Account Size (EGP):", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).grid(row=0, column=0, sticky="e", padx=6)
        acct_var = tk.StringVar(value=str(int(K.ACCOUNT_SIZE)))
        tk.Entry(inp_frm, textvariable=acct_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=14).grid(row=0, column=1, padx=6)
        tk.Label(inp_frm, text="Risk per trade (%):", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).grid(row=0, column=2, sticky="e", padx=6)
        risk_var = tk.StringVar(value="2")
        tk.Entry(inp_frm, textvariable=risk_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=6).grid(row=0, column=3, padx=6)

        ctf = tk.Frame(win, bg=C.BG); ctf.pack(fill="both", expand=True, padx=16, pady=6)
        CCOLS = ("Symbol","Action","Entry","Stop","Target","Risk/Share","# Shares","Total Invest","Max Loss","Max Profit")
        ctree = ttk.Treeview(ctf, columns=CCOLS, show="headings", height=14)
        for c in CCOLS:
            ctree.heading(c, text=c); ctree.column(c, width=88 if c in ("Symbol","Action","Total Invest","Max Profit") else 68, anchor="center")
        cvsb = ttk.Scrollbar(ctf, orient="vertical", command=ctree.yview)
        ctree.configure(yscrollcommand=cvsb.set); cvsb.pack(side="right", fill="y"); ctree.pack(fill="both", expand=True)

        col_idx = {c: i for i, c in enumerate(COLS)}

        def recalc(*_):
            ctree.delete(*ctree.get_children())
            try:
                acct = float(acct_var.get().replace(",", ""))
                risk_pct = float(risk_var.get()) / 100.0
            except ValueError:
                return
            risk_amt = acct * risk_pct
            for row in rows_data:
                try:
                    sym    = row[col_idx["Symbol"]]
                    action = row[col_idx["Action"]]
                    entry  = float(row[col_idx["Entry"]])
                    stop   = float(row[col_idx["Stop"]])
                    target = float(row[col_idx["Target"]])
                except (IndexError, ValueError, KeyError):
                    continue
                rps   = max(abs(entry - stop), 0.01)
                shares = max(1, int(risk_amt / rps))
                ctree.insert("", tk.END, values=(
                    sym, action, f"{entry:.2f}", f"{stop:.2f}", f"{target:.2f}",
                    f"{rps:.2f}", shares, f"{shares*entry:,.0f}", f"{shares*rps:,.0f}", f"{shares*abs(target-entry):,.0f}",
                ))

        recalc()
        acct_var.trace_add("write", recalc)
        risk_var.trace_add("write", recalc)
        tk.Label(win, text="💡 Change account size or risk% — table updates live",
                 font=F_SMALL, fg=C.MUTED, bg=C.BG).pack(pady=4)

    calc_btn = tk.Button(top_bar, text="💰 Calc", font=F_HEADER,
                          fg=C.BG, bg=C.GOLD, relief="flat", padx=8, pady=3, command=open_calc)
    calc_btn.pack(side="right", padx=6)

    # ── Source settings ───────────────────────────────────────────────────────
    def open_settings() -> None:
        win = tk.Toplevel(root)
        win.title("⚙️ الإعدادات")
        win.geometry("520x700")
        win.configure(bg=C.BG)
        win.grab_set()

        bottom_frm = tk.Frame(win, bg=C.BG)
        bottom_frm.pack(side="bottom", fill="x", pady=10)

        content_frm = tk.Frame(win, bg=C.BG)
        content_frm.pack(side="top", fill="both", expand=True)

        tk.Label(content_frm, text="⚙️ الإعدادات", font=F_TITLE, fg=C.ACCENT, bg=C.BG).pack(pady=(14, 4))

        nb = ttk.Notebook(content_frm)
        nb.pack(fill="both", expand=True, padx=12, pady=4)

        # ── Tab 1: Account & Data Sources ─────────────────────────────────────
        tab_main = tk.Frame(nb, bg=C.BG2); nb.add(tab_main, text="📊 الإعدادات العامة")

        # --- Section 1: Capital ---
        cap_frm = tk.LabelFrame(tab_main, text="💰 رأس المال (Capital)", bg=C.BG2, fg=C.GOLD, font=F_HEADER, padx=10, pady=10)
        cap_frm.pack(fill="x", padx=10, pady=10)

        tk.Label(cap_frm, text="حجم الحساب (ج.م):", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).grid(row=0, column=0, sticky="w", pady=5)
        
        with _data_cfg_lock:
            _acct = float(DATA_SOURCE_CFG.get("account_size", K.ACCOUNT_SIZE))
            
        acct_var = tk.StringVar(value=f"{_acct:,.0f}")
        tk.Entry(cap_frm, textvariable=acct_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=16).grid(row=0, column=1, padx=10, pady=5)

        def _apply_capital():
            try:
                new_acct = float(acct_var.get().replace(",", ""))
                assert new_acct > 0
            except (ValueError, AssertionError):
                messagebox.showerror("خطأ", "قيمة غير صحيحة في إعدادات الحساب.")
                return

            with _data_cfg_lock:
                DATA_SOURCE_CFG["account_size"] = new_acct

            save_source_settings()
            _refresh_account_badge()
            messagebox.showinfo("تم الحفظ ✅", f"تم تحديث رأس المال إلى: {new_acct:,.0f} ج.م")

        tk.Button(cap_frm, text="Set Capital", font=F_BODY, fg=C.BG, bg=C.GOLD, relief="flat", padx=10, command=_apply_capital).grid(row=0, column=2, padx=10)

        # --- Section 2: Data Sources ---
        src_frm = tk.LabelFrame(tab_main, text="🌐 مصادر البيانات (Data Sources)", bg=C.BG2, fg=C.CYAN, font=F_HEADER, padx=10, pady=10)
        src_frm.pack(fill="x", padx=10, pady=10)

        vars_map = {}
        for key, label, desc in [
            ("use_yahoo",        "✅ Yahoo Finance", "Primary — 2yr history"),
            ("use_stooq",        "📊 Stooq",         "Free, no key"),
            ("use_alpha_vantage","🔑 Alpha Vantage",  "Requires free API key"),
            ("use_investing",    "🌐 Investing.com",  "Price cross-check only"),
            ("use_twelve_data",  "🕐 Twelve Data",    "Best EGX coverage"),
        ]:
            with _data_cfg_lock:
                cur = bool(DATA_SOURCE_CFG.get(key, False))
            v = tk.BooleanVar(value=cur); vars_map[key] = v
            row = tk.Frame(src_frm, bg=C.BG2); row.pack(fill="x", pady=2)
            tk.Checkbutton(row, text=label, variable=v, font=F_BODY, fg=C.TEXT,
                           bg=C.BG2, selectcolor=C.BG3, activebackground=C.BG2).pack(side="left")
            tk.Label(row, text=desc, font=F_SMALL, fg=C.MUTED, bg=C.BG2).pack(side="left", padx=8)

        tk.Label(src_frm, text="🔑 Alpha Vantage API Key:", font=F_BODY, fg=C.ACCENT2, bg=C.BG2).pack(anchor="w", pady=(8,0))
        with _data_cfg_lock:
            cur_av = str(DATA_SOURCE_CFG.get("alpha_vantage_key", ""))
        av_var = tk.StringVar(value=cur_av)
        tk.Entry(src_frm, textvariable=av_var, font=F_BODY, fg=C.TEXT, bg=C.BG3, insertbackground=C.TEXT, width=38).pack(pady=4, fill="x")

        tk.Label(src_frm, text="🕐 Twelve Data API Key:", font=F_BODY, fg=C.GOLD, bg=C.BG2).pack(anchor="w", pady=(10,0))
        with _data_cfg_lock:
            cur_td = str(DATA_SOURCE_CFG.get("twelve_data_key", ""))
        td_var = tk.StringVar(value=cur_td)
        td_entry = tk.Entry(src_frm, textvariable=td_var, font=F_BODY, fg=C.TEXT, bg=C.BG3,
                            insertbackground=C.TEXT, width=38, show="*")
        td_entry.pack(pady=2, fill="x")

        def _apply_sources():
            with _data_cfg_lock:
                for k, v in vars_map.items():
                    DATA_SOURCE_CFG[k] = v.get()
                DATA_SOURCE_CFG["alpha_vantage_key"] = av_var.get().strip()
                DATA_SOURCE_CFG["twelve_data_key"]   = td_var.get().strip()
            
            save_source_settings()
            src_badge_var.set(_build_src_badge())
            messagebox.showinfo("تم الحفظ ✅", "تم تحديث مصادر البيانات!")

        tk.Button(src_frm, text="Update Sources", font=F_BODY, fg=C.BG, bg=C.CYAN, relief="flat", padx=10, pady=5, command=_apply_sources).pack(pady=10)

        # ── Tab 2: Advanced Risk ──────────────────────────────────────────────
        tab_risk = tk.Frame(nb, bg=C.BG2); nb.add(tab_risk, text="⚠️ إعدادات المخاطر (متقدم)")
        frm_r = tk.Frame(tab_risk, bg=C.BG2, padx=20, pady=16); frm_r.pack(fill="x")

        def _lbl_entry(parent, row_i, label, var, desc="", fg=C.ACCENT2):
            tk.Label(parent, text=label, font=F_BODY, fg=fg, bg=C.BG2, anchor="w").grid(
                row=row_i, column=0, sticky="w", pady=5)
            e = tk.Entry(parent, textvariable=var, font=F_BODY, fg=C.TEXT,
                         bg=C.BG3, insertbackground=C.TEXT, width=16)
            e.grid(row=row_i, column=1, padx=10, pady=5, sticky="w")
            if desc:
                tk.Label(parent, text=desc, font=F_SMALL, fg=C.MUTED, bg=C.BG2, anchor="w").grid(
                    row=row_i, column=2, sticky="w", padx=4)
            return e

        with _data_cfg_lock:
            _risk = float(DATA_SOURCE_CFG.get("risk_per_trade", K.RISK_PER_TRADE))
            _exp  = float(DATA_SOURCE_CFG.get("portfolio_max_atr_exposure", K.PORTFOLIO_MAX_ATR_EXPOSURE))
            _mps  = int(DATA_SOURCE_CFG.get("portfolio_max_per_sector", K.PORTFOLIO_MAX_PER_SECTOR))

        risk_var = tk.StringVar(value=f"{_risk*100:.1f}")
        exp_var  = tk.StringVar(value=f"{_exp*100:.1f}")
        mps_var  = tk.StringVar(value=str(_mps))

        _lbl_entry(frm_r, 0, "⚠️ نسبة المخاطرة لكل صفقة %:", risk_var,
                   "الافتراضي 2% (نصيحة: 1-3%)")
        _lbl_entry(frm_r, 1, "🛡️ حد ATR Exposure %:", exp_var,
                   "الافتراضي 4% — رفعه يسمح بإشارات أكثر")
        _lbl_entry(frm_r, 2, "📊 أقصى أسهم لكل قطاع:", mps_var,
                   "الافتراضي 2")

        def _apply_risk():
            try:
                new_risk = float(risk_var.get()) / 100
                new_exp  = float(exp_var.get()) / 100
                new_mps  = int(mps_var.get())
                assert 0 < new_risk <= 0.5 and 0 < new_exp <= 0.5 and new_mps >= 1
            except (ValueError, AssertionError):
                messagebox.showerror("خطأ", "قيمة غير صحيحة في إعدادات المخاطر.")
                return

            with _data_cfg_lock:
                DATA_SOURCE_CFG["risk_per_trade"]             = new_risk
                DATA_SOURCE_CFG["portfolio_max_atr_exposure"] = new_exp
                DATA_SOURCE_CFG["portfolio_max_per_sector"]   = new_mps
            
            save_source_settings()
            messagebox.showinfo("تم الحفظ ✅", "تم تحديث إعدادات المخاطر المتقدمة!")

        tk.Button(frm_r, text="Update Risk Settings", font=F_BODY, fg=C.BG, bg=C.ACCENT, relief="flat", padx=10, pady=5, command=_apply_risk).grid(row=3, column=0, columnspan=3, pady=10)


        tk.Button(bottom_frm, text="🚪 إغلاق نافذة الإعدادات (Close)", font=F_HEADER, fg=C.TEXT, bg=C.BG3,
                  relief="flat", padx=14, pady=7, command=win.destroy).pack()

    def _build_src_badge() -> str:
        with _data_cfg_lock:
            parts = []
            if DATA_SOURCE_CFG.get("use_yahoo"):         parts.append("Yahoo")
            if DATA_SOURCE_CFG.get("use_stooq"):         parts.append("Stooq")
            if DATA_SOURCE_CFG.get("use_alpha_vantage"): parts.append("AV")
            if DATA_SOURCE_CFG.get("use_investing"):     parts.append("INV")
            if DATA_SOURCE_CFG.get("use_twelve_data"):   parts.append("TD🕐")
        return "🌐 " + "+".join(parts) if parts else "🌐 Yahoo"

    src_badge_var = tk.StringVar(value=_build_src_badge())
    tk.Label(top_bar, textvariable=src_badge_var, font=F_SMALL, fg=C.CYAN, bg=C.BG).pack(side="right", padx=4)
    tk.Button(
        top_bar,
        text="⚙️ Sources",
        font=("Segoe UI", 11, "bold"),
        fg="#ffffff",
        bg="#0b6a9c",
        activeforeground="#ffffff",
        activebackground="#1580b8",
        relief="flat",
        padx=12,
        pady=5,
        command=open_settings,
    ).pack(side="right", padx=4)

    # ── Account badge (live) ───────────────────────────────────────────────────
    acct_badge_var = tk.StringVar(value=f"💼 {get_account_size():,.0f} ج.م")
    tk.Label(top_bar, textvariable=acct_badge_var, font=F_SMALL, fg=C.GOLD, bg=C.BG).pack(side="right", padx=6)

    def _refresh_account_badge():
        acct_badge_var.set(f"💼 {get_account_size():,.0f} ج.م")

    # ── Market Health Dashboard ───────────────────────────────────────────────
    health_bar = tk.Frame(root, bg="#0d1b2a", pady=4)
    health_bar.pack(fill="x", padx=16, pady=(4, 0))
    
    tk.Label(health_bar, text="📈 Market Health:", font=F_HEADER, fg=C.CYAN, bg="#0d1b2a").pack(side="left", padx=(6, 12))
    
    health_lbl = tk.Label(health_bar, text="Label: —", font=("Segoe UI", 10, "bold"), fg=C.MUTED, bg="#0d1b2a")
    health_lbl.pack(side="left", padx=8)

    health_avg_var = tk.StringVar(value="Avg Rank: 0.0")
    tk.Label(health_bar, textvariable=health_avg_var, font=F_BODY, fg=C.WHITE, bg="#0d1b2a").pack(side="left", padx=8)

    health_act_var = tk.StringVar(value="Actionable (>35): 0")
    tk.Label(health_bar, textvariable=health_act_var, font=F_BODY, fg=C.GREEN, bg="#0d1b2a").pack(side="left", padx=8)

    health_elite_var = tk.StringVar(value="Elite (>45): 0")
    tk.Label(health_bar, textvariable=health_elite_var, font=F_BODY, fg=C.CYAN, bg="#0d1b2a").pack(side="left", padx=8)

    health_sell_var = tk.StringVar(value="SELL Signals: 0")
    tk.Label(health_bar, textvariable=health_sell_var, font=F_BODY, fg=C.RED, bg="#0d1b2a").pack(side="left", padx=8)

    verdict_frm = tk.Frame(root, bg="#06131f", pady=5)
    verdict_frm.pack(fill="x", padx=16, pady=(4, 0))
    verdict_var = tk.StringVar(value="🧠 Awaiting scan…")
    verdict_lbl_w = tk.Label(verdict_frm, textvariable=verdict_var,
                              font=("Consolas", 11, "bold"), fg=C.ACCENT2, bg="#06131f", anchor="w")
    verdict_lbl_w.pack(fill="x", padx=10)

    # ── Rotation + flow + guard bars ──────────────────────────────────────────
    rot_bar = tk.Frame(root, bg=C.BG, pady=3)
    rot_bar.pack(fill="x", padx=16)
    tk.Label(rot_bar, text="🔮 Rotation:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    rot_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(rot_bar, text=f"{sec}\n—", width=15, height=2, bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); rot_labels[sec] = lbl

    flow_bar = tk.Frame(root, bg=C.BG, pady=3)
    flow_bar.pack(fill="x", padx=16)
    tk.Label(flow_bar, text="🧭 ΔFlow:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    flow_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(flow_bar, text=f"{sec}\n—", width=15, height=2, bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); flow_labels[sec] = lbl
    regime_lbl = tk.Label(flow_bar, text="📊 NEUTRAL", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    regime_lbl.pack(side="right", padx=12)

    guard_bar = tk.Frame(root, bg=C.BG, pady=3)
    guard_bar.pack(fill="x", padx=16)
    tk.Label(guard_bar, text="🛡️ Guard:", font=F_HEADER, fg=C.MUTED, bg=C.BG).pack(side="left", padx=(0,6))
    guard_sector_labels: Dict[str, tk.Label] = {}
    for sec in SECTORS:
        lbl = tk.Label(guard_bar, text=f"{sec}\n0/{K.PORTFOLIO_MAX_PER_SECTOR}", width=15, height=2,
                       bg=C.BG3, fg=C.MUTED, font=("Consolas",9,"bold"))
        lbl.pack(side="left", padx=3); guard_sector_labels[sec] = lbl
    guard_exposure_lbl = tk.Label(guard_bar, text="ATR Exp: 0.0%", font=F_HEADER, fg=C.MUTED, bg=C.BG)
    guard_exposure_lbl.pack(side="right", padx=12)
    guard_blocked_lbl = tk.Label(guard_bar, text="🛡️ Blocked: —", font=F_SMALL, fg=C.MUTED, bg=C.BG)
    guard_blocked_lbl.pack(side="right", padx=8)

    # ── Progress + status ─────────────────────────────────────────────────────
    pbar = ttk.Progressbar(root, orient="horizontal", mode="determinate")
    pbar.pack(fill="x", padx=16, pady=4)
    status_var = tk.StringVar(value="Ready ✅ — Press 🚀 Gravity Scan or F5")
    tk.Label(root, textvariable=status_var, font=F_SMALL, fg=C.MUTED, bg=C.BG, anchor="w", pady=2).pack(fill="x", padx=20)

    # ── Results table ─────────────────────────────────────────────────────────
    tf = tk.Frame(root, bg=C.BG)
    tf.pack(fill="both", expand=True, padx=16, pady=4)

    global COLS
    COLS = (
        "Symbol", "Sector", "Price", "ADX", "RSI", "AdaptMom",
        "% EMA200", "Volume", "Tech%", "Gravity", "Zone",
        "🔮Future", "🧠CPI", "🏛️IET", "🐳Whale",
        "Phase/Signals", "Signal", "Direction", "Confidence%", "SmartRank",
        "Action", "Timeframe", "Entry", "Stop", "Target", "Size", "WinRate%",
        "R:R", "🔥InstConf", "ATR Risk", "Trend", "ATR", "VWAP%", "VolZ",
        "Signal Reason", "🛡️Guard",
    )
    col_w = {
        "Symbol": 50, "Sector": 88, "Price": 64, "ADX": 48, "RSI": 46,
        "AdaptMom": 68, "% EMA200": 72, "Volume": 60, "Tech%": 46,
        "Gravity": 100, "Zone": 70, "🔮Future": 68,
        "🧠CPI": 58, "🏛️IET": 58, "🐳Whale": 62,
        "Phase/Signals": 215, "Signal": 155, "Direction": 82,
        "Confidence%": 74, "SmartRank": 80,
        "Action": 100, "Timeframe": 110, "Entry": 65, "Stop": 65, "Target": 65,
        "Size": 52, "WinRate%": 68, "R:R": 58, "🔥InstConf": 90,
        "ATR Risk": 72, "Trend": 40, "ATR": 60, "VWAP%": 65, "VolZ": 55,
        "Signal Reason": 220, "🛡️Guard": 260,
    }

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background=C.BG2, foreground=C.TEXT,
                    rowheight=27, font=F_BODY, fieldbackground=C.BG2, borderwidth=0)
    style.configure("Treeview.Heading", background=C.BG3, foreground=C.MUTED,
                    font=F_HEADER, relief="flat")
    style.map("Treeview", background=[("selected", C.ROW_SEL)], foreground=[("selected", C.WHITE)])
    # FIX: Dark.Treeview used in Outcomes window but was never defined; inherit from Treeview
    style.configure("Dark.Treeview", background=C.BG2, foreground=C.TEXT,
                    rowheight=25, font=F_BODY, fieldbackground=C.BG2, borderwidth=0)
    style.configure("Dark.Treeview.Heading", background=C.BG3, foreground=C.MUTED,
                    font=F_SMALL, relief="flat")
    style.map("Dark.Treeview", background=[("selected", C.ROW_SEL)], foreground=[("selected", C.WHITE)])

    tree = ttk.Treeview(tf, columns=COLS, show="headings", height=18)
    for c in COLS:
        tree.heading(c, text=c)
        tree.column(c, width=col_w.get(c, 70), anchor="center", minwidth=40)

    for tag_name, (bg, fg) in {
        "ultra":     ("#071c2b", C.CYAN),
        "early":     ("#0a1f33", C.CYAN),
        "buy":       ("#0a2218", C.GREEN),
        "watch":     ("#1c1a08", C.YELLOW),
        "sell":      ("#220a0a", C.RED),
        "radar":     ("#0f1a26", C.ACCENT2),
        "accum_top": ("#2a1e00", C.GOLD),
        "blocked":   ("#1a1a2e", C.MUTED),
    }.items():
        tree.tag_configure(tag_name, background=bg, foreground=fg)

    vsb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    tree.bind("<Motion>",   lambda e: _show_tooltip(e, tree, COLS))
    tree.bind("<Leave>",    _destroy_tooltip)
    tree.bind("<Button-1>", _destroy_tooltip)

    # ── Legend ────────────────────────────────────────────────────────────────
    leg = tk.Frame(root, bg=C.BG, pady=3)
    leg.pack(fill="x", padx=20)
    for txt, col in [
        ("🧠 ULTRA", C.CYAN), ("🚀 EARLY", C.CYAN), ("🔥 BUY", C.GREEN),
        ("👀 WATCH", C.YELLOW), ("❌ SELL", C.RED),
        ("🧬 Silent", C.ACCENT2), ("🐳 Whale", C.PURPLE), ("🎯 Hunter", C.YELLOW),
        ("💥 Break", "#ff9f43"), ("⚡ Exp", C.CYAN), ("🧿 Quantum", C.PURPLE),
        ("☠️ Fake", C.RED), ("👑 Leader", C.YELLOW), ("🧲 Gravity", C.CYAN),
        ("ACCUMULATE", C.GOLD), ("PROBE", C.YELLOW), ("🔔 EMA✚", C.GREEN),
        ("🔀 VolDiv", C.YELLOW), ("|  ⚠️OB WATCH", C.YELLOW),
        ("|  ⚠️ATR HIGH", C.RED), ("|  🟡ATR MED", C.YELLOW),
        ("⏳ WAIT(ADX)", C.MUTED), ("|  🛡️BLOCKED", C.MUTED),
        ("|  ⚡Flow>Tech", C.YELLOW), ("|  🔒RankCap", C.MUTED),
        ("|  ⌛WR-Build", C.MUTED), ("|  v78✅", C.GREEN),
    ]:
        tk.Label(leg, text=txt, font=F_MICRO, fg=col, bg=C.BG, padx=4).pack(side="left")

    tk.Label(root, text="⚠️  Data delayed 15 minutes — execution risk warning",
             fg=C.RED_DIM, bg=C.BG, font=F_MICRO).pack(side="bottom", pady=2)

    # ── Wire up ───────────────────────────────────────────────────────────────
    widgets = {
        "tree": tree, "pbar": pbar, "status_var": status_var,
        "gauge_rank": gauge_rank, "gauge_flow": gauge_flow,
        "heat_labels": heat_labels, "rot_labels": rot_labels,
        "flow_labels": flow_labels, "regime_lbl": regime_lbl,
        "brain_lbl": brain_lbl, "verdict_var": verdict_var,
        "verdict_frm": verdict_frm, "verdict_lbl_w": verdict_lbl_w,
        "scan_btn": scan_btn,
        "guard_sector_labels": guard_sector_labels,
        "guard_exposure_lbl":  guard_exposure_lbl,
        "guard_blocked_lbl":   guard_blocked_lbl,
        "health_lbl":          health_lbl,
        "health_avg_var":      health_avg_var,
        "health_act_var":      health_act_var,
        "health_elite_var":    health_elite_var,
        "health_sell_var":     health_sell_var,
        "force_refresh_var":   force_refresh_var,
    }
    scan_btn.configure(command=lambda: start_scan(widgets))
    save_btn.configure(command=lambda: export_csv(tree, COLS))
    root.bind("<F5>", lambda _: start_scan(widgets))

    def _on_close():
        request_shutdown()
        _pulse.stop()
        STATE.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    _pump(root)
    root.mainloop()


__all__ = ["main"]
