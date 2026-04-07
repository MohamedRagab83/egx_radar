# EGX Radar Production Cleanup Audit

Date: 2026-03-25

## Scope

This cleanup pass was intentionally conservative.

- Core trading logic was not modified.
- Signal generation, risk formulas, scanner flow, and backtest code were left in place.
- No files were deleted.
- Non-runtime files were moved into `archive/` or `experimental/` only.

## 1. Files Kept

### Core runtime

These remain in their original locations because they are part of the active execution path or package surface:

- `egx_radar/main.py`
- `egx_radar/__main__.py`
- `egx_radar/ui/`
- `egx_radar/core/`
- `egx_radar/scan/`
- `egx_radar/backtest/`
- `egx_radar/data/`
- `egx_radar/config/`
- `egx_radar/outcomes/`
- `egx_radar/database/`
- `egx_radar/dashboard/`
- `egx_radar/market_data/`
- `egx_radar/state/`
- `egx_radar/advanced/`

### Support modules kept intentionally

These are not core execution modules, but they are valid support assets and were left accessible:

- `egx_radar/data_validator.py`
- `egx_radar/error_handler.py`
- `egx_radar/backup.py`
- `egx_radar/tools/`
- `run_bt.bat`
- `run_3_backtests.py`
- `_run_single_bt.py`

### Runtime state and data files kept

These are generated or consumed by the application and should stay available at the root unless runtime paths are changed explicitly:

- `egx_radar.db`
- `scan_snapshot.json`
- `source_settings.json`
- `brain_state.json`
- `trades_log.json`
- `trades_history.json`
- `history/`

## 2. Files Moved

### Archived root diagnostics

Moved to `archive/diagnostics/root_scripts/`.

Reason: one-off analysis, comparison, verification, and exploratory helpers not used by production imports.

Examples:

- `_analyze_trades.py`
- `_debug_bt.py`
- `_diagnose_gate.py`
- `_diagnostic_deep.py`
- `_generate_report.py`
- `_run_after.py`
- `_run_after_v2.py`
- `_run_baseline.py`
- `_run_before_after.py`
- `_run_extended.py`
- `_show_diffs.py`
- `_trace_changes.py`
- `backup.py`
- `check_db.py`
- `cleanup_phase3.py`
- `cleanup_phase4.py`
- `diagnostic_summary.py`
- `fix2c_verify.py`

### Archived phase scripts

Moved to `archive/diagnostics/phase_scripts/`.

Reason: phased remediation scripts and temporary verification utilities are not part of runtime.

Examples:

- `phase1_check.py`
- `phase2_diagnostic.py`
- `phase3_backup.py`
- `phase3_verify.py`
- `phase4_verify.py`
- `phase5_verify.py`
- `phase6a_verify.py`
- `phase6e_verify.py`
- `phase8_verify.py`
- `verify_phase8_tmp.py`
- `verify_phase9_tmp.py`

### Archived manual test scripts

Moved to `archive/diagnostics/manual_tests/`.

Reason: ad hoc integration and live test scripts were cluttering the project root and are not part of automated test discovery.

Examples:

- `_live_test_api.py`
- `_live_test_db_ws.py`
- `_live_test_scanner.py`
- `_test_import.py`
- `_test_missed_trades.py`
- `_test_tracking_dashboard.py`

### Archived package-internal legacy tests

Moved to `archive/diagnostics/package_tests/`.

Reason: these files matched test naming but lived inside the package namespace and were not used by `pytest.ini`, which already restricts discovery to `tests/`.

Moved files:

- `egx_radar/test_alpha_monitor.py`
- `egx_radar/test_audit_safeties.py`
- `egx_radar/test_comprehensive_audit_v2.py`
- `egx_radar/test_data_guard.py`
- `egx_radar/test_hardcoded.py`
- `egx_radar/test_momentum_guard.py`
- `egx_radar/test_position_manager.py`
- `egx_radar/test_prereqs.py`
- `egx_radar/test_smoke.py`

### Archived generated backtest outputs

Moved to `archive/generated/backtests/`.

Reason: timestamped CSV output files are generated artifacts, not source.

Examples:

- `EGX_Radar_Backtest_*.csv`
- `EGX_Radar_v80_*.csv`
- `EGX_Radar_v083_*.csv`
- `backtest_SR0.csv`
- `backtest_SR20.csv`

### Archived generated reports and manifests

Moved to `archive/generated/reports/`.

Reason: validation output, hybrid reports, manifests, and fix summaries are useful for audit history but should not live at the root.

Examples:

- `VALIDATION_REPORT_*.txt`
- `VALIDATION_SUMMARY_*.json`
- `VALIDATION_TRADES_*.json`
- `HYBRID_REPORT_*.txt`
- `HYBRID_SUMMARY_*.json`
- `HYBRID_TRADES_*.json`
- `_DB_FIX_COMPLETE.txt`
- `_DB_GAP_FIX_SUMMARY.txt`
- `_EXACT_PATCHES_APPLIED.txt`
- `phase5_test_manifest.json`

