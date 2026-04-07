#!/usr/bin/env python
"""
EGX Radar — FULL 6-YEAR VALIDATION (2020-01-01 → 2026-03-01)
=============================================================
Strict realism. Brutally honest. No justifying bad results.

10-Part Professional Report:
  1. Test Period & Configuration
  2. Realistic Execution Model
  3. Core Metrics
  4. Risk Analysis
  5. Consistency by Year
  6. Regime Analysis
  7. Failure Detection
  8. Trade Quality Analysis
  9. Final Report
 10. Decision Engine

Decision Criteria:
  trades >= 30 AND win_rate >= 55% AND max_drawdown < 5% AND consistency stable
  → "READY FOR REAL MONEY"
  Otherwise → "NOT READY"
"""

import sys, os, math, json, time, traceback
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
from egx_radar.backtest.engine import run_backtest
from egx_radar.backtest.metrics import compute_metrics


def log(msg=""):
    print(msg, flush=True)


# ════════════════════════════════════════════════════════════════════
# Year-by-year execution to avoid OOM on large date ranges
# ════════════════════════════════════════════════════════════════════

PERIODS = [
    ("2020-01-01", "2020-12-31", "2020"),
    ("2021-01-01", "2021-12-31", "2021"),
    ("2022-01-01", "2022-12-31", "2022"),
    ("2023-01-01", "2023-12-31", "2023"),
    ("2024-01-01", "2024-12-31", "2024"),
    ("2025-01-01", "2026-03-01", "2025-26Q1"),
]


def run_all_periods_pro():
    """Run backtest for each period, return combined results."""
    all_trades = []
    all_equity = []
    all_missed = []
    yearly_results = {}
    errors = []
    total_periods = len(PERIODS)
    pipeline_start = time.time()

    log("🚀 STARTING FULL VALIDATION...")

    for index, (date_from, date_to, label) in enumerate(PERIODS, 1):
        log(f"\n{'='*60}")
        log(f"[{index}/{total_periods}] Processing {label}")
        log(f"Date: {date_from} → {date_to}")
        log(f"{'='*60}")
        try:
            start_time = time.time()
            trades, equity, params, extras = run_backtest(
                date_from, date_to,
                max_bars=K.BT_MAX_BARS,
                max_concurrent_trades=K.PORTFOLIO_MAX_OPEN_TRADES,
                entry_mode="touch",
                progress_callback=lambda message, period=label: log(f"[{period}] {message}"),
            )
            duration = round(time.time() - start_time, 2)
            missed = extras.get("missed_entries", [])
            log(f"Trades: {len(trades)}")
            log(f"Missed: {len(missed)}")
            log(f"Time: {duration} sec")
            for t in trades:
                t["_period"] = label
            yearly_results[label] = {
                "trades": trades,
                "equity": equity,
                "missed": missed,
                "params": params,
                "duration_sec": duration,
            }
            all_trades.extend(trades)
            if len(all_equity) + len(equity) > 100000:
                all_equity = all_equity[-50000:]
            all_equity.extend(equity)
            all_missed.extend(missed)
        except Exception as e:
            duration = round(time.time() - start_time, 2) if "start_time" in locals() else 0.0
            err_msg = f"ERROR in {label}: {e}"
            log(err_msg)
            log(f"Time before failure: {duration} sec")
            log(traceback.format_exc().rstrip())
            errors.append(err_msg)
            yearly_results[label] = {
                "trades": [],
                "equity": [],
                "missed": [],
                "error": str(e),
                "duration_sec": duration,
            }

    log(f"Total pipeline time: {round(time.time() - pipeline_start, 2)} sec")
    log("🔥 ALL PERIODS COMPLETED")

    return all_trades, all_equity, all_missed, yearly_results, errors


# ════════════════════════════════════════════════════════════════════
# Metric computation helpers
# ════════════════════════════════════════════════════════════════════

def compute_drawdown(trades):
    """Compute max drawdown from trade sequence."""
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


def compute_monthly_returns(trades):
    """Group trades by exit month and compute monthly return."""
    monthly = defaultdict(list)
    for t in trades:
        exit_date = t.get("exit_date", "")
        if len(exit_date) >= 7:
            month_key = exit_date[:7]  # YYYY-MM
            monthly[month_key].append(t)
    
    results = {}
    for month, month_trades in sorted(monthly.items()):
        total_pnl = sum(t["pnl_pct"] for t in month_trades)
        wins = sum(1 for t in month_trades if t["pnl_pct"] > 0)
        wr = wins / len(month_trades) * 100 if month_trades else 0
        results[month] = {
            "trades": len(month_trades),
            "pnl_pct": round(total_pnl, 2),
            "win_rate": round(wr, 1),
        }
    return results


def compute_rolling_metrics(trades, window=10):
    """Compute rolling win rate and drawdown over N-trade windows."""
    if len(trades) < window:
        return [], []
    rolling_wr = []
    rolling_dd = []
    for i in range(window, len(trades) + 1):
        chunk = trades[i-window:i]
        wins = sum(1 for t in chunk if t["pnl_pct"] > 0)
        wr = wins / window * 100
        rolling_wr.append(round(wr, 1))
        dd, _, _ = compute_drawdown(chunk)
        rolling_dd.append(round(dd, 4))
    return rolling_wr, rolling_dd


