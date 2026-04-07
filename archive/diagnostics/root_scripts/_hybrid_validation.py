#!/usr/bin/env python
"""
EGX Radar — HYBRID SYSTEM 6-YEAR VALIDATION + BEFORE/AFTER COMPARISON
======================================================================
Runs the full 2020→2026 backtest with hybrid settings and generates
a 10-part professional report with Before vs After comparison.
"""

import sys, os, math, json, traceback
# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics

# ── BEFORE snapshot (from previous validation) ──────────────────────
BEFORE = {
    "total_trades": 5,
    "trades_per_year": 0.8,
    "win_rate": 40.0,
    "total_pnl": -0.34,
    "profit_factor": 0.97,
    "max_drawdown": 0.57,
    "expectancy": -0.068,
    "avg_bars": 3.0,
    "strong_trades": 3,
    "medium_trades": 2,
    "strong_wr": 67.0,
    "medium_wr": 0.0,
    "years_with_trades": 3,
    "years_without": 3,
}

PERIODS = [
    ("2020-01-01", "2020-12-31", "2020"),
    ("2021-01-01", "2021-12-31", "2021"),
    ("2022-01-01", "2022-12-31", "2022"),
    ("2023-01-01", "2023-12-31", "2023"),
    ("2024-01-01", "2024-12-31", "2024"),
    ("2025-01-01", "2026-03-01", "2025-26Q1"),
]


def run_all_periods():
    all_trades = []
    all_missed = []
    yearly_results = {}
    errors = []

    for date_from, date_to, label in PERIODS:
        print(f"\n{'='*60}")
        print(f"  Running: {label} ({date_from} → {date_to})")
        print(f"{'='*60}")
        try:
            trades, equity, params, extras = run_backtest(
                date_from, date_to,
                max_bars=K.BT_MAX_BARS,
                max_concurrent_trades=K.PORTFOLIO_MAX_OPEN_TRADES,
                entry_mode="touch",
            )
            missed = extras.get("missed_entries", [])
            print(f"  → {len(trades)} trades, {len(missed)} missed")
            for t in trades:
                t["_period"] = label
            yearly_results[label] = {"trades": trades, "equity": equity, "missed": missed}
            all_trades.extend(trades)
            all_missed.extend(missed)
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            errors.append(f"{label}: {e}")
            yearly_results[label] = {"trades": [], "equity": [], "missed": []}

    return all_trades, all_missed, yearly_results, errors


def compute_drawdown(trades):
    if not trades:
        return 0.0, 0, ""
    equity = 100.0
    peak = 100.0
    max_dd = 0.0
    max_dd_trade = ""
    dd_streak = 0
    max_dd_streak = 0
    for t in trades:
        alloc = float(t.get("alloc_pct", 0.20))
        equity *= (1 + alloc * t["pnl_pct"] / 100)
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            max_dd_trade = f"{t['sym']} {t.get('exit_date', '')}"
        if t["pnl_pct"] <= 0:
            dd_streak += 1
            max_dd_streak = max(max_dd_streak, dd_streak)
        else:
            dd_streak = 0
    return round(max_dd, 4), max_dd_streak, max_dd_trade


def compute_expectancy(trades):
    if not trades:
        return 0.0
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t["pnl_pct"] for t in losses)) / len(losses) if losses else 0
    wr = len(wins) / len(trades)
    return round(wr * avg_win - (1 - wr) * avg_loss, 4)


