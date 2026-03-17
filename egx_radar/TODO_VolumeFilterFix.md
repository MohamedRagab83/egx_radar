# TODO - Volume Filter Bug Fix (Phase 4)

## Status: COMPLETED

### Step 1: Update settings.py - Change LIQUIDITY_GATE_MIN_VOLUME
- [x] Read settings.py to understand current state
- [x] Change LIQUIDITY_GATE_MIN_VOLUME from 1_000_000.0 → 100_000.0

### Step 2: Update runner.py - Modify liquidity gate
- [x] Read runner.py to understand current state
- [x] Modify post-scoring liquidity gate (~line 677) to show warning instead of killing signal
- [x] Remove `continue` statement
- [x] Downgrade buy/ultra → watch for low volume

### Step 3: Add vol_tier to _process_symbol
- [x] Add volume tier logic after avg_vol computation (~line 342)
- [x] Add "vol_tier" field to res_dict (~line 454)

### Changes Made:
| File | Change |
|------|--------|
| config/settings.py | LIQUIDITY_GATE_MIN_VOLUME: 1,000,000 → 100,000 |
| scan/runner.py | Liquidity gate: Removed `continue`, shows warning instead of killing signal |
| scan/runner.py | Added vol_tier field for UI display |

