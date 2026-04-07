# EGX Radar Refactoring TODO
Current Working Directory: d:/egx radar seprated

## Approved Steps (Surgical Refactor)

### 1. ✅ Centralize Position Constants [settings.py]
- Add POSITION MANAGEMENT section with exact matches from pro_system.py
- Import/replace in pro_system.py only (no other files)

### 2. ✅ Replace Legacy Params [pro_system.py] 
- Replace RiskConfig defaults → from settings import *
- No logic changes, no restructuring

### 3. ❌ SKIPPED: Sector Hard Block
- Rejected: Would change signal selection parity

### 4. ✅ Delete Dead Code
- Delete all .bak files
- Delete egx_radar_pro/ directory (post-merge obsolete)
- Safety: grep confirm no active references

## Progress Tracking
- [x] Step 1: settings.py updated ✓ POSITION MANAGEMENT section added
- [x] Step 2: pro_system.py imports settings ✓ RiskConfig centralized
- [ ] Step 4a: .bak files deleted  
- [ ] Step 4b: egx_radar_pro/ deleted
- [ ] Validation: python -m egx_radar runs
- [ ] Validation: No magic numbers remain
- [ ] COMPLETE

## Validation Commands (run after)
```
grep -r "partial.*0\." *.py  # Should find only settings.py
grep -r "risk_per_trade.*=" *.py  # Should be imports only
find . -name "*.bak"  # Empty
python -m egx_radar  # Launches without errors
```

