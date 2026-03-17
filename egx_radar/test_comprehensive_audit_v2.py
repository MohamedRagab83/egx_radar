import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import math
import json
import datetime
from egx_radar.core.data_guard import DataGuard
from egx_radar.core.momentum_guard import MomentumGuard
from egx_radar.core.position_manager import PositionManager
from egx_radar.state.app_state import STATE
from egx_radar.core.indicators import compute_vwap_dist, compute_vol_zscore
from egx_radar.core.portfolio import compute_portfolio_guard
from egx_radar.outcomes.engine import oe_record_signal, oe_load_log, oe_save_log, oe_save_history_batch

def test_momentum_guard_import():
    print("Testing MomentumGuard import safety...")
    mg = MomentumGuard()
    # Test record_breakout_result with a date object to trigger the datetime logic
    mg.record_breakout_result("TEST", True, trade_date=datetime.date.today())
    print("[SUCCESS] MomentumGuard record_breakout_result worked without import errors.")

def test_position_manager_lock():
    print("Testing PositionManager confirm_addon...")
    test_log = "test_trades_log_pm.json"
    from egx_radar.config.settings import K
    original_log = K.OUTCOME_LOG_FILE
    K.OUTCOME_LOG_FILE = test_log
    
    try:
        pm = PositionManager()
        # Create a dummy open trade
        trades = [{"sym": "TEST", "status": "OPEN", "entry": 10.0, "addon_count": 0}]
        oe_save_log(trades)
        
        success = pm.confirm_addon("TEST")
        assert success
        
        updated = oe_load_log()
        assert updated[0]["addon_count"] == 1
        assert "addon_date" in updated[0]
        print("[SUCCESS] PositionManager confirm_addon worked correctly.")
    finally:
        K.OUTCOME_LOG_FILE = original_log
        if os.path.exists(test_log): os.remove(test_log)

def test_app_state_bias_consolidation():
    print("Testing AppState record_signal_bias consolidation...")
    STATE.neural_bias_memory.clear()
    results = [
        {"plan": {"action": "ACCUMULATE"}},
        {"plan": {"action": "PROBE"}},
        {"plan": {"action": "ACCUMULATE"}},
    ]
    # Old logic would append 3 times. New logic should append once.
    STATE.record_signal_bias(results)
    assert len(STATE.neural_bias_memory) == 1
    # Mean of (0.2, 0.05, 0.2) = 0.45 / 3 = 0.15
    assert abs(STATE.neural_bias_memory[0] - 0.15) < 1e-9
    print("[SUCCESS] AppState correctly consolidated signal bias.")

def test_indicator_robustness():
    print("Testing indicator robustness with missing columns...")
    df_empty = pd.DataFrame({"Other": [1, 2, 3]})
    
    v_dist = compute_vwap_dist(df_empty, 10.0)
    assert v_dist == 0.0
    
    z_score = compute_vol_zscore(df_empty)
    assert z_score == 0.0
    print("[SUCCESS] Indicators handled missing columns gracefully.")

def test_portfolio_zero_division():
    print("Testing portfolio guard zero-division safety...")
    results = [{"sym": "TEST", "sector": "BANKS", "tag": "buy", "atr": 0.5, "plan": {"size": 100}}]
    # Testing with account_size = 0
    guarded, counts, exp, blocked = compute_portfolio_guard(results, account_size=0.0)
    # Should not crash. The percentage calculation uses max(1e-9, account_size).
    # Since exp = 0.5 * 100 = 50, and 50 / 1e-9 is huge, it should block based on ATR cap.
    assert guarded[0].is_blocked
    assert "ATR cap" in guarded[0].guard_reason
    print("[SUCCESS] Portfolio guard handled zero account size safely.")

if __name__ == "__main__":
    try:
        test_momentum_guard_import()
        test_position_manager_lock()
        test_app_state_bias_consolidation()
        test_indicator_robustness()
        test_portfolio_zero_division()
        print("\nALL COMPREHENSIVE AUDIT FIXES VERIFIED SUCCESSFULLY.")
    except Exception as e:
        print(f"\n[FAILURE] VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
