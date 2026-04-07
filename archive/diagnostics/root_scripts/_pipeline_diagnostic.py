"""Pipeline diagnostic — trace where signals die at each stage."""
import sys, os, warnings
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

import pandas as pd
from egx_radar.config.settings import K, get_sector
from egx_radar.backtest.data_loader import load_backtest_data, SYMBOLS
from egx_radar.core.signal_engine import evaluate_symbol_snapshot, detect_conservative_market_regime

period_start, period_end = '2020-01-01', '2026-03-01'

print('Downloading data...')
data = load_backtest_data(period_start, period_end)
print(f'Downloaded {len(data)} symbols')

yahoo_to_sym = {v: k for k, v in SYMBOLS.items()}

dates = pd.bdate_range(period_start, period_end, freq='B')
sample_dates = dates[::20]  # every ~month (more granular for better stats)

stats = dict(
    total_symbol_days=0,
    has_result=0,
    accum_detected=0,
    entry_ready=0,
    action_accum_probe=0,
    regime_bull=0,
    regime_neutral=0,
    regime_bear=0,
)

# Also track per-condition failures
condition_fails = dict(
    accum_quality=0, structure_strength=0, volume_quality=0,
    trend_alignment=0, higher_lows=0, price_above_ema50=0,
    ema20_slope=0, rsi_range=0, fake_move=0,
)

print(f'Checking {len(sample_dates)} sample dates...')
for di, date in enumerate(sample_dates):
    results = []
    for yahoo, df in data.items():
        sym = yahoo_to_sym.get(yahoo, yahoo)
        if date not in df.index:
            continue
        df_slice = df[df.index <= date].tail(260).copy()
        if df_slice.empty or len(df_slice) < 210:
            continue
        stats['total_symbol_days'] += 1

        result = evaluate_symbol_snapshot(
            df_ta=df_slice, sym=sym, sector=get_sector(sym), regime='BULL',
        )
        if result is None:
            continue
        stats['has_result'] += 1

        # Check individual accumulation conditions
        aq = result.get('accumulation_quality_score', 0)
        ss = result.get('structure_strength_score', 0)
        vq = result.get('volume_quality_score', 0)
        ta = result.get('trend_alignment_score', 0)
        hl = result.get('higher_lows', False)
        rsi = result.get('rsi', 50)
        fm = result.get('fake_move', False)
        price = result.get('price', 0)
        ema50 = result.get('ema50', 0)
        ema20_slope = result.get('ema20_slope_pct', 0)

        if aq < 65: condition_fails['accum_quality'] += 1
        if ss < 62: condition_fails['structure_strength'] += 1
        if vq < 58: condition_fails['volume_quality'] += 1
        if ta < 58: condition_fails['trend_alignment'] += 1
        if not hl: condition_fails['higher_lows'] += 1
        if price < ema50 * 0.995: condition_fails['price_above_ema50'] += 1
        if ema20_slope < -0.10: condition_fails['ema20_slope'] += 1
        if not (45.0 <= rsi <= 60.0): condition_fails['rsi_range'] += 1
        if fm: condition_fails['fake_move'] += 1

        if result.get('accumulation_detected'):
            stats['accum_detected'] += 1
        if result.get('entry_ready'):
            stats['entry_ready'] += 1
        action = (result.get('plan') or {}).get('action', 'WAIT')
        if action in ('ACCUMULATE', 'PROBE'):
            stats['action_accum_probe'] += 1
        results.append(result)

    if results:
        regime = detect_conservative_market_regime(results)
        stats[f'regime_{regime.lower()}'] += 1

    if (di + 1) % 5 == 0:
        print(f'  ... {di+1}/{len(sample_dates)} dates done')

total_days = stats['regime_bull'] + stats['regime_neutral'] + stats['regime_bear']
hr = stats['has_result']

print()
print('=' * 60)
print('  SIGNAL PIPELINE DIAGNOSTIC')
print('=' * 60)
print(f'  Sample dates checked:    {len(sample_dates)}')
print(f'  Total symbol-days:       {stats["total_symbol_days"]}')
print(f'  Pass data+turnover:      {hr} ({100*hr/max(stats["total_symbol_days"],1):.1f}%)')
print(f'  Accum. detected:         {stats["accum_detected"]} ({100*stats["accum_detected"]/max(hr,1):.1f}% of passed)')
print(f'  Entry ready:             {stats["entry_ready"]} ({100*stats["entry_ready"]/max(hr,1):.1f}% of passed)')
print(f'  Action ACCUM/PROBE:      {stats["action_accum_probe"]} ({100*stats["action_accum_probe"]/max(hr,1):.1f}% of passed)')
print()
print(f'  Regime distribution ({total_days} sample days):')
print(f'    BULL:    {stats["regime_bull"]} ({100*stats["regime_bull"]/max(total_days,1):.1f}%)')
print(f'    NEUTRAL: {stats["regime_neutral"]} ({100*stats["regime_neutral"]/max(total_days,1):.1f}%)')
print(f'    BEAR:    {stats["regime_bear"]} ({100*stats["regime_bear"]/max(total_days,1):.1f}%)')
print()
print('  Accumulation condition failure rates (of symbols that pass data filters):')
for cond, count in sorted(condition_fails.items(), key=lambda x: -x[1]):
    pct = 100 * count / max(hr, 1)
    bar = '#' * int(pct / 2)
    print(f'    {cond:25s}: {count:5d} ({pct:5.1f}%) {bar}')