def losing_streaks(trades):
    """Find all losing streaks."""
    streaks = []
    current = []
    for t in trades:
        if t["pnl_pct"] <= 0:
            current.append(t)
        else:
            if current:
                streaks.append(current)
            current = []
    if current:
        streaks.append(current)
    return streaks


def compute_expectancy(trades):
    """E = (WR × avg_win) - ((1-WR) × avg_loss)."""
    if not trades:
        return 0.0
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    if not wins or not losses:
        avg_win = sum(t["pnl_pct"] for t in wins) / max(len(wins), 1) if wins else 0
        avg_loss = abs(sum(t["pnl_pct"] for t in losses)) / max(len(losses), 1) if losses else 0
        wr = len(wins) / len(trades)
        return round(wr * avg_win - (1 - wr) * avg_loss, 4)
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins)
    avg_loss = abs(sum(t["pnl_pct"] for t in losses)) / len(losses)
    wr = len(wins) / len(trades)
    return round(wr * avg_win - (1 - wr) * avg_loss, 4)


def trade_quality_breakdown(trades):
    """Breakdown by trade_type, outcome, holding period."""
    by_type = defaultdict(list)
    by_outcome = defaultdict(list)
    by_bars = {"short": [], "medium": [], "long": []}
    
    for t in trades:
        by_type[t.get("trade_type", "UNCLASSIFIED")].append(t)
        by_outcome[t.get("outcome", "UNKNOWN")].append(t)
        bars = t.get("bars_held", 0)
        if bars <= 5:
            by_bars["short"].append(t)
        elif bars <= 12:
            by_bars["medium"].append(t)
        else:
            by_bars["long"].append(t)
    
    return by_type, by_outcome, by_bars


# ════════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ════════════════════════════════════════════════════════════════════

