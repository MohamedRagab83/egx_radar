# Phase 3 - Data Validation Layer Implementation

## Task List

- [x] Step 1: Update config/settings.py - Add new DG_ constants and adjust weights
- [x] Step 2: Update core/data_guard.py - Add check_consecutive_zero_volume() method
- [x] Step 3: Update core/data_guard.py - Add check_data_staleness() method
- [x] Step 4: Update core/data_guard.py - Update compute_confidence() to include zero-vol score
- [x] Step 5: Update core/data_guard.py - Update evaluate() to force DEGRADED on stale data
- [x] Step 6: Update data/merge.py - Add _cross_source_agreement() function
- [x] Step 7: Update data/merge.py - Call _cross_source_agreement() inside _merge_ohlcv()
- [x] Step 8: Verify implementation

## Status: COMPLETED

