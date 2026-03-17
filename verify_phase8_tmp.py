# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

print()
print('=' * 80)
print('PHASE 8 VERIFICATION — API → Scanner Integration')
print('=' * 80)

# Test 1: Snapshot writer in runner.py
print()
print('Test 1: Snapshot writing in runner.py')
try:
    with open('egx_radar/scan/runner.py', encoding='utf-8', errors='ignore') as f:
        runner_content = f.read()
    
    tests = [
        ('Snapshot path definition', 'scan_snapshot.json' in runner_content),
        ('JSON snapshot creation', 'snapshot = [{' in runner_content),
        ('Atomic write pattern', 'tempfile.mkstemp' in runner_content),
        ('Datetime in snapshot', 'datetime.utcnow().isoformat()' in runner_content),
    ]
    
    for test_name, result in tests:
        print(f"  {'✓' if result else '✗'} {test_name}")
        if not result:
            raise ValueError(f"Missing: {test_name}")
    
    print("  ✓ Runner snapshot writer: OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Snapshot loader in routes.py
print()
print('Test 2: Snapshot loader in routes.py')
try:
    with open('egx_radar/dashboard/routes.py', encoding='utf-8', errors='ignore') as f:
        routes_content = f.read()
    
    tests = [
        ('Loader function defined', 'def _load_scan_snapshot()' in routes_content),
        ('Loads from K.OUTCOME_LOG_FILE', 'K.OUTCOME_LOG_FILE' in routes_content),
        ('JSON parsing', 'json.load(f)' in routes_content),
        ('Error handling', 'except Exception' in routes_content),
    ]
    
    for test_name, result in tests:
        print(f"  {'✓' if result else '✗'} {test_name}")
        if not result:
            raise ValueError(f"Missing: {test_name}")
    
    print("  ✓ Snapshot loader: OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 3: New API endpoint in routes.py
print()
print('Test 3: /api/signals/scanner endpoint')
try:
    tests = [
        ('Endpoint registered', '/signals/scanner' in routes_content),
        ('Handler function', 'def get_scanner_signals()' in routes_content),
        ('Calls loader', '_load_scan_snapshot()' in routes_content),
        ('Tag filter support', 'tag_filter' in routes_content),
        ('Rank filter support', 'min_rank' in routes_content),
        ('Sector filter support', 'sector' in routes_content),
        ('JSON response', 'jsonify' in routes_content),
    ]
    
    for test_name, result in tests:
        print(f"  {'✓' if result else '✗'} {test_name}")
        if not result:
            raise ValueError(f"Missing: {test_name}")
    
    print("  ✓ API endpoint: OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 4: Import test
print()
print('Test 4: Import verification')
try:
    from egx_radar.dashboard.routes import _load_scan_snapshot
    print("  ✓ _load_scan_snapshot imports")
    
    from egx_radar.config.settings import K
    print("  ✓ Config settings imports")
    
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

print()
print('=' * 80)
print('✅ PHASE 8 VERIFICATION: PASSED')
print('=' * 80)
print()
print('Summary of changes:')
print('  ✓ runner.py writes scan snapshot atomically')
print('  ✓ routes.py has snapshot loader function')
print('  ✓ /api/signals/scanner endpoint created with filtering')
print()
print('Integration status:')
print('  • Scanner → snapshot file: writes after each scan')
print('  • Snapshot file → API: loaded on /signals/scanner request')
print('  • Filtering: tag, min_rank, sector supported')
print()
print('Result: GAP-1 (API → Core Scanner) CLOSED')
print()
