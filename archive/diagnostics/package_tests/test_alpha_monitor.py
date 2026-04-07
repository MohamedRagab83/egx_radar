"""Verification tests for AlphaMonitor (Module 3)."""

import sys, os, json, tempfile, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def _make_trade(pnl_pct, setup_type="buy", status="WIN", sym="TEST"):
    """Helper: create a minimal resolved trade dict."""
    return {
        "sym": sym,
        "sector": "BANKS",
        "date": "2026-01-01",
        "entry": 10.0,
        "stop": 9.5,
        "target": 11.0,
        "atr": 0.5,
        "smart_rank": 20.0,
        "anticipation": 0.5,
        "action": "PROBE",
        "status": status,
        "setup_type": setup_type,
        "exit_price": 10.5 if pnl_pct > 0 else 9.5,
        "pnl_pct": pnl_pct,
        "stop_hit": status == "LOSS",
        "resolved_date": "2026-01-10",
        "days_held": 5,
    }


def _with_history(trades, test_fn):
    """Run test_fn with a temporary history file."""
    from egx_radar.config.settings import K
    original = K.OUTCOME_HISTORY_FILE
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(trades, f)
            tmp_path = f.name
        K.OUTCOME_HISTORY_FILE = tmp_path
        test_fn()
    finally:
        K.OUTCOME_HISTORY_FILE = original
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
# Test 1: Empty history → warning_level=0, flag INSUFFICIENT_TRADES
# ═══════════════════════════════════════════════════════════════════
def test_1_empty_history():
    from egx_radar.core.alpha_monitor import AlphaMonitor

    def run():
        am = AlphaMonitor()
        status = am.evaluate()
        assert status.warning_level == 0, f"Expected level=0, got {status.warning_level}"
        assert status.position_scale == 1.0, f"Expected scale=1.0, got {status.position_scale}"
        assert status.pause_new_entries is False
        has_flag = ("INSUFFICIENT_TRADES" in status.flags or "NO_HISTORY_FILE" in status.flags)
        assert has_flag, f"Expected INSUFFICIENT_TRADES or NO_HISTORY_FILE, got {status.flags}"
        print(f"✅ Test 1 PASSED — Empty history: level={status.warning_level}, flags={status.flags}")

    _with_history([], run)


# ═══════════════════════════════════════════════════════════════════
# Test 2: 20 trades all losses → warning_level=3, pause=True
# ═══════════════════════════════════════════════════════════════════
def test_2_all_losses():
    from egx_radar.core.alpha_monitor import AlphaMonitor

    trades = [_make_trade(pnl_pct=-2.0, status="LOSS") for _ in range(20)]

    def run():
        am = AlphaMonitor()
        status = am.evaluate()
        assert status.warning_level == 3, f"Expected level=3, got {status.warning_level}"
        assert status.position_scale == 0.0, f"Expected scale=0.0, got {status.position_scale}"
        assert status.rank_threshold_boost == 10, f"Expected boost=10, got {status.rank_threshold_boost}"
        assert status.pause_new_entries is True, f"Expected pause=True, got {status.pause_new_entries}"
        assert status.metrics_20["win_rate"] == 0.0
        print(f"✅ Test 2 PASSED — All losses: level={status.warning_level}, pause={status.pause_new_entries}, "
              f"sharpe={status.metrics_20['sharpe']}")

    _with_history(trades, run)


# ═══════════════════════════════════════════════════════════════════
# Test 3: 20 trades mixed (60% win, avg_win=5%, avg_loss=2%) → level=0
# ═══════════════════════════════════════════════════════════════════
def test_3_healthy_trades():
    from egx_radar.core.alpha_monitor import AlphaMonitor

    trades = (
        [_make_trade(pnl_pct=5.0, status="WIN") for _ in range(12)] +
        [_make_trade(pnl_pct=-2.0, status="LOSS") for _ in range(8)]
    )

    def run():
        am = AlphaMonitor()
        status = am.evaluate()
        m20 = status.metrics_20
        assert abs(m20["win_rate"] - 0.60) < 0.01, f"Expected WR~0.60, got {m20['win_rate']}"
        assert abs(m20["avg_win"] - 5.0) < 0.01, f"Expected avg_win~5.0, got {m20['avg_win']}"
        assert abs(m20["avg_loss"] - 2.0) < 0.01, f"Expected avg_loss~2.0, got {m20['avg_loss']}"
        expected_exp = (0.6 * 5.0) - (0.4 * 2.0)  # 3.0 - 0.8 = 2.2
        assert abs(m20["expectancy"] - expected_exp) < 0.1, f"Expected exp~{expected_exp}, got {m20['expectancy']}"
        assert status.warning_level == 0, f"Expected level=0, got {status.warning_level}"
        assert status.position_scale == 1.0
        assert status.pause_new_entries is False
        print(f"✅ Test 3 PASSED — Healthy trades: level={status.warning_level}, WR={m20['win_rate']}, "
              f"exp={m20['expectancy']}, sharpe={m20['sharpe']}")

    _with_history(trades, run)


# ═══════════════════════════════════════════════════════════════════
# Test 4: setup_breakdown groups correctly by setup_type
# ═══════════════════════════════════════════════════════════════════
def test_4_setup_breakdown():
    from egx_radar.core.alpha_monitor import AlphaMonitor

    trades = (
        [_make_trade(pnl_pct=4.0, setup_type="ultra", status="WIN") for _ in range(5)] +
        [_make_trade(pnl_pct=-1.0, setup_type="ultra", status="LOSS") for _ in range(2)] +
        [_make_trade(pnl_pct=2.0, setup_type="early", status="WIN") for _ in range(3)] +
        [_make_trade(pnl_pct=-3.0, setup_type="early", status="LOSS") for _ in range(5)]
    )

    def run():
        am = AlphaMonitor()
        status = am.evaluate()
        sb = status.setup_breakdown
        assert "ultra" in sb, f"Missing 'ultra' in breakdown: {sb}"
        assert "early" in sb, f"Missing 'early' in breakdown: {sb}"
        assert sb["ultra"]["n"] == 7, f"Expected ultra n=7, got {sb['ultra']['n']}"
        assert sb["early"]["n"] == 8, f"Expected early n=8, got {sb['early']['n']}"
        assert abs(sb["ultra"]["win_rate"] - 5/7) < 0.01, f"Expected ultra WR~0.714, got {sb['ultra']['win_rate']}"
        assert abs(sb["early"]["win_rate"] - 3/8) < 0.01, f"Expected early WR~0.375, got {sb['early']['win_rate']}"
        print(f"✅ Test 4 PASSED — Setup breakdown: ultra={sb['ultra']}, early={sb['early']}")

    _with_history(trades, run)


# ═══════════════════════════════════════════════════════════════════
# Run all
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION: Alpha Monitor (Module 3)")
    print("=" * 60)
    test_1_empty_history()
    test_2_all_losses()
    test_3_healthy_trades()
    test_4_setup_breakdown()
    print()
    print("=" * 60)
    print("ALL 4 ALPHA MONITOR TESTS PASSED ✅")
    print("=" * 60)