def generate_report(all_trades, all_missed, yearly_results, errors):
    L = []
    def W(t=""):
        L.append(t)
    def HR():
        W("=" * 72)

    HR()
    W("  EGX RADAR — HYBRID SYSTEM 6-YEAR VALIDATION")
    W(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    HR()
    W()

    # ── PART 1: CONFIGURATION ──────────────────────────────────────────
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  PART 1: HYBRID SYSTEM CONFIGURATION                        ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    W(f"  SmartRank STRONG:     >= {K.TRADE_TYPE_STRONG_MIN} (risk {K.RISK_PER_TRADE_STRONG*100:.2f}%)")
    W(f"  SmartRank MEDIUM:     >= {K.TRADE_TYPE_MEDIUM_MIN} (risk {K.RISK_PER_TRADE_MEDIUM*100:.2f}%)")
    W(f"  Min SmartRank:        {K.BT_MIN_SMARTRANK}")
    W(f"  Max Open Trades:      {K.PORTFOLIO_MAX_OPEN_TRADES}")
    W(f"  Daily Top N:          {K.BT_DAILY_TOP_N}")
    W(f"  Quality Gate:         5/10 soft checks (3 hard disqualifiers kept)")
    W(f"  Regime:               BULL=all, NEUTRAL=STRONG only, BEAR=none")
    W(f"  Max Stop Loss:        {K.MAX_STOP_LOSS_PCT*100:.1f}%")
    W(f"  Slippage:             {K.BT_SLIPPAGE_PCT*100:.1f}%")
    W(f"  Fees:                 {K.BT_FEES_PCT*100:.1f}%")
    W()

    # ── PART 2: BEFORE vs AFTER ────────────────────────────────────────
    total = len(all_trades)
    wins = [t for t in all_trades if t["pnl_pct"] > 0]
    losses = [t for t in all_trades if t["pnl_pct"] <= 0]
    wr = len(wins) / total * 100 if total else 0
    total_pnl = sum(t["pnl_pct"] for t in all_trades)
    gp = sum(t["pnl_pct"] for t in wins)
    gl = abs(sum(t["pnl_pct"] for t in losses))
    pf = gp / (gl + 1e-9) if gl else float("inf")
    exp = compute_expectancy(all_trades)
    max_dd, max_streak, dd_trade = compute_drawdown(all_trades)
    avg_bars = sum(t.get("bars_held", 0) for t in all_trades) / max(total, 1)

    # Tier breakdown
    strong = [t for t in all_trades if t.get("trade_type") == "STRONG" or t.get("smart_rank", 0) >= K.TRADE_TYPE_STRONG_MIN]
    medium = [t for t in all_trades if t not in strong]
    strong_wr = sum(1 for t in strong if t["pnl_pct"] > 0) / max(len(strong), 1) * 100
    medium_wr = sum(1 for t in medium if t["pnl_pct"] > 0) / max(len(medium), 1) * 100

    active_years = sum(1 for yr in yearly_results.values() if len(yr.get("trades", [])) > 0)

    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  PART 2: BEFORE vs AFTER COMPARISON                         ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    W(f"  {'Metric':<25} {'BEFORE':>12} {'AFTER':>12} {'Change':>12}")
    W("  " + "─" * 65)
    W(f"  {'Total Trades':<25} {BEFORE['total_trades']:>12} {total:>12} {total - BEFORE['total_trades']:>+12}")
    W(f"  {'Trades/Year':<25} {BEFORE['trades_per_year']:>12.1f} {total/6.17:>12.1f} {total/6.17 - BEFORE['trades_per_year']:>+12.1f}")
    W(f"  {'Win Rate %':<25} {BEFORE['win_rate']:>11.1f}% {wr:>11.1f}% {wr - BEFORE['win_rate']:>+11.1f}%")
    W(f"  {'Total PnL %':<25} {BEFORE['total_pnl']:>+11.2f}% {total_pnl:>+11.2f}% {total_pnl - BEFORE['total_pnl']:>+11.2f}%")
    W(f"  {'Profit Factor':<25} {BEFORE['profit_factor']:>12.2f} {pf:>12.2f} {pf - BEFORE['profit_factor']:>+12.2f}")
    W(f"  {'Max Drawdown %':<25} {BEFORE['max_drawdown']:>11.2f}% {max_dd:>11.2f}% {max_dd - BEFORE['max_drawdown']:>+11.2f}%")
    W(f"  {'Expectancy %/trade':<25} {BEFORE['expectancy']:>+11.4f}% {exp:>+11.4f}% {exp - BEFORE['expectancy']:>+11.4f}%")
    W(f"  {'Avg Bars Held':<25} {BEFORE['avg_bars']:>12.1f} {avg_bars:>12.1f} {avg_bars - BEFORE['avg_bars']:>+12.1f}")
    W(f"  {'Years with Trades':<25} {BEFORE['years_with_trades']:>12} {active_years:>12} {active_years - BEFORE['years_with_trades']:>+12}")
    W()

    # ── PART 3: CORE METRICS ──────────────────────────────────────────
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  PART 3: CORE METRICS                                       ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    if total == 0:
        W("  *** ZERO TRADES ***")
    else:
        avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
        W(f"  Total Trades:         {total}")
        W(f"  Trades/Year:          {total/6.17:.1f}")
        W(f"  Missed Signals:       {len(all_missed)}")
        W(f"  Win Rate:             {wr:.1f}% ({len(wins)}W / {len(losses)}L)")
        W(f"  Total PnL:            {total_pnl:+.2f}%")
        W(f"  Avg Return/Trade:     {total_pnl/total:+.2f}%")
        W(f"  Avg Win:              {avg_win:+.2f}%")
        W(f"  Avg Loss:             {avg_loss:+.2f}%")
        W(f"  Largest Win:          {max(t['pnl_pct'] for t in all_trades):+.2f}%")
        W(f"  Largest Loss:         {min(t['pnl_pct'] for t in all_trades):+.2f}%")
        W(f"  Profit Factor:        {pf:.2f}")
        W(f"  Expectancy:           {exp:+.4f}%/trade")
        W(f"  Max Drawdown:         {max_dd:.2f}%")
        W(f"  Max Losing Streak:    {max_streak} trades")
        W(f"  Avg Bars Held:        {avg_bars:.1f}")
    W()

    # ── PART 4: STRONG vs MEDIUM ──────────────────────────────────────
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  PART 4: STRONG vs MEDIUM PERFORMANCE                       ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    for label, group in [("STRONG (SR≥70)", strong), ("MEDIUM (45≤SR<70)", medium)]:
        if group:
            n = len(group)
            w = sum(1 for t in group if t["pnl_pct"] > 0)
            p = sum(t["pnl_pct"] for t in group)
            gp_g = sum(t["pnl_pct"] for t in group if t["pnl_pct"] > 0)
            gl_g = abs(sum(t["pnl_pct"] for t in group if t["pnl_pct"] <= 0))
            pf_g = gp_g / (gl_g + 1e-9) if gl_g else float("inf")
            dd_g, _, _ = compute_drawdown(group)
            W(f"  {label}:")
            W(f"    Trades:       {n}")
            W(f"    Win Rate:     {w/n*100:.1f}%")
            W(f"    Total PnL:    {p:+.2f}%")
            W(f"    Profit Factor:{pf_g:.2f}")
            W(f"    Max DD:       {dd_g:.2f}%")
            W()
        else:
            W(f"  {label}: 0 trades")
            W()

    # ── PART 5: CONSISTENCY BY YEAR ───────────────────────────────────
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  PART 5: CONSISTENCY BY YEAR                                ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    W(f"  {'Year':<12} {'Trades':>7} {'WR%':>7} {'PnL%':>9} {'DD%':>7} {'PF':>7}")
    W("  " + "─" * 55)
    yearly_stats = {}
    for label in [p[2] for p in PERIODS]:
        yr = yearly_results.get(label, {})
        trades = yr.get("trades", [])
        n = len(trades)
        if n == 0:
            W(f"  {label:<12} {0:>7} {'---':>7} {'---':>9} {'---':>7} {'---':>7}")
            yearly_stats[label] = {"trades": 0}
            continue
        w = sum(1 for t in trades if t["pnl_pct"] > 0)
        wr_y = w / n * 100
        pnl_y = sum(t["pnl_pct"] for t in trades)
        dd_y, _, _ = compute_drawdown(trades)
        gp_y = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0)
        gl_y = abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0))
        pf_y = gp_y / (gl_y + 1e-9) if gl_y else float("inf")
        pf_s = f"{pf_y:.2f}" if pf_y < 100 else "∞"
        W(f"  {label:<12} {n:>7} {wr_y:>6.1f}% {pnl_y:>+8.2f}% {dd_y:>6.2f}% {pf_s:>7}")
        yearly_stats[label] = {"trades": n, "wr": wr_y, "pnl": pnl_y}
    W()

    # ── PART 6: RISK PROFILE ─────────────────────────────────────────
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  PART 6: RISK PROFILE                                       ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    if total > 0:
        # Symbol & sector concentration
        by_sym = defaultdict(list)
        by_sec = defaultdict(list)
        for t in all_trades:
            by_sym[t["sym"]].append(t)
            by_sec[t.get("sector", "?")].append(t)
        W("  Symbol Distribution:")
        for sym, tl in sorted(by_sym.items(), key=lambda x: len(x[1]), reverse=True):
            p = sum(t["pnl_pct"] for t in tl)
            w = sum(1 for t in tl if t["pnl_pct"] > 0)
            W(f"    {sym:<8}: {len(tl)} trades, WR {w/len(tl)*100:.0f}%, PnL {p:+.2f}%")
        W()
        W("  Sector Distribution:")
        for sec, tl in sorted(by_sec.items(), key=lambda x: len(x[1]), reverse=True):
            p = sum(t["pnl_pct"] for t in tl)
            W(f"    {sec:<20}: {len(tl)} trades, PnL {p:+.2f}%")
        W()
        # Regime
        by_reg = defaultdict(list)
        for t in all_trades:
            by_reg[t.get("regime", "?")].append(t)
        W("  Regime Distribution:")
        for reg, tl in sorted(by_reg.items()):
            w = sum(1 for t in tl if t["pnl_pct"] > 0)
            p = sum(t["pnl_pct"] for t in tl)
            W(f"    {reg:<12}: {len(tl)} trades, WR {w/len(tl)*100:.0f}%, PnL {p:+.2f}%")
        W()
        # Partial TP / Trailing
        partials = sum(1 for t in all_trades if t.get("partial_taken"))
        trailing = sum(1 for t in all_trades if t.get("trailing_active"))
        W(f"  Partial TP Taken:     {partials}/{total} ({partials/total*100:.0f}%)")
        W(f"  Trailing Activated:   {trailing}/{total} ({trailing/total*100:.0f}%)")
    W()

    # ── PART 7: STABILITY ANALYSIS ───────────────────────────────────
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  PART 7: STABILITY ANALYSIS                                 ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    active = [s for s in yearly_stats.values() if s.get("trades", 0) > 0]
    if len(active) >= 2:
        wrs = [s["wr"] for s in active if "wr" in s]
        pnls = [s["pnl"] for s in active if "pnl" in s]
        prof_years = sum(1 for p in pnls if p > 0)
        W(f"  Active Years:         {len(active)} / {len(PERIODS)}")
        W(f"  Profitable Years:     {prof_years} / {len(active)}")
        if wrs:
            mean_wr = sum(wrs) / len(wrs)
            W(f"  Mean WR:              {mean_wr:.1f}%")
            if len(wrs) > 1:
                std = (sum((w - mean_wr)**2 for w in wrs) / (len(wrs)-1)) ** 0.5
                cv = std / mean_wr if mean_wr > 0 else float("inf")
                W(f"  WR Std Dev:           {std:.1f}%")
                W(f"  WR CV:                {cv:.2f} ({'stable' if cv < 0.3 else 'moderate' if cv < 0.6 else 'unstable'})")
    else:
        W("  Insufficient data for stability analysis.")
    W()

    # ── FULL TRADE LOG ────────────────────────────────────────────────
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  FULL TRADE LOG                                             ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()
    if total > 0:
        W(f"  {'#':>3} {'Sym':<8} {'Tier':<7} {'Entry':>10} {'Exit':>10} {'PnL%':>8} {'Out':<6} {'Bars':>5} {'SR':>5} {'Period':<10}")
        W("  " + "─" * 85)
        for i, t in enumerate(all_trades, 1):
            tier = t.get("trade_type", "?")
            W(f"  {i:>3} {t['sym']:<8} {tier:<7} {t.get('entry_date',''):<10} {t.get('exit_date',''):<10} "
              f"{t['pnl_pct']:>+7.2f}% {t.get('outcome','?'):<6} {t.get('bars_held',0):>5} "
              f"{t.get('smart_rank',0):>5.0f} {t.get('_period',''):<10}")
    W()

    # ── MISSED TRADES SUMMARY ────────────────────────────────────────
    if all_missed:
        W("╔═══════════════════════════════════════════════════════════════╗")
        W("║  MISSED TRADES SUMMARY                                      ║")
        W("╚═══════════════════════════════════════════════════════════════╝")
        W()
        by_reason = defaultdict(list)
        for m in all_missed:
            by_reason[m.get("reason", "unknown")].append(m)
        W(f"  Total Missed: {len(all_missed)}")
        for reason, ml in sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True):
            with_sim = [m for m in ml if "approx_pnl_pct" in m]
            if with_sim:
                avg = sum(m["approx_pnl_pct"] for m in with_sim) / len(with_sim)
                w = sum(1 for m in with_sim if m["approx_pnl_pct"] > 0)
                W(f"    {reason:<25}: {len(ml)} (sim WR {w/len(with_sim)*100:.0f}%, avg PnL {avg:+.2f}%)")
            else:
                W(f"    {reason:<25}: {len(ml)}")
        W()

    # ── DECISION ENGINE ──────────────────────────────────────────────
    HR()
    W()
    W("╔═══════════════════════════════════════════════════════════════╗")
    W("║  DECISION ENGINE — FINAL VERDICT                            ║")
    W("╚═══════════════════════════════════════════════════════════════╝")
    W()

    c = {}
    c["trades"] = total >= 30
    W(f"  [{'PASS' if c['trades'] else 'FAIL'}] Trades >= 30:        {total} {'✓' if c['trades'] else '✗'}")

    c["wr"] = wr >= 55 if total > 0 else False
    W(f"  [{'PASS' if c['wr'] else 'FAIL'}] Win Rate >= 55%:     {wr:.1f}% {'✓' if c['wr'] else '✗'}")

    c["dd"] = max_dd < 5
    W(f"  [{'PASS' if c['dd'] else 'FAIL'}] Max DD < 5%:         {max_dd:.2f}% {'✓' if c['dd'] else '✗'}")

    c["pf"] = pf > 1.2 if total > 0 else False
    W(f"  [{'PASS' if c['pf'] else 'FAIL'}] Profit Factor > 1.2: {pf:.2f} {'✓' if c['pf'] else '✗'}")

    c["exp"] = exp > 0 if total > 0 else False
    W(f"  [{'PASS' if c['exp'] else 'FAIL'}] Expectancy > 0:     {exp:+.4f}% {'✓' if c['exp'] else '✗'}")

    W()

    all_pass = all(c.values())
    HR()
    W()
    if all_pass:
        W("  ████████████████████████████████████████████████████████")
        W("  ██                                                    ██")
        W("  ██   VERDICT:  ✓ READY FOR REAL MONEY                ██")
        W("  ██                                                    ██")
        W("  ██   All criteria passed. System is balanced,         ██")
        W("  ██   active, and profitable over 6 years.             ██")
        W("  ██                                                    ██")
        W("  ████████████████████████████████████████████████████████")
    else:
        W("  ████████████████████████████████████████████████████████")
        W("  ██                                                    ██")
        W("  ██   VERDICT:  ✗ NOT READY FOR REAL MONEY            ██")
        W("  ██                                                    ██")
        failed = [k for k, v in c.items() if not v]
        for f in failed:
            labels = {"trades": "Insufficient trades", "wr": "Low win rate",
                      "dd": "High drawdown", "pf": "Low profit factor",
                      "exp": "Negative expectancy"}
            W(f"  ██   ✗ {labels.get(f, f):<47} ██")
        W("  ██                                                    ██")
        W("  ████████████████████████████████████████████████████████")
    W()

    # Improvement summary
    W("  IMPROVEMENT vs PREVIOUS SYSTEM:")
    trade_increase = total - BEFORE["total_trades"]
    W(f"    Trade count:    {BEFORE['total_trades']} → {total} ({trade_increase:+d}, {trade_increase/max(BEFORE['total_trades'],1)*100:+.0f}%)")
    W(f"    Win rate:       {BEFORE['win_rate']:.1f}% → {wr:.1f}% ({wr - BEFORE['win_rate']:+.1f}%)")
    W(f"    Total PnL:      {BEFORE['total_pnl']:+.2f}% → {total_pnl:+.2f}% ({total_pnl - BEFORE['total_pnl']:+.2f}%)")
    W(f"    Profit Factor:  {BEFORE['profit_factor']:.2f} → {pf:.2f}")
    W(f"    Max Drawdown:   {BEFORE['max_drawdown']:.2f}% → {max_dd:.2f}%")
    W(f"    Expectancy:     {BEFORE['expectancy']:+.4f}% → {exp:+.4f}%")
    W()
    W(f"  هل النظام جاهز للسوق الحقيقي؟  {'نعم ✓ — جاهز' if all_pass else 'لا ✗ — مش جاهز'}")
    HR()

    return "\n".join(L), c, {
        "total_trades": total, "win_rate": wr, "total_pnl": total_pnl,
        "profit_factor": round(pf, 2), "max_drawdown": round(max_dd, 2),
        "expectancy": exp, "criteria": c, "verdict": "READY" if all_pass else "NOT READY",
    }


