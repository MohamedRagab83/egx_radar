"""Deep diagnostic: why so few trades?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.config.settings import K, SYMBOLS
from egx_radar.backtest.data_loader import load_backtest_data
from egx_radar.core.signal_engine import evaluate_symbol_snapshot
from egx_radar.config.settings import get_sector
import pandas as pd

print(f"Total symbols: {len(SYMBOLS)}")

K.BT_MIN_SMARTRANK = 0.0
all_data = load_backtest_data('2024-01-01', '2025-12-31')
print(f"Symbols loaded: {len(all_data)}")

yahoo_to_sym = {v: k for k, v in SYMBOLS.items()}

# Check a sample date
sample_dates = pd.Timestamp('2024-06-15'), pd.Timestamp('2024-09-15'), pd.Timestamp('2025-01-15')

for sample_date in sample_dates:
    print(f"\n=== Date: {sample_date.date()} ===")
    results = []
    for yahoo, df in all_data.items():
        sym = yahoo_to_sym.get(yahoo)
        if not sym:
            continue
        if sample_date not in df.index:
            print(f"  {sym}: no data for this date")
            continue
        df_slice = df[df.index <= sample_date].tail(260).copy()
        if df_slice.empty:
            print(f"  {sym}: empty slice")
            continue
        
        close = df_slice["Close"].astype(float).dropna()
        vol = df_slice["Volume"].fillna(0).astype(float)
        avg_turnover = (close.tail(20) * vol.tail(20)).mean()
        bars = len(close)
        price = float(close.iloc[-1])
        
        # Try evaluating
        result = evaluate_symbol_snapshot(
            df_ta=df_slice, sym=sym, sector=get_sector(sym), regime="BULL"
        )
        if result is None:
            print(f"  {sym}: REJECTED (bars={bars}, price={price:.1f}, turnover={avg_turnover/1e6:.1f}M)")
        else:
            sr = result.get("smart_rank", 0)
            action = result.get("plan", {}).get("action", "?")
            phase = result.get("phase", "?")
            tag = result.get("tag", "?")
            accum = result.get("accumulation_detected", False)
            print(f"  {sym}: SR={sr:.1f} action={action} tag={tag} phase={phase} accum={accum}")
            results.append(result)
    
    print(f"  → {len(results)} symbols passed evaluate_symbol_snapshot")
