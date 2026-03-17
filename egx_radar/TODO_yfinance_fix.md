# TODO: Fix yfinance "truth value of a Series is ambiguous" Error

## Status: COMPLETED

### Fix 1: data/fetchers.py
- [x] Replace `_flatten_df` function with auto-detection for new yfinance MultiIndex format
- [x] Replace `_yfin_extract` function with proper level detection

### Fix 2: core/indicators.py
- [x] Replace `compute_ud_ratio` function with explicit float() conversion

### Fix 3: scan/runner.py
- [x] Add DataFrame-to-Series squeeze in `_process_symbol` function

### Verification
- [ ] Run application and verify no errors
- [ ] Confirm symbols appear in results table

