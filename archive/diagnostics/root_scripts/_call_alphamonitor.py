import sys; sys.path.insert(0, '.')

print("=" * 80)
print("STEP 5: Call AlphaMonitor.evaluate() and show output")
print("=" * 80)
print()

from egx_radar.core.alpha_monitor import AlphaMonitor
from egx_radar.config.settings import K

print("Configuration thresholds:")
print("  AM_MIN_TRADES        = {} (minimum before warnings)".format(K.AM_MIN_TRADES))
print("  AM_LEVEL1_SHARPE     = {} (Sharpe threshold for Level 1)".format(K.AM_LEVEL1_SHARPE))
print("  AM_LEVEL2_SHARPE     = {} (Sharpe threshold for Level 2)".format(K.AM_LEVEL2_SHARPE))
print("  AM_LEVEL3_SHARPE     = {} (Sharpe threshold for Level 3)".format(K.AM_LEVEL3_SHARPE))
print("  AM_LEVEL1_EXPECTANCY = {} (Expectancy threshold for Level 1)".format(K.AM_LEVEL1_EXPECTANCY))
print("  AM_LEVEL1_WINRATE    = {} (WinRate threshold for Level 1)".format(K.AM_LEVEL1_WINRATE))
print("  AM_LEVEL2_WINRATE    = {} (WinRate threshold for Level 2)".format(K.AM_LEVEL2_WINRATE))
print("  AM_LEVEL3_EXPECTANCY = {} (Expectancy threshold for Level 3)".format(K.AM_LEVEL3_EXPECTANCY))
print()

print("-" * 80)
print("Creating AlphaMonitor instance...")
print("-" * 80)
print()

monitor = AlphaMonitor()
history = monitor.load_history()

print("load_history() returned: {} trades".format(len(history)))
print()

if len(history) > 0:
    print("First 3 trades loaded:")
    for i, t in enumerate(history[:3], 1):
        print("  {}. sym={} pnl_pct={} status={}".format(
            i, t.get('sym'), t.get('pnl_pct'), t.get('status')))
    print()

print("-" * 80)
print("Calling monitor.evaluate()...")
print("-" * 80)
print()

status = monitor.evaluate()

print("RESULT: AlphaStatus object")
print()
print("  warning_level      : {}".format(status.warning_level))
print("  position_scale     : {}".format(status.position_scale))
print("  rank_threshold_boost : {}".format(status.rank_threshold_boost))
print("  pause_new_entries  : {}".format(status.pause_new_entries))
print("  stability_score    : {}".format(status.stability_score))
print("  message            : {}".format(status.message))
print("  flags              : {}".format(status.flags))
print()

print("-" * 80)
print("metrics_20 (last 20 trades):")
print("-" * 80)
print()

if status.metrics_20:
    for key, val in sorted(status.metrics_20.items()):
        if isinstance(val, float):
            print("  {:<20} : {:.4f}".format(key, val))
        else:
            print("  {:<20} : {}".format(key, val))
else:
    print("  (empty - insufficient trades)")

print()
print("-" * 80)
print("metrics_50 (last 50 trades):")
print("-" * 80)
print()

if status.metrics_50:
    for key, val in sorted(status.metrics_50.items()):
        if isinstance(val, float):
            print("  {:<20} : {:.4f}".format(key, val))
        else:
            print("  {:<20} : {}".format(key, val))
else:
    print("  (empty - insufficient trades)")

print()
print("-" * 80)
print("setup_breakdown (by setup type):")
print("-" * 80)
print()

if status.setup_breakdown:
    for setup, metrics in sorted(status.setup_breakdown.items()):
        print("  {}:".format(setup))
        for key, val in metrics.items():
            if isinstance(val, float):
                print("    {:<20} : {:.4f}".format(key, val))
            else:
                print("    {:<20} : {}".format(key, val))
else:
    print("  (empty)")

print()
