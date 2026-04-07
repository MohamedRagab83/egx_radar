from __future__ import annotations

"""Conservative EGX backtest engine with live/backtest signal parity."""

import logging
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from egx_radar.data.data_engine import get_data_engine
from egx_radar.config.settings import (
    K,
    DECISION_PRIORITY,
    SYMBOLS,
    get_account_size,
    get_risk_per_trade,
    get_sector,
)
from egx_radar.core.portfolio import compute_portfolio_guard
from egx_radar.core.signal_engine import (
    apply_regime_gate,
    candle_hits_trigger,
    detect_conservative_market_regime,
    evaluate_symbol_snapshot,
    is_high_probability_trade,
    trigger_fill_tolerance,
)

log = logging.getLogger(__name__)

REGIME_MAP = {"BULL": "BULL", "BEAR": "BEAR", "NEUTRAL": "NEUTRAL"}
MEDIUM_MAX_STOP_LOSS_PCT = 0.028  # tighter stop cap for MEDIUM-class trades


def detect_market_regime(index_df: pd.DataFrame) -> str:
    """Classify the broad market as STRONG or WEAK using the proxy index series."""
    if index_df is None or len(index_df) < 210:
        return "WEAK"
    required_cols = {"High", "Low", "Close"}
    if not required_cols.issubset(index_df.columns):
        return "WEAK"

    close = index_df["Close"].astype(float)
    high = index_df["High"].astype(float)
    low = index_df["Low"].astype(float)
    price = float(close.iloc[-1]) if not close.empty else 0.0
    if price <= 0.0:
        return "WEAK"

    ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])
    price_near_ema50 = abs(price - ema50) / max(ema50, 1e-9) <= K.MARKET_REGIME_EMA_NEAR_PCT

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    atr_last = float(atr.iloc[-1]) if not atr.dropna().empty else 0.0
    atr_pct = atr_last / max(price, 1e-9)

    plus_di = 100.0 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr.replace(0.0, pd.NA)
    minus_di = 100.0 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr.replace(0.0, pd.NA)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, pd.NA)
    adx = float(dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().fillna(0.0).iloc[-1])

    returns = close.pct_change().dropna().tail(K.MARKET_REGIME_VOL_LOOKBACK)
    recent_std = float(returns.std()) if not returns.empty else 0.0

    lookback = min(K.MARKET_REGIME_HIGHER_HIGHS_LOOKBACK, len(high))
    recent_window = min(K.MARKET_REGIME_RECENT_WINDOW, lookback)
    recent_highs = high.tail(recent_window)
    prior_highs = high.tail(lookback).head(max(lookback - recent_window, 1))
    recent_lows = low.tail(recent_window)
    prior_lows = low.tail(lookback).head(max(lookback - recent_window, 1))
    higher_highs = bool(not recent_highs.empty and not prior_highs.empty and recent_highs.max() > prior_highs.max())
    higher_lows = bool(not recent_lows.empty and not prior_lows.empty and recent_lows.min() > prior_lows.min())

    strong_trend = (
        price > ema50 > ema200
        and adx > K.MARKET_REGIME_STRONG_ADX
        and higher_highs
        and higher_lows
        and atr_pct <= K.MARKET_REGIME_ATR_PCT_MAX_STRONG
        and recent_std <= K.MARKET_REGIME_STD_MAX_STRONG
    )
    if strong_trend:
        return "STRONG"

    weak_trend = (
        price_near_ema50
        or adx < K.MARKET_REGIME_WEAK_ADX
        or price <= ema50
        or ema50 <= ema200
        or not higher_highs
        or recent_std > K.MARKET_REGIME_STD_MAX_STRONG
    )
    return "WEAK" if weak_trend else "STRONG"


def _yahoo_to_sym() -> Dict[str, str]:
    return {v: k for k, v in SYMBOLS.items()}


def _build_results_for_day(
    all_data: Dict[str, pd.DataFrame],
    date: pd.Timestamp,
    yahoo_to_sym: Dict[str, str],
) -> Tuple[List[dict], Dict[str, float], str, str]:
    results: List[dict] = []
    sector_strength: Dict[str, List[float]] = {}
    market_regime = "WEAK"  # conservative default for downstream rank/volume filters
    pre_regime    = "BULL"  # signal evaluation default when proxy data is unavailable

    proxy_df = all_data.get(K.EGX30_SYMBOL)
    if proxy_df is not None and date in proxy_df.index:
        proxy_slice = proxy_df[proxy_df.index <= date].tail(260).copy()
        market_regime = detect_market_regime(proxy_slice)
        # STRONG → BULL (all tiers enter); WEAK → NEUTRAL (only STRONG tier enters)
        pre_regime = "BULL" if market_regime == "STRONG" else "NEUTRAL"

    for yahoo, df in all_data.items():
        sym = yahoo_to_sym.get(yahoo)
        if not sym or date not in df.index:
            continue
        df_slice = df[df.index <= date].tail(260).copy()
        if df_slice.empty:
            continue
        result = evaluate_symbol_snapshot(
            df_ta=df_slice,
            sym=sym,
            sector=get_sector(sym),
            regime=pre_regime,
        )
        if result is None:
            continue
        results.append(result)
        sector_strength.setdefault(result["sector"], []).append(result["quantum"])

    if not results:
        return [], {}, "NEUTRAL", market_regime

    regime = detect_conservative_market_regime(results)
    if regime != "BULL":
        results = [apply_regime_gate(r, regime) for r in results]

    sector_strength_avg = {
        sec: (sum(vals) / len(vals) if vals else 0.0)
        for sec, vals in sector_strength.items()
    }
    return results, sector_strength_avg, regime, market_regime


