from __future__ import annotations

"""Performance metrics from backtest trades."""

import logging
from collections import defaultdict
from typing import Any, Dict, List

from egx_radar.config.settings import K

log = logging.getLogger(__name__)


def compute_metrics(trades: List[dict]) -> Dict[str, Any]:
    """
    Compute overall, per-regime, per-signal, per-sector, per-symbol, and monthly metrics.
    trades: list of closed trade dicts with keys entry_date, exit_date, sym, sector,
            signal_type, regime, entry, exit, pnl_pct, rr, outcome, etc.
    """
    if not trades:
        return _empty_metrics()

    # Overall
    total_trades = len(trades)
    wins = [t for t in trades if t.get("pnl_pct", 0) > 0]
    losses = [t for t in trades if t.get("pnl_pct", 0) <= 0]
    win_rate = len(wins) / total_trades * 100 if total_trades else 0.0
    rr_list = [t["rr"] for t in trades if t.get("rr") is not None]
    avg_return = sum(t.get("pnl_pct", 0.0) for t in trades) / total_trades if total_trades else 0.0
    avg_rr = sum(rr_list) / len(rr_list) if rr_list else 0.0
    total_return = sum(t["pnl_pct"] for t in trades)
    gross_profit = sum(t["pnl_pct"] for t in wins)
    gross_loss = abs(sum(t["pnl_pct"] for t in losses))
    profit_factor = gross_profit / (gross_loss + 1e-9) if gross_loss else (float("inf") if gross_profit else 0.0)
    bars_list = [t.get("bars_held", 0) for t in trades]
    avg_bars = sum(bars_list) / len(bars_list) if bars_list else 0.0
    largest_win = max((t["pnl_pct"] for t in wins), default=0.0)
    largest_loss = min((t["pnl_pct"] for t in losses), default=0.0)

    # Equity curve for drawdown using actual backtest allocations when available.
    if all(t.get("equity_after") is not None for t in trades):
        equity_points = [100.0] + [float(t["equity_after"]) for t in trades]
    else:
        equity_points = [100.0]
        equity_m = 100.0
        for t in trades:
            alloc = float(t.get("alloc_pct", 0.20))
            equity_m *= (1 + alloc * t["pnl_pct"] / 100)
            equity_points.append(equity_m)
    peak = equity_points[0]
    max_dd = 0.0
    for point in equity_points[1:]:
        peak = max(peak, point)
        dd = (peak - point) / peak * 100 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    max_drawdown_pct = max_dd
    total_return = (equity_points[-1] - 100.0) / 100.0 * 100

    # Sharpe: annualized, scaled by trades-per-year (not sqrt(252))
    # since these are per-trade returns, not daily returns
    if total_trades >= 2:
        returns = [t["pnl_pct"] for t in trades]
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std = variance ** 0.5 if variance > 0 else 1e-9
        daily_rf = K.RISK_FREE_ANNUAL_PCT / K.TRADING_DAYS_PER_YEAR / 100
        per_trade_rf = daily_rf * avg_bars if avg_bars > 0 else daily_rf
        trades_per_year = K.TRADING_DAYS_PER_YEAR / max(avg_bars, 1)
        sharpe = ((mean_ret / 100 - per_trade_rf) / (std / 100 + 1e-9)) * (trades_per_year ** 0.5) if std > 0 else 0.0
    else:
        sharpe = 0.0

    overall = {
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 1),
        "avg_return_pct": round(avg_return, 2),
        "expectancy_pct": round(avg_return, 2),
        "avg_rr": round(avg_rr, 2),
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_bars_in_trade": round(avg_bars, 1),
        "largest_win_pct": round(largest_win, 2),
        "largest_loss_pct": round(largest_loss, 2),
    }

    # Per regime
    by_regime: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"trades": [], "pnl": 0.0})
    for t in trades:
        reg = t.get("regime", "NEUTRAL")
        by_regime[reg]["trades"].append(t)
        by_regime[reg]["pnl"] += t["pnl_pct"]
    per_regime = {}
    for reg, data in by_regime.items():
        tr = data["trades"]
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        wr = w / n * 100 if n else 0.0
        rrs = [x["rr"] for x in tr if x.get("rr") is not None]
        per_regime[reg] = {
            "win_rate_pct": round(wr, 1),
            "avg_rr": round(sum(rrs) / len(rrs), 2) if rrs else 0.0,
            "total_trades": n,
        }

    # Per signal type
    by_signal: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_signal[t.get("signal_type", "—")].append(t)
    per_signal = {}
    for sig, tr in by_signal.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        rrs = [x["rr"] for x in tr if x.get("rr") is not None]
        per_signal[sig] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_rr": round(sum(rrs) / len(rrs), 2) if rrs else 0.0,
            "avg_return_pct": round(sum(x.get("pnl_pct", 0.0) for x in tr) / n, 2) if n else 0.0,
            "total_trades": n,
        }

    # Per trade type
    by_trade_type: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_trade_type[t.get("trade_type", "UNCLASSIFIED")].append(t)
    per_trade_type = {}
    for trade_type, tr in by_trade_type.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        rrs = [x["rr"] for x in tr if x.get("rr") is not None]
        per_trade_type[trade_type] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "avg_return_pct": round(sum(x.get("pnl_pct", 0.0) for x in tr) / n, 2) if n else 0.0,
            "avg_rr": round(sum(rrs) / len(rrs), 2) if rrs else 0.0,
            "avg_risk_used_pct": round(sum(float(x.get("risk_used", 0.0)) for x in tr) / n * 100.0, 2) if n else 0.0,
            "total_trades": n,
        }

    # Per sector
    by_sector: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_sector[t.get("sector", "—")].append(t)
    per_sector = {}
    for sec, tr in by_sector.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        ret = sum(x["pnl_pct"] for x in tr)
        per_sector[sec] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "total_trades": n,
            "avg_return_pct": round(ret / n, 2) if n else 0.0,
        }

    # Per symbol
    by_sym: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        by_sym[t.get("sym", "—")].append(t)
    per_symbol = {}
    for sym, tr in by_sym.items():
        n = len(tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        ret = sum(x["pnl_pct"] for x in tr)
        pnls = [x["pnl_pct"] for x in tr]
        per_symbol[sym] = {
            "win_rate_pct": round(w / n * 100, 1) if n else 0.0,
            "total_trades": n,
            "avg_return_pct": round(ret / n, 2) if n else 0.0,
            "best_trade_pct": round(max(pnls), 2) if pnls else 0.0,
            "worst_trade_pct": round(min(pnls), 2) if pnls else 0.0,
        }

    # Monthly
    by_month: Dict[str, List[dict]] = defaultdict(list)
    for t in trades:
        exit_d = t.get("exit_date", "")
        if len(exit_d) >= 7:
            month_key = exit_d[:7]
            by_month[month_key].append(t)
    monthly = []
    for month in sorted(by_month.keys()):
        tr = by_month[month]
        ret = sum(x["pnl_pct"] for x in tr)
        w = sum(1 for x in tr if x.get("pnl_pct", 0) > 0)
        monthly.append({
            "month": month,
            "trade_count": len(tr),
            "return_pct": round(ret, 2),
            "win_rate_pct": round(w / len(tr) * 100, 1) if tr else 0.0,
        })

    return {
        "overall": overall,
        "per_regime": dict(per_regime),
        "per_signal": per_signal,
        "per_trade_type": per_trade_type,
        "per_sector": per_sector,
        "per_symbol": per_symbol,
        "monthly": monthly,
    }


def _empty_metrics() -> Dict[str, Any]:
    return {
        "overall": {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "avg_return_pct": 0.0,
            "expectancy_pct": 0.0,
            "avg_rr": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0,
            "avg_bars_in_trade": 0.0,
            "largest_win_pct": 0.0,
            "largest_loss_pct": 0.0,
        },
        "per_regime": {},
        "per_signal": {},
        "per_trade_type": {},
        "per_sector": {},
        "per_symbol": {},
        "monthly": [],
    }
