"""Trade outcome engine: logging, history, and resolution (Layer 9)."""

import json
import logging
import math
import os
import pathlib
import tempfile
import threading
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import pandas as pd

from egx_radar.config.settings import K, SYMBOLS
from egx_radar.state.app_state import STATE
from egx_radar.core.indicators import pct_change_safe
from egx_radar.core.signal_engine import candle_hits_trigger

log = logging.getLogger(__name__)

_LOG_DIR = pathlib.Path(K.OUTCOME_LOG_FILE).parent
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_io_lock = threading.Lock()

# ── Database integration (lazy-loaded) ──────────────────────────────────
_DB_ENABLED = False
_db_manager = None
_db_init_lock = threading.Lock()


def _get_db_manager():
    """Lazy-load DatabaseManager to avoid circular imports.
    
    This function is called optionally by oe_record_signal() to persist
    trades to the database. If the database is unavailable, the scanner
    continues using JSON logs as the fallback.
    
    Thread-safe: uses _db_init_lock to prevent double-init from
    concurrent scan threads.
    
    Returns:
        DatabaseManager instance if available, None otherwise.
    """
    global _db_manager, _DB_ENABLED
    if _db_manager is not None:
        return _db_manager
    
    with _db_init_lock:
        if _db_manager is not None:
            return _db_manager
        try:
            from egx_radar.database.manager import DatabaseManager
            _db_manager = DatabaseManager()
            _db_manager.init_db()
            _DB_ENABLED = True
            return _db_manager
        except Exception as exc:
            log.debug("DatabaseManager unavailable (%s) — using JSON only", exc)
            _DB_ENABLED = False
            return None


def _atomic_json_write(filepath: str, data: object) -> None:
    """Write JSON atomically: temp → os.replace()."""
    dirpath = os.path.dirname(os.path.abspath(filepath)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp", prefix=".egx_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, filepath)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _canonical_resolved_status(status: object, pnl_pct: object) -> str:
    """Keep terminal WIN/LOSS status aligned with realised pnl_pct.

    This fixes the known case where a stop-managed trade can still finish
    positive after a partial take-profit, which previously produced
    status='LOSS' alongside pnl_pct > 0.
    """
    status_text = str(status or "").upper()
    if status_text not in {"WIN", "LOSS"} or not _is_finite_number(pnl_pct):
        return status_text

    pnl_value = float(pnl_pct)
    if pnl_value > 0:
        return "WIN"
    if pnl_value < 0:
        return "LOSS"
    return status_text


def _trade_identity_key(trade: dict) -> Tuple[str, str, str, float]:
    """Stable key for de-duplicating persisted trade history rows."""
    trigger_or_entry = trade.get("trigger_price", trade.get("entry", 0.0))
    key_price = round(float(trigger_or_entry or 0.0), 4)
    return (
        str(trade.get("sym", "") or ""),
        str(trade.get("date", "") or ""),
        str(trade.get("entry_date", "") or ""),
        key_price,
    )


def _normalise_trade_record(trade: dict) -> dict:
    """Backfill optional fields so old and new records share one schema."""
    rec = dict(trade or {})

    if rec.get("setup_type") in (None, "") and rec.get("action"):
        rec["setup_type"] = rec.get("action")
    if rec.get("trade_type") in (None, ""):
        rec["trade_type"] = "UNCLASSIFIED"

    score = rec.get("score")
    smart_rank = rec.get("smart_rank")
    if _is_finite_number(score):
        rec["score"] = round(float(score), 2)
    elif _is_finite_number(smart_rank):
        rec["score"] = round(float(smart_rank), 2)

    risk_used = rec.get("risk_used")
    rec["risk_used"] = round(float(risk_used), 4) if _is_finite_number(risk_used) else 0.0

    trigger_price = rec.get("trigger_price")
    entry = rec.get("entry")
    if _is_finite_number(trigger_price):
        rec["trigger_price"] = round(float(trigger_price), 3)
    elif _is_finite_number(entry):
        rec["trigger_price"] = round(float(entry), 3)

    if rec.get("fill_mode") in (None, ""):
        rec["fill_mode"] = "next_candle_touch"

    trailing_stop_pct = rec.get("trailing_stop_pct")
    if not _is_finite_number(trailing_stop_pct):
        rec["trailing_stop_pct"] = float(K.TRAILING_STOP_PCT)
    else:
        rec["trailing_stop_pct"] = round(float(trailing_stop_pct), 4)

    pnl_pct = rec.get("pnl_pct")
    if _is_finite_number(pnl_pct):
        rec["pnl_pct"] = round(float(pnl_pct), 2)
        if not _is_finite_number(rec.get("result_pct")):
            rec["result_pct"] = rec["pnl_pct"]
        rec["status"] = _canonical_resolved_status(rec.get("status"), rec["pnl_pct"])

    return rec


