"""Integration smoke test for full guard pipeline."""

import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def test_full_guard_pipeline():
    """
    Simulates one symbol passing through all 4 guards in the correct order.
    Uses minimal mock data — no real market data needed.
    """
    from egx_radar.core.data_guard import DataGuard
    from egx_radar.core.momentum_guard import MomentumGuard
    from egx_radar.core.alpha_monitor import AlphaMonitor
    from egx_radar.core.position_manager import PositionManager

    symbol = "TEST"

    # Step 1: DataGuard — clean data
    dg = DataGuard()
    
    # 250 bars with clean data, no gaps, no crazy volume spikes
    dates = pd.date_range(end=datetime.now(), periods=250, freq='B')
    df = pd.DataFrame({
        "Open": np.linspace(10, 20, 250),
        "High": np.linspace(11, 21, 250),
        "Low": np.linspace(9, 19, 250),
        "Close": np.linspace(10, 20, 250),
        "Volume": np.random.normal(10000, 1000, 250).clip(min=1000)
    }, index=dates)

    dg_result = dg.evaluate(df, symbol)
    assert dg_result.confidence_tier in ("FULL", "DEGRADED"), f"Expected FULL/DEGRADED, got {dg_result.confidence_tier}"

    # Step 2: MomentumGuard — strong momentum
    mg = MomentumGuard()
    mg_result = mg.evaluate(symbol, momentum_today=3.0, momentum_yesterday=3.0, adx=30.0, vol_ratio=1.0)
    assert mg_result.momentum_persistent is True, "Momentum should be persistent"
    assert mg_result.position_scale == 1.0, f"Expected 1.0 scale, got {mg_result.position_scale}"

    from unittest.mock import patch

    # Step 3: AlphaMonitor — no history (returns OK with warning_level 0)
    am = AlphaMonitor()
    with patch("egx_radar.core.alpha_monitor.oe_load_history", return_value=[]):
        am_result = am.evaluate()
    assert am_result.warning_level == 0, f"Expected warning level 0, got {am_result.warning_level}"
    assert am_result.pause_new_entries is False, "New entries should not be paused"

    # Step 4: PositionManager — no open position
    pm = PositionManager()
    open_pos = pm.get_open_position(symbol)
    assert open_pos is None, "Should not have open position for TEST_SYM absent from live log"

    # Step 5: Combined scaling
    combined_scale = mg_result.position_scale * am_result.position_scale
    assert combined_scale == 1.0, f"Expected 1.0, got {combined_scale}"

    print("✅ Full guard pipeline smoke test PASSED")

if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION: Full Guard Pipeline")
    print("=" * 60)
    test_full_guard_pipeline()
    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
