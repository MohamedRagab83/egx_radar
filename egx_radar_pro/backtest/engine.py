"""
backtest/engine.py — EGX Radar Pro
======================================
Walk-forward backtest simulation engine.

Design
------
  - Date-sequential simulation over all dates in market_data
  - For each date: close qualifying positions, then open new entries
  - Entries are filled at next-day open price (realistic simulation)
  - Equity curve tracks compounding portfolio returns
  - All execution decisions delegate to generate_trade_signal()
    which is SmartRank-only — AI and Alpha parameters are for
    display logging only

Trade lifecycle
---------------
  OPEN  → STOP    : Stop-loss hit (priority: gap-down open first)
  OPEN  → TARGET  : Profit target hit
  OPEN  → TIME    : Max holding period reached (time-stop)
  OPEN  → FINAL   : Force-closed at backtest end date

PnL calculation
---------------
  gross_pnl_pct  = (exit_price - entry_price) / entry_price × 100
  net_pnl_pct    = gross_pnl_pct − fee_pct × 100
  equity_update  = equity × (1 + alloc_pct × net_pnl_pct / 100)
  alloc_pct      = min(entry × size / account_size, max_sector_exposure)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd

from config.settings import RISK, Snapshot, Trade
from core.market_regime import detect_market_regime
from core.signal_engine import evaluate_snapshot, generate_trade_signal
from risk.position_sizing import compute_position_size
from risk.portfolio import sector_positions
from utils.logger import get_logger

log = get_logger(__name__)


def _close_trade(t: Trade, px: float, date: pd.Timestamp, reason: str) -> None:
    """
    Finalise a trade: record exit details and compute net PnL.

    Parameters
    ----------
    t      : Open Trade object (mutated in place)
    px     : Exit price (post-slippage)
    date   : Exit date
    reason : "STOP" | "TARGET" | "TIME" | "FINAL"
    """
    gross    = (px - t.entry) / max(t.entry, 1e-9) * 100.0
    net      = gross - (RISK.fee_pct * 100.0)
    t.exit_price = float(px)
    t.exit_date  = date
    t.status     = reason
    t.pnl_pct    = float(net)


def run_backtest(
    market_data:  Dict[str, pd.DataFrame],
    use_ai:       bool                   = True,
    use_alpha:    bool                   = True,
    learning=None,
    strategy: str = "legacy",
    strategy_params: Optional[Dict] = None,
) -> Tuple[List[Trade], List[Tuple[str, float]]]:
    """
    Full walk-forward backtest simulation.

    Parameters
    ----------
    market_data : {symbol: OHLCV DataFrame}
                  All DataFrames must share compatible date ranges.
    use_ai      : Passed through to generate_trade_signal() — no execution
                  effect (kept for API compatibility and logging).
    use_alpha   : Passed through to generate_trade_signal() — no execution
                  effect (kept for API compatibility and logging).
    learning    : Optional LearningModule.
                  If provided, records each closed trade and supplies an
                  adaptive bias to probability_engine() (display only).
    strategy    : "legacy" or "v2".
    strategy_params : Optional parameter overrides for strategy.

    Returns
    -------
    (closed_trades, equity_curve)
      closed_trades : list of all completed Trade objects
      equity_curve  : list of (date_str, cumulative_return_pct)
                      e.g. [("2023-01-03", 0.0), ("2023-01-04", 0.24), ...]
    """
    all_dates: List[pd.Timestamp] = sorted(
        {d for df in market_data.values() for d in df.index}
    )

    open_trades: List[Trade] = []
    closed:      List[Trade] = []
    equity       = 100.0
    curve:       List[Tuple[str, float]] = []

    for i, date in enumerate(all_dates):

        # ── Build snapshots for every symbol available on this date ────
        snaps: List[Snapshot] = []
        for sym, df in market_data.items():
            if date not in df.index:
                continue
            df_slice = df[df.index <= date].tail(260)
            bias = learning.bias if learning is not None else 0.0
            snap = evaluate_snapshot(df_slice, sym, learning_bias=bias)
            if snap is not None:
                snaps.append(snap)

        regime = detect_market_regime(snaps)

        # ── Manage existing positions ───────────────────────────────────
        for t in list(open_trades):
            sym_df = market_data.get(t.symbol)
            if sym_df is None or date not in sym_df.index:
                continue

            row     = sym_df.loc[date]
            t.bars_held += 1
            open_px = float(row["Open"])
            high    = float(row["High"])
            low     = float(row["Low"])
            close   = float(row["Close"])

            # Stop-loss checks (gap-open priority)
            if open_px <= t.stop:
                _close_trade(t, open_px * (1.0 - RISK.slippage_pct), date, "STOP")
            elif low <= t.stop:
                _close_trade(t, t.stop  * (1.0 - RISK.slippage_pct), date, "STOP")
            elif high >= t.target:
                _close_trade(t, t.target * (1.0 - RISK.slippage_pct), date, "TARGET")
            elif t.bars_held >= RISK.max_bars_hold:
                _close_trade(t, close   * (1.0 - RISK.slippage_pct), date, "TIME")
            else:
                continue   # position still open

            # Update equity for the closed trade
            alloc_pct = min(
                (t.entry * t.size) / max(RISK.account_size, 1e-9),
                RISK.max_sector_exposure_pct,
            )
            equity *= 1.0 + alloc_pct * (t.pnl_pct / 100.0)
            closed.append(t)

            if learning is not None:
                learning.record(t.pnl_pct)

            open_trades.remove(t)

            log.debug(
                "Closed %-6s @ %.3f  PnL=%+.2f%%  [%s]  bars=%d",
                t.symbol, t.exit_price, t.pnl_pct, t.status, t.bars_held,
            )

        # ── Generate new entries (filled at next open) ──────────────────
        if i + 1 < len(all_dates):
            next_date   = all_dates[i + 1]
            taken_today = {t.symbol for t in open_trades if t.status == "OPEN"}

            if strategy == "v2":
                ranked_snaps = sorted(snaps, key=lambda x: x.smart_rank_v2, reverse=True)
            else:
                ranked_snaps = sorted(snaps, key=lambda x: x.smart_rank, reverse=True)

            for s in ranked_snaps:
                if s.symbol in taken_today:
                    continue

                sig = generate_trade_signal(
                    s, regime, open_trades,
                    use_ai=use_ai, use_alpha=use_alpha,
                    strategy=strategy,
                    strategy_params=strategy_params,
                )
                if sig is None:
                    continue

                signal_type, plan = sig
                next_df = market_data.get(s.symbol)
                if next_df is None or next_date not in next_df.index:
                    continue

                next_open = float(next_df.loc[next_date]["Open"])
                entry     = float(plan["entry"])
                stop      = float(plan["stop"])
                target    = float(plan["target"])
                risk_used = float(plan["risk_used"])

                size = compute_position_size(entry, stop, risk_used, RISK.account_size)
                if size <= 0:
                    continue

                trade = Trade(
                    symbol          = s.symbol,
                    sector          = s.sector,
                    entry_date      = next_date,
                    entry           = next_open * (1.0 + RISK.slippage_pct),
                    stop            = stop,
                    target          = target,
                    size            = size,
                    risk_used       = risk_used,
                    signal_type     = signal_type,
                    smart_rank      = s.smart_rank_v2 if strategy == "v2" else s.smart_rank,
                    probability     = s.probability,      # display only
                    sentiment_score = s.sentiment_score,  # display only
                    alpha_score     = s.alpha_score,       # display only
                )
                open_trades.append(trade)
                taken_today.add(s.symbol)

                log.debug(
                    "Entry  %-6s @ %.3f  SR=%.1f  type=%s  P=%.3f  "
                    "Sent=%.3f  Alpha=%.1f",
                    s.symbol, next_open, s.smart_rank, signal_type,
                    s.probability, s.sentiment_score, s.alpha_score,
                )

                if len([t for t in open_trades if t.status == "OPEN"]) >= RISK.max_open_trades:
                    break

        curve.append((date.strftime("%Y-%m-%d"), round(equity - 100.0, 3)))

    # ── Force-close remaining positions at end of data ─────────────────
    if all_dates:
        last = all_dates[-1]
        for t in list(open_trades):
            sym_df = market_data.get(t.symbol)
            if sym_df is not None and last in sym_df.index:
                exit_px = float(sym_df.loc[last]["Close"]) * (1.0 - RISK.slippage_pct)
                _close_trade(t, exit_px, last, "FINAL")
                alloc_pct = min(
                    (t.entry * t.size) / max(RISK.account_size, 1e-9),
                    RISK.max_sector_exposure_pct,
                )
                equity *= 1.0 + alloc_pct * (t.pnl_pct / 100.0)
                closed.append(t)
                if learning is not None:
                    learning.record(t.pnl_pct)

        if curve:
            curve[-1] = (curve[-1][0], round(equity - 100.0, 3))

    log.info(
        "Backtest finished — %d trades closed  |  final equity: %+.2f%%",
        len(closed), equity - 100.0,
    )
    return closed, curve