def generate_report(all_trades, all_equity, all_missed, yearly_results, errors):
    """Generate the full 10-part report."""
    
    lines = []
    def W(text=""):
        lines.append(text)
    def HR():
        W("═" * 70)
    def hr():
        W("─" * 70)
    
    HR()
    W("  EGX RADAR — FULL 6-YEAR VALIDATION REPORT")
    W(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    HR()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 1 — TEST PERIOD & CONFIGURATION
    # ═══════════════════════════════════════════════════════════════
    W()
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 1: TEST PERIOD & CONFIGURATION                       ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    W(f"  Test Period:          2020-01-01 → 2026-03-01 (6+ years)")
    W(f"  Execution Mode:       Year-by-year (avoid OOM)")
    W(f"  Account Size:         {K.ACCOUNT_SIZE:,.0f} EGP")
    W(f"  Risk Per Trade:       {K.RISK_PER_TRADE*100:.1f}%")
    W(f"  Max Open Trades:      {K.PORTFOLIO_MAX_OPEN_TRADES}")
    W(f"  Max Stop Loss:        {K.MAX_STOP_LOSS_PCT*100:.1f}%")
    W(f"  Partial TP:           {K.PARTIAL_TP_PCT*100:.1f}%")
    W(f"  Trailing Trigger:     {K.TRAILING_TRIGGER_PCT*100:.1f}%")
    W(f"  Trailing Stop:        {K.TRAILING_STOP_PCT*100:.1f}%")
    W(f"  Min SmartRank:        {K.BT_MIN_SMARTRANK}")
    W(f"  Min Action:           {K.BT_MIN_ACTION}")
    W(f"  Max Bars Held:        {K.BT_MAX_BARS}")
    W(f"  Daily Top N:          {K.BT_DAILY_TOP_N}")
    W(f"  Entry Mode:           touch (price must hit trigger)")
    W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 2 — REALISTIC EXECUTION MODEL
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 2: REALISTIC EXECUTION MODEL                         ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    W(f"  Slippage:             {K.BT_SLIPPAGE_PCT*100:.1f}% per trade")
    W(f"  Broker + EGX Fees:    {K.BT_FEES_PCT*100:.1f}% per trade")
    W(f"  Total Cost/Trade:     {K.BT_TOTAL_COST_PCT*100:.1f}%")
    W(f"  Gap Handling:         Stop priority (gap down → exit at open)")
    W(f"  Partial TP:           50% at +{K.PARTIAL_TP_PCT*100:.0f}%, stop→breakeven")
    W(f"  Trailing Stop:        Activates at +{K.TRAILING_TRIGGER_PCT*100:.0f}%, trails {K.TRAILING_STOP_PCT*100:.0f}%")
    W(f"  Max Holding:          {K.BT_MAX_BARS} bars → forced exit at close")
    W(f"  Quality Gate:         3 hard + 10 soft checks (≥6/10 required)")
    W(f"  Regime Filter:        BULL only (no entries in BEAR/NEUTRAL)")
    W()
    
    if errors:
        W("  ⚠ ERRORS DURING EXECUTION:")
        for e in errors:
            W(f"    {e}")
        W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 3 — CORE METRICS
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 3: CORE METRICS                                      ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    
    total_trades = len(all_trades)
    total_missed = len(all_missed)
    
    if total_trades == 0:
        W("  *** ZERO TRADES IN 6 YEARS ***")
        W("  The system generated NO actionable signals that passed all filters.")
        W("  This is a CRITICAL failure. Cannot compute any metrics.")
        W()
    else:
        wins = [t for t in all_trades if t["pnl_pct"] > 0]
        losses = [t for t in all_trades if t["pnl_pct"] <= 0]
        win_rate = len(wins) / total_trades * 100
        
        avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
        
        total_pnl = sum(t["pnl_pct"] for t in all_trades)
        gross_profit = sum(t["pnl_pct"] for t in wins)
        gross_loss = abs(sum(t["pnl_pct"] for t in losses))
        profit_factor = gross_profit / (gross_loss + 1e-9) if gross_loss else float("inf")
        
        expectancy = compute_expectancy(all_trades)
        max_dd, max_dd_streak, dd_trade = compute_drawdown(all_trades)
        
        avg_bars = sum(t.get("bars_held", 0) for t in all_trades) / total_trades
        avg_rr = sum(t.get("rr", 0) for t in all_trades) / total_trades
        
        largest_win = max(t["pnl_pct"] for t in all_trades) if all_trades else 0
        largest_loss = min(t["pnl_pct"] for t in all_trades) if all_trades else 0
        
        # Trades per year
        trades_per_year = total_trades / 6.17  # ~6.17 years
        
        W(f"  Total Trades:         {total_trades}")
        W(f"  Trades/Year:          {trades_per_year:.1f}")
        W(f"  Missed Signals:       {total_missed}")
        W()
        W(f"  Win Rate (PnL>0):     {win_rate:.1f}%")
        W(f"  Wins / Losses:        {len(wins)} / {len(losses)}")
        W()
        W(f"  Total PnL:            {total_pnl:+.2f}%")
        W(f"  Avg Return/Trade:     {total_pnl/total_trades:+.2f}%")
        W(f"  Avg Win:              {avg_win:+.2f}%")
        W(f"  Avg Loss:             {avg_loss:+.2f}%")
        W(f"  Largest Win:          {largest_win:+.2f}%")
        W(f"  Largest Loss:         {largest_loss:+.2f}%")
        W()
        W(f"  Profit Factor:        {profit_factor:.2f}")
        W(f"  Expectancy:           {expectancy:+.4f}%/trade")
        W(f"  Avg R:R:              {avg_rr:.2f}")
        W()
        W(f"  Max Drawdown:         {max_dd:.2f}%")
        W(f"  Max Losing Streak:    {max_dd_streak} trades")
        W(f"  DD Peak Trade:        {dd_trade}")
        W()
        W(f"  Avg Bars Held:        {avg_bars:.1f}")
        W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 4 — RISK ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 4: RISK ANALYSIS                                     ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    
    if total_trades > 0:
        # Losing streaks
        l_streaks = losing_streaks(all_trades)
        if l_streaks:
            longest = max(l_streaks, key=len)
            W(f"  Number of Losing Streaks:   {len(l_streaks)}")
            W(f"  Longest Losing Streak:      {len(longest)} trades")
            streak_loss = sum(t["pnl_pct"] for t in longest)
            W(f"  Worst Streak PnL:           {streak_loss:+.2f}%")
            W()
            W("  Losing Streak Details:")
            for i, streak in enumerate(l_streaks, 1):
                syms = [t["sym"] for t in streak]
                pnl = sum(t["pnl_pct"] for t in streak)
                W(f"    Streak {i}: {len(streak)} trades ({', '.join(syms)}) → {pnl:+.2f}%")
        else:
            W("  No losing streaks detected.")
        W()
        
        # Stop-hit analysis
        stop_hits = [t for t in all_trades if t.get("outcome") in ("WIN", "LOSS") 
                     and t.get("exit", 0) <= t.get("initial_stop", 0) * 1.01]
        full_stop_losses = [t for t in all_trades if t.get("outcome") == "LOSS"]
        W(f"  Full Stop Losses:         {len(full_stop_losses)}")
        W(f"  Forced Exits (max bars):  {len([t for t in all_trades if t.get('outcome') == 'EXIT'])}")
        W(f"  Clean Wins (target hit):  {len([t for t in all_trades if t.get('outcome') == 'WIN' and t.get('pnl_pct', 0) > 0])}")
        W()
        
        # Partial TP analysis
        partials = [t for t in all_trades if t.get("partial_taken")]
        W(f"  Partial TP Taken:         {len(partials)} / {total_trades} trades ({len(partials)/total_trades*100:.0f}%)")
        if partials:
            partial_avg = sum(t["pnl_pct"] for t in partials) / len(partials)
            W(f"  Avg PnL (with partial):   {partial_avg:+.2f}%")
        W()
        
        # Trailing stop analysis  
        trailing = [t for t in all_trades if t.get("trailing_active")]
        W(f"  Trailing Stop Activated:  {len(trailing)} / {total_trades} trades ({len(trailing)/total_trades*100:.0f}%)")
        W()
        
        # Concentration risk
        by_sym = defaultdict(list)
        for t in all_trades:
            by_sym[t["sym"]].append(t)
        W("  Symbol Concentration:")
        for sym, trades_list in sorted(by_sym.items(), key=lambda x: len(x[1]), reverse=True):
            pnl = sum(t["pnl_pct"] for t in trades_list)
            wr = sum(1 for t in trades_list if t["pnl_pct"] > 0) / len(trades_list) * 100
            W(f"    {sym:8s}: {len(trades_list)} trades, WR {wr:.0f}%, PnL {pnl:+.2f}%")
        W()
        
        # Sector concentration
        by_sector = defaultdict(list)
        for t in all_trades:
            by_sector[t.get("sector", "UNKNOWN")].append(t)
        W("  Sector Concentration:")
        for sector, trades_list in sorted(by_sector.items(), key=lambda x: len(x[1]), reverse=True):
            pnl = sum(t["pnl_pct"] for t in trades_list)
            wr = sum(1 for t in trades_list if t["pnl_pct"] > 0) / len(trades_list) * 100
            W(f"    {sector:20s}: {len(trades_list)} trades, WR {wr:.0f}%, PnL {pnl:+.2f}%")
        W()
    else:
        W("  Cannot compute risk metrics — zero trades.")
        W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 5 — CONSISTENCY BY YEAR
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 5: CONSISTENCY BY YEAR                               ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    W(f"  {'Year':<12} {'Trades':>7} {'WR%':>7} {'PnL%':>9} {'MaxDD%':>8} {'PF':>7} {'Exp%':>8}")
    hr()
    
    yearly_stats = {}
    for label in [p[2] for p in PERIODS]:
        yr = yearly_results.get(label, {})
        trades = yr.get("trades", [])
        n = len(trades)
        if n == 0:
            W(f"  {label:<12} {0:>7} {'---':>7} {'---':>9} {'---':>8} {'---':>7} {'---':>8}")
            yearly_stats[label] = {"trades": 0, "wr": 0, "pnl": 0, "dd": 0, "pf": 0, "exp": 0}
            continue
        
        wins = sum(1 for t in trades if t["pnl_pct"] > 0)
        wr = wins / n * 100
        pnl = sum(t["pnl_pct"] for t in trades)
        dd, _, _ = compute_drawdown(trades)
        gp = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0)
        gl = abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0))
        pf = gp / (gl + 1e-9) if gl else float("inf")
        exp = compute_expectancy(trades)
        
        yearly_stats[label] = {"trades": n, "wr": wr, "pnl": pnl, "dd": dd, "pf": pf, "exp": exp}
        
        pf_str = f"{pf:.2f}" if pf < 100 else "∞"
        W(f"  {label:<12} {n:>7} {wr:>6.1f}% {pnl:>+8.2f}% {dd:>7.2f}% {pf_str:>7} {exp:>+7.4f}%")
    
    W()
    
    # Consistency assessment
    active_years = [s for s in yearly_stats.values() if s["trades"] > 0]
    if len(active_years) >= 2:
        wr_values = [s["wr"] for s in active_years]
        pnl_values = [s["pnl"] for s in active_years]
        profitable_years = sum(1 for p in pnl_values if p > 0)
        
        W(f"  Years with Trades:    {len(active_years)} / {len(PERIODS)}")
        W(f"  Profitable Years:     {profitable_years} / {len(active_years)}")
        W(f"  WR Range:             {min(wr_values):.1f}% — {max(wr_values):.1f}%")
        W(f"  PnL Range:            {min(pnl_values):+.2f}% — {max(pnl_values):+.2f}%")
        
        # Stability metric: coefficient of variation of win rates
        if len(wr_values) > 1:
            mean_wr = sum(wr_values) / len(wr_values)
            std_wr = (sum((w - mean_wr)**2 for w in wr_values) / (len(wr_values) - 1)) ** 0.5
            cv = std_wr / mean_wr if mean_wr > 0 else float("inf")
            W(f"  WR Stability (CV):    {cv:.2f} ({'stable' if cv < 0.3 else 'unstable' if cv < 0.6 else 'highly unstable'})")
    else:
        W("  Insufficient active years for consistency analysis.")
    W()
    
    # Monthly breakdown
    if total_trades > 0:
        monthly = compute_monthly_returns(all_trades)
        if monthly:
            W("  Monthly Breakdown:")
            W(f"    {'Month':<10} {'Trades':>7} {'PnL%':>9} {'WR%':>7}")
            W("    " + "─" * 40)
            positive_months = 0
            negative_months = 0
            for month, data in sorted(monthly.items()):
                W(f"    {month:<10} {data['trades']:>7} {data['pnl_pct']:>+8.2f}% {data['win_rate']:>6.1f}%")
                if data["pnl_pct"] > 0:
                    positive_months += 1
                elif data["pnl_pct"] < 0:
                    negative_months += 1
            W()
            W(f"  Positive Months:      {positive_months}")
            W(f"  Negative Months:      {negative_months}")
            W(f"  Flat Months:          {len(monthly) - positive_months - negative_months}")
        W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 6 — REGIME ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 6: REGIME ANALYSIS                                   ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    
    if total_trades > 0:
        by_regime = defaultdict(list)
        for t in all_trades:
            by_regime[t.get("regime", "UNKNOWN")].append(t)
        
        W(f"  {'Regime':<15} {'Trades':>7} {'WR%':>7} {'PnL%':>9} {'Avg R:R':>8}")
        hr()
        for regime, trades_list in sorted(by_regime.items()):
            n = len(trades_list)
            wr = sum(1 for t in trades_list if t["pnl_pct"] > 0) / n * 100
            pnl = sum(t["pnl_pct"] for t in trades_list)
            avg_rr = sum(t.get("rr", 0) for t in trades_list) / n
            W(f"  {regime:<15} {n:>7} {wr:>6.1f}% {pnl:>+8.2f}% {avg_rr:>7.2f}")
        W()
        
        # Note: system only enters in BULL regime, so all trades should be BULL
        non_bull = [t for t in all_trades if t.get("regime") not in ("BULL", "Bullish")]
        if non_bull:
            W(f"  ⚠ WARNING: {len(non_bull)} trades entered in non-BULL regime!")
            for t in non_bull:
                W(f"    {t['sym']} {t.get('entry_date', '')} regime={t.get('regime', '?')}")
        else:
            W("  ✓ All trades entered in BULL regime (as expected)")
        W()
    else:
        W("  No regime analysis possible — zero trades.")
        W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 7 — FAILURE DETECTION
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 7: FAILURE DETECTION                                 ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    
    failures = []
    warnings = []
    
    # F1: Trade count
    if total_trades < 30:
        failures.append(f"CRITICAL: Only {total_trades} trades in 6 years (need ≥30). "
                       f"System is too selective to be statistically valid.")
    elif total_trades < 50:
        warnings.append(f"LOW SAMPLE: {total_trades} trades — marginally sufficient for statistics.")
    
    # F2: Win rate
    if total_trades > 0:
        overall_wr = sum(1 for t in all_trades if t["pnl_pct"] > 0) / total_trades * 100
        if overall_wr < 40:
            failures.append(f"CRITICAL: Win rate {overall_wr:.1f}% is below 40%.")
        elif overall_wr < 55:
            warnings.append(f"LOW WIN RATE: {overall_wr:.1f}% (target ≥55%)")
    
    # F3: Drawdown
    if total_trades > 0:
        dd_val, _, _ = compute_drawdown(all_trades)
        if dd_val > 10:
            failures.append(f"CRITICAL: Max drawdown {dd_val:.2f}% exceeds 10%.")
        elif dd_val > 5:
            warnings.append(f"HIGH DRAWDOWN: {dd_val:.2f}% (target <5%)")
    
    # F4: Profit factor
    if total_trades > 0:
        gp = sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] > 0)
        gl = abs(sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] <= 0))
        pf = gp / (gl + 1e-9) if gl else float("inf")
        if pf < 1.0:
            failures.append(f"CRITICAL: Profit factor {pf:.2f} < 1.0 — system loses money overall.")
        elif pf < 1.3:
            warnings.append(f"LOW PROFIT FACTOR: {pf:.2f} (needs ≥1.3 for real trading)")
    
    # F5: Years without trades
    empty_years = [label for label, s in yearly_stats.items() if s["trades"] == 0]
    if len(empty_years) >= 3:
        failures.append(f"CRITICAL: {len(empty_years)} years had ZERO trades: {', '.join(empty_years)}")
    elif empty_years:
        warnings.append(f"GAPS: {len(empty_years)} years with no trades: {', '.join(empty_years)}")
    
    # F6: Concentration risk
    if total_trades > 0:
        by_sym = defaultdict(int)
        for t in all_trades:
            by_sym[t["sym"]] += 1
        most_traded = max(by_sym.values())
        if most_traded > total_trades * 0.5:
            sym_name = [k for k, v in by_sym.items() if v == most_traded][0]
            warnings.append(f"CONCENTRATION: {most_traded}/{total_trades} trades in {sym_name}")
    
    # F7: Negative expectancy
    if total_trades > 0:
        exp = compute_expectancy(all_trades)
        if exp < 0:
            failures.append(f"CRITICAL: Negative expectancy {exp:.4f}%/trade. System destroys capital.")
    
    # F8: Missed trades analysis
    if total_missed > total_trades * 5 and total_missed > 20:
        warnings.append(f"EXCESSIVE FILTERING: {total_missed} missed vs {total_trades} taken. "
                       f"System may be over-filtered.")
    
    W("  FAILURES (deal-breakers):")
    if failures:
        for f in failures:
            W(f"    ✗ {f}")
    else:
        W("    None detected.")
    W()
    W("  WARNINGS (concerns):")
    if warnings:
        for w in warnings:
            W(f"    ⚠ {w}")
    else:
        W("    None detected.")
    W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 8 — TRADE QUALITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 8: TRADE QUALITY ANALYSIS                            ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    
    if total_trades > 0:
        by_type, by_outcome, by_bars = trade_quality_breakdown(all_trades)
        
        W("  By Trade Type:")
        for ttype, trades_list in sorted(by_type.items()):
            n = len(trades_list)
            wr = sum(1 for t in trades_list if t["pnl_pct"] > 0) / n * 100
            pnl = sum(t["pnl_pct"] for t in trades_list)
            W(f"    {ttype:<20s}: {n} trades, WR {wr:.0f}%, PnL {pnl:+.2f}%")
        W()
        
        W("  By Outcome:")
        for outcome, trades_list in sorted(by_outcome.items()):
            n = len(trades_list)
            pnl = sum(t["pnl_pct"] for t in trades_list)
            W(f"    {outcome:<10s}: {n} trades, PnL {pnl:+.2f}%")
        W()
        
        W("  By Holding Period:")
        for period_name, trades_list in [("Short (1-5)", by_bars["short"]), 
                                          ("Medium (6-12)", by_bars["medium"]),
                                          ("Long (13-20)", by_bars["long"])]:
            if trades_list:
                n = len(trades_list)
                wr = sum(1 for t in trades_list if t["pnl_pct"] > 0) / n * 100
                pnl = sum(t["pnl_pct"] for t in trades_list)
                avg_b = sum(t.get("bars_held", 0) for t in trades_list) / n
                W(f"    {period_name:<15s}: {n} trades, WR {wr:.0f}%, PnL {pnl:+.2f}%, avg {avg_b:.0f} bars")
        W()
        
        # SmartRank analysis
        sr_high = [t for t in all_trades if t.get("smart_rank", 0) >= 80]
        sr_mid  = [t for t in all_trades if 60 <= t.get("smart_rank", 0) < 80]
        sr_low  = [t for t in all_trades if t.get("smart_rank", 0) < 60]
        W("  By SmartRank:")
        for label, group in [("SR ≥ 80", sr_high), ("60 ≤ SR < 80", sr_mid), ("SR < 60", sr_low)]:
            if group:
                n = len(group)
                wr = sum(1 for t in group if t["pnl_pct"] > 0) / n * 100
                pnl = sum(t["pnl_pct"] for t in group)
                W(f"    {label:<15s}: {n} trades, WR {wr:.0f}%, PnL {pnl:+.2f}%")
        W()
        
        # Individual trade log
        W("  Full Trade Log:")
        W(f"    {'#':>3} {'Symbol':<8} {'Entry Date':<12} {'Exit Date':<12} {'Entry':>8} {'Exit':>8} {'PnL%':>8} {'Outcome':<8} {'Bars':>5} {'SR':>5}")
        W("    " + "─" * 95)
        for i, t in enumerate(all_trades, 1):
            W(f"    {i:>3} {t['sym']:<8} {t.get('entry_date',''):<12} {t.get('exit_date',''):<12} "
              f"{t.get('entry',0):>8.3f} {t.get('exit',0):>8.3f} {t['pnl_pct']:>+7.2f}% "
              f"{t.get('outcome','?'):<8} {t.get('bars_held',0):>5} {t.get('smart_rank',0):>5.0f}")
        W()
    else:
        W("  No trades to analyze.")
        W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 9 — MISSED TRADES ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 9: MISSED TRADES ANALYSIS                            ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    
    if all_missed:
        # Group by reason
        by_reason = defaultdict(list)
        for m in all_missed:
            by_reason[m.get("reason", "unknown")].append(m)
        
        W(f"  Total Missed Signals:  {len(all_missed)}")
        W()
        W("  By Rejection Reason:")
        for reason, missed_list in sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True):
            n = len(missed_list)
            with_approx = [m for m in missed_list if "approx_pnl_pct" in m]
            if with_approx:
                avg_pnl = sum(m["approx_pnl_pct"] for m in with_approx) / len(with_approx)
                wins = sum(1 for m in with_approx if m["approx_pnl_pct"] > 0)
                wr = wins / len(with_approx) * 100
                W(f"    {reason:<25s}: {n:>4} signals (simulated: WR {wr:.0f}%, avg PnL {avg_pnl:+.2f}%)")
            else:
                W(f"    {reason:<25s}: {n:>4} signals")
        W()
        
        # Top missed by score
        scored_missed = [m for m in all_missed if m.get("score", 0) > 0]
        scored_missed.sort(key=lambda m: m.get("score", 0), reverse=True)
        if scored_missed[:10]:
            W("  Top 10 Missed Signals (by SmartRank):")
            W(f"    {'Symbol':<8} {'Date':<12} {'Score':>6} {'Reason':<20} {'Approx PnL':>10}")
            W("    " + "─" * 60)
            for m in scored_missed[:10]:
                approx = f"{m.get('approx_pnl_pct', 0):+.2f}%" if "approx_pnl_pct" in m else "N/A"
                W(f"    {m['sym']:<8} {m.get('signal_date',''):<12} {m.get('score',0):>6.1f} "
                  f"{m.get('reason',''):<20} {approx:>10}")
        W()
    else:
        W("  No missed signals recorded.")
        W()
    
    # ═══════════════════════════════════════════════════════════════
    # PART 10 — DECISION ENGINE
    # ═══════════════════════════════════════════════════════════════
    HR()
    W()
    W("╔══════════════════════════════════════════════════════════════╗")
    W("║  PART 10: DECISION ENGINE — FINAL VERDICT                  ║")
    W("╚══════════════════════════════════════════════════════════════╝")
    W()
    
    # Decision criteria
    criteria = {}
    
    # C1: Trade count
    criteria["trades_sufficient"] = total_trades >= 30
    W(f"  [{'PASS' if criteria['trades_sufficient'] else 'FAIL'}] Trades ≥ 30: "
      f"{total_trades} trades {'✓' if criteria['trades_sufficient'] else '✗ INSUFFICIENT SAMPLE'}")
    
    # C2: Win rate
    if total_trades > 0:
        wr = sum(1 for t in all_trades if t["pnl_pct"] > 0) / total_trades * 100
        criteria["win_rate_ok"] = wr >= 55
        W(f"  [{'PASS' if criteria['win_rate_ok'] else 'FAIL'}] Win Rate ≥ 55%: "
          f"{wr:.1f}% {'✓' if criteria['win_rate_ok'] else '✗'}")
    else:
        criteria["win_rate_ok"] = False
        W(f"  [FAIL] Win Rate ≥ 55%: N/A (zero trades)")
    
    # C3: Max drawdown
    if total_trades > 0:
        dd, _, _ = compute_drawdown(all_trades)
        criteria["drawdown_ok"] = dd < 5
        W(f"  [{'PASS' if criteria['drawdown_ok'] else 'FAIL'}] Max Drawdown < 5%: "
          f"{dd:.2f}% {'✓' if criteria['drawdown_ok'] else '✗'}")
    else:
        criteria["drawdown_ok"] = True  # vacuously true
        W(f"  [PASS] Max Drawdown < 5%: N/A (zero trades, zero DD)")
    
    # C4: Consistency
    if len(active_years) >= 2:
        wr_values = [s["wr"] for s in active_years]
        mean_wr = sum(wr_values) / len(wr_values)
        if len(wr_values) > 1:
            std_wr = (sum((w - mean_wr)**2 for w in wr_values) / (len(wr_values) - 1)) ** 0.5
            cv = std_wr / mean_wr if mean_wr > 0 else float("inf")
        else:
            cv = 0
        criteria["consistency_ok"] = cv < 0.3
        W(f"  [{'PASS' if criteria['consistency_ok'] else 'FAIL'}] Consistency (CV < 0.3): "
          f"{cv:.2f} {'✓' if criteria['consistency_ok'] else '✗'}")
    else:
        criteria["consistency_ok"] = False
        W(f"  [FAIL] Consistency (CV < 0.3): insufficient data")
    
    # C5: Positive expectancy
    if total_trades > 0:
        exp = compute_expectancy(all_trades)
        criteria["expectancy_ok"] = exp > 0
        W(f"  [{'PASS' if criteria['expectancy_ok'] else 'FAIL'}] Positive Expectancy: "
          f"{exp:+.4f}% {'✓' if criteria['expectancy_ok'] else '✗'}")
    else:
        criteria["expectancy_ok"] = False
        W(f"  [FAIL] Positive Expectancy: N/A")
    
    # C6: Profit factor
    if total_trades > 0:
        gp = sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] > 0)
        gl = abs(sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] <= 0))
        pf = gp / (gl + 1e-9) if gl else float("inf")
        criteria["profit_factor_ok"] = pf >= 1.0
        W(f"  [{'PASS' if criteria['profit_factor_ok'] else 'FAIL'}] Profit Factor ≥ 1.0: "
          f"{pf:.2f} {'✓' if criteria['profit_factor_ok'] else '✗'}")
    else:
        criteria["profit_factor_ok"] = False
        W(f"  [FAIL] Profit Factor ≥ 1.0: N/A")
    
    W()
    
    # VERDICT
    all_pass = all(criteria.values())
    critical_fails = len(failures)
    
    HR()
    W()
    if all_pass and critical_fails == 0:
        W("  ████████████████████████████████████████████████████████")
        W("  ██                                                    ██")
        W("  ██   VERDICT:  ✓ READY FOR REAL MONEY                ██")
        W("  ██                                                    ██")  
        W("  ██   All criteria passed. System survived 6 years     ██")
        W("  ██   with acceptable risk and consistent returns.     ██")
        W("  ██                                                    ██")
        W("  ████████████████████████████████████████████████████████")
    else:
        W("  ████████████████████████████████████████████████████████")
        W("  ██                                                    ██")
        W("  ██   VERDICT:  ✗ NOT READY FOR REAL MONEY            ██")
        W("  ██                                                    ██")
        
        # Identify the reason
        if total_trades < 30:
            W("  ██   PRIMARY ISSUE: Insufficient trades.             ██")
            W(f"  ██   {total_trades} trades in 6 years is not enough           ██")
            W("  ██   for statistical confidence. The system is       ██")
            W("  ██   too selective — signals are rare events.        ██")
        elif not criteria.get("win_rate_ok"):
            W("  ██   PRIMARY ISSUE: Win rate below threshold.        ██")
        elif not criteria.get("drawdown_ok"):
            W("  ██   PRIMARY ISSUE: Drawdown exceeds tolerance.      ██")
        elif not criteria.get("consistency_ok"):
            W("  ██   PRIMARY ISSUE: Results inconsistent by year.    ██")
        elif not criteria.get("expectancy_ok"):
            W("  ██   PRIMARY ISSUE: Negative expectancy.             ██")
        else:
            W("  ██   MULTIPLE ISSUES — see failure list above.       ██")
        
        W("  ██                                                    ██")
        W("  ████████████████████████████████████████████████████████")
    
    W()
    
    # Recommendations
    W("  RECOMMENDATIONS:")
    if total_trades < 30:
        W("  1. REDUCE SELECTIVITY: Lower BT_MIN_SMARTRANK from 60 to 40-50")
        W("  2. WIDEN ENTRY: Change BT_MIN_ACTION from PROBE to WAIT")
        W("  3. INCREASE CAPACITY: Raise PORTFOLIO_MAX_OPEN_TRADES from 2 to 3-4")
        W("  4. RELAX QUALITY GATE: Lower soft check threshold from 6/10 to 5/10")
        W("  5. SCAN MORE DAYS: Raise BT_DAILY_TOP_N from 1 to 2")
        W("  6. TEST IN BEAR/NEUTRAL: Allow entries outside BULL regime with tighter stops")
    else:
        if not criteria.get("win_rate_ok"):
            W("  1. Improve entry timing or signal quality")
            W("  2. Tighten quality gate checks")
        if not criteria.get("drawdown_ok"):
            W("  1. Reduce position sizing")
            W("  2. Tighten stops")
        if not criteria.get("consistency_ok"):
            W("  1. Add regime-adaptive parameters")
            W("  2. Consider market-neutral periods")
    W()
    
    # Summary stats JSON
    summary = {
        "total_trades": total_trades,
        "total_missed": total_missed,
        "win_rate": round(sum(1 for t in all_trades if t["pnl_pct"] > 0) / max(total_trades, 1) * 100, 1),
        "total_pnl": round(sum(t["pnl_pct"] for t in all_trades), 2),
        "max_drawdown": round(compute_drawdown(all_trades)[0], 2) if total_trades > 0 else 0,
        "expectancy": round(compute_expectancy(all_trades), 4),
        "criteria": {k: v for k, v in criteria.items()},
        "failures": len(failures),
        "warnings": len(warnings),
        "verdict": "READY" if (all_pass and critical_fails == 0) else "NOT READY",
    }
    
    HR()
    W(f"  Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    W(f"  هل النظام جاهز للسوق الحقيقي؟  {'نعم ✓' if summary['verdict'] == 'READY' else 'لا ✗ — مش جاهز'}")
    HR()
    
    return "\n".join(lines), summary, all_trades


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log()
    log("═" * 70)
    log("  EGX RADAR — FULL 6-YEAR VALIDATION")
    log("  2020-01-01 → 2026-03-01")
    log("  Running year-by-year to avoid memory issues...")
    log("═" * 70)
    log()
    
    # Current settings snapshot
    log("Current Settings:")
    log(f"  BT_MIN_SMARTRANK = {K.BT_MIN_SMARTRANK}")
    log(f"  BT_MIN_ACTION    = {K.BT_MIN_ACTION}")
    log(f"  RISK_PER_TRADE   = {K.RISK_PER_TRADE}")
    log(f"  MAX_STOP_LOSS    = {K.MAX_STOP_LOSS_PCT}")
    log(f"  MAX_OPEN_TRADES  = {K.PORTFOLIO_MAX_OPEN_TRADES}")
    log(f"  BT_DAILY_TOP_N   = {K.BT_DAILY_TOP_N}")
    log(f"  SLIPPAGE         = {K.BT_SLIPPAGE_PCT}")
    log(f"  FEES             = {K.BT_FEES_PCT}")
    log()
    
    # Run all periods
    all_trades, all_equity, all_missed, yearly_results, errors = run_all_periods_pro()
    
    log("\n\n")
    
    # Generate report
    report_text, summary, _ = generate_report(
        all_trades, all_equity, all_missed, yearly_results, errors
    )
    
    # Print report
    log(report_text)
    
    # Save report to file
    report_filename = f"VALIDATION_REPORT_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report_text)
    log(f"\n  Report saved to: {report_filename}")
    
    # Save trade log to JSON
    trades_filename = f"VALIDATION_TRADES_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"
    with open(trades_filename, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, default=str)
    log(f"  Trade log saved to: {trades_filename}")
    
    # Save summary
    summary_filename = f"VALIDATION_SUMMARY_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"
    with open(summary_filename, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    log(f"  Summary saved to: {summary_filename}")