def oe_load_log() -> List[dict]:
    with _io_lock:
        if not os.path.exists(K.OUTCOME_LOG_FILE):
            return []
        try:
            with open(K.OUTCOME_LOG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                return [_normalise_trade_record(t) for t in raw if isinstance(t, dict)]
        except (OSError, json.JSONDecodeError) as e:
            log.warning("oe_load_log: %s", e)
            return []


def oe_save_log(trades: List[dict]) -> None:
    with _io_lock:
        try:
            _atomic_json_write(K.OUTCOME_LOG_FILE, [_normalise_trade_record(t) for t in trades])
        except OSError as e:
            log.error("oe_save_log: %s", e)


def _oe_load_history_unsafe() -> List[dict]:
    """Load history WITHOUT acquiring _io_lock (caller must hold it)."""
    if not os.path.exists(K.OUTCOME_HISTORY_FILE):
        return []
    try:
        with open(K.OUTCOME_HISTORY_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return [_normalise_trade_record(t) for t in raw if isinstance(t, dict)]
    except (OSError, json.JSONDecodeError) as e:
        log.warning("oe_load_history: %s", e)
        return []


def oe_load_history() -> List[dict]:
    with _io_lock:
        return _oe_load_history_unsafe()


def oe_save_history_batch(new_trades: List[dict]) -> None:
    if not new_trades:
        return
    with _io_lock:
        history = _oe_load_history_unsafe()
        seen = {_trade_identity_key(t) for t in history}
        appended = 0
        for trade in new_trades:
            norm = _normalise_trade_record(trade)
            trade_key = _trade_identity_key(norm)
            if trade_key in seen:
                continue
            history.append(norm)
            seen.add(trade_key)
            appended += 1
        if appended == 0:
            return
        try:
            _atomic_json_write(K.OUTCOME_HISTORY_FILE, history)
        except OSError as e:
            log.error("oe_save_history_batch: %s", e)


def _normalise_df_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    try:
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert(None)
    except Exception as e:
        try:
            df.index = pd.to_datetime(df.index).tz_localize(None)
        except Exception as e2:
            log.warning("oe_normalise_df_index failed: %s", e2)
    return df


def oe_resolve_trade(trade: dict, df: Optional[pd.DataFrame]) -> Optional[dict]:
    """Resolve a logged signal using the same next-candle trigger logic as the backtest."""
    if df is None or df.empty:
        return None

    try:
        df = _normalise_df_index(df)
    except Exception as e:
        log.warning("oe_resolve_trade normalise error: %s", e)
        return None

    trade_date_str = trade.get("date", "")
    if not trade_date_str:
        return None

    try:
        signal_dt = pd.Timestamp(trade_date_str[:10])
    except (ValueError, TypeError) as e:
        log.warning("oe_resolve_trade date parse error for %s: %s", trade.get("sym"), e)
        return None

    future_positions = [i for i, d in enumerate(df.index) if d > signal_dt]
    if not future_positions:
        return None

    activation_idx = future_positions[0]
    activation_date = df.index[activation_idx]
    activation_row = df.iloc[activation_idx]
    trigger_price = float(trade.get("trigger_price") or trade.get("entry") or 0.0)
    if trigger_price <= 0:
        return None

    next_open = float(activation_row["Open"])
    next_high = float(activation_row["High"])
    if not candle_hits_trigger(next_high, trigger_price):
        resolved = dict(trade)
        resolved.update({
            "status": "MISSED",
            "entry_date": activation_date.strftime("%Y-%m-%d"),
            "trigger_price": round(trigger_price, 3),
            "next_open": round(next_open, 3),
            "next_high": round(next_high, 3),
            "days_held": 0,
            "mfe_pct": 0.0,
            "mae_pct": 0.0,
            "pnl_pct": 0.0,
            "result_pct": 0.0,
            "stop_hit": False,
            "resolved_date": datetime.now().strftime("%Y-%m-%d"),
            "fill_mode": "next_candle_touch",
        })
        return resolved

    entry = round(trigger_price * (1.0 + K.BT_SLIPPAGE_PCT / 2.0), 3)
    stop = float(trade.get("stop") or (entry * (1.0 - K.MAX_STOP_LOSS_PCT)))
    stop = min(stop, entry * 0.995)
    if stop >= entry:
        stop = entry * (1.0 - K.MAX_STOP_LOSS_PCT)
    target = float(trade.get("target") or (entry * (1.0 + K.POSITION_MAIN_TP_PCT)))
    partial_target = float(trade.get("partial_target") or (entry * (1.0 + K.PARTIAL_TP_PCT)))
    trailing_trigger = float(trade.get("trailing_trigger") or (entry * (1.0 + K.TRAILING_TRIGGER_PCT)))
    trailing_stop_pct = float(trade.get("trailing_stop_pct") or K.TRAILING_STOP_PCT)

    window = df.iloc[activation_idx:activation_idx + K.OUTCOME_LOOKFORWARD_DAYS + 1]
    if len(window) < K.OUTCOME_MIN_BARS_NEEDED:
        return None

    outcome = None
    exit_price = None
    bars_held = 0
    mfe = 0.0
    mae = 0.0
    partial_taken = False
    partial_exit_price = None
    trailing_active = False
    trailing_anchor = entry

    for ts, row in window.iterrows():
        open_px = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        bars_held += 1

        mfe = max(mfe, pct_change_safe(high, entry))
        mae = max(mae, -pct_change_safe(low, entry))

        if open_px <= stop:
            exit_price = round(open_px * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "LOSS"
        elif low <= stop:
            exit_price = round(stop * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
            outcome = "LOSS"
        else:
            if (not partial_taken) and high >= partial_target:
                partial_taken = True
                partial_exit_price = round(partial_target * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
                stop = max(stop, entry)

            if high >= trailing_trigger:
                trailing_active = True
                trailing_anchor = max(trailing_anchor, high)

            if trailing_active:
                stop = max(stop, trailing_anchor * (1.0 - trailing_stop_pct))

            if high >= target:
                exit_price = round(target * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
                outcome = "WIN"
            elif bars_held >= K.OUTCOME_LOOKFORWARD_DAYS:
                exit_price = round(close * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
                outcome = "TIMEOUT"

        if outcome is not None:
            exit_date = ts
            break

    if outcome is None:
        age = (datetime.now() - datetime.strptime(trade_date_str[:10], "%Y-%m-%d")).days
        if age <= K.OUTCOME_LOOKFORWARD_DAYS * K.OUTCOME_STALE_MULTIPLIER:
            return None
        exit_date = window.index[-1]
        exit_price = round(float(window.iloc[-1]["Close"]) * (1.0 - K.BT_SLIPPAGE_PCT / 2.0), 3)
        outcome = "TIMEOUT"

    partial_return_pct = 0.0
    partial_fraction = float(K.PARTIAL_EXIT_FRACTION)
    if partial_taken and partial_exit_price:
        partial_return_pct = partial_fraction * ((partial_exit_price - entry) / max(entry, 1e-9) * 100.0)
    remaining_fraction = (1.0 - partial_fraction) if partial_taken else 1.0
    remaining_return_pct = remaining_fraction * ((exit_price - entry) / max(entry, 1e-9) * 100.0)
    gross_return_pct = partial_return_pct + remaining_return_pct
    pnl_pct = gross_return_pct - (K.BT_FEES_PCT * 100.0)
    resolved_status = _canonical_resolved_status(outcome, pnl_pct)

    resolved = dict(trade)
    resolved.update({
        "status": resolved_status,
        "entry": entry,
        "entry_date": activation_date.strftime("%Y-%m-%d"),
        "trigger_price": round(trigger_price, 3),
        "exit_price": round(float(exit_price), 3),
        "days_held": bars_held,
        "mfe_pct": round(mfe, 2),
        "mae_pct": round(mae, 2),
        "pnl_pct": round(pnl_pct, 2),
        "result_pct": round(pnl_pct, 2),
        "stop_hit": outcome == "LOSS",
        "resolved_date": datetime.now().strftime("%Y-%m-%d"),
        "fill_mode": "next_candle_touch",
        "partial_taken": partial_taken,
        "trade_type": trade.get("trade_type", "UNCLASSIFIED"),
        "score": round(float(trade.get("score", trade.get("smart_rank", 0.0))), 2),
        "risk_used": round(float(trade.get("risk_used") or 0.0), 4),
    })

    # Feed breakout result back to MomentumGuard for fatigue tracking
    setup = trade.get("setup_type", "")
    if "breakout" in setup.lower() or trade.get("action", "").lower() in ("buy", "ultra"):
        followed_through = outcome == "WIN"
        try:
            entry_date = date.fromisoformat(trade.get("date", "")[:10])
            if hasattr(STATE, "momentum_guard") and STATE.momentum_guard:
                STATE.momentum_guard.record_breakout_result(
                    symbol=trade.get("sym", ""),
                    followed_through=followed_through,
                    trade_date=entry_date,
                )
        except Exception as e:
            log.warning("[engine] breakout feedback failed: %s", e)

    return resolved


def oe_record_signal(
    sym: str, sector: str, entry: float, stop: float, target: float,
    atr: float, smart_rank: float, anticipation: float, action: str,
    existing_trades: Optional[List[dict]] = None,
    tag: str = "",
    trade_type: str = "UNCLASSIFIED",
    score: float = 0.0,
    risk_used: float = 0.0,
    trigger_price: Optional[float] = None,
    partial_target: Optional[float] = None,
    trailing_trigger: Optional[float] = None,
    trailing_stop_pct: Optional[float] = None,
) -> None:
    today_str = datetime.now().strftime("%Y-%m-%d")
    trades    = existing_trades if existing_trades is not None else oe_load_log()
    for t in trades:
        if t.get("sym") == sym and t.get("date", "")[:10] == today_str:
            return
    trades.append({
        "sym": sym, "sector": sector, "date": today_str,
        "entry": round(entry, 3), "stop": round(stop, 3), "target": round(target, 3),
        "atr": round(atr, 3) if (atr is not None and math.isfinite(atr)) else 0.0,
        "smart_rank": round(smart_rank, 2) if (smart_rank is not None and math.isfinite(smart_rank)) else 0.0,
        "anticipation": round(anticipation, 2) if (anticipation is not None and math.isfinite(anticipation)) else 0.0,
        "action": action, "status": "PENDING_TRIGGER",
        # Fields for alpha_monitor (populated here or at resolution)
        "setup_type": tag or action,  # signal tag (ultra/early/buy/watch)
        "exit_price": None,           # set by oe_resolve_trade()
        "result_pct": None,           # set by oe_resolve_trade()
        "stop_hit": None,             # set by oe_resolve_trade() → True if status=="LOSS"
        "trade_type": trade_type,
        "score": round(score, 2) if (score is not None and math.isfinite(score)) else 0.0,
        "risk_used": round(risk_used, 4) if (risk_used is not None and math.isfinite(risk_used)) else 0.0,
        "trigger_price": round(trigger_price if trigger_price is not None else entry, 3),
        "partial_target": round(partial_target, 3) if partial_target else None,
        "trailing_trigger": round(trailing_trigger, 3) if trailing_trigger else None,
        "trailing_stop_pct": round(trailing_stop_pct, 4) if trailing_stop_pct else K.TRAILING_STOP_PCT,
        "fill_mode": "next_candle_touch",
    })
    oe_save_log(trades)
    
    # ── Database write (additive — JSON log remains primary) ──────────────
    try:
        db = _get_db_manager()
        if db is not None:
            db.save_trade_signal({
                "sym":          sym,
                "sector":       sector,
                "entry":        entry,
                "stop":         stop,
                "target":       target,
                "atr":          atr if atr is not None else 0.0,
                "smart_rank":   smart_rank if smart_rank and math.isfinite(smart_rank) else 0.0,
                "anticipation": anticipation if anticipation is not None else 0.0,
                "action":       action,
                "recorded_at":  datetime.utcnow().isoformat(),
            })
    except Exception as _db_exc:
        log.debug("DB trade write failed (non-critical): %s", _db_exc)
        # Never let a DB failure break the scanner — JSON remains the source of truth


def oe_process_open_trades(all_data: Dict[str, pd.DataFrame]) -> Tuple[List[dict], int, int]:
    """Resolve open trades. Returns (remaining, wins, losses)."""
    trades = oe_load_log()
    if not trades:
        return [], 0, 0

    remaining: List[dict] = []
    batch:     List[dict] = []
    wins = losses = 0

    for trade in trades:
        sym   = trade.get("sym", "")
        yahoo = SYMBOLS.get(sym)
        df    = all_data.get(yahoo) if yahoo else None

        # Fix: outcomes resolution — fallback for symbols not in SYMBOLS (e.g. delisted, typo,
        # or symbols added/removed since the trade was recorded). Attempt a direct yfinance
        # fetch so the trade can still be resolved rather than staying OPEN indefinitely.
        if df is None and sym:
            try:
                import yfinance as yf
                _yf_sym = (yahoo or sym) + (".CA" if not sym.endswith(".CA") else "")
                _yf_df = yf.download(_yf_sym, period="3mo", auto_adjust=True, progress=False)
                if _yf_df is not None and not _yf_df.empty:
                    df = _yf_df
                    log.debug("outcomes fallback fetch OK: %s → %s (%d bars)", sym, _yf_sym, len(df))
                else:
                    # Try without .CA suffix
                    _yf_df2 = yf.download(yahoo or sym, period="3mo", auto_adjust=True, progress=False)
                    if _yf_df2 is not None and not _yf_df2.empty:
                        df = _yf_df2  # Fix: outcomes resolution
            except Exception as _yf_exc:
                log.debug("outcomes fallback fetch failed for %s: %s", sym, _yf_exc)

        resolved = oe_resolve_trade(trade, df)
        if resolved is None:
            remaining.append(trade)
            continue
        batch.append(resolved)
        outcome = resolved["status"]
        rank    = trade.get("smart_rank", 0.0)
        ant     = trade.get("anticipation", 0.0)
        sec     = trade.get("sector", "")
        t_tag   = trade.get("action", "").lower()   # FIX-5: pass sector+tag
        if outcome == "WIN":
            wins += 1
            STATE.record_win(rank, ant, sector=sec, tag=t_tag)
        elif outcome == "LOSS":
            losses += 1
            STATE.record_loss(rank, ant, sector=sec, tag=t_tag)
        elif outcome == "TIMEOUT":
            # Neutral outcome: did not win or lose — record as a partial loss
            # with reduced weight (0.5) so it slightly dampens WinRate
            # without fully penalizing the signal
            timeout_pnl = resolved.get("pnl_pct", 0.0)
            if timeout_pnl >= 0:
                # Timed out with small gain or flat → treat as weak win
                STATE.record_win(rank * 0.5, ant, sector=sec, tag=t_tag)
            else:
                # Timed out in the red → treat as weak loss
                STATE.record_loss(rank * 0.5, ant, sector=sec, tag=t_tag)

    oe_save_history_batch(batch)
    oe_save_log(remaining)
    
    # ── Database write for resolved outcomes (new) ─────────────────────────
    # Update each resolved trade in the database with exit/outcome information
    try:
        db = _get_db_manager()
        if db is not None and batch:
            for resolved_trade in batch:
                try:
                    entry_date_str = resolved_trade.get("date", "")
                    if entry_date_str:
                        entry_dt = datetime.strptime(entry_date_str[:10], "%Y-%m-%d")
                        db.update_trade_outcome(
                            symbol=resolved_trade.get("sym", ""),
                            entry_date=entry_dt,
                            exit_date=datetime.strptime(
                                resolved_trade.get("resolved_date", ""), "%Y-%m-%d"
                            ) if resolved_trade.get("resolved_date") else datetime.utcnow(),
                            exit_price=resolved_trade.get("exit_price", 0.0),
                            pnl_pct=resolved_trade.get("pnl_pct", 0.0),
                            outcome=resolved_trade.get("status", "TIMEOUT"),
                            exit_reason="Hit " + resolved_trade.get("status", "").lower(),
                        )
                except Exception as trade_exc:
                    log.debug("DB outcome update failed for %s: %s", 
                              resolved_trade.get("sym"), trade_exc)
    except Exception as db_exc:
        log.debug("DB outcome batch update skipped: %s", db_exc)
        # Never let DB failure break the outcome resolution — JSON is source of truth
    
    return remaining, wins, losses


def oe_save_rejections(rejections: List[Dict[str, str]]) -> None:
    """Save a list of rejected symbols and reasons to a CSV file."""
    if not rejections:
        return
        
    filepath = _LOG_DIR / "rejected_symbols.csv"
    try:
        df = pd.DataFrame(rejections)
        df["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Append if exists and today, else overwrite
        mode = 'a' if os.path.exists(filepath) else 'w'
        header = not os.path.exists(filepath)
        df.to_csv(filepath, mode=mode, header=header, index=False, encoding="utf-8")
    except Exception as e:
        log.error("Failed to save rejections: %s", e)


def oe_save_daily_scan(results: list, scan_date: str = None) -> str:
    """Save full scan results as a dated CSV snapshot.
    
    Saves to: egx_radar/history/YYYY-MM-DD_scan.csv
    Returns the filepath string.
    """
    if not results:
        return ""

    if scan_date is None:
        scan_date = datetime.now().strftime("%Y-%m-%d")

    history_dir = _LOG_DIR / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    filepath = history_dir / f"{scan_date}_scan.csv"

    # Build flat rows — only the columns useful for review
    rows = []
    for r in results:
        plan = r.get("plan", {})
        rows.append({
            "date":        scan_date,
            "symbol":      r.get("sym", ""),
            "sector":      r.get("sector", ""),
            "price":       r.get("price", 0.0),
            "action":      plan.get("action", "WAIT"),
            "trade_type":  plan.get("trade_type", "SKIP"),
            "score":       round(plan.get("score", r.get("smart_rank", 0.0)), 2),
            "risk_used":   round(plan.get("risk_used", 0.0), 4),
            "signal":      r.get("signal", ""),
            "smart_rank":  round(r.get("smart_rank", 0.0), 2),
            "confidence":  round(r.get("confidence", 0.0), 1),
            "zone":        r.get("zone", ""),
            "rsi":         round(r.get("rsi", 0.0), 1),
            "adx":         round(r.get("adx", 0.0), 1),
            "entry":       round(plan.get("entry", 0.0), 2),
            "trigger_price": round(plan.get("trigger_price", r.get("trigger_price", 0.0)), 2),
            "stop":        round(plan.get("stop", 0.0), 2),
            "target":      round(plan.get("target", 0.0), 2),
            "rr":          plan.get("rr", 0.0),
            "atr":         round(r.get("atr", 0.0), 3) if r.get("atr") else "",
            "vol_ratio":   round(r.get("vol_ratio", 0.0), 2),
            "pct_ema200":  round(r.get("pct_ema200", 0.0), 1),
            "adapt_mom":   round(r.get("adaptive_mom", 0.0), 2),
            "dg_tier":     r.get("dg_tier", ""),
            "signal_reason": r.get("signal_reason", ""),
            # Paper trading columns — filled manually later
            "price_1w":    "",   # price after 1 week
            "price_2w":    "",   # price after 2 weeks
            "result":      "",   # WIN / LOSS / HOLD
            "notes":       "",
        })

    df = pd.DataFrame(rows)

    # Don't overwrite existing file — append a suffix if needed
    if filepath.exists():
        ts = datetime.now().strftime("%H-%M")
        filepath = history_dir / f"{scan_date}_{ts}_scan.csv"

    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    log.info("Daily scan saved → %s (%d symbols)", filepath.name, len(rows))
    return str(filepath)


def oe_weekly_report() -> str:
    """Scan the history folder and produce a summary of PROBE signals
    from the past 7 days, comparing entry price to latest close.
    
    Returns a formatted text report string.
    """
    from datetime import timedelta

    history_dir = _LOG_DIR / "history"
    if not history_dir.exists():
        return "No scan history found. Run at least one scan first."

    cutoff = datetime.now() - timedelta(days=7)
    all_rows = []

    for csv_file in sorted(history_dir.glob("*_scan.csv")):
        try:
            file_date_str = csv_file.name[:10]
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
            if file_date < cutoff:
                continue
            df = pd.read_csv(csv_file, encoding="utf-8-sig")
            # Only PROBE signals are worth tracking
            probe_rows = df[df["action"] == "PROBE"].copy()
            if not probe_rows.empty:
                probe_rows["scan_date"] = file_date_str
                all_rows.append(probe_rows)
        except Exception:
            continue

    if not all_rows:
        return "No PROBE signals found in the past 7 days."

    combined = pd.concat(all_rows, ignore_index=True)

    lines = ["=" * 50]
    lines.append(f"EGX Radar — Weekly PROBE Signal Report")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Signals tracked: {len(combined)}")
    lines.append("=" * 50)
    lines.append("")

    for _, row in combined.iterrows():
        result = row.get("result", "")
        price_1w = row.get("price_1w", "")
        
        if result:
            status = f"→ {result}"
        elif price_1w:
            try:
                p1w = float(price_1w)
                entry = float(row["entry"])
                pct = (p1w - entry) / (entry + 1e-9) * 100
                status = f"→ {p1w:.2f} ({pct:+.1f}%)"
            except (ValueError, TypeError):
                status = "→ pending"
        else:
            status = "→ pending review"

        lines.append(
            f"[{row['scan_date']}] {row['symbol']:6s} | "
            f"Entry={row['entry']:.2f} Stop={row['stop']:.2f} Target={row['target']:.2f} "
            f"R:R={row['rr']:.1f}x | {status}"
        )

    lines.append("")
    lines.append("=" * 50)
    lines.append("HOW TO UPDATE: Open the CSV in history/ folder,")
    lines.append("fill in 'price_1w' column with actual price after 1 week.")
    lines.append("=" * 50)

    return "\n".join(lines)


__all__ = [
    "oe_load_log",
    "oe_save_log",
    "oe_load_history",
    "oe_save_history_batch",
    "_normalise_df_index",
    "oe_resolve_trade",
    "oe_record_signal",
    "oe_process_open_trades",
    "oe_save_rejections",
    "oe_save_daily_scan",
    "oe_weekly_report",
]
