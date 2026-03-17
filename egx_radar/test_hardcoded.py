"""Verification tests for hardcoded values refactoring."""

import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from egx_radar.config.settings import K

def test_hardcoded_values_refactor():
    assert K.CACHE_TTL_SECONDS == 3600, f"Expected 3600, got {K.CACHE_TTL_SECONDS}"
    assert K.MARKET_BREADTH_THRESHOLD == 0.50, f"Expected 0.50, got {K.MARKET_BREADTH_THRESHOLD}"
    assert K.SCAN_MAX_WORKERS == 8, f"Expected 8, got {K.SCAN_MAX_WORKERS}"
    assert K.CPI_FLOOR == 0.1, f"Expected 0.1, got {K.CPI_FLOOR}"
    assert K.MOM_NORM_LO == -3.0, f"Expected -3.0, got {K.MOM_NORM_LO}"
    assert K.MOM_NORM_HI == 6.0, f"Expected 6.0, got {K.MOM_NORM_HI}"
    assert K.ATR_INTRADAY_THRESH == 1.5, f"Expected 1.5, got {K.ATR_INTRADAY_THRESH}"
    assert K.OUTCOME_STALE_MULTIPLIER == 2, f"Expected 2, got {K.OUTCOME_STALE_MULTIPLIER}"
    
    print("✅ All 8 K. constants are accessible and have the correct default values.")

if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION: Refactoring Hardcoded Values")
    print("=" * 60)
    test_hardcoded_values_refactor()
    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
