"""End-to-end test of the Trade Tracking Dashboard using real CSV data."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from egx_radar.backtest.tracking_dashboard import run_dashboard

print("=" * 60)
print("TEST 1: Full backtest CSV (backtest_SR0.csv — ~930 trades)")
print("=" * 60)

result = run_dashboard(csv_path="backtest_SR0.csv", print_report=True)

print("\n\n")
print("=" * 60)
print("TEST 2: Smaller CSV (backtest_SR20.csv)")
print("=" * 60)

result2 = run_dashboard(csv_path="backtest_SR20.csv", print_report=True)

print("\n\n")
print("=" * 60)
print("TEST 3: Empty trades (edge case)")
print("=" * 60)

result3 = run_dashboard(trades=[], print_report=True)

print("\n\n=== ALL TESTS COMPLETE ===")
print(f"Test 1: {result['verdict']['verdict']} (health={result['health_score']})")
print(f"Test 2: {result2['verdict']['verdict']} (health={result2['health_score']})")
print(f"Test 3: {result3['verdict']['verdict']} (health={result3['health_score']})")
