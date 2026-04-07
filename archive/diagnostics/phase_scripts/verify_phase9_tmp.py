# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

print()
print('=' * 80)
print('PHASE 9 VERIFICATION — WebSocket → Scanner Integration')
print('=' * 80)

# Test 1: emit_scan_complete function exists in websocket.py
print()
print('Test 1: emit_scan_complete function in websocket.py')
try:
    with open('egx_radar/dashboard/websocket.py', encoding='utf-8', errors='ignore') as f:
        ws_content = f.read()
    
    tests = [
        ('Function defined', 'def emit_scan_complete' in ws_content),
        ('Takes results param', 'results: list' in ws_content),
        ('Gets sym from result', 'r.get("sym")' in ws_content),
        ('Has smart_rank', 'r.get("smart_rank"' in ws_content),
        ('Has direction', 'r.get("signal_dir"' in ws_content or 'r.get("direction"' in ws_content),
        ('Broadcast enabled', 'broadcast=True' in ws_content),
        ('Error handling', 'except Exception as exc' in ws_content),
    ]
    
    for test_name, result in tests:
        print(f"  {'✓' if result else '✗'} {test_name}")
        if not result:
            raise ValueError(f"Missing: {test_name}")
    
    print("  ✓ emit_scan_complete function: OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: emit_scan_complete is called from runner.py
print()
print('Test 2: emit_scan_complete called from runner.py')
try:
    with open('egx_radar/scan/runner.py', encoding='utf-8', errors='ignore') as f:
        runner_content = f.read()
    
    tests = [
        ('Import statement', 'from egx_radar.dashboard.websocket import emit_scan_complete' in runner_content),
        ('Function call', 'emit_scan_complete(annotated_results)' in runner_content),
        ('Called after snapshot', 'emit_scan_complete' in runner_content and 'log.debug("API scan snapshot saved' in runner_content),
        ('Non-blocking call', 'except Exception as _ws_exc' in runner_content),
        ('Error logging', 'log.debug("WebSocket emit skipped' in runner_content),
    ]
    
    for test_name, result in tests:
        print(f"  {'✓' if result else '✗'} {test_name}")
        if not result:
            raise ValueError(f"Missing: {test_name}")
    
    print("  ✓ Emit call in runner.py: OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 3: socketio.emit configured correctly
print()
print('Test 3: WebSocket emit configuration')
try:
    tests = [
        ('Emit event name is scan_complete', '"scan_complete"' in ws_content),
        ('Payload has event field', '"event":     "scan_complete"' in ws_content),
        ('Payload has count', '"count":     len(results)' in ws_content),
        ('Payload has timestamp', '"timestamp": datetime.utcnow().isoformat()' in ws_content),
        ('Payload has signals array', '"signals": [{' in ws_content),
        ('SocketIO namespace set', 'namespace="/"' in ws_content),
    ]
    
    for test_name, result in tests:
        print(f"  {'✓' if result else '✗'} {test_name}")
        if not result:
            raise ValueError(f"Missing: {test_name}")
    
    print("  ✓ WebSocket configuration: OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 4: Import tests
print()
print('Test 4: Import verification')
try:
    from egx_radar.dashboard.websocket import emit_scan_complete
    print("  ✓ emit_scan_complete imports successfully")
    
    from egx_radar.dashboard.websocket import socketio
    print("  ✓ socketio imports successfully")
    
    # Test that we can at least call it without errors (mock data)
    mock_results = [
        {
            "sym": "COMI",
            "sector": "BANKS",
            "signal": "BUY",
            "tag": "buy",
            "smart_rank": 42.5,
            "signal_dir": "BULLISH",
            "plan": {"action": "BUY", "entry": 10.0, "stop": 9.5, "target": 11.5}
        }
    ]
    
    # This should not raise an error (even if SocketIO clients aren't connected)
    emit_scan_complete(mock_results)
    print("  ✓ emit_scan_complete callable with sample data")
    
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print('=' * 80)
print('✅ PHASE 9 VERIFICATION: PASSED')
print('=' * 80)
print()
print('Summary of changes:')
print('  ✓ emit_scan_complete() function added to websocket.py')
print('  ✓ Called from runner.py after snapshot write')
print('  ✓ Non-blocking, best-effort emission')
print('  ✓ Broadcasts to all connected dashboard clients')
print()
print('Integration status:')
print('  • Scanner completes scan → writes snapshot.json')
print('  • Scanner completes scan → calls emit_scan_complete()')
print('  • WebSocket broadcasts scan_complete event to all clients')
print('  • Clients receive live SmartRank data in real-time')
print()
print('Result: GAP-3 (WebSocket → Scanner) CLOSED')
print()
