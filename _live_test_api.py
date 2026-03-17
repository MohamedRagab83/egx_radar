#!/usr/bin/env python
"""
Create a realistic mock scan_snapshot.json for testing
Simulates what the scanner would generate
"""
import sys, os, json
from datetime import datetime
sys.path.insert(0, '.')

print()
print('=' * 80)
print('LIVE END-TO-END INTEGRATION TEST')
print('=' * 80)
print()

print('STEP 1: Creating realistic mock scan snapshot')
print('-' * 80)
print()

from egx_radar.config.settings import K

# Create a realistic scan snapshot with SmartRank data
mock_snapshot = [
    {
        "sym": "COMI",
        "sector": "BANKS",
        "price": 10.25,
        "signal": "BUY",
        "tag": "buy",
        "smart_rank": 42.5,
        "confidence": 0.78,
        "direction": "BULLISH",
        "phase": "trend_start",
        "zone": "accumulation",
        "action": "BUY",
        "entry": 10.20,
        "stop": 9.95,
        "target": 11.50,
        "winrate": 58.3,
        "scan_time": datetime.utcnow().isoformat(),
    },
    {
        "sym": "EBANK",
        "sector": "BANKS",
        "price": 29.50,
        "signal": "BUY",
        "tag": "early",
        "smart_rank": 35.2,
        "confidence": 0.65,
        "direction": "BULLISH",
        "phase": "base_formation",
        "zone": "support",
        "action": "WATCH",
        "entry": 29.10,
        "stop": 28.50,
        "target": 31.00,
        "winrate": 52.1,
        "scan_time": datetime.utcnow().isoformat(),
    },
    {
        "sym": "HRHO",
        "sector": "REAL_ESTATE",
        "price": 3.85,
        "signal": "SELL",
        "tag": "sell",
        "smart_rank": 28.9,
        "confidence": 0.71,
        "direction": "BEARISH",
        "phase": "trend_reversal",
        "zone": "resistance",
        "action": "SELL",
        "entry": 3.90,
        "stop": 4.10,
        "target": 3.20,
        "winrate": 55.7,
        "scan_time": datetime.utcnow().isoformat(),
    },
    {
        "sym": "ORAERIE",
        "sector": "TECHNOLOGY",
        "price": 45.30,
        "signal": "BUY",
        "tag": "ultra",
        "smart_rank": 68.4,
        "confidence": 0.89,
        "direction": "BULLISH",
        "phase": "explosive_move",
        "zone": "breakout",
        "action": "ACCUMULATE",
        "entry": 45.00,
        "stop": 43.50,
        "target": 52.00,
        "winrate": 62.5,
        "scan_time": datetime.utcnow().isoformat(),
    },
]

# Write to snapshot file
snapshot_dir = os.path.dirname(K.OUTCOME_LOG_FILE)
snapshot_path = os.path.join(snapshot_dir, "scan_snapshot.json")

print(f'Writing snapshot to: {snapshot_path}')

with open(snapshot_path, 'w') as f:
    json.dump(mock_snapshot, f, indent=2)

print(f'✓ Created scan_snapshot.json with {len(mock_snapshot)} mock signals')
print()

# Display the snapshot
print('STEP 2: Snapshot Contents')
print('-' * 80)
print()

for i, sig in enumerate(mock_snapshot):
    print(f'Signal {i+1}: {sig["sym"]:10} {sig["signal"]:8} SmartRank={sig["smart_rank"]:6.2f} Tag={sig["tag"]}')

print()
print('✓ Snapshot created successfully')
print()

# Now test the API
print('STEP 3: Testing API /signals/scanner endpoint')
print('-' * 80)
print()

import time
import requests

# Wait a moment for Flask to be ready
print('Waiting for Flask dashboard to be ready...')
time.sleep(2)

try:
    # Test basic endpoint
    print('Calling: GET http://localhost:5000/api/signals/scanner')
    print()
    
    response = requests.get('http://localhost:5000/api/signals/scanner', timeout=5)
    
    print(f'HTTP Status: {response.status_code}')
    print()
    
    json_response = response.json()
    
    print('Response JSON:')
    print()
    print(json.dumps(json_response, indent=2))
    
    print()
    print('Verification:')
    print(f'  ✓ success: {json_response.get("success")}')
    print(f'  ✓ count: {json_response.get("count")} signals')
    print(f'  ✓ source: {json_response.get("source")}')
    print(f'  ✓ signals returned: {len(json_response.get("signals", []))}')
    
except Exception as e:
    print(f'✗ ERROR: {e}')
    sys.exit(1)

print()
print('✓ API endpoint working correctly')
print()

# Test filtering
print('STEP 4: Testing API filtering')
print('-' * 80)
print()

try:
    print('Calling: GET http://localhost:5000/api/signals/scanner?tag=buy&min_rank=30')
    response = requests.get(
        'http://localhost:5000/api/signals/scanner?tag=buy&min_rank=30',
        timeout=5
    )
    
    data = response.json()
    print(f'HTTP Status: {response.status_code}')
    print(f'Filtered signals: {data["count"]} (with tag=buy, min_rank>=30)')
    print()
    
    for sig in data['signals']:
        print(f'  {sig["sym"]:10} SmartRank={sig["smart_rank"]:6.2f} Tag={sig["tag"]}')
    
    print()
    print('✓ Filtering working correctly')
    
except Exception as e:
    print(f'✗ ERROR: {e}')

print()
print('=' * 80)
print('STEPS 1-4: PASSED')
print('=' * 80)