### Archived logs and temp run output

Moved to `archive/generated/logs/`.

Reason: stdout, stderr, progress files, and transient logs are non-source artifacts.

Examples:

- `bt_*.txt`
- `dbg_*.txt`
- `mq*.txt`
- `mt_*.txt`
- `_after_stderr.txt`
- `_after_stdout.txt`
- `_diag_err.txt`
- `_diag_out.txt`
- `_full_6year_validation_*.log`

### Archived zip and snapshot backups

Moved to `archive/backups/zips/` and `archive/backups/package_bak/`.

Reason: zip snapshots and `.bak_*` files are legacy backups, not active code.

Examples:

- `egx_radar.zip`
- `egx_radar (2).zip` through `egx_radar (11).zip`
- `egx_radar_full_code_for_claude.txt`
- `engine.py.bak_hybrid`
- `engine.py.bak_precision`
- `settings.py.bak_hybrid`
- `signal_engine.py.bak_hybrid`
- `accumulation.py.bak_hybrid`

### Moved package notes and isolated tools

Moved planning notes to `archive/package_notes/` and isolated experimental utilities to `experimental/package_tools/`.

Reason: these were not production imports and did not belong on the package surface.

Moved notes:

- `egx_radar/TODO_Phase3.md`
- `egx_radar/TODO_Phase3_DataValidation.md`
- `egx_radar/TODO_VolumeFilterFix.md`
- `egx_radar/TODO_yfinance_fix.md`
- `egx_radar/CLAUDE_backup_section.md`

Moved tools:

- `egx_radar/verify_sharpe_refactor.py`
- `egx_radar/diagnose_am.py`
- `egx_radar/backtest_compare_v3.py`

## 3. Files Suspected Unused But Left In Place

These were left untouched because they may still be operator-facing, environment-specific, or worth a separate decision:

- `run_3_backtests.py`
  Reason: manual runner, but not part of the packaged entry point.

- `_run_single_bt.py`
  Reason: currently used by the workspace task and referenced in the README.

- `test_egx_radar.db`
  Reason: looks like a test artifact, but could still be referenced during manual checks.

- `.tmp.driveupload/`
  Reason: external temporary upload/cache folder, not a project source folder.

- `history/`
  Reason: historical output rather than source, but it may be intentionally retained for trader review.

## 4. Risk Issues Found

### Duplicate utility naming

- `backup.py` existed both at the root and inside `egx_radar/`.
- The package version was kept accessible; the root duplicate was archived.

### Hardcoded path logic in legacy tests

- Several archived test files used `sys.path.insert(...)` or even a hardcoded workspace path.
- This is not production risk now that they are archived, but it shows prior test sprawl.

### Runtime path injection in entry points

- `egx_radar/__main__.py` and `egx_radar/dashboard/run.py` use `sys.path.insert(...)`.
- This works, but it is brittle and should be replaced by cleaner package execution assumptions.

### Broad CORS and dev-oriented defaults

- `egx_radar/dashboard/app.py` enables `CORS(... origins='*')` for `/api/*`.
- This is acceptable for internal/dev usage, but not ideal for a production-facing deployment.

### Root still contains runtime state next to source

- Database, scan snapshot, state JSON, and trade logs still live beside source files.
- That is functional, but a dedicated `var/` or `runtime/` directory would reduce operational risk.

### Package structure target should not be forced in one pass

- The requested ideal structure is sensible, but physically moving core modules into a new namespace now would require broad import rewrites.
- That is not a safe cleanup action for a live, working trading system.

## 5. Suggested Improvements

### Safe next structural step

Add a `scripts/` directory for intentional operator tools and move only maintained wrappers there in a future pass:

- `_run_single_bt.py`
- `run_3_backtests.py`
- `run_bt.bat`

### Runtime data segregation

Introduce a configured runtime data directory for:

- database files
- scan snapshots
- trade logs
- UI state files

### Logging improvements

- Use rotating file handlers instead of loose `*_stdout.txt` and `*_stderr.txt` files.
- Separate app logs, scan logs, dashboard logs, and backtest logs.
- Add structured logging for scan completion, signal emission, and DB persistence.

### Monitoring hooks

Add explicit hooks for:

- scan duration
- symbol failure counts
- DB write failures
- websocket emit failures
- API latency and error rate

### Config hardening

- Centralize dashboard host, port, CORS, and DB URL under config/env handling.
- Eliminate remaining hardcoded fallback values where possible.

## 6. Recommended Target Structure

This is a recommended future-state layout, not a change applied in this cleanup pass:

```text
egx_radar/
  core/
  strategies/
  risk/
  execution/
  data/
  config/
  utils/

tests/
archive/
scripts/
runtime/
```

The current codebase is already partially organized around this model. A full migration should be treated as a separate refactor project with import updates and regression validation, not as a cleanup-only change.

## Outcome

The repository is materially cleaner now:

- root clutter was reduced
- package namespace noise was reduced
- generated artifacts were isolated
- legacy tests and backups were quarantined
- production code paths were preserved
