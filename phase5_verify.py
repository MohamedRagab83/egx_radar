#!/usr/bin/env python
"""Phase 5: Testing & Infrastructure Verification."""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def verify_test_infrastructure():
    """Verify all testing infrastructure is in place."""
    print("\n" + "=" * 70)
    print("PHASE 5: TESTING & INFRASTRUCTURE VERIFICATION")
    print("=" * 70)
    
    checks = {
        'pytest_config': False,
        'test_suite': False,
        'ci_cd': False,
        'data_validation': False,
        'error_handling': False,
    }
    
    # Check 1: Pytest configuration
    print("\n✓ Checking pytest configuration...")
    if os.path.exists('pytest.ini'):
        with open('pytest.ini', 'r') as f:
            content = f.read()
            if 'testpaths = tests' in content:
                print("  ✓ pytest.ini configured")
                checks['pytest_config'] = True
    
    # Check 2: Test suite structure
    print("\n✓ Checking test suite...")
    test_files = [
        'tests/conftest.py',
        'tests/test_unit_engine.py',
        'tests/test_integration_pipeline.py',
        'tests/test_performance_benchmarks.py',
        'tests/test_data_validation.py',
        'tests/test_error_handling.py',
    ]
    
    missing_tests = []
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"  ✓ {test_file}")
        else:
            print(f"  ✗ {test_file} (MISSING)")
            missing_tests.append(test_file)
    
    if not missing_tests:
        checks['test_suite'] = True
    
    # Check 3: CI/CD configuration
    print("\n✓ Checking CI/CD pipeline...")
    if os.path.exists('.github/workflows/ci.yml'):
        with open('.github/workflows/ci.yml', 'r') as f:
            content = f.read()
            if 'pytest' in content:
                print("  ✓ .github/workflows/ci.yml configured")
                checks['ci_cd'] = True
    
    # Check 4: Data validation framework
    print("\n✓ Checking data validation framework...")
    try:
        from egx_radar.data_validator import DataValidator, validate_dataset
        print("  ✓ DataValidator imported successfully")
        print("  ✓ validate_dataset function available")
        checks['data_validation'] = True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
    
    # Check 5: Error handling framework
    print("\n✓ Checking error handling framework...")
    try:
        from egx_radar.error_handler import (
            ErrorHandler,
            RetryManager,
            RecoveryStrategy,
            handle_backtest_error,
        )
        print("  ✓ ErrorHandler imported successfully")
        print("  ✓ RetryManager imported successfully")
        print("  ✓ RecoveryStrategy imported successfully")
        checks['error_handling'] = True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for check, result in checks.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{check:25} {status}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ PHASE 5 VERIFICATION PASSED")
        return True
    else:
        print("\n⚠️  PHASE 5 VERIFICATION INCOMPLETE")
        return False


def generate_test_manifest():
    """Generate manifest of all test files and their purposes."""
    manifest = {
        'phase': 5,
        'title': 'Testing & Infrastructure',
        'timestamp': datetime.now().isoformat(),
        'test_files': {
            'conftest.py': {
                'purpose': 'Pytest fixtures and configuration',
                'fixtures': [
                    'sample_ohlcv_data',
                    'clean_data_guard',
                    'momentum_guard',
                    'test_settings',
                    'backtest_engine',
                    'test_trade_data',
                    'performance_baseline',
                ]
            },
            'test_unit_engine.py': {
                'purpose': 'Unit tests for backtest engine',
                'test_classes': [
                    'TestBacktestEngineImports',
                    'TestMetricsCalculation',
                    'TestEngineConfiguration',
                    'TestDataGuardIntegration',
                    'TestMomentumGuardIntegration',
                    'TestErrorHandling',
                    'TestParallelProcessing',
                ]
            },
            'test_integration_pipeline.py': {
                'purpose': 'Integration tests for full pipeline',
                'test_classes': [
                    'TestBacktestPipeline',
                    'TestDataPipeline',
                    'TestGuardSequence',
                    'TestEndToEndBacktest',
                    'TestSymbolProcessing',
                    'TestProgressCallback',
                ]
            },
            'test_performance_benchmarks.py': {
                'purpose': 'Performance and benchmark tests',
                'test_classes': [
                    'TestPerformanceBenchmarks',
                    'TestParallelizationBenefit',
                    'TestMemoryUsage',
                    'TestConcurrencyScaling',
                    'TestLongRunningPerformance',
                    'TestCPUScaling',
                ]
            },
            'test_data_validation.py': {
                'purpose': 'Data validation framework tests',
                'test_classes': [
                    'TestDataValidator',
                    'TestMetricsValidation',
                    'TestValidationUtilities',
                    'TestQualityChecks',
                ]
            },
            'test_error_handling.py': {
                'purpose': 'Error handling and recovery tests',
                'test_classes': [
                    'TestErrorHandler',
                    'TestRecoveryStrategy',
                    'TestRetryManager',
                    'TestErrorStructure',
                    'TestGlobalErrorHandler',
                    'TestErrorSeverityLevels',
                ]
            }
        },
        'modules': {
            'data_validator.py': {
                'purpose': 'Data validation framework',
                'classes': [
                    'DataValidator',
                    'validate_dataset',
                    'validate_all_symbols',
                    'generate_validation_report',
                ]
            },
            'error_handler.py': {
                'purpose': 'Error handling and recovery framework',
                'classes': [
                    'ErrorSeverity',
                    'BacktestError',
                    'ErrorHandler',
                    'RetryManager',
                    'TimeoutManager',
                    'RecoveryStrategy',
                ]
            }
        },
        'ci_cd': {
            'pipeline': '.github/workflows/ci.yml',
            'jobs': [
                'test',
                'performance',
                'lint',
                'build',
            ]
        },
        'metrics': {
            'test_count': 60,  # Approximate
            'test_classes': 27,
            'coverage_targets': {
                'engine': 90,
                'metrics': 85,
                'data_validation': 80,
                'error_handling': 85,
            }
        }
    }
    
    return manifest


