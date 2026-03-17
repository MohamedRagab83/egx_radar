"""Position Manager: open position and add-on logic (Module 4).

Stateless evaluator that reads from the trades log to determine if
an open position exists and if it qualifies for an add-on.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from egx_radar.config.settings import K
from egx_radar.outcomes.engine import oe_load_log, oe_save_log

log = logging.getLogger(__name__)


@dataclass
class AddOnResult:
    """Result of an add-on evaluation for an open position."""
    approved: bool
    symbol: str
    reason: str
    flags: List[str]
    # If approved:
    add_on_r: float = 0.0          # PM_ADDON_R or 0.0
    new_stop_initial: float = 0.0  # Break-even stop for the original position
    new_stop_addon: float = 0.0    # Tighter stop for the add-on
    total_exposure_r: float = 0.0  # Total R after add-on
    profit_pct: float = 0.0        # Open profit % at evaluation time


class PositionManager:
    """
    Stateless evaluator for open positions and add-ons.
    Always reads live data from the trades log file via engine.py.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def get_all_open_positions(self) -> List[dict]:
        """Returns a list of all currently open trades."""
        try:
            trades = oe_load_log()
            return [t for t in trades if t.get("status") == "OPEN"]
        except Exception as e:
            log.error("[PositionManager] Failed to load open positions: %s", e)
            return []

    def get_open_position(self, symbol: str) -> Optional[dict]:
        """Returns the open trade dict for symbol, or None if not open."""
        try:
            trades = oe_load_log()
            for t in trades:
                if t.get("sym") == symbol and t.get("status") == "OPEN":
                    return t
        except Exception as e:
            log.error("[PositionManager] Error getting position for %s: %s", symbol, e)
        return None

    def evaluate_addon(
        self,
        symbol: str,
        current_price: float,
        adx: float,
        momentum: float,
        smart_rank: float,
        smart_rank_threshold: float,
        bearish_divergence: bool,
    ) -> AddOnResult:
        """
        Evaluate whether an add-on is justified for an existing open position.
        Fail-fast condition checks before approval.
        """
        flags = []

        # 1. Position exists?
        trade = self.get_open_position(symbol)
        if trade is None:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="NO_OPEN_POSITION", flags=["NO_OPEN_POSITION"]
            )

        # 2. Already has add-on?
        addon_count = trade.get("addon_count", 0)
        if addon_count >= K.PM_MAX_ADDONS_PER_POSITION:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="MAX_ADDONS_REACHED", flags=["MAX_ADDONS_REACHED"]
            )

        # 3. Exposure limit? (Initial is 1.0R, each addon is PM_ADDON_R)
        current_total_r = 1.0 + (K.PM_ADDON_R * addon_count)
        if current_total_r + K.PM_ADDON_R > K.PM_MAX_EXPOSURE_R:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="MAX_EXPOSURE_EXCEEDED", flags=["MAX_EXPOSURE_EXCEEDED"]
            )

        # 4. Profit threshold?
        entry_price = trade.get("entry", 0.0)
        if entry_price <= 0:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="INVALID_ENTRY_PRICE", flags=["INVALID_ENTRY_PRICE"]
            )
            
        profit_pct = (current_price - entry_price) / entry_price * 100
        if profit_pct < K.PM_ADD_MIN_PROFIT_PCT:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="INSUFFICIENT_PROFIT", flags=["INSUFFICIENT_PROFIT"]
            )

        # 5. ADX strong enough?
        if adx < K.PM_ADD_MIN_ADX:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="WEAK_ADX", flags=["WEAK_ADX"]
            )

        # 6. Momentum strong enough?
        if momentum < K.PM_ADD_MIN_MOMENTUM:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="WEAK_MOMENTUM", flags=["WEAK_MOMENTUM"]
            )

        # 7. No bearish divergence?
        if bearish_divergence:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="BEARISH_DIVERGENCE", flags=["BEARISH_DIVERGENCE"]
            )

        # 8. SmartRank still valid?
        if smart_rank < smart_rank_threshold:
            return AddOnResult(
                approved=False, symbol=symbol,
                reason="RANK_BELOW_THRESHOLD", flags=["RANK_BELOW_THRESHOLD"]
            )

        # All conditions pass → approve
        atr = trade.get("atr", 0.0)
        new_stop_initial = entry_price
        new_stop_addon = current_price - (atr * K.PM_ADDON_STOP_ATR_MULT)
        new_total_r = current_total_r + K.PM_ADDON_R

        return AddOnResult(
            approved=True,
            symbol=symbol,
            reason="ADDON_APPROVED",
            flags=["ADDON_APPROVED"],
            add_on_r=K.PM_ADDON_R,
            new_stop_initial=new_stop_initial,
            new_stop_addon=new_stop_addon,
            total_exposure_r=new_total_r,
            profit_pct=profit_pct,
        )

    def confirm_addon(self, symbol: str) -> bool:
        """
        Called after the broker order for the add-on is confirmed.
        Updates the trade in the log.
        """
        with self._lock:
            try:
                trades = oe_load_log()
                for t in trades:
                    if t.get("sym") == symbol and t.get("status") == "OPEN":
                        t["addon_count"] = t.get("addon_count", 0) + 1
                        t["addon_date"] = datetime.now().strftime("%Y-%m-%d")
                        oe_save_log(trades)
                        return True
            except Exception as e:
                log.error("[PositionManager] Failed to confirm addon for %s: %s", symbol, e)
            return False

    def get_open_position_from_list(self, symbol: str, open_trades: List[dict]) -> Optional[dict]:
        """Backtest version — reads from provided list instead of oe_load_log()."""
        for t in open_trades:
            if t.get("sym") == symbol and t.get("status") == "OPEN":
                return t
        return None


__all__ = ["PositionManager", "AddOnResult"]
