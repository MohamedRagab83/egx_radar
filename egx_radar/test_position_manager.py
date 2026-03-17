"""Verification tests for Position Manager (Module 4)."""

import sys
import os
from unittest.mock import patch
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from egx_radar.config.settings import K
from egx_radar.core.position_manager import PositionManager

# Setup dummy logs
dummy_trades = [
    {
        "sym": "OPEN_PROFIT",
        "status": "OPEN",
        "entry": 100.0,
        "atr": 5.0,
        "addon_count": 0
    },
    {
        "sym": "OPEN_LOSS",
        "status": "OPEN",
        "entry": 100.0,
        "atr": 5.0,
        "addon_count": 0
    },
    {
        "sym": "MAX_ADDON",
        "status": "OPEN",
        "entry": 100.0,
        "atr": 5.0,
        "addon_count": 1
    }
]

def mock_oe_load_log():
    return [dict(t) for t in dummy_trades]

mock_saved_trades = []
def mock_oe_save_log(trades):
    global mock_saved_trades
    mock_saved_trades = trades

# ═══════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════
@patch("egx_radar.core.position_manager.oe_load_log", new=mock_oe_load_log)
@patch("egx_radar.core.position_manager.oe_save_log", new=mock_oe_save_log)
def run_tests():
    pm = PositionManager()
    
    print("Test 1: No open position")
    res1 = pm.evaluate_addon(
        symbol="NEW_SYM", current_price=105.0, adx=35.0, momentum=5.0,
        smart_rank=60.0, smart_rank_threshold=40.0, bearish_divergence=False
    )
    assert not res1.approved
    assert res1.reason == "NO_OPEN_POSITION"
    print("✅ Passed")
    
    print("Test 2: Open position, profit below threshold")
    # Entry 100 -> current 101 -> 1% profit < 3% threshold
    res2 = pm.evaluate_addon(
        symbol="OPEN_LOSS", current_price=101.0, adx=35.0, momentum=5.0,
        smart_rank=60.0, smart_rank_threshold=40.0, bearish_divergence=False
    )
    assert not res2.approved
    assert res2.reason == "INSUFFICIENT_PROFIT"
    print("✅ Passed")
    
    print("Test 3: Open position, all conditions met")
    # Entry 100 -> current 110 -> 10% profit > 3%
    res3 = pm.evaluate_addon(
        symbol="OPEN_PROFIT", current_price=110.0, adx=35.0, momentum=5.0,
        smart_rank=60.0, smart_rank_threshold=40.0, bearish_divergence=False
    )
    assert res3.approved
    assert res3.reason == "ADDON_APPROVED"
    assert res3.new_stop_initial == 100.0  # Break even (entry)
    assert res3.new_stop_addon == 110.0 - (5.0 * 0.5)  # Current - (ATR * 0.5) = 110 - 2.5 = 107.5
    print("✅ Passed")
    
    print("Test 4: Confirm addon updates log")
    success = pm.confirm_addon("OPEN_PROFIT")
    assert success
    assert len(mock_saved_trades) > 0
    updated_trade = next(t for t in mock_saved_trades if t["sym"] == "OPEN_PROFIT")
    assert updated_trade["addon_count"] == 1
    assert "addon_date" in updated_trade
    print("✅ Passed")
    
    
if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION: Position Manager")
    print("=" * 60)
    run_tests()
    print("=" * 60)
    print("ALL 4 TESTS PASSED ✅")
    print("=" * 60)