def _find_next_bar_date(df: pd.DataFrame, current_date: pd.Timestamp) -> Optional[pd.Timestamp]:
    future_dates = df.index[df.index > current_date]
    return future_dates[0] if len(future_dates) else None


def _trade_notional(entry: float, size: int, account_size: float) -> float:
    return min((entry * size) / max(account_size, 1e-9), K.PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT)


def _is_strong_rejection_candle(row: pd.Series) -> bool:
    open_px = float(row["Open"])
    high_px = float(row["High"])
    low_px = float(row["Low"])
    close_px = float(row["Close"])
    candle_range = max(high_px - low_px, 1e-9)
    body_fraction = abs(close_px - open_px) / candle_range
    close_position = (close_px - low_px) / candle_range
    return close_px < open_px and body_fraction >= 0.75 and close_position <= 0.10


def _build_open_trade(
    pending: dict,
    entry_base: float,
    account_size: float,
    entry_date: pd.Timestamp,
    fill_mode: str,
) -> dict:
    if not math.isfinite(account_size) or account_size <= 0:
        account_size = float(get_account_size())
    entry = float(entry_base) * (1.0 + K.BT_SLIPPAGE_PCT / 2.0)
    if not math.isfinite(entry) or entry <= 0:
        entry = 1.0
    entry = round(entry, 3)
    trade_type = str(pending.get("trade_type", "")).upper()
    stop_cap = MEDIUM_MAX_STOP_LOSS_PCT if trade_type == "MEDIUM" else K.MAX_STOP_LOSS_PCT
    risk_pct = float(pending.get("risk_pct", 0.02) or 0.02)
    if not math.isfinite(risk_pct) or risk_pct <= 0:
        risk_pct = 0.02
    risk_pct = min(risk_pct, float(stop_cap))
    target_pct = float(pending.get("target_pct", 0.08) or 0.08)
    if not math.isfinite(target_pct):
        target_pct = 0.08

    stop = round(entry * (1.0 - risk_pct), 3)
    target = round(entry * (1.0 + target_pct), 3)
    partial_target = round(entry * (1.0 + K.PARTIAL_TP_PCT), 3)
    trailing_trigger = round(entry * (1.0 + K.TRAILING_TRIGGER_PCT), 3)

    risk_fraction = float(pending.get("risk_used") or get_risk_per_trade())
    if not math.isfinite(risk_fraction) or risk_fraction <= 0:
        risk_fraction = float(get_risk_per_trade())
    risk_amount = account_size * risk_fraction
    if not math.isfinite(risk_amount) or risk_amount <= 0:
        risk_amount = 0.0
    risk_per_share = max(entry - stop, entry * 0.005)
    if not math.isfinite(risk_per_share) or risk_per_share <= 0:
        risk_per_share = max(abs(entry) * 0.005, 1e-6)
    size = max(1, int(risk_amount / max(risk_per_share, 1e-9))) if risk_amount > 0 else 0
    max_notional_shares = max(
        1,
        int((account_size * K.PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT) / max(entry, 1e-9)),
    )
    if size > 0:
        size = min(size, max_notional_shares)

    return {
        "sym": pending["sym"],
        "sector": pending["sector"],
        "signal_type": pending["signal_type"],
        "regime": pending["regime"],
        "signal_date": pending["signal_date"],
        "entry_date": entry_date.strftime("%Y-%m-%d"),
        "entry": entry,
        "initial_stop": stop,
        "stop": stop,
        "target": target,
        "partial_target": partial_target,
        "trailing_trigger": trailing_trigger,
        "trailing_stop_pct": float(K.TRAILING_STOP_PCT),
        "bars_held": 0,
        "status": "OPEN",
        "smart_rank": pending["smart_rank"],
        "multi_factor_rank": float(pending.get("multi_factor_rank", 0.0)),
        "final_rank": float(pending.get("final_rank", 0.0)),
        "score": pending.get("score", pending["smart_rank"]),
        "trade_type": pending.get("trade_type", "UNCLASSIFIED"),
        "risk_used": round(risk_fraction, 4),
        "anticipation": pending["anticipation"],
        "atr": pending["atr"],
        "size": size,
        "partial_taken": False,
        "partial_exit_price": None,
        "remaining_fraction": 1.0,
        "trailing_active": False,
        "trailing_anchor": entry,
        "trigger_price": float(pending.get("trigger_price") or entry_base),
        "fill_mode": fill_mode,
    }


