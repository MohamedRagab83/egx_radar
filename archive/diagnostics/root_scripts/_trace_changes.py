"""Trace the impact of each change on trade count and WR."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K
import egx_radar.backtest.engine as eng

# Save current (optimized) settings
ORIG = {
    'BT_MIN_SMARTRANK': K.BT_MIN_SMARTRANK,
    'BT_MIN_ACTION': K.BT_MIN_ACTION,
    'BT_DAILY_TOP_N': K.BT_DAILY_TOP_N,
    'MAX_STOP_LOSS_PCT': K.MAX_STOP_LOSS_PCT,
    'PARTIAL_TP_PCT': K.PARTIAL_TP_PCT,
    'TRAILING_TRIGGER_PCT': K.TRAILING_TRIGGER_PCT,
    'TRAILING_STOP_PCT': K.TRAILING_STOP_PCT,
    'RISK_PER_TRADE': K.RISK_PER_TRADE,
    'PORTFOLIO_MAX_OPEN_TRADES': K.PORTFOLIO_MAX_OPEN_TRADES,
    'MIN_TURNOVER_EGP': K.MIN_TURNOVER_EGP,
    'MAX_3DAY_GAIN_PCT': K.MAX_3DAY_GAIN_PCT,
    'MAX_GAP_UP_PCT': K.MAX_GAP_UP_PCT,
}

# BEFORE settings (from .bak analysis)
BEFORE = {
    'BT_MIN_SMARTRANK': 70.0,
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

def apply_settings(cfg):
    for k, v in cfg.items():
        setattr(K, k, v)

def run_test(label, use_gate=True):
    """Run 3-year backtest and return summary."""
    if not use_gate:
        eng._is_high_probability_trade = lambda r: True
    else:
        eng._is_high_probability_trade = _real_gate
    
    from egx_radar.backtest.engine import run_backtest
    all_trades = []
    for year in [2023, 2024, 2025]:
        t, _, _, _ = run_backtest(f'{year}-01-01', f'{year}-12-31')
        all_trades.extend(t)
    
    tot = len(all_trades)
    if tot == 0:
        return {"label": label, "trades": 0, "wr_label": 0, "wr_pnl": 0, "max_dd": 0, "total_ret": 0}
    
    wins = sum(1 for t in all_trades if t['outcome'] == 'WIN')
    pnl_pos = sum(1 for t in all_trades if t['pnl_pct'] > 0)
    pnls = [t['pnl_pct'] for t in all_trades]
    
    peak = 100.0; equity = 100.0; max_dd = 0
    for t in all_trades:
        a = t.get('alloc_pct', 0.1)
        equity *= 1 + a * t['pnl_pct'] / 100
        peak = max(peak, equity); dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
    
    return {
        "label": label, "trades": tot,
        "wr_label": round(wins/tot*100, 1),
        "wr_pnl": round(pnl_pos/tot*100, 1),
        "max_dd": round(max_dd, 2),
        "total_ret": round(sum(pnls), 2),
        "trades_detail": [(t['sym'], t['signal_date'], t.get('smart_rank',0), t['pnl_pct'], t['outcome']) for t in all_trades],
    }

# Save the real gate
_real_gate = eng._is_high_probability_trade

# Test 1: BEFORE settings + NO gate (baseline)
print("Test 1: BEFORE settings, NO quality gate...")
apply_settings(BEFORE)
r1 = run_test("BEFORE (no gate)", use_gate=False)
print(f"  -> {r1['trades']} trades, WR_label={r1['wr_label']}%, WR_pnl={r1['wr_pnl']}%, DD={r1['max_dd']}%")
if r1.get('trades_detail'):
    for sym, sd, sr, pnl, out in r1['trades_detail']:
        print(f"     {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out}")

# Test 2: BEFORE settings + outcome fix only (what outcome fix alone does)
print("\nTest 2: BEFORE settings + outcome fix (no gate, just reclassification)...")
# outcome fix is already in engine.py, so same as test 1 but with labels updated
# Actually test 1 already has the outcome fix. So this IS test 1.

# Test 3: AFTER settings + NO gate
print("\nTest 3: AFTER settings, NO quality gate...")
apply_settings(ORIG)
r3 = run_test("AFTER settings (no gate)", use_gate=False)
print(f"  -> {r3['trades']} trades, WR_label={r3['wr_label']}%, WR_pnl={r3['wr_pnl']}%, DD={r3['max_dd']}%")
if r3.get('trades_detail'):
    for sym, sd, sr, pnl, out in r3['trades_detail']:
        print(f"     {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out}")

# Test 4: AFTER settings + quality gate
print("\nTest 4: AFTER settings + quality gate...")
apply_settings(ORIG)
r4 = run_test("AFTER (full optimization)", use_gate=True)
print(f"  -> {r4['trades']} trades, WR_label={r4['wr_label']}%, WR_pnl={r4['wr_pnl']}%, DD={r4['max_dd']}%")
if r4.get('trades_detail'):
    for sym, sd, sr, pnl, out in r4['trades_detail']:
        print(f"     {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out}")

# Test 5: BEFORE settings + quality gate (just gate, no settings changes)
print("\nTest 5: BEFORE settings + quality gate only...")
apply_settings(BEFORE)
r5 = run_test("BEFORE + gate only", use_gate=True)
print(f"  -> {r5['trades']} trades, WR_label={r5['wr_label']}%, WR_pnl={r5['wr_pnl']}%, DD={r5['max_dd']}%")
if r5.get('trades_detail'):
    for sym, sd, sr, pnl, out in r5['trades_detail']:
        print(f"     {sym:6s} {sd} SR={sr:5.1f} pnl={pnl:+6.2f}% {out}")

print(f"\n{'='*70}")
print(f"SUMMARY")
print(f"{'='*70}")
print(f"{'Config':35s} {'Trades':>7s} {'WR(label)':>10s} {'WR(PnL)':>8s} {'MaxDD':>7s} {'TotRet':>8s}")
for r in [r1, r3, r5, r4]:
    print(f"{r['label']:35s} {r['trades']:7d} {r['wr_label']:9.1f}% {r['wr_pnl']:7.1f}% {r['max_dd']:6.2f}% {r['total_ret']:+7.2f}%")
