from egx_radar.core.indicators import sharpe_from_trades
from egx_radar.core.alpha_monitor import AlphaMonitor

# Test 1: Formula sanity check
returns = [5.0, -2.0, 3.0, -1.5, 4.0, -2.5, 2.0, -1.0, 3.5, -2.0,
           4.5, -1.5, 2.5, -2.0, 1.5, -3.0, 5.0, -1.0, 3.0, -2.5]
sharpe = sharpe_from_trades(returns)
assert 0.2 <= sharpe <= 2.0, f"Sharpe {sharpe} outside realistic range"
print(f"DONE sharpe_from_trades: {sharpe:.3f} (realistic)")

# Test 2: AlphaMonitor triggers Level 1 warning with poor trades
poor_trades = [
    {"pnl_pct": -3.0, "setup_type": "breakout"} for _ in range(15)
] + [
    {"pnl_pct": 2.0, "setup_type": "breakout"} for _ in range(5)
]
am = AlphaMonitor()
status = am.evaluate_from_trades(poor_trades)
assert status.warning_level >= 1, f"Expected warning, got level {status.warning_level}"
print(f"DONE AlphaMonitor Level {status.warning_level} warning triggered correctly")

print("ALL TESTS PASSED")
