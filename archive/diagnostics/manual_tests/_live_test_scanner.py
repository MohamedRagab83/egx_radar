#!/usr/bin/env python
"""
Live end-to-end integration test
Step 1: Trigger a scan and verify snapshot
"""
import sys, os, json, time
sys.path.insert(0, '.')

print()
print('=' * 80)
print('LIVE END-TO-END INTEGRATION TEST')
print('=' * 80)
print()

print('STEP 1: Triggering scanner...')
print('-' * 80)

# Import scanner 
from egx_radar.scan.runner import run_scan
from egx_radar.config.settings import K
import threading

# Create a minimal widgets dict for run_scan
widgets = {
    'scan_btn': type('obj', (object,), {'configure': lambda **kw: None})(),
    'status_var': type('obj', (object,), {'set': lambda msg: print(f'[SCANNER] {msg}')})(),
}

print('Starting scan in background thread...')
print()

scan_thread = threading.Thread(target=run_scan, args=(widgets,), daemon=False)
scan_thread.start()

print('Waiting for scan to complete (max 60 seconds)...')
print()

# Wait for scan to complete
scan_thread.join(timeout=60)

if scan_thread.is_alive():
    print('✗ Scan did not complete within timeout')
    sys.exit(1)

print()
print('✓ Scan completed')
print()

# STEP 2: Check if snapshot was written
print('STEP 2: Checking scan_snapshot.json')
print('-' * 80)
print()

snapshot_path = os.path.join(
    os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
)

print(f'Looking for: {snapshot_path}')
print()

if os.path.exists(snapshot_path):
    print('✓ scan_snapshot.json found')
    
    # Read and display snapshot
    with open(snapshot_path) as f:
        snapshot = json.load(f)
    
    print(f'✓ Snapshot contains {len(snapshot)} signals')
    print()
    print('Sample signals (first 3):')
    print()
    
    for i, sig in enumerate(snapshot[:3]):
        print(f'  Signal {i+1}:')
        print(f'    Symbol: {sig.get("sym")}')
        print(f'    Sector: {sig.get("sector")}')
        print(f'    Signal: {sig.get("signal")}')
        print(f'    Tag: {sig.get("tag")}')
        print(f'    SmartRank: {sig.get("smart_rank"):.2f}')
        print(f'    Direction: {sig.get("direction")}')
        print(f'    Action: {sig.get("action")}')
        print(f'    Entry: {sig.get("entry"):.4f}')
        print(f'    Stop: {sig.get("stop"):.4f}')
        print(f'    Target: {sig.get("target"):.4f}')
        print()
    
    print(f'All signals in snapshot:')
    for sig in snapshot:
        print(f'  {sig.get("sym"):8} {sig.get("signal"):8} SmartRank={sig.get("smart_rank"):6.2f}  Tag={sig.get("tag")}')
    
else:
    print('✗ scan_snapshot.json NOT found')
    print(f'Expected at: {snapshot_path}')
    sys.exit(1)

print()
print('=' * 80)
print('STEP 1-2: PASSED')
print('=' * 80)
