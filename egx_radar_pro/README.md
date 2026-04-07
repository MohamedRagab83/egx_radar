# EGX Radar Pro

A production-ready algorithmic trading system for the Egyptian Exchange (EGX), structured as a clean, multi-module Python project.

---

## Architecture

```
egx_radar_pro/
├── config/
│   └── settings.py          RiskConfig, EngineConfig, SYMBOLS, SECTORS, Snapshot, Trade
├── utils/
│   ├── helpers.py            clamp() and utility functions
│   └── logger.py             Centralised logging factory
├── core/
│   ├── indicators.py         RSI, ATR, EMA, Volume Ratio (stateless, vectorised)
│   ├── smart_rank.py         SmartRank composite scorer — the ONLY execution signal
│   ├── market_regime.py      Breadth-based regime detector (BULL / NEUTRAL / BEAR)
│   └── signal_engine.py      evaluate_snapshot(), generate_trade_signal(), format_signal_log()
├── ai/
│   ├── learning.py           Rolling win/loss tracker with JSON persistence
│   ├── probability_engine.py Logistic probability estimator (DISPLAY ONLY)
│   └── advisor.py            AI context formatter for console output
├── news/
│   ├── nlp_arabic.py         Arabic financial phrase sentiment lexicon
│   ├── news_fetcher.py       News retrieval layer (synthetic stub, swap for live feed)
│   ├── sentiment_engine.py   Multi-factor sentiment aggregator (DISPLAY ONLY)
│   └── news_intelligence.py  High-level news report builder
├── alpha/
│   ├── alpha_engine.py       News-driven alpha score (DISPLAY ONLY)
│   ├── alpha_filter.py       Alpha quality screener (DISPLAY ONLY)
│   └── alpha_execution.py    Alpha trade parameter calculator (DISPLAY ONLY)
├── risk/
│   ├── position_sizing.py    Fixed fractional position sizer
│   └── portfolio.py          Portfolio constraint enforcement
├── backtest/
│   ├── engine.py             Walk-forward backtest simulation
│   ├── metrics.py            Sharpe, drawdown, winrate, expectancy
│   └── validator.py          Three-mode parity validator
├── data/
│   └── loader.py             Synthetic OHLCV generator (swap for real feed)
├── main.py                   Entry point
└── requirements.txt
```

---

## Execution Philosophy

**SmartRank is the ONLY execution signal.**

The system contains three analytical layers (AI, News, Alpha) that are computed, logged, and displayed to the trader — but they have **zero influence** on which trades are entered or exited.

| Layer        | Computed | Logged | Affects Entry | Affects Exit |
|:-------------|:--------:|:------:|:-------------:|:------------:|
| SmartRank    | ✓        | ✓      | **YES**       | NO           |
| AI Probability | ✓      | ✓      | NO            | NO           |
| News Sentiment | ✓      | ✓      | NO            | NO           |
| Alpha Score  | ✓        | ✓      | NO            | NO           |

This design is enforced at a code level:
- `generate_trade_signal()` contains `_ = (use_ai, use_alpha)` to explicitly suppress the parameters.
- `validate_system()` runs three parallel backtests and raises `RuntimeError` if trade counts differ.

---

## SmartRank Formula

```
SmartRank = 30% Capital Flow   (volume_ratio normalised)
          + 25% Market Structure (EMA alignment score)
          + 20% Timing          (RSI position in [35, 75] range)
          + 10% Momentum        (price vs EMA50 normalised)
          + 10% Regime          (above/below EMA200: 1.0 or 0.4)
          +  5% Neural Offset   (stable 0.5 baseline)
```

Entry rules:
- SmartRank ≥ 70.0 → **MAIN** entry (full risk)
- SmartRank ≥ 55.0 → **PROBE** entry (0.65× risk)
- Regime == "BEAR"  → No entries regardless of SmartRank

---

## Installation

```bash
cd egx_radar_pro
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

---

## Running

```bash
cd egx_radar_pro
python main.py
```

Expected output:
1. Signal preview for the latest date (top 5 by SmartRank)
2. Three-mode validation results table
3. Execution parity confirmation

---

## Configuration

Edit `config/settings.py` to change trading parameters. The two key classes are:

```python
@dataclass(frozen=True)
class RiskConfig:
    account_size:           float = 100_000.0   # Base account size
    risk_per_trade:         float = 0.005        # 0.5% per trade
    max_open_trades:        int   = 6            # Global open position cap
    max_sector_positions:   int   = 2            # Per-sector concentration limit
    max_sector_exposure_pct:float = 0.30         # Max 30% capital per sector
    slippage_pct:           float = 0.003        # 0.3% round-trip slippage
    fee_pct:                float = 0.0015       # 0.15% commission
    max_bars_hold:          int   = 20           # Time-stop (trading days)

@dataclass(frozen=True)
class EngineConfig:
    warmup_bars:            int   = 80           # Min bars before signal generation
    smart_rank_accumulate:  float = 70.0         # MAIN entry threshold
    smart_rank_probe:       float = 55.0         # PROBE entry threshold
```

To change the universe of symbols, edit `SECTORS` and `SYMBOLS` in the same file.

---

## Adding Real Market Data

Replace `data/loader.py`'s `load_market_data()` function body. The returned format must be:

```python
{
    "COMI": pd.DataFrame(
        {"Open": [...], "High": [...], "Low": [...], "Close": [...], "Volume": [...]},
        index=pd.DatetimeIndex([...])  # business days, timezone-naive
    ),
    "TMGH": pd.DataFrame(...),
    ...
}
```

### Option A — yfinance (free, EGX tickers end in `.CA`)

```python
import yfinance as yf

def load_market_data(symbols, start="2020-01-01", end=None):
    data = {}
    for sym in symbols:
        df = yf.download(f"{sym}.CA", start=start, end=end, auto_adjust=True)
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        if not df.empty:
            data[sym] = df
    return data
```

### Option B — EGX CSV files

```python
import os, pandas as pd

def load_market_data(symbols, data_dir="./market_data"):
    data = {}
    for sym in symbols:
        path = os.path.join(data_dir, f"{sym}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            data[sym] = df
    return data
```

---

## Module Reference

### core/smart_rank.py
`smart_rank(snapshot: Snapshot) -> float`
The central scoring function. Returns [0, 100]. Modify only with backtest validation.

### core/signal_engine.py
`generate_trade_signal(snapshot, regime, open_trades, use_ai, use_alpha) -> Optional[Tuple[str, dict]]`
Returns `("MAIN", plan)`, `("PROBE", plan)`, or `None`.
`use_ai` and `use_alpha` are accepted but suppressed — SmartRank is the only gate.

### backtest/engine.py
`run_backtest(market_data, use_ai, use_alpha, learning) -> (trades, curve)`
Walk-forward simulation. Entries filled at next-day open. Slippage and fees applied.

### backtest/validator.py
`validate_system(market_data) -> {mode: metrics}`
Runs all three modes and raises `RuntimeError` on parity failure.

### ai/learning.py
`LearningModule` records trade outcomes and provides `bias` property in [-0.1, +0.1].
The bias enriches AI probability display after 10 or more closed trades.

### news/news_fetcher.py
`fetch_news(symbol, date) -> List[dict]`
Stub implementation. Replace with a real feed in production.

---

## License

MIT License — use freely at your own risk. This software does not constitute financial advice.
