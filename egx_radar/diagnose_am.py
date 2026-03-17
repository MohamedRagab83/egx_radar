"""Quick diagnostic: compute what AlphaMonitor sees for a synthetic 30% winrate dataset."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from egx_radar.core.alpha_monitor import AlphaMonitor
from egx_radar.config.settings import K

# Simulate trade set matching Backtest B: ~30% win rate, avg +9% win, avg -4% loss
# 47 trades: 14 wins (+9% each), 33 losses (-4% each)
trades = []
for i in range(14):
    trades.append({"pnl_pct": 9.0, "outcome": "WIN", "setup_type": "buy"})
for i in range(33):
    trades.append({"pnl_pct": -4.0, "outcome": "LOSS", "setup_type": "buy"})

am = AlphaMonitor()
result = am.evaluate_from_trades(trades)

print(f"Warning level: {result.warning_level}")
print(f"Flags: {result.flags}")
print(f"Message: {result.message}")
print()
print(f"K.AM_MIN_TRADES       = {K.AM_MIN_TRADES}")
print(f"K.AM_LEVEL1_WINRATE   = {K.AM_LEVEL1_WINRATE}")
print(f"K.AM_LEVEL2_WINRATE   = {K.AM_LEVEL2_WINRATE}")
print(f"K.AM_LEVEL1_SHARPE    = {K.AM_LEVEL1_SHARPE}")
print(f"K.AM_LEVEL2_SHARPE    = {K.AM_LEVEL2_SHARPE}")
print(f"K.AM_LEVEL3_SHARPE    = {K.AM_LEVEL3_SHARPE}")
print(f"K.AM_LEVEL1_EXPECTANCY= {K.AM_LEVEL1_EXPECTANCY}")
print(f"K.AM_LEVEL3_EXPECTANCY= {K.AM_LEVEL3_EXPECTANCY}")
print()
m20 = result.metrics_20
print(f"metrics_20['win_rate']   = {m20.get('win_rate')}")
print(f"metrics_20['sharpe']     = {m20.get('sharpe')}")
print(f"metrics_20['expectancy'] = {m20.get('expectancy')}")

print()  
print("--- Checking conditions ---")
wr_20  = m20.get("win_rate", 0)
sh_20  = m20.get("sharpe", 0)
exp_20 = m20.get("expectancy", 0)
print(f"Level3: sh_20({sh_20:.4f}) <= AM_LEVEL3_SHARPE({K.AM_LEVEL3_SHARPE}) ? {sh_20 <= K.AM_LEVEL3_SHARPE}")
print(f"Level3: exp_20({exp_20:.4f}) < AM_LEVEL3_EXPECTANCY({K.AM_LEVEL3_EXPECTANCY}) ? {exp_20 < K.AM_LEVEL3_EXPECTANCY}")
print(f"Level2: sh_20({sh_20:.4f}) < AM_LEVEL2_SHARPE({K.AM_LEVEL2_SHARPE}) ? {sh_20 < K.AM_LEVEL2_SHARPE}")
print(f"Level2: wr_20({wr_20:.4f}) < AM_LEVEL2_WINRATE({K.AM_LEVEL2_WINRATE}) ? {wr_20 < K.AM_LEVEL2_WINRATE}")
print(f"Level1: sh_20({sh_20:.4f}) < AM_LEVEL1_SHARPE({K.AM_LEVEL1_SHARPE}) ? {sh_20 < K.AM_LEVEL1_SHARPE}")
print(f"Level1: wr_20({wr_20:.4f}) < AM_LEVEL1_WINRATE({K.AM_LEVEL1_WINRATE}) ? {wr_20 < K.AM_LEVEL1_WINRATE}")
print(f"Level1: exp_20({exp_20:.4f}) < AM_LEVEL1_EXPECTANCY({K.AM_LEVEL1_EXPECTANCY}) ? {exp_20 < K.AM_LEVEL1_EXPECTANCY}")
