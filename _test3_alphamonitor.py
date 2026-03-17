import sys; sys.path.insert(0, '.')
from egx_radar.core.alpha_monitor import AlphaMonitor
am = AlphaMonitor()
status = am.evaluate()
print(f'Warning level : {status.warning_level}')
print(f'Message       : {status.message}')
print(f'Position scale: {status.position_scale}')
print(f'Metrics 20    : {status.metrics_20}')
print(f'Flags         : {status.flags}')
