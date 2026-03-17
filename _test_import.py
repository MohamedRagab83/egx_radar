import sys, os
sys.path.insert(0, os.path.dirname(__file__))
try:
    from egx_radar.config.settings import K
    print("OK: SR =", K.BT_MIN_SMARTRANK)
except Exception as e:
    print("FAIL:", e)
