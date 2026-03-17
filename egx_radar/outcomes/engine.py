"""Trade outcome engine: logging, history, and resolution (Layer 9)."""

import json
import logging
import math
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import pathlib

import pandas as pd

from egx_radar.config.settings import K, SYMBOLS
from egx_radar.state.app_state import STATE
from egx_radar.core.risk import compute_dynamic_stop
from egx_radar.core.indicators import pct_change_safe

log = logging.getLogger(__name__)

_LOG_DIR = pathlib.Path(K.OUTCOME_LOG_FILE).parent
_LOG_DIR.mkdir(parents=True, exist_ok=True)
import threading
_io_lock = threading.Lock()

# ── Database integration (lazy-loaded) ──────────────────────────────────
_DB_ENABLED = False
_db_manager = None


def _get_db_manager():
    """Lazy-load DatabaseManager to avoid circular imports.
    
    This function is called optionally by oe_record_signal() to persist
    trades to the database. If the database is unavailable, the scanner
    continues using JSON logs as the fallback.
    
    Returns:
        DatabaseManager instance if available, None otherwise.
    """
    global _db_manager, _DB_ENABLED
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
    import tempfile

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


def oe_load_log() -> List[dict]:
    with _io_lock:
        if not os.path.exists(K.OUTCOME_LOG_FILE):
            return []
        try:
            with open(K.OUTCOME_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.warning("oe_load_log: %s", e)
            return []


def oe_save_log(trades: List[dict]) -> None:
    with _io_lock:
        try:
            _atomic_json_write(K.OUTCOME_LOG_FILE, trades)
        except OSError as e:
            log.error("oe_save_log: %s", e)


def _oe_load_history_unsafe() -> List[dict]:
    """Load history WITHOUT acquiring _io_lock (caller must hold it)."""
    if not os.path.exists(K.OUTCOME_HISTORY_FILE):
        return []
    try:
        with open(K.OUTCOME_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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
        history.extend(new_trades)
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
    """Resolve a trade against forward price data. Returns resolved dict or None if still open."""
    if df is None or df.empty:
        return None
    entry  = trade.get("entry", 0.0)
    stop   = trade.get("stop", 0.0)
    target = trade.get("target", 0.0)
    if entry <= 0:
        return None

    try:
        df = _normalise_df_index(df)
    except Exception as e:
        log.warning("oe_resolve_trade normalise error: %s", e)
        return None

    # Stale trade: beyond scaled lookforward
    try:
        trade_date_str = trade.get("date", "")
        if not trade_date_str:
            return None
        trade_date = datetime.strptime(trade_date_str[:10], "%Y-%m-%d")
        age = (datetime.now() - trade_date).days
        if age > K.OUTCOME_LOOKFORWARD_DAYS * K.OUTCOME_STALE_MULTIPLIER:
            try:
                last_close = float(df["Close"].iloc[-1])
            except (IndexError, ValueError):
                last_close = entry
            resolved = dict(trade)
            resolved.update({
                "status": "TIMEOUT",
                "exit_price": round(last_close, 3),
                "days_held": age, "mfe_pct": 0.0, "mae_pct": 0.0,
                "pnl_pct": round(pct_change_safe(last_close, entry), 2),
                "resolved_date": datetime.now().strftime("%Y-%m-%d"),
            })
            return resolved
    except (ValueError, TypeError):
        pass

    try:
        entry_dt  = pd.Timestamp(trade.get("date", ""))
        positions = [i for i, d in enumerate(df.index) if d >= entry_dt]
        if not positions:
            return None
        start = positions[0]
    except (ValueError, TypeError, KeyError) as e:
        log.warning("oe_resolve_trade date parse error for %s: %s", trade.get("sym"), e)
        return None

    window = df.iloc[start:start + K.OUTCOME_LOOKFORWARD_DAYS + 1]
    if len(window) < K.OUTCOME_MIN_BARS_NEEDED:
        return None

    highs  = window["High"].values
    lows   = window["Low"].values
    closes = window["Close"].values
    
    # Needs a 5-bar momentum lookback from the start. We can use the main df for this.
    try:
        start_idx_in_df = df.index.get_loc(window.index[0])
    except KeyError as e:
        log.warning("oe_resolve_trade index missing: %s", e)
        start_idx_in_df = 5  # fallback
        
    outcome = "OPEN"
    exit_bar = len(window) - 1
    mfe = mae = 0.0
    
    # Action type
    is_short = trade.get("action", "").lower() == "sell" or trade.get("tag", "").lower() == "sell"
    current_stop = stop
    current_target = target

    for i, (h, l, c) in enumerate(zip(highs, lows, closes)):
        mfe = max(mfe, pct_change_safe(h, entry))
        mae = max(mae, -pct_change_safe(l, entry))
        
        # Calculate trailing metrics
        df_idx = start_idx_in_df + i
        if df_idx >= 5:
            past_c = df["Close"].iloc[df_idx - 5]
            momentum = pct_change_safe(c, past_c)
        else:
            momentum = 0.0
            
        # Simplified regime flag for trailing: ADX > 25 and close > EMA50 (approximate MOMENTUM)
        # We don't have full ADX here nicely in arrays, so we use momentum proxy
        pseudo_regime = "MOMENTUM" if momentum > 2.5 else "NEUTRAL"
        
        current_stop, current_target, _ = compute_dynamic_stop(
            current_price=c,
            entry=entry,
            current_stop=current_stop,
            current_target=current_target,
            momentum=momentum,
            regime=pseudo_regime,
            is_short=is_short
        )
        
        if is_short:
            if h >= current_stop:
                outcome, exit_bar = "LOSS", i; break
            if l <= current_target:
                outcome, exit_bar = "WIN", i; break
        else:
            if l <= current_stop:
                outcome, exit_bar = "LOSS", i; break
            if h >= current_target:
                outcome, exit_bar = "WIN", i;  break

    if outcome == "OPEN" and len(window) >= K.OUTCOME_LOOKFORWARD_DAYS:
        outcome, exit_bar = "TIMEOUT", len(window) - 1

    if outcome == "OPEN":
        return None

    exit_price = closes[min(exit_bar, len(closes) - 1)]
    resolved   = dict(trade)
    resolved.update({
        "status":     outcome,
        "exit_price": round(float(exit_price), 3),
        "days_held":  exit_bar + 1,
        "mfe_pct":    round(mfe, 2),
        "mae_pct":    round(mae, 2),
        "pnl_pct":    round(pct_change_safe(float(exit_price), entry), 2),
        "resolved_date": datetime.now().strftime("%Y-%m-%d"),
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
        "action": action, "status": "OPEN",
        # Fields for alpha_monitor (populated here or at resolution)
        "setup_type": tag or action,  # signal tag (ultra/early/buy/watch)
        "exit_price": None,           # set by oe_resolve_trade()
        "result_pct": None,           # set by oe_resolve_trade()
        "stop_hit": None,             # set by oe_resolve_trade() → True if status=="LOSS"
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
            "signal":      r.get("signal", ""),
            "smart_rank":  round(r.get("smart_rank", 0.0), 2),
            "confidence":  round(r.get("confidence", 0.0), 1),
            "zone":        r.get("zone", ""),
            "rsi":         round(r.get("rsi", 0.0), 1),
            "adx":         round(r.get("adx", 0.0), 1),
            "entry":       round(plan.get("entry", 0.0), 2),
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
