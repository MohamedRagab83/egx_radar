"""Final comprehensive comparison: SR>=0 baseline vs optimized.
This compares the FULL universe of signals (SR>=0) before vs after optimization.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
import egx_radar.backtest.engine as eng

# Save the real quality gate
_real_gate = eng._is_high_probability_trade

BEFORE_SETTINGS = {
    'BT_MIN_SMARTRANK': 0.0,  # No SR filter to see all signals
    'BT_MIN_ACTION': "PROBE",
    'BT_DAILY_TOP_N': 2,
    'MAX_STOP_LOSS_PCT': 0.05,
    'PARTIAL_TP_PCT': 0.05,
    'TRAILING_TRIGGER_PCT': 0.06,
    'TRAILING_STOP_PCT': 0.03,
    'RISK_PER_TRADE': 0.01,
    'PORTFOLIO_MAX_OPEN_TRADES': 3,
    'MIN_TURNOVER_EGP': 5000000.0,
    'MAX_3DAY_GAIN_PCT': 10.0,
    'MAX_GAP_UP_PCT': 3.0,
}

AFTER_SETTINGS = {
    'BT_MIN_SMARTRANK': 65.0,
    'BT_MIN_ACTION': "ACCUMULATE",
    'BT_DAILY_TOP_N': 1,
    'MAX_STOP_LOSS_PCT': 0.03,
    'PARTIAL_TP_PCT': 0.04,
    'TRAILING_TRIGGER_PCT': 0.03,
    'TRAILING_STOP_PCT': 0.02,
    'RISK_PER_TRADE': 0.005,
    'PORTFOLIO_MAX_OPEN_TRADES': 2,
    'MIN_TURNOVER_EGP': 7000000.0,
    'MAX_3DAY_GAIN_PCT': 5.0,
    'MAX_GAP_UP_PCT': 2.0,
}

def apply(cfg):
    for k, v in cfg.items():
        setattr(K, k, v)

def run_bt():
    from egx_radar.backtest.engine import run_backtest
    all_t = []
    for y in [2023, 2024, 2025]:
        t, _, _, _ = run_backtest(f'{y}-01-01', f'{y}-12-31')
        all_t.extend(t)
    return all_t

def stats(trades, label):
    tot = len(trades)
    if not tot:
        print(f"\n{label}: 0 trades")
        return {"trades": 0}
    
    wins = sum(1 for t in trades if t['outcome'] == 'WIN')
    losses = sum(1 for t in trades if t['outcome'] == 'LOSS')
    exits = sum(1 for t in trades if t['outcome'] == 'EXIT')
    pnl_pos = sum(1 for t in trades if t['pnl_pct'] > 0)
    pnls = [t['pnl_pct'] for t in trades]
    
    pos_sum = sum(p for p in pnls if p > 0)
    neg_sum = sum(p for p in pnls if p < 0)
    pf = abs(pos_sum / neg_sum) if neg_sum < 0 else float('inf')
    
    peak = 100.0; eq = 100.0; max_dd = 0
    for t in trades:
        a = t.get('alloc_pct', 0.1)
        eq *= 1 + a * t['pnl_pct'] / 100
        peak = max(peak, eq)
        dd = (peak - eq) / peak * 100
        max_dd = max(max_dd, dd)
    
    avg_w = sum(t['pnl_pct'] for t in trades if t['outcome']=='WIN') / max(wins, 1)
    avg_l = sum(t['pnl_pct'] for t in trades if t['outcome']=='LOSS') / max(losses, 1)
    
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Trades:          {tot} (W:{wins} L:{losses} E:{exits})")
    print(f"  Label WR:        {wins/tot*100:.1f}%")
    print(f"  PnL WR:          {pnl_pos/tot*100:.1f}%")
    print(f"  Avg Win:         +{avg_w:.2f}%")
    print(f"  Avg Loss:        {avg_l:.2f}%")
    print(f"  Total Return:    {sum(pnls):+.2f}%")
    print(f"  Profit Factor:   {pf:.2f}")
    print(f"  Max Drawdown:    {max_dd:.2f}%")
    
    for i, t in enumerate(trades, 1):
        sym = t.get('sym', '?')
        sd = t.get('signal_date', '?')
        sr = t.get('smart_rank', 0)
        pnl = t.get('pnl_pct', 0)
        out = t.get('outcome', '?')
        bars = t.get('bars_held', 0)
        partial = t.get('partial_taken', False)
        print(f"    {i:2}. {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out:4s} bars={bars} partial={partial}")
    
    return {
        "trades": tot, "wr_label": round(wins/tot*100,1), "wr_pnl": round(pnl_pos/tot*100,1),
        "max_dd": round(max_dd, 2), "total_ret": round(sum(pnls), 2), "pf": round(pf, 2),
        "avg_win": round(avg_w, 2), "avg_loss": round(avg_l, 2),
    }

# ── BEFORE: no gate, no SR filter, old stop/trailing settings ──
print("Running BEFORE baseline (SR>=0, no gate, old settings)...")
apply(BEFORE_SETTINGS)
eng._is_high_probability_trade = lambda r: True
before_trades = run_bt()
r_before = stats(before_trades, "BEFORE (Original System)")

# ── AFTER: with gate, with SR filter, new settings ──
print("\nRunning AFTER (optimized settings + quality gate)...")
apply(AFTER_SETTINGS)
eng._is_high_probability_trade = _real_gate
after_trades = run_bt()
r_after = stats(after_trades, "AFTER (Optimized System)")

# ── COMPARISON ──
print(f"\n{'='*60}")
print(f"  BEFORE vs AFTER COMPARISON")
print(f"{'='*60}")
print(f"  {'Metric':25s} {'BEFORE':>10s} {'AFTER':>10s} {'Change':>12s}")
print(f"  {'-'*57}")

def delta(b, a, fmt=".1f", suffix="%"):
    d = a - b
    return f"{d:+{fmt}}{suffix}"

if r_before['trades'] and r_after['trades']:
    for metric, key, fmt, suf in [
        ("Trades", "trades", "d", ""),
        ("Label Win Rate", "wr_label", ".1f", "%"),
        ("PnL Win Rate", "wr_pnl", ".1f", "%"),
        ("Max Drawdown", "max_dd", ".2f", "%"),
        ("Total Return", "total_ret", ".2f", "%"),
        ("Profit Factor", "pf", ".2f", ""),
        ("Avg Win", "avg_win", ".2f", "%"),
        ("Avg Loss", "avg_loss", ".2f", "%"),
    ]:
        bv = r_before[key]
        av = r_after[key]
        print(f"  {metric:25s} {bv:>10{fmt}} {av:>10{fmt}} {delta(bv, av, fmt, suf):>12s}")
elif r_after['trades'] == 0:
    print("  AFTER has 0 trades — quality gate too strict")
