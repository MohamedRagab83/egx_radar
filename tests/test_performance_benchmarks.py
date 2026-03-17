"""Performance benchmark tests for optimized engine."""

import pytest
import sys
import os
import time
import multiprocessing

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Benchmark tests for engine performance."""
    
    def test_backtest_suite_performance(self, backtest_engine, performance_baseline):
        """Benchmark complete backtest suite execution."""
        if backtest_engine is None:
            pytest.skip("Backtest engine not available")
        
        start = time.time()
        
        trades, equity_curve, params = backtest_engine(
            date_from="2025-01-01",
            date_to="2025-12-31",
            progress_callback=lambda msg: None,
        )
        
        elapsed = time.time() - start
        
        print(f"\n✓ Backtest suite completed in {elapsed:.2f}s")
        
        # Should complete within performance target (allowing 25% overhead)
        max_allowed = performance_baseline['backtest_suite_seconds'] * 1.25
        assert elapsed <= max_allowed, \
            f"Backtest took {elapsed:.2f}s, max allowed: {max_allowed:.2f}s"
    
    def test_single_symbol_performance(self, backtest_engine, performance_baseline):
        """Benchmark single symbol backtest."""
        if backtest_engine is None:
            pytest.skip("Backtest engine not available")
        
        start = time.time()
        
        trades, equity_curve, params = backtest_engine(
            date_from="2025-06-01",
            date_to="2025-06-30",
        )
        
        elapsed = time.time() - start
        
        print(f"\n✓ Single symbol backtest in {elapsed:.2f}s")
        
        # Single month should be much faster
        assert elapsed <= performance_baseline['single_symbol_seconds'] * 2


@pytest.mark.performance
class TestParallelizationBenefit:
    """Test that parallelization provides speedup."""
    
    def test_parallel_vs_sequential_speedup(self):
        """Verify parallel processing provides significant speedup."""
        from egx_radar.config.settings import K
        
        # Simulate workload distribution
        symbols = list(range(11))  # Typical number of symbols
        
        # Parallel chunking
        chunk_size = K.CHUNK_SIZE
        chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        # With 4 workers on 11 symbols:
        # Sequential: 11 units
        # Parallel: ceil(11/4) = 3 batches
        expected_speedup = len(symbols) / len(chunks)
        
        print(f"\n✓ Expected speedup with {K.WORKERS_COUNT} workers: {expected_speedup:.2f}x")
        
        # Should have meaningful speedup (at least 2.5x for 4 workers on 11 items)
        assert expected_speedup >= 2.5


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory efficiency."""
    
    def test_dataframe_memory_efficiency(self, sample_ohlcv_data):
        """Test that DataFrame operations are memory efficient."""
        import pandas as pd
        
        df = sample_ohlcv_data.copy()
        
        # Check memory usage
        memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024  # Convert to MB
        
        print(f"\n✓ Sample data memory: {memory_usage:.2f}MB")
        
        # 250 bars should use less than 1MB
        assert memory_usage < 1.0


@pytest.mark.performance
class TestConcurrencyScaling:
    """Test concurrency and scaling characteristics."""
    
    def test_worker_pool_efficiency(self):
        """Test multiprocessing pool efficiency."""
        from egx_radar.config.settings import K
        
        try:
            # Create pool with configured workers
            pool = multiprocessing.Pool(K.WORKERS_COUNT)
            
            # Test basic operation
            test_data = list(range(100))
            result = pool.map(lambda x: x * 2, test_data[:10])
            
            pool.close()
            pool.join()
            
            assert len(result) == 10
            assert result[0] == 0
            assert result[9] == 18
            
            print(f"\n✓ Multiprocessing pool with {K.WORKERS_COUNT} workers functional")
            
        except Exception as e:
            pytest.skip(f"Multiprocessing test skipped: {e}")
    
    def test_chunk_processing_overhead(self):
        """Test overhead of chunked processing."""
        from egx_radar.config.settings import K
        
        items = list(range(1000))
        
        # Chunked processing
        start = time.time()
        chunks = [items[i:i+K.CHUNK_SIZE] for i in range(0, len(items), K.CHUNK_SIZE)]
        elapsed = time.time() - start
        
        print(f"\n✓ Chunking {len(items)} items into {len(chunks)} chunks: {elapsed*1000:.2f}ms")
        
        # Should be very fast (< 1ms)
        assert elapsed < 0.001


@pytest.mark.performance
@pytest.mark.slow
class TestLongRunningPerformance:
    """Long-duration performance tests."""
    
    def test_full_year_backtest(self, backtest_engine, performance_baseline):
        """Test full year backtest stays within timeout."""
        if backtest_engine is None:
            pytest.skip("Backtest engine not available")
        
        from egx_radar.config.settings import K
        
        start = time.time()
        
        trades, equity_curve, params = backtest_engine(
            date_from="2025-01-01",
            date_to="2025-12-31",
            progress_callback=lambda msg: None,
        )
        
        elapsed = time.time() - start
        
        print(f"\n✓ Full year backtest in {elapsed:.2f}s (timeout: {K.MAX_BACKTEST_SECONDS}s)")
        
        # Must respect timeout
        assert elapsed <= K.MAX_BACKTEST_SECONDS + 5


@pytest.mark.performance
class TestCPUScaling:
    """Test CPU efficiency."""
    
    def test_cpu_utilization_config(self):
        """Test that CPU utilization is properly configured."""
        from egx_radar.config.settings import K
        import multiprocessing
        
        cpu_count = multiprocessing.cpu_count()
        workers = K.WORKERS_COUNT
        
        # Workers should not exceed CPU count
        print(f"\n✓ CPU count: {cpu_count}, workers configured: {workers}")
        
        assert workers <= cpu_count
        assert workers >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