if __name__ == "__main__":
    print()
    print("=" * 72)
    print("  EGX RADAR — HYBRID SYSTEM VALIDATION")
    print("  2020-01-01 -> 2026-03-01 (6+ years)")
    print("=" * 72)
    print()
    print("HYBRID SETTINGS:")
    print(f"  STRONG threshold:  SR >= {K.TRADE_TYPE_STRONG_MIN} (risk {K.RISK_PER_TRADE_STRONG*100:.2f}%)")
    print(f"  MEDIUM threshold:  SR >= {K.TRADE_TYPE_MEDIUM_MIN} (risk {K.RISK_PER_TRADE_MEDIUM*100:.2f}%)")
    print(f"  Min SmartRank:     {K.BT_MIN_SMARTRANK}")
    print(f"  Max Open Trades:   {K.PORTFOLIO_MAX_OPEN_TRADES}")
    print(f"  Daily Top N:       {K.BT_DAILY_TOP_N}")
    print(f"  Quality Gate:      5/10")
    print(f"  Regime:            BULL=all, NEUTRAL=STRONG only")
    print()

    all_trades, all_missed, yearly_results, errors = run_all_periods()

    print("\n\n")
    report, criteria, summary = generate_report(all_trades, all_missed, yearly_results, errors)
    print(report)

    ts = datetime.now().strftime('%Y-%m-%d_%H-%M')
    with open(f"HYBRID_REPORT_{ts}.txt", "w", encoding="utf-8") as f:
        f.write(report)
    with open(f"HYBRID_TRADES_{ts}.json", "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, default=str)
    with open(f"HYBRID_SUMMARY_{ts}.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Files saved: HYBRID_REPORT_{ts}.txt, HYBRID_TRADES_{ts}.json, HYBRID_SUMMARY_{ts}.json")