def print_infrastructure_summary():
    """Print summary of testing infrastructure."""
    print("\n" + "=" * 70)
    print("TESTING & INFRASTRUCTURE SUMMARY")
    print("=" * 70)
    
    summary = """
COMPONENTS CREATED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. PYTEST CONFIGURATION
   • pytest.ini - Test discovery and marker configuration
   • tests/conftest.py - Shared fixtures and setup

2. COMPREHENSIVE TEST SUITE (60+ tests)
   • Unit Tests (test_unit_engine.py)
     - Engine imports and configuration
     - Metrics calculation
     - Performance profile validation
     - Error handling
     - Parallel processing capabilities
   
   • Integration Tests (test_integration_pipeline.py)
     - Full backtest pipeline
     - Data pipeline flow
     - Guard sequence execution
     - End-to-end backtest
     - Symbol processing
   
   • Performance Benchmarks (test_performance_benchmarks.py)
     - Backtest suite performance (target: < 20s)
     - Single symbol performance
     - Parallelization speedup verification
     - Memory usage efficiency
     - Concurrency scaling
     - Long-running performance
   
   • Data Validation Tests (test_data_validation.py)
     - OHLCV data validation
     - Quality checks
     - Trade metrics validation
     - Report generation

   • Error Handling Tests (test_error_handling.py)
     - ErrorHandler functionality
     - Recovery strategies
     - Retry management
     - Error severity tracking

3. DATA VALIDATION FRAMEWORK
   • DataValidator class
   • OHLC constraint checking
   • Gap detection
   • NaN and negative value detection
   • Metrics validation
   • HTML/JSON report generation

4. ERROR HANDLING & RECOVERY FRAMEWORK
   • Centralized ErrorHandler
   • BacktestError structured logging
   • Recovery strategies (skip, reduce range, sequential, clear cache)
   • RetryManager with exponential backoff
   • TimeoutManager
   • Global error handler instance

5. CI/CD PIPELINE (.github/workflows/ci.yml)
   • Python 3.8-3.11 matrix testing
   • Automated pytest execution
   • Performance benchmarks
   • Code quality checks (flake8, black, isort)
   • Package build and distribution
   • Artifact archiving

PERFORMANCE TARGETS ENFORCED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   • Backtest suite: < 20 seconds (with 4-worker parallel)
   • Single symbol: < 2 seconds
   • Memory usage: < 500 MB
   • Parallel speedup: >= 2.5x
   • Timeout enforcement: 60 seconds max

USAGE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   # Run all tests
   pytest tests/ -v
   
   # Run unit tests only
   pytest tests/ -m unit -v
   
   # Run integration tests
   pytest tests/ -m integration -v
   
   # Run performance benchmarks
   pytest tests/ -m performance -v
   
   # Run data validation tests
   pytest tests/ -m datavalidation -v
   
   # Generate coverage report
   pytest tests/ --cov=egx_radar --cov-report=html

VALIDATION STATUS:
"""
    
    print(summary)
    
    # Run verification
    verify_test_infrastructure()


if __name__ == "__main__":
    print_infrastructure_summary()
    
    # Generate manifest
    manifest = generate_test_manifest()
    manifest_file = 'phase5_test_manifest.json'
    
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✓ Test manifest saved to {manifest_file}")
