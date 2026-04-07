"""Verification test for DataGuard module."""

import sys, os
sys.path.insert(0, r"d:\egx radar seprated")

import numpy as np
import pandas as pd

from egx_radar.core.data_guard import DataGuard, DataGuardResult
from egx_radar.config.settings import K


def make_df(n=200, broken=0, zero_vol_pct=0.0):
    """Build a synthetic OHLCV DataFrame."""
    np.random.seed(42)
    close = 50 + np.cumsum(np.random.randn(n) * 0.3)
    high  = close + np.abs(np.random.randn(n)) * 0.5
    low   = close - np.abs(np.random.randn(n)) * 0.5
    # Ensure Open is always within [Low, High]
    opn   = low + np.random.rand(n) * (high - low)
    vol   = np.random.randint(100_000, 500_000, size=n).astype(float)

    # Inject broken candles (High < Low)
    for i in range(broken):
        idx = i * (n // max(broken, 1))
        high[idx], low[idx] = low[idx] - 1, high[idx] + 1

    # Inject zero-volume bars
    zero_count = int(n * zero_vol_pct)
    if zero_count > 0:
        indices = np.random.choice(n, zero_count, replace=False)
        vol[indices] = 0.0

    return pd.DataFrame({
        "Open": opn, "High": high, "Low": low, "Close": close, "Volume": vol,
    })


def test_full_tier():
    """Good data -> FULL tier, confidence >= 65."""
    dg = DataGuard()
    df = make_df(200, broken=0)
    r = dg.evaluate(df, "TEST_GOOD")
    assert r.passed, f"Expected passed=True, got {r}"
    assert r.confidence_tier == "FULL", f"Expected FULL, got {r.confidence_tier}"
    assert r.confidence >= 65.0, f"Expected conf>=65, got {r.confidence:.1f}"
    print(f"  PASS FULL tier: conf={r.confidence:.1f}, reason={r.reason}")


def test_degraded_tier():
    """Moderate data issues -> DEGRADED (40-64)."""
    dg = DataGuard()
    df = make_df(100, broken=5, zero_vol_pct=0.15)
    r = dg.evaluate(df, "TEST_DEGRADED")
    print(f"  INFO Result: conf={r.confidence:.1f}, tier={r.confidence_tier}, reason={r.reason}")
    assert r.passed, f"Expected passed=True, got {r}"


def test_rejected_tier():
    """Severely broken data -> REJECTED (conf < 40)."""
    dg = DataGuard()
    df = make_df(30, broken=8, zero_vol_pct=0.5)
    r = dg.evaluate(df, "TEST_REJECTED")
    print(f"  INFO Result: conf={r.confidence:.1f}, tier={r.confidence_tier}, reason={r.reason}")
    assert not r.passed, f"Expected passed=False, got {r}"
    assert r.confidence_tier == "REJECTED", f"Expected REJECTED, got {r.confidence_tier}"
    print(f"  PASS REJECTED tier: conf={r.confidence:.1f}")


def test_empty_dataframe():
    """Empty DF -> REJECTED."""
    dg = DataGuard()
    df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    r = dg.evaluate(df, "TEST_EMPTY")
    assert not r.passed, "Empty DF should be REJECTED"
    assert r.confidence_tier == "REJECTED"
    print(f"  PASS Empty DF: tier={r.confidence_tier}, conf={r.confidence:.1f}")


def test_zero_volume():
    """All-zero volume -> should penalise heavily."""
    dg = DataGuard()
    df = make_df(200, broken=0, zero_vol_pct=1.0)
    r = dg.evaluate(df, "TEST_ZEROVOL")
    print(f"  INFO All-zero vol: conf={r.confidence:.1f}, tier={r.confidence_tier}")
    assert r.confidence < 80, f"Expected reduced confidence, got {r.confidence:.1f}"
    print(f"  PASS Zero-vol penalised: conf={r.confidence:.1f}")


def test_result_is_namedtuple():
    """DataGuardResult has all expected fields."""
    dg = DataGuard()
    df = make_df(200)
    r = dg.evaluate(df, "TEST_FIELDS")
    assert hasattr(r, "passed")
    assert hasattr(r, "confidence")
    assert hasattr(r, "confidence_tier")
    assert hasattr(r, "reason")
    assert isinstance(r, DataGuardResult)
    print(f"  PASS NamedTuple structure correct")


if __name__ == "__main__":
    print("\nDataGuard Verification Tests")
    print("=" * 40)

    tests = [
        ("FULL tier (good data)", test_full_tier),
        ("DEGRADED tier (moderate issues)", test_degraded_tier),
        ("REJECTED tier (bad data)", test_rejected_tier),
        ("Empty DataFrame", test_empty_dataframe),
        ("Zero volume", test_zero_volume),
        ("NamedTuple structure", test_result_is_namedtuple),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n> {name}")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
