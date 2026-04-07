"""Portfolio guard: sector and ATR exposure limits (Layer 7)."""

import logging
from typing import Dict, List, NamedTuple, Tuple

from egx_radar.config.settings import (
    K,
    SECTORS,
    get_account_size,
    get_max_per_sector,
    get_atr_exposure,
)

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 7: PORTFOLIO GUARD — Pure function, non-mutating, idempotent
# ═══════════════════════════════════════════════════════════════════════════


class GuardedResult(NamedTuple):
    """Immutable wrapper for a result record with guard annotation."""
    result: dict
    guard_reason: str
    is_blocked: bool


def compute_portfolio_guard(
    results: List[dict],
    account_size: float = None,
    open_trades: List[dict] = None,
) -> Tuple[List[GuardedResult], Dict[str, int], float, List[str], bool]:
    """
    FIX-G: Pure function.  Does NOT mutate input `results`.
    Uses live account_size from DATA_SOURCE_CFG so UI changes apply immediately.
    """
    if account_size is None:
        account_size = get_account_size()
    max_per_sector = get_max_per_sector()
    atr_exposure   = get_atr_exposure()
    max_open_trades = int(getattr(K, "PORTFOLIO_MAX_OPEN_TRADES", 3))
    max_sector_exposure_value = account_size * float(getattr(K, "PORTFOLIO_MAX_SECTOR_EXPOSURE_PCT", 0.30))

    active_tags    = {"buy", "ultra", "early"}
    sector_counts: Dict[str, int] = {s: 0 for s in SECTORS}
    sector_notional: Dict[str, float] = {s: 0.0 for s in SECTORS}
    cumulative     = 0.0
    active_positions = 0
    
    # Feature 5: Advanced Portfolio Guard
    # Pre-fill exposure with currently active trades
    if open_trades:
        for t in open_trades:
            sec = t.get("sector")
            if sec in sector_counts:
                sector_counts[sec] += 1
                sector_notional[sec] += float(t.get("entry", 0.0)) * float(t.get("size", 0))
            if t.get("status", "OPEN") == "OPEN":
                active_positions += 1
            # Assuming size and atr are present or can be calculated (using standard risk)
            # If not present, we will estimate based on standard 4% risk
            t_atr = t.get("atr", 0.0)
            if t_atr > 0 and t.get("size"):
                cumulative += (t_atr * t.get("size", 0))
            else:
                # Estimate standard risk deduction if missing from log
                cumulative += account_size * atr_exposure

    max_exposure   = account_size * atr_exposure

    DAILY_LOSS_LIMIT_PCT = 0.03  # Block new entries if daily drawdown exceeds 3%
    daily_pnl = 0.0
    if open_trades:
        for t in open_trades:
            entry  = t.get("entry", 0.0)
            stop   = t.get("stop", 0.0)
            size   = t.get("size", 0)
            status = t.get("status", "OPEN")

            # Use pnl_pct if already resolved (TIMEOUT trades have it)
            if t.get("pnl_pct") is not None and entry > 0 and size > 0:
                daily_pnl += (t["pnl_pct"] / 100) * entry * size
            # For OPEN trades: estimate unrealized at 50% of worst-case stop loss
            # (full worst-case is too conservative; true mark-to-market needs live prices)
            elif status == "OPEN" and entry > 0 and stop > 0 and size > 0:
                worst_case = (stop - entry) * size  # negative number = loss
                daily_pnl += worst_case * 0.5
    daily_loss_triggered = daily_pnl < -(account_size * DAILY_LOSS_LIMIT_PCT)

    guarded:       List[GuardedResult] = []
    blocked_syms:  List[str]           = []

    for r in results:
        if r["tag"] not in active_tags:
            guarded.append(GuardedResult(r, "", False))
            continue

        if daily_loss_triggered and r["tag"] in active_tags:
            guarded.append(GuardedResult(
                r,
                f"\U0001f6d1 Daily loss limit reached ({daily_pnl:.0f} EGP). No new entries.",
                True,
            ))
            blocked_syms.append(r.get("symbol", ""))
            continue

        sector  = r["sector"]
        atr     = r.get("atr") or 0.0
        plan    = r.get("plan") or {}
        size    = plan.get("size", 0)
        entry   = float(plan.get("entry", r.get("price", 0.0)) or 0.0)
        contrib = atr * size
        notional = entry * size

        if active_positions >= max_open_trades:
            reason = f"Open-trade cap reached ({active_positions}/{max_open_trades})"
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        if sector_counts.get(sector, 0) >= max_per_sector:
            reason = (
                f"Sector cap: {sector} already has "
                f"{sector_counts[sector]} signal(s) (max {max_per_sector})"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        if sector_notional.get(sector, 0.0) + notional > max_sector_exposure_value:
            reason = (
                f"Sector exposure cap: {sector} would reach "
                f"{(sector_notional.get(sector, 0.0) + notional):.0f} EGP "
                f"(max {max_sector_exposure_value:.0f} EGP)"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        if cumulative + contrib > max_exposure:
            reason = (
                f"ATR cap: +{contrib:.0f} EGP would bring total to "
                f"{(cumulative+contrib):.0f} EGP "
                f"({(cumulative+contrib)/max(1e-9, account_size)*100:.1f}% of account, "
                f"max {atr_exposure*100:.0f}%)"
            )
            blocked_syms.append(r["sym"])
            guarded.append(GuardedResult(r, reason, True))
            continue

        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        sector_notional[sector] = sector_notional.get(sector, 0.0) + notional
        cumulative += contrib
        active_positions += 1
        guarded.append(GuardedResult(r, "", False))

    return guarded, sector_counts, cumulative, blocked_syms, daily_loss_triggered