def _process_trade_bar(trade: dict, row: pd.Series, max_bars: int) -> Tuple[dict, Optional[float], Optional[str]]:
    open_px = float(row["Open"])
    high = float(row["High"])
    low = float(row["Low"])
    close = float(row["Close"])
    trade["bars_held"] += 1

    exit_price = None
    outcome = None

    # Gap-Down Circuit Breaker: EGX has ±10% daily price limits.
    # A gap-down beyond BT_GAP_DOWN_MAX_PCT signals a data error or corporate
    # action (capital reduction, reverse split) — cap the open price so the
    # backtest does not absorb an unrealistic single-day collapse.
    gap_down_limit = trade["entry"] * (1.0 - K.BT_GAP_DOWN_MAX_PCT)
    if open_px < gap_down_limit:
        open_px = gap_down_limit

    if open_px <= trade["stop"]:
        exit_price = round(open_px * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
        # FIX: classify by actual PnL, not just stop-hit event
        outcome = "STOP_HIT"  # resolved to WIN/LOSS in _close_trade by PnL
    elif low <= trade["stop"]:
        exit_price = round(trade["stop"] * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
        outcome = "STOP_HIT"  # resolved to WIN/LOSS in _close_trade by PnL
    else:
        if (not trade["partial_taken"]) and high >= trade["partial_target"]:
            trade["partial_taken"] = True
            trade["remaining_fraction"] = 1.0 - float(K.PARTIAL_EXIT_FRACTION)
            trade["partial_exit_price"] = round(
                trade["partial_target"] * (1.0 - K.BT_SLIPPAGE_PCT / 2.0),
                3,
            )
            trade["stop"] = max(trade["stop"], trade["entry"])

        if high >= trade["trailing_trigger"]:
            trade["trailing_active"] = True
            trade["trailing_anchor"] = max(trade.get("trailing_anchor", trade["entry"]), high)

        if trade.get("trailing_active"):
            trailing_stop = trade["trailing_anchor"] * (1.0 - trade["trailing_stop_pct"])
            trade["stop"] = max(trade["stop"], trailing_stop)

        if high >= trade["target"]:
            exit_price = round(trade["target"] * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "WIN"
        elif trade["bars_held"] >= max_bars:
            exit_price = round(close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "EXIT"

    return trade, exit_price, outcome


def _simulate_trade_path(
    trade: dict,
    df: pd.DataFrame,
    start_date: pd.Timestamp,
    account_size: float,
    max_bars: int,
) -> Optional[dict]:
    if df is None or df.empty:
        return None
    future = df[df.index >= start_date]
    if future.empty:
        return None

    sim_trade = dict(trade)
    for sim_date, row in future.iterrows():
        sim_trade, exit_price, outcome = _process_trade_bar(sim_trade, row, max_bars)
        if outcome is None:
            continue
        return _close_trade(sim_trade, sim_date, exit_price, outcome, account_size)

    last_date = future.index[-1]
    last_close = float(future.iloc[-1]["Close"])
    exit_price = round(last_close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
    return _close_trade(sim_trade, last_date, exit_price, "EXIT", account_size)


def _activate_pending_trades(
    date: pd.Timestamp,
    pending_entries: List[dict],
    open_trades: List[dict],
    all_data: Dict[str, pd.DataFrame],
    account_size: float,
    missed_entries: List[dict],
    entry_mode: str,
    max_bars: int,
) -> List[dict]:
    remaining_pending: List[dict] = []
    for pending in pending_entries:
        if pending["activation_date"] != date:
            remaining_pending.append(pending)
            continue

        yahoo = SYMBOLS.get(pending["sym"])
        if not yahoo or yahoo not in all_data or date not in all_data[yahoo].index:
            continue

        row = all_data[yahoo].loc[date]
        open_px = float(row["Open"])
        high_px = float(row["High"])
        if open_px <= 0:
            continue
        trigger_price = float(pending.get("trigger_price") or 0.0)
        trigger_tolerance = trigger_fill_tolerance(trigger_price)

        if entry_mode == "open_only":
            filled = trigger_price <= 0 or open_px + trigger_tolerance >= trigger_price
            entry_base = open_px
            fill_mode = "next_open"
            miss_reason = "open_below_trigger"
        else:
            filled = candle_hits_trigger(high_px, trigger_price)
            entry_base = trigger_price if trigger_price > 0 else open_px
            fill_mode = "next_candle_touch"
            miss_reason = "trigger_not_touched"

        if not filled:
            missed_trade = {
                "sym": pending["sym"],
                "sector": pending["sector"],
                "signal_date": pending["signal_date"],
                "activation_date": date.strftime("%Y-%m-%d"),
                "trigger_price": round(trigger_price, 3),
                "next_open": round(open_px, 3),
                "next_high": round(high_px, 3),
                "trade_type": pending.get("trade_type", "UNCLASSIFIED"),
                "score": round(float(pending.get("score", pending.get("smart_rank", 0.0))), 2),
                "risk_used": round(float(pending.get("risk_used") or 0.0), 4),
                "reason": miss_reason,
            }
            forced_trade = _build_open_trade(
                pending,
                entry_base=open_px,
                account_size=account_size,
                entry_date=date,
                fill_mode="forced_open_approx",
            )
            approx = _simulate_trade_path(
                forced_trade,
                all_data[yahoo],
                date,
                account_size,
                max_bars,
            )
            if approx is not None:
                missed_trade["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                missed_trade["approx_outcome"] = approx.get("outcome", "EXIT")
                missed_trade["approx_exit_date"] = approx.get("exit_date", "")
            missed_entries.append(missed_trade)
            continue

        if str(pending.get("trade_type", "")).upper() == "MEDIUM" and _is_strong_rejection_candle(row):
            missed_trade = {
                "sym": pending["sym"],
                "sector": pending["sector"],
                "signal_date": pending["signal_date"],
                "activation_date": date.strftime("%Y-%m-%d"),
                "trigger_price": round(trigger_price, 3),
                "next_open": round(open_px, 3),
                "next_high": round(high_px, 3),
                "trade_type": pending.get("trade_type", "UNCLASSIFIED"),
                "score": round(float(pending.get("score", pending.get("smart_rank", 0.0))), 2),
                "risk_used": round(float(pending.get("risk_used") or 0.0), 4),
                "reason": "next_candle_rejection",
            }
            forced_trade = _build_open_trade(
                pending,
                entry_base=entry_base,
                account_size=account_size,
                entry_date=date,
                fill_mode="forced_rejection_approx",
            )
            approx = _simulate_trade_path(
                forced_trade,
                all_data[yahoo],
                date,
                account_size,
                max_bars,
            )
            if approx is not None:
                missed_trade["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                missed_trade["approx_outcome"] = approx.get("outcome", "EXIT")
                missed_trade["approx_exit_date"] = approx.get("exit_date", "")
            missed_entries.append(missed_trade)
            continue

        open_trades.append(
            _build_open_trade(
                pending,
                entry_base=entry_base,
                account_size=account_size,
                entry_date=date,
                fill_mode=fill_mode,
            )
        )
    return remaining_pending


def _close_trade(
    trade: dict,
    exit_date: pd.Timestamp,
    exit_price: float,
    outcome: str,
    account_size: float,
) -> dict:
    partial_return_pct = 0.0
    partial_fraction = float(K.PARTIAL_EXIT_FRACTION)
    partial_taken = bool(trade.get("partial_taken"))
    if partial_taken and trade.get("partial_exit_price"):
        partial_return_pct = partial_fraction * (
            (float(trade["partial_exit_price"]) - trade["entry"]) / max(trade["entry"], 1e-9) * 100.0
        )
    remaining_fraction = (1.0 - partial_fraction) if partial_taken else 1.0
    remaining_return_pct = remaining_fraction * (
        (exit_price - trade["entry"]) / max(trade["entry"], 1e-9) * 100.0
    )
    gross_return_pct = partial_return_pct + remaining_return_pct
    pnl_pct = gross_return_pct - (K.BT_FEES_PCT * 100.0)
    stop_dist_pct = max(
        ((trade["entry"] - trade["initial_stop"]) / max(trade["entry"], 1e-9)) * 100.0,
        0.01,
    )
    rr = gross_return_pct / stop_dist_pct
    alloc_pct = _trade_notional(trade["entry"], trade["size"], account_size)

    # FIX: Resolve STOP_HIT outcome by actual PnL — a profitable stop-hit is WIN
    if outcome == "STOP_HIT":
        outcome = "WIN" if pnl_pct > 0 else "LOSS"

    resolved = dict(trade)
    resolved.update(
        {
            "exit_date": exit_date.strftime("%Y-%m-%d"),
            "exit": round(exit_price, 3),
            "pnl_pct": round(pnl_pct, 2),
            "gross_return_pct": round(gross_return_pct, 2),
            "rr": round(rr, 2),
            "outcome": outcome,
            "alloc_pct": round(alloc_pct, 4),
        }
    )
    return resolved


def _update_open_trades(
    date: pd.Timestamp,
    open_trades: List[dict],
    closed_trades: List[dict],
    all_data: Dict[str, pd.DataFrame],
    account_size: float,
    equity: float,
    max_bars: int,
) -> Tuple[List[dict], float]:
    still_open: List[dict] = []

    for trade in open_trades:
        yahoo = SYMBOLS.get(trade["sym"])
        if not yahoo or yahoo not in all_data or date not in all_data[yahoo].index:
            still_open.append(trade)
            continue

        row = all_data[yahoo].loc[date]
        trade, exit_price, outcome = _process_trade_bar(trade, row, max_bars)

        if outcome is None:
            still_open.append(trade)
            continue

        resolved = _close_trade(trade, date, exit_price, outcome, account_size)
        equity *= 1.0 + resolved["alloc_pct"] * resolved["pnl_pct"] / 100.0
        resolved["equity_after"] = round(equity, 4)
        closed_trades.append(resolved)

    return still_open, equity


def run_backtest(
    date_from: str,
    date_to: str,
    max_bars: int = K.BT_MAX_BARS,
    max_concurrent_trades: int = K.PORTFOLIO_MAX_OPEN_TRADES,
    entry_mode: str = "touch",
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[List[dict], List[Tuple[str, float]], Dict[str, Any], Dict[str, Any]]:
    all_data = get_data_engine().fetch_backtest(date_from, date_to)
    if not all_data:
        empty_params = {
            "date_from": date_from,
            "date_to": date_to,
            "max_bars": max_bars,
            "entry_mode": entry_mode,
        }
        return [], [], empty_params, {"missed_entries": []}

    yahoo_to_sym = _yahoo_to_sym()
    all_dates: List[pd.Timestamp] = sorted({d for df in all_data.values() for d in df.index})
    if not all_dates:
        empty_params = {
            "date_from": date_from,
            "date_to": date_to,
            "max_bars": max_bars,
            "entry_mode": entry_mode,
        }
        return [], [], empty_params, {"missed_entries": []}

    account_size = get_account_size()
    trade_cap = min(max_concurrent_trades, K.PORTFOLIO_MAX_OPEN_TRADES)
    open_trades: List[dict] = []
    pending_entries: List[dict] = []
    closed_trades: List[dict] = []
    missed_entries: List[dict] = []
    equity = 100.0
    equity_curve: List[Tuple[str, float]] = [(all_dates[0].strftime("%Y-%m-%d"), 0.0)]
    last_market_regime: Optional[str] = None
    # Symbol loss cooldown: after BT_SYM_COOLDOWN_LOSSES consecutive losses on a
    # symbol, skip the next BT_SYM_COOLDOWN_BARS trading days for that symbol.
    sym_loss_streak: Dict[str, int] = {}   # sym -> consecutive loss count
    sym_cooldown_until: Dict[str, int] = {}  # sym -> day_idx when cooldown expires
    _SYM_COOLDOWN_LOSSES = int(K.BT_SYM_COOLDOWN_LOSSES)  # consecutive losses that trigger cooldown
    _SYM_COOLDOWN_DAYS   = int(K.SYMBOL_COOLDOWN_DAYS)    # trading-day ban length

    for day_idx, date in enumerate(all_dates):
        if progress_callback and day_idx % 5 == 0:
            progress_callback(
                f"Backtesting {date.strftime('%Y-%m-%d')} ({day_idx + 1}/{len(all_dates)})"
            )

        pending_entries = _activate_pending_trades(
            date,
            pending_entries,
            open_trades,
            all_data,
            account_size,
            missed_entries,
            entry_mode,
            max_bars,
        )
        open_trades, equity = _update_open_trades(
            date,
            open_trades,
            closed_trades,
            all_data,
            account_size,
            equity,
            max_bars,
        )

        # ── Symbol loss cooldown tracking ─────────────────────────
        # Check newly closed trades (appended to closed_trades by _update_open_trades)
        for ct in closed_trades:
            sym = ct.get("sym", "")
            if ct.get("_cooldown_tracked"):
                continue
            ct["_cooldown_tracked"] = True
            if ct.get("pnl_pct", 0) <= 0:
                sym_loss_streak[sym] = sym_loss_streak.get(sym, 0) + 1
                if sym_loss_streak[sym] >= _SYM_COOLDOWN_LOSSES:
                    sym_cooldown_until[sym] = day_idx + _SYM_COOLDOWN_DAYS
            else:
                sym_loss_streak[sym] = 0

        results, _sector_strength, regime, market_regime = _build_results_for_day(all_data, date, yahoo_to_sym)
        if not results:
            equity_curve.append((date.strftime("%Y-%m-%d"), round(equity - 100.0, 2)))
            continue

        if progress_callback and market_regime != last_market_regime:
            progress_callback(f"Market regime: {market_regime} ({K.EGX30_SYMBOL})")
            last_market_regime = market_regime

        guarded_list, _, _, _, _ = compute_portfolio_guard(
            results,
            account_size=account_size,
            open_trades=open_trades,
        )

        weak_rank_floor = K.TRADE_TYPE_STRONG_MIN + 3.0 if market_regime == "WEAK" else K.BT_MIN_SMARTRANK

        # --- Track filter-rejected signals for missed-trade analysis ------
        open_or_pending = {t["sym"] for t in open_trades} | {t["sym"] for t in pending_entries}
        # Only simulate top rejects (by score) to avoid excessive compute.
        _MAX_SIM_PER_DAY = 5
        _MIN_SCORE_FOR_SIM = 50.0
        filter_rejects: List[dict] = []
        for gr in guarded_list:
            r = gr.result
            if not r.get("plan"):
                continue
            action = r["plan"].get("action", "")
            if action not in ("ACCUMULATE", "PROBE"):
                continue
            sr = r.get("smart_rank", 0.0)
            # Determine rejection reason
            if gr.is_blocked:
                reject_reason = "guard_blocked"
            elif sr < K.BT_MIN_SMARTRANK:
                reject_reason = "low_smartrank"
            elif regime != "BULL":
                reject_reason = "non_bull_regime"
            elif market_regime == "WEAK" and sr < K.TRADE_TYPE_STRONG_MIN:
                reject_reason = "weak_market_medium_block"
            elif market_regime == "WEAK" and sr < weak_rank_floor:
                reject_reason = "weak_market_rank_filter"
            elif market_regime == "WEAK" and not r.get("volume_confirmed", False):
                reject_reason = "weak_market_volume_filter"
            else:
                continue  # not rejected — will go through allowed path
            # Skip symbols already open/pending
            if r["sym"] in open_or_pending:
                continue
            filter_rejects.append((gr, r, sr, reject_reason))

        # Sort by score descending, simulate only top N above threshold
        filter_rejects.sort(key=lambda x: x[2], reverse=True)
        _day_sim_count = 0
        for _gr, r, sr, reject_reason in filter_rejects:
            yahoo = SYMBOLS.get(r["sym"])
            if not yahoo or yahoo not in all_data:
                continue
            act_date = _find_next_bar_date(all_data[yahoo], date)
            if act_date is None or act_date not in all_data[yahoo].index:
                continue
            row_next = all_data[yahoo].loc[act_date]
            open_px = float(row_next["Open"])
            if open_px <= 0:
                continue

            missed_entry = {
                "sym": r["sym"],
                "sector": r["sector"],
                "signal_date": date.strftime("%Y-%m-%d"),
                "activation_date": act_date.strftime("%Y-%m-%d"),
                "trigger_price": round(float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))), 3),
                "next_open": round(open_px, 3),
                "next_high": round(float(row_next["High"]), 3),
                "trade_type": r.get("plan", {}).get("trade_type", "UNCLASSIFIED"),
                "score": round(float(sr), 2),
                "risk_used": round(float(r.get("plan", {}).get("risk_used", get_risk_per_trade())), 4),
                "reason": reject_reason,
            }

            # Simulate only top rejects with score >= threshold
            if sr >= _MIN_SCORE_FOR_SIM and _day_sim_count < _MAX_SIM_PER_DAY:
                fake_pending = {
                    "sym": r["sym"], "sector": r["sector"],
                    "signal_type": r["tag"], "regime": REGIME_MAP.get(regime, regime),
                    "signal_date": date.strftime("%Y-%m-%d"),
                    "activation_date": act_date,
                    "risk_pct": max(float(r["plan"].get("risk_pct", 0.02)), 0.005),
                    "target_pct": float(r["plan"].get("target_pct", 0.08)),
                    "trigger_price": missed_entry["trigger_price"],
                    "smart_rank": float(sr),
                    "score": round(float(sr), 2),
                    "trade_type": missed_entry["trade_type"],
                    "risk_used": missed_entry["risk_used"],
                    "anticipation": float(r.get("anticipation", 0.0)),
                    "atr": float(r.get("atr") or 0.0),
                }
                forced = _build_open_trade(fake_pending, open_px, account_size, act_date, "forced_filter_approx")
                approx = _simulate_trade_path(forced, all_data[yahoo], act_date, account_size, max_bars)
                if approx is not None:
                    missed_entry["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                    missed_entry["approx_outcome"] = approx.get("outcome", "EXIT")
                    missed_entry["approx_exit_date"] = approx.get("exit_date", "")
                _day_sim_count += 1

            missed_entries.append(missed_entry)

        allowed = [
            gr.result
            for gr in guarded_list
            if not gr.is_blocked
            and gr.result.get("plan")
            and gr.result["plan"].get("action") in ("ACCUMULATE", "PROBE")
            and gr.result.get("smart_rank", 0.0) >= K.BT_MIN_SMARTRANK
            and is_high_probability_trade(gr.result)
        ]

        # ── SYMBOL LOSS COOLDOWN FILTER ───────────────────────────
        # Skip symbols that have consecutive recent losses (discipline rule).
        allowed = [
            r for r in allowed
            if day_idx >= sym_cooldown_until.get(r.get("sym", ""), 0)
        ]

        if market_regime == "WEAK":
            strong_rank_floor = weak_rank_floor
            allowed = [
                r for r in allowed
                if r.get("smart_rank", 0.0) >= strong_rank_floor
                and r.get("volume_confirmed", False)
            ]
        # ── BACKTEST SECTOR BLACKLIST ─────────────────────────────
        # Sectors in BLACKLISTED_SECTORS_BT are completely excluded from the backtest.
        # Use for sectors with persistent structural weakness (e.g. REAL_ESTATE: WR 30%, avg -3.60%).
        if K.BLACKLISTED_SECTORS_BT:
            allowed = [
                r for r in allowed
                if r.get("sector") not in K.BLACKLISTED_SECTORS_BT
            ]
        # ── WEAK SECTOR FILTER ────────────────────────────────────
        # Sectors in WEAK_SECTOR_DOWNGRADE require STRONG conviction (SR >= STRONG_MIN).
        # This prevents mediocre setups in historically underperforming sectors.
        if K.WEAK_SECTOR_DOWNGRADE:
            allowed = [
                r for r in allowed
                if r.get("sector") not in K.WEAK_SECTOR_DOWNGRADE
                or r.get("smart_rank", 0.0) >= K.TRADE_TYPE_STRONG_MIN
            ]
        # ── HYBRID REGIME FLEXIBILITY ──────────────────────────────
        # BULL: all qualifying trades enter
        # NEUTRAL: only STRONG trades (SR >= STRONG threshold) enter
        # BEAR: no trades
        if regime == "NEUTRAL":
            allowed = [r for r in allowed
                       if r.get("smart_rank", 0.0) >= K.TRADE_TYPE_STRONG_MIN]

        # ── HYBRID TWO-TIER RISK MODEL ────────────────────────────
        # Tag each allowed signal with its risk tier
        for r in allowed:
            sr = r.get("smart_rank", 0.0)
            regime_risk_mult = K.MARKET_REGIME_WEAK_RISK_MULT if market_regime == "WEAK" else 1.0
            if sr >= K.TRADE_TYPE_STRONG_MIN:
                r["_hybrid_risk"] = K.RISK_PER_TRADE_STRONG * regime_risk_mult
                r["_hybrid_tier"] = "STRONG"
            else:
                r["_hybrid_risk"] = K.RISK_PER_TRADE_MEDIUM * regime_risk_mult
                r["_hybrid_tier"] = "MEDIUM"
            r["_market_regime"] = market_regime

        allowed.sort(
            key=lambda r: (
                0 if r["plan"].get("action") == "ACCUMULATE" else 1,
                0 if r.get("_hybrid_tier") == "STRONG" else 1,
                DECISION_PRIORITY.get(r["tag"], 99),
                -r["smart_rank"],
            )
        )

        if regime in ("BULL", "NEUTRAL"):
            available_slots = max(0, trade_cap - len(open_trades) - len(pending_entries))
            added_this_day = set()
            for r in allowed:
                if available_slots <= 0:
                    # Track slot-limited signals as missed
                    if r["sym"] not in open_or_pending and r["sym"] not in added_this_day:
                        yahoo = SYMBOLS.get(r["sym"])
                        if yahoo and yahoo in all_data:
                            act_date = _find_next_bar_date(all_data[yahoo], date)
                            if act_date and act_date in all_data[yahoo].index:
                                row_next = all_data[yahoo].loc[act_date]
                                open_px = float(row_next["Open"])
                                if open_px > 0:
                                    fp = {
                                        "sym": r["sym"], "sector": r["sector"],
                                        "signal_type": r["tag"], "regime": market_regime,
                                        "signal_date": date.strftime("%Y-%m-%d"),
                                        "activation_date": act_date,
                                        "risk_pct": max(float(r["plan"].get("risk_pct", 0.02)), 0.005),
                                        "target_pct": float(r["plan"].get("target_pct", 0.08)),
                                        "trigger_price": float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))),
                                        "smart_rank": float(r.get("smart_rank", 0.0)),
                                        "score": float(r.get("plan", {}).get("score", r.get("smart_rank", 0.0))),
                                        "trade_type": r.get("plan", {}).get("trade_type", "UNCLASSIFIED"),
                                        "risk_used": float(r.get("plan", {}).get("risk_used", get_risk_per_trade())),
                                        "anticipation": float(r.get("anticipation", 0.0)),
                                        "atr": float(r.get("atr") or 0.0),
                                    }
                                    forced = _build_open_trade(fp, open_px, account_size, act_date, "forced_filter_approx")
                                    approx = _simulate_trade_path(forced, all_data[yahoo], act_date, account_size, max_bars)
                                    me = {
                                        "sym": r["sym"], "sector": r["sector"],
                                        "signal_date": date.strftime("%Y-%m-%d"),
                                        "activation_date": act_date.strftime("%Y-%m-%d"),
                                        "trigger_price": round(float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))), 3),
                                        "next_open": round(open_px, 3),
                                        "next_high": round(float(row_next["High"]), 3),
                                        "trade_type": fp["trade_type"],
                                        "score": round(float(r.get("smart_rank", 0.0)), 2),
                                        "risk_used": round(float(fp["risk_used"]), 4),
                                        "reason": "slot_limit",
                                    }
                                    if approx is not None:
                                        me["approx_pnl_pct"] = approx.get("pnl_pct", 0.0)
                                        me["approx_outcome"] = approx.get("outcome", "EXIT")
                                        me["approx_exit_date"] = approx.get("exit_date", "")
                                    missed_entries.append(me)
                    continue
                if r["sym"] in open_or_pending:
                    continue
                yahoo = SYMBOLS.get(r["sym"])
                if not yahoo or yahoo not in all_data:
                    continue
                activation_date = _find_next_bar_date(all_data[yahoo], date)
                if activation_date is None:
                    continue
                pending_entries.append(
                    {
                        "sym": r["sym"],
                        "sector": r["sector"],
                        "signal_type": r["tag"],
                        "regime": market_regime,
                        "signal_date": date.strftime("%Y-%m-%d"),
                        "activation_date": activation_date,
                        "risk_pct": max(float(r["plan"].get("risk_pct", 0.02)), 0.005),
                        "target_pct": float(r["plan"].get("target_pct", 0.08)),
                        "trigger_price": float(r["plan"].get("trigger_price", r["plan"].get("entry", r["price"]))),
                        "smart_rank": float(r.get("smart_rank", 0.0)),
                        "multi_factor_rank": float(r.get("multi_factor_rank", 0.0)),
                        "final_rank": float(r.get("final_rank", 0.0)),
                        "score": float(r.get("plan", {}).get("score", r.get("smart_rank", 0.0))),
                        "trade_type": r.get("_hybrid_tier", r.get("plan", {}).get("trade_type", "UNCLASSIFIED")),
                        "risk_used": float(r.get("_hybrid_risk", get_risk_per_trade())),
                        "anticipation": float(r.get("anticipation", 0.0)),
                        "atr": float(r.get("atr") or 0.0),
                    }
                )
                open_or_pending.add(r["sym"])
                added_this_day.add(r["sym"])
                available_slots -= 1

        equity_curve.append((date.strftime("%Y-%m-%d"), round(equity - 100.0, 2)))

    if all_dates:
        last_date = all_dates[-1]
        for trade in list(open_trades):
            yahoo = SYMBOLS.get(trade["sym"])
            if not yahoo or yahoo not in all_data or last_date not in all_data[yahoo].index:
                continue
            close = float(all_data[yahoo].loc[last_date]["Close"])
            exit_price = round(close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            resolved = _close_trade(trade, last_date, exit_price, "EXIT", account_size)
            equity *= 1.0 + resolved["alloc_pct"] * resolved["pnl_pct"] / 100.0
            resolved["equity_after"] = round(equity, 4)
            closed_trades.append(resolved)
        equity_curve[-1] = (equity_curve[-1][0], round(equity - 100.0, 2))

    return (
        closed_trades,
        equity_curve,
        {
            "date_from": date_from,
            "date_to": date_to,
            "max_bars": max_bars,
            "max_concurrent_trades": trade_cap,
            "entry_mode": entry_mode,
            "execution": f"next_candle_{entry_mode}_stop_first_partial_tp_trailing",
            "slippage_pct": K.BT_SLIPPAGE_PCT,
            "fees_pct": K.BT_FEES_PCT,
        },
        {
            "missed_entries": missed_entries,
        },
    )


# ── CLI Entrypoint: Run backtest and output results to file ─────────────
if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Run EGX Radar backtest and output results.")
    parser.add_argument("--date-from", type=str, required=True, help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", type=str, required=True, help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, required=True, help="Path to output JSON file for backtest results.")
    parser.add_argument("--max-bars", type=int, default=None, help="Max bars per trade (optional)")
    parser.add_argument("--max-trades", type=int, default=None, help="Max concurrent trades (optional)")
    parser.add_argument("--entry-mode", type=str, default="touch", help="Entry mode: touch or open_only (optional)")
    args = parser.parse_args()

    # Use provided or default values
    max_bars = args.max_bars if args.max_bars is not None else K.BT_MAX_BARS
    max_trades = args.max_trades if args.max_trades is not None else K.PORTFOLIO_MAX_OPEN_TRADES
    entry_mode = args.entry_mode

    closed_trades, equity_curve, params, extras = run_backtest(
        args.date_from, args.date_to, max_bars=max_bars, max_concurrent_trades=max_trades, entry_mode=entry_mode
    )
    out = {
        "closed_trades": closed_trades,
        "equity_curve": equity_curve,
        "params": params,
        "extras": extras,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Backtest complete. Results written to {args.output}")
