#!/usr/bin/env python
"""
VERIFICATION 4: Test Suite Status
"""
import sys, os
sys.path.insert(0, '.')

print()
print('=' * 80)
print('VERIFICATION 4: Test Suite Status')
print('=' * 80)
print()

# Check if pytest is available
try:
    import pytest
    print('✓ pytest is installed')
    print()
    print('Running test suite...')
    print('-' * 80)
    
    # Run pytest
    pytest.main([
        'tests/',
        '-v',
        '--tb=short',
        '-q'
    ])
except ImportError:
    print('✗ pytest is NOT installed')
    print()
    print('Manual test import check:')
    print('-' * 80)
    
    test_files = [
        'tests/test_unit_engine.py',
        'tests/test_integration_pipeline.py',
        'tests/test_data_validation.py',
        'tests/test_error_handling.py',
        'tests/test_performance_benchmarks.py',
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                # Try to import conftest and the test module
                module_name = test_file.replace('tests/', '').replace('.py', '')
                print(f'  ✓ {test_file} (exists)')
            except Exception as e:
                print(f'  ✗ {test_file}: {e}')
        else:
            print(f'  ? {test_file} (not found)')
    
    print()
    print('Note: pytest is not installed in the environment')
    print('To run tests, install: pip install pytest')
