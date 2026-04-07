import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import math
import json
from egx_radar.core.data_guard import DataGuard
from egx_radar.outcomes.engine import oe_record_signal, oe_load_log, oe_save_log

def test_dataguard_safeties():
    print("Testing DataGuard column safeties...")
    dg = DataGuard()
    
    # Missing columns
    df_missing = pd.DataFrame({"Close": [1.0, 2.0]})
    res = dg.evaluate(df_missing, "TEST")
    assert not res.passed
    assert "missing" in res.reason.lower()
    print("[SUCCESS] DataGuard correctly rejected missing columns.")

def test_outcomes_none_guards():
    print("Testing OutcomesEngine None-guards...")
    # Mock settings / file
    test_log = "test_trades_log.json"
    if os.path.exists(test_log): os.remove(test_log)
    
    from egx_radar.config.settings import K
    original_log = K.OUTCOME_LOG_FILE
    K.OUTCOME_LOG_FILE = test_log
    
    try:
        # Test recording with None values
        oe_record_signal(
            sym="TEST", sector="TEST", entry=10.0, stop=9.0, target=12.0,
            atr=None, smart_rank=float('nan'), anticipation=None, action="buy"
        )
        
        trades = oe_load_log()
        assert len(trades) == 1
        t = trades[0]
        assert t["atr"] == 0.0
        assert t["smart_rank"] == 0.0
        assert t["anticipation"] == 0.0
        print("[SUCCESS] OutcomesEngine correctly handled None/NaN values.")
        
    finally:
        K.OUTCOME_LOG_FILE = original_log
        if os.path.exists(test_log): os.remove(test_log)

if __name__ == "__main__":
    try:
        test_dataguard_safeties()
        test_outcomes_none_guards()
        print("\nALL AUDIT FIXES VERIFIED SUCCESSFULLY.")
    except Exception as e:
        print(f"\n[FAILURE] VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
