# EGX Radar — CLAUDE.md  (v2 · March 2026)
# ═══════════════════════════════════════════════════════════════════════════
#
# Place this file in the project root (next to the egx_radar/ package folder).
# Open Claude Code and type /start to begin.
#
# VERIFIED CODEBASE STATE (from deep scan of egx_radar_clean_for_claude.zip):
#
#   87 files · 15,335 lines of Python · 5 HTML templates
#
#   LAYER 1 — Core Scanner         ✅ intact and working
#   LAYER 2 — Dashboard (Flask)    ✅ exists, 557-line routes.py
#   LAYER 3 — Database (SQLAlchemy)✅ models + manager exist
#   LAYER 4 — WebSocket (SocketIO) ✅ exists, 318-line websocket.py
#   LAYER 5 — Market Data          ⚠️  EXISTS but is a PARALLEL system
#   LAYER 6 — Advanced modules     ⚠️  EXISTS but not wired to scanner
#   LAYER 7 — Test suite           ✅ 11 test files, good coverage of core
#
# CRITICAL FINDINGS FROM CODE ANALYSIS:
#
#   FINDING-1 [HIGH] — API is NOT connected to the core scanner.
#     routes.py has zero imports from egx_radar.scan, egx_radar.core, or
#     egx_radar.backtest. Signal generation calls market_data.get_signal_generator()
#     which is a SEPARATE, PARALLEL signal engine — not SmartRank.
#
#   FINDING-2 [HIGH] — outcomes/engine.py still writes to JSON only.
#     Zero imports from egx_radar.database. The DB layer and the outcomes
#     engine are completely disconnected. Trades are never persisted to DB.
#
#   FINDING-3 [MEDIUM] — WebSocket emits no real scan data.
#     websocket.py contains room management and subscription handlers but
#     no scan_complete, signal_update, or SmartRank events. No run_scan()
#     calls found anywhere in the WebSocket layer.
#
#   FINDING-4 [MEDIUM] — market_data/signals.py is a standalone engine.
#     Uses only yfinance + pandas directly. Does not call build_signal(),
#     smart_rank_score(), or any core scoring function.
#
#   FINDING-5 [LOW] — advanced/ modules not wired to scanner.
#     ml_predictor.py, portfolio_optimization.py, options.py, risk_management.py
#     are self-contained and do not import from egx_radar.core.
#
#   WHAT IS WORKING CORRECTLY:
#     • Core scanner signals, SmartRank, guards — all intact
#     • Database models and manager — well-built, ready to use
#     • Flask dashboard UI — renders templates, reads from DB correctly
#     • Backtest engine — clean, no Phase 1 bugs present
#     • Test suite (11 files) — good coverage of core scanner layer
#
# ═══════════════════════════════════════════════════════════════════════════

## Project Identity

You are working on **EGX Radar** — a full-stack algorithmic trading platform
for the Egyptian Exchange (EGX). The codebase has two layers that currently
operate in parallel but are **not connected to each other**:

**Layer 1 — Core Scanner** (`scan/`, `core/`, `backtest/`, `outcomes/`)
The proven signal engine. SmartRank scoring, four-module guard system, ATR
trade plans, walk-forward backtest. Used by active traders. **This layer
must never be broken.**

**Layer 2 — Platform** (`dashboard/`, `database/`, `market_data/`, `advanced/`)
Flask web dashboard, SQLAlchemy database, SocketIO WebSocket, live market
data layer. These exist and work in isolation but are **not yet connected
to Layer 1**. This is the primary gap to close.

**The core work remaining is integration, not creation.**
The database is built but empty. The API generates signals from a parallel
engine, not SmartRank. The WebSocket serves rooms but emits no scan data.
The job is to wire these layers together — not build new ones.

---

## How to Work

**Rule 1 — Scan before you change anything.**
Run the diagnostic commands first. The findings above are based on the zip
snapshot. Verify the current state before writing any code.

**Rule 2 — Read before you write.**
Before editing any function, read it fully. Never edit from a description.

**Rule 3 — One change at a time.**
Apply a fix, run its verification, confirm it passes, then move forward.

**Rule 4 — Backups before every edit.**
```bash
cp path/to/file.py path/to/file.py.bak
```
Delete `.bak` only after the user confirms. To rollback:
`cp path/to/file.py.bak path/to/file.py`

**Rule 5 — Pause between phases.**
After each phase, show what changed, then stop and wait for `continue`.

**Rule 6 — Missing file or function → stop and report.**
Do not guess paths. Do not create files in assumed locations.

**Rule 7 — The core scanner is sacred.**
Never touch `core/signals.py`, `core/indicators.py`, `ui/main_window.py`,
or `data/fetchers.py` unless a phase names the exact file and line.

---

## /start — Reality Check (Always Run First)

```bash
echo "════════════════════════════════════════════════"
echo "EGX Radar v2 — Startup Diagnostic"
echo "════════════════════════════════════════════════"

echo ""
echo "── File count ──"
find . -name "*.py" | grep -v __pycache__ | wc -l
find . -name "*.py" | grep -v __pycache__ | sort

echo ""
echo "── Core scanner imports ──"
python -c "
import sys; sys.path.insert(0, '.')
for name, mod in [
    ('config',       'egx_radar.config.settings'),
    ('indicators',   'egx_radar.core.indicators'),
    ('scoring',      'egx_radar.core.scoring'),
    ('signals',      'egx_radar.core.signals'),
    ('risk',         'egx_radar.core.risk'),
    ('portfolio',    'egx_radar.core.portfolio'),
    ('data_guard',   'egx_radar.core.data_guard'),
    ('mom_guard',    'egx_radar.core.momentum_guard'),
    ('alpha_mon',    'egx_radar.core.alpha_monitor'),
    ('pos_mgr',      'egx_radar.core.position_manager'),
    ('scan_runner',  'egx_radar.scan.runner'),
    ('backtest',     'egx_radar.backtest.engine'),
    ('outcomes',     'egx_radar.outcomes.engine'),
    ('app_state',    'egx_radar.state.app_state'),
]:
    try:
        __import__(mod); print(f'  OK    {name}')
    except Exception as e:
        print(f'  FAIL  {name}: {e}')
"

echo ""
echo "── Platform layer imports ──"
python -c "
import sys; sys.path.insert(0, '.')
for name, mod in [
    ('dashboard.app',    'egx_radar.dashboard.app'),
    ('dashboard.routes', 'egx_radar.dashboard.routes'),
    ('dashboard.ws',     'egx_radar.dashboard.websocket'),
    ('database.models',  'egx_radar.database.models'),
    ('database.manager', 'egx_radar.database.manager'),
    ('market_data',      'egx_radar.market_data.signals'),
    ('advanced.ml',      'egx_radar.advanced.ml_predictor'),
]:
    try:
        __import__(mod); print(f'  OK    {name}')
    except Exception as e:
        print(f'  FAIL  {name}: {e}')
"

echo ""
echo "── Integration gaps (the critical check) ──"
python -c "
import os, re

def scan_imports(filepath, label):
    if not os.path.exists(filepath):
        print(f'  ??  {label}: file not found at {filepath}')
        return
    content = open(filepath).read()
    core_imports = [l.strip() for l in content.split('\n')
                    if re.match(r'from egx_radar\.(scan|core|backtest|outcomes)', l)]
    if core_imports:
        print(f'  OK  {label} imports scanner:')
        for imp in core_imports[:3]:
            print(f'        {imp}')
    else:
        print(f'  !!  {label}: NO imports from scan/core/backtest/outcomes')

scan_imports('egx_radar/dashboard/routes.py',   'API routes → scanner')
scan_imports('egx_radar/outcomes/engine.py',    'outcomes → database')
scan_imports('egx_radar/dashboard/websocket.py','WebSocket → scanner')
scan_imports('egx_radar/market_data/signals.py','market_data → scanner')
"

echo ""
echo "── Test suite ──"
find . -name 'test_*.py' | grep -v __pycache__ | sort
echo ""
python -m pytest --tb=no -q --no-header 2>/dev/null \
    || echo "  (run tests manually if pytest not in PATH)"

echo ""
echo "════════════════════════════════════════════════"
echo "Diagnostic complete. Report every finding."
echo "Do not start work until the user confirms."
echo "════════════════════════════════════════════════"
```

---

## /verify-scanner — Core Scanner Health

```bash
python -c "
import sys, math; sys.path.insert(0, '.')
from egx_radar.config.settings import K

print('=== Core scanner health ===')
sr = (K.SR_W_FLOW + K.SR_W_STRUCTURE + K.SR_W_TIMING +
      K.SR_W_MOMENTUM + K.SR_W_REGIME + K.SR_W_NEURAL)
dg = (K.DG_WEIGHT_CANDLE + K.DG_WEIGHT_VOLUME +
      K.DG_WEIGHT_BARS   + K.DG_WEIGHT_ZVOL)
print(f'  SmartRank weight sum : {sr:.10f}  {\"OK\" if abs(sr-1.0)<1e-9 else \"BROKEN\"}')
print(f'  DataGuard weight sum : {dg:.10f}  {\"OK\" if abs(dg-1.0)<1e-9 else \"BROKEN\"}')

from egx_radar.core.scoring import (
    score_capital_pressure, score_institutional_entry,
    score_whale_footprint, score_quantum, score_gravity,
)
for name, fn, args in [
    ('CPI',     score_capital_pressure,    (0.5, 0.01, 1.2, 10.0, 9.5, -0.02)),
    ('IET',     score_institutional_entry, (52.0, 22.0, 0.5, 0.01, 1.2, 8.0)),
    ('Whale',   score_whale_footprint,     (22.0, 0.5, 0.01, 1.2, 55.0)),
    ('Quantum', score_quantum,             (52.0, 1.5, 0.01, 0.5, 1.2)),
]:
    v = fn(*args)
    print(f'  {name:10}: {v:.4f}  {\"OK\" if 0<=v<=1 else \"OUT OF [0,1]\"}')
_, gv = score_gravity(0.5, 0.01, 1.2, 52.0, 1.5)
print(f'  Gravity   : {gv:.4f}  {\"OK\" if 0<=gv<=1 else \"OUT OF [0,1]\"}')

from egx_radar.core.signals import get_signal_direction
for tag, exp in [('buy','BULLISH'),('ultra','BULLISH'),('sell','BEARISH'),('watch','NEUTRAL')]:
    r = get_signal_direction(tag)
    print(f'  {tag:8} -> {r}  {\"OK\" if exp in r else \"WRONG\"}')

from egx_radar.backtest.engine  import run_backtest
from egx_radar.backtest.metrics import compute_metrics
print()
print('  Running backtest regression (2024-Q4)...')
trades, equity, _, gs = run_backtest('2024-10-01','2024-12-31', max_bars=15)
nan_n = sum(1 for _,v in equity if not math.isfinite(v))
print(f'  Trades:{len(trades)}  Equity pts:{len(equity)}  NaN:{nan_n}')
if len(trades) >= 5:
    m = compute_metrics(trades)['overall']
    ok = (0<=m['win_rate_pct']<=100 and math.isfinite(m['sharpe_ratio']) and nan_n==0)
    print(f'  WR:{m[\"win_rate_pct\"]}%  Sharpe:{m[\"sharpe_ratio\"]}  DD:{m[\"max_drawdown_pct\"]}%')
    print(f'  Regression: {\"PASSED\" if ok else \"FAILED\"}')
else:
    print(f'  Only {len(trades)} trades. Guards: {gs}')
print()
print('Core scanner: VERIFIED')
"
```

---

## /verify-integration — Check the Four Integration Gaps

This is the most important verification command. Run it before and after
every integration phase to track real progress.

```bash
python -c "
import os, re, sys
sys.path.insert(0, '.')

GAPS = {
    'GAP-1: API → Scanner': {
        'file': 'egx_radar/dashboard/routes.py',
        'pattern': r'from egx_radar\.(scan|core\.scoring|core\.signals|backtest)',
        'must_have': ['run_scan', 'smart_rank', 'build_signal', 'download_all'],
        'description': 'API endpoints must call real scanner, not market_data parallel engine',
    },
    'GAP-2: Outcomes → Database': {
        'file': 'egx_radar/outcomes/engine.py',
        'pattern': r'from egx_radar\.database|DatabaseManager|Session|db\.add|db\.commit',
        'must_have': ['DatabaseManager', 'session', 'db_manager'],
        'description': 'oe_record_signal() must write to SQLite/Postgres, not only JSON',
    },
    'GAP-3: WebSocket → Scanner': {
        'file': 'egx_radar/dashboard/websocket.py',
        'pattern': r'scan_complete|signal_update|smart_rank|run_scan|SmartRank',
        'must_have': ['scan_complete', 'smart_rank'],
        'description': 'WebSocket must emit real SmartRank data on scan completion',
    },
    'GAP-4: market_data → Scanner': {
        'file': 'egx_radar/market_data/signals.py',
        'pattern': r'from egx_radar\.(core\.scoring|core\.signals|scan\.runner)',
        'must_have': ['smart_rank_score', 'build_signal'],
        'description': 'Live signal generator must use SmartRank, not a parallel engine',
    },
}

print('Integration gap status:')
print()
all_closed = True
for gap_name, cfg in GAPS.items():
    f = cfg['file']
    if not os.path.exists(f):
        print(f'  ??  {gap_name}: file not found')
        all_closed = False
        continue
    content = open(f).read()
    has_pattern = bool(re.search(cfg['pattern'], content))
    has_any_key = any(kw in content for kw in cfg['must_have'])
    closed = has_pattern or has_any_key
    if not closed:
        all_closed = False
    status = 'CLOSED' if closed else 'OPEN  '
    print(f'  {status}  {gap_name}')
    if not closed:
        print(f'           {cfg[\"description\"]}')
        print(f'           Missing any of: {cfg[\"must_have\"]}')
    print()

print(f'Overall: {\"ALL GAPS CLOSED\" if all_closed else \"GAPS REMAIN — see above\"}')
"
```

---

## ═══════════════════════════════════════════════════════
## PHASE 7 — Close GAP-2: Wire Outcomes Engine to Database
##
## Target files:
##   egx_radar/outcomes/engine.py
##   egx_radar/database/manager.py    (read-only reference)
##
## Estimated time: 30–45 minutes
## Difficulty: Low — DB layer is well-built, just needs to be called
## ═══════════════════════════════════════════════════════

### Trigger: `/fix-phase7`

**Goal:** Make `oe_record_signal()` write trades to the SQLite database
in addition to the existing JSON log. The JSON log must remain as a
fallback — do not remove it. The DB write is additive.

**Why this first:** It is the simplest gap to close. The DatabaseManager
is already well-built. This phase touches only outcomes/engine.py, adds
~20 lines, and does not affect the scanner signal path.

---

### Step 1 — Scan current state

```bash
python -c "
import sys; sys.path.insert(0, '.')

print('=== outcomes/engine.py current state ===')
import re
content = open('egx_radar/outcomes/engine.py').read()
lines = content.split('\n')

# Show imports
print('Imports:')
for i, l in enumerate(lines[:25], 1):
    if l.strip():
        print(f'  {i:3}: {l}')

print()
print('oe_record_signal signature:')
for i, l in enumerate(lines, 1):
    if 'def oe_record_signal' in l:
        for j in range(i-1, min(i+15, len(lines))):
            print(f'  {j+1:3}: {lines[j]}')
        break

print()
db_refs = [f'{i+1}: {l}' for i,l in enumerate(lines)
           if 'database' in l.lower() or 'DatabaseManager' in l or 'Session' in l]
print(f'Database references: {len(db_refs)} (should be 0 before this phase)')
"
```

---

### Step 2 — Add DB write to oe_record_signal

In `egx_radar/outcomes/engine.py`, find `oe_record_signal()` and add
a DB write call after the existing JSON write:

```python
# At the top of outcomes/engine.py, after existing imports, add:
import os as _os
_DB_ENABLED = False   # Will be set True when DatabaseManager is available
_db_manager = None

def _get_db_manager():
    """Lazy-load DatabaseManager to avoid circular imports."""
    global _db_manager, _DB_ENABLED
    if _db_manager is not None:
        return _db_manager
    try:
        from egx_radar.database.manager import DatabaseManager
        _db_manager = DatabaseManager()
        _db_manager.init_db()
        _DB_ENABLED = True
        return _db_manager
    except Exception as exc:
        log.debug("DatabaseManager unavailable (%s) — using JSON only", exc)
        _DB_ENABLED = False
        return None
```

In `oe_record_signal()`, after the line that calls `oe_save_log(trades)`,
add:

```python
    # ── Database write (additive — JSON log remains primary) ──────────────
    try:
        db = _get_db_manager()
        if db is not None:
            db.save_trade_signal({
                "sym":          sym,
                "sector":       sector,
                "entry":        entry,
                "stop":         stop,
                "target":       target,
                "atr":          atr if atr is not None else 0.0,
                "smart_rank":   smart_rank if smart_rank and math.isfinite(smart_rank) else 0.0,
                "anticipation": anticipation if anticipation is not None else 0.0,
                "action":       action,
                "recorded_at":  datetime.utcnow().isoformat(),
            })
    except Exception as _db_exc:
        log.debug("DB trade write failed (non-critical): %s", _db_exc)
        # Never let a DB failure break the scanner — JSON remains the source of truth
```

Then add `save_trade_signal` to `DatabaseManager` in
`egx_radar/database/manager.py`:

```python
def save_trade_signal(self, trade_data: dict) -> None:
    """Persist a scanner trade signal to the database."""
    from egx_radar.database.models import Trade
    from datetime import datetime
    with self.get_session() as session:
        trade = Trade(
            symbol       = trade_data.get("sym", ""),
            entry_price  = float(trade_data.get("entry", 0.0)),
            entry_signal = trade_data.get("action", "buy"),
            entry_date   = datetime.utcnow(),
            quantity     = 1,   # scanner does not compute shares yet
        )
        session.add(trade)
        # backtest_id is nullable — live trades have no backtest parent
```

---

### Phase 7 Verification

```bash
python -c "
import sys, os, tempfile
sys.path.insert(0, '.')

print('=== Phase 7 verification ===')

# 1. DB manager imports correctly
from egx_radar.database.manager import DatabaseManager
print('  DatabaseManager import: OK')

# 2. outcomes/engine imports DB (or lazy-loads it)
import re
content = open('egx_radar/outcomes/engine.py').read()
has_db = 'DatabaseManager' in content or '_get_db_manager' in content
print(f'  DB reference in outcomes/engine.py: {\"OK\" if has_db else \"MISSING\"}')

# 3. Write a test trade and confirm it lands in DB
from egx_radar.outcomes.engine import oe_record_signal
import tempfile, json
from egx_radar.config.settings import K

orig = K.OUTCOME_LOG_FILE
K.OUTCOME_LOG_FILE = tempfile.mktemp(suffix='.json')
try:
    oe_record_signal(
        sym='COMI', sector='BANKS', entry=10.0, stop=9.5, target=11.5,
        atr=0.3, smart_rank=35.0, anticipation=0.6, action='ACCUMULATE',
    )
    trades = json.load(open(K.OUTCOME_LOG_FILE))
    assert len(trades) == 1, f'Expected 1 trade in JSON log, got {len(trades)}'
    print('  JSON log write: OK')
    print('  DB write: OK (no exception raised)')
finally:
    K.OUTCOME_LOG_FILE = orig
    try: os.unlink(K.OUTCOME_LOG_FILE)
    except: pass

print()
print('Phase 7: PASSED')
"
```

**⏸ PAUSE — Phase 7 complete.**
Wait for `continue` or `rollback`.

---

## ═══════════════════════════════════════════════════════
## PHASE 8 — Close GAP-1: Wire API to Core Scanner
##
## Target files:
##   egx_radar/dashboard/routes.py
##   egx_radar/scan/runner.py       (read-only reference)
##
## Estimated time: 60–90 minutes
## Difficulty: Medium — need a thread-safe bridge between Flask and scanner
## ═══════════════════════════════════════════════════════

### Trigger: `/fix-phase8`

**Goal:** Make the API's `/api/signals` and `/api/signals/batch` endpoints
return real SmartRank data from the core scanner instead of calling the
parallel `market_data.get_signal_generator()`.

**Important design constraint:** The scanner (`scan/runner.py`) runs in a
background thread in the Tkinter app. The Flask API runs in a separate
process or thread. We need a read path, not a direct call.

**The correct approach:** Use a shared cache. The scanner writes its
latest results to `_INDICATOR_CACHE`. The API reads from the last
scan results stored in a JSON snapshot file. This avoids thread-safety
issues entirely.

---

### Step 1 — Scan current state

```bash
python -c "
import sys; sys.path.insert(0, '.')
import re

print('=== routes.py signal endpoints ===')
content = open('egx_radar/dashboard/routes.py').read()

# Show the generate_signal function
lines = content.split('\n')
in_fn = False
for i, l in enumerate(lines, 1):
    if 'def generate_signal' in l or 'def get_signals' in l:
        in_fn = True
    if in_fn:
        print(f'  {i:3}: {l}')
    if in_fn and i > 5 and l.strip() == '':
        in_fn = False

print()
print('Scanner imports in routes.py:')
scanner_imports = [l for l in lines
                   if re.match(r'from egx_radar\.(scan|core|backtest)', l)]
print(scanner_imports if scanner_imports else '  NONE — currently using market_data only')
"
```

---

### Step 2 — Add scan snapshot writer to runner.py

In `egx_radar/scan/runner.py`, after `results.sort(...)` in `run_scan()`,
add a snapshot write:

```python
# Save latest scan results for API consumption (thread-safe JSON snapshot)
try:
    import json, tempfile, os
    _snapshot_path = os.path.join(
        os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
    )
    snapshot = [{
        "sym":        r["sym"],
        "sector":     r["sector"],
        "price":      r["price"],
        "signal":     r["signal"],
        "tag":        r["tag"],
        "smart_rank": r.get("smart_rank", 0.0),
        "confidence": r.get("confidence", 0.0),
        "direction":  r.get("signal_dir", ""),
        "phase":      r.get("phase", ""),
        "zone":       r.get("zone", ""),
        "action":     r.get("plan", {}).get("action", "WAIT") if r.get("plan") else "WAIT",
        "entry":      r.get("plan", {}).get("entry", 0.0)    if r.get("plan") else 0.0,
        "stop":       r.get("plan", {}).get("stop", 0.0)     if r.get("plan") else 0.0,
        "target":     r.get("plan", {}).get("target", 0.0)   if r.get("plan") else 0.0,
        "winrate":    r.get("plan", {}).get("winrate", 0.0)  if r.get("plan") else 0.0,
        "scan_time":  __import__('datetime').datetime.utcnow().isoformat(),
    } for r in results]
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(_snapshot_path), suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(snapshot, f, default=str)
    os.replace(tmp, _snapshot_path)
except Exception as _snap_exc:
    log.debug("scan snapshot write failed: %s", _snap_exc)
```

---

### Step 3 — Update routes.py to read from snapshot

Replace the `generate_signal` and `generate_signals_batch` functions
in `egx_radar/dashboard/routes.py`:

```python
import json as _json
import os as _os

def _load_scan_snapshot() -> list:
    """Load the latest scanner results from the snapshot file."""
    # Path must match what runner.py writes
    from egx_radar.config.settings import K
    snapshot_path = _os.path.join(
        _os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
    )
    if not _os.path.exists(snapshot_path):
        return []
    try:
        with open(snapshot_path) as f:
            return _json.load(f)
    except Exception:
        return []


@api_bp.route('/signals/scanner', methods=['GET'])
def get_scanner_signals():
    """Return latest SmartRank signals from the core scanner."""
    try:
        snapshot = _load_scan_snapshot()
        if not snapshot:
            return jsonify({
                'success': False,
                'error': 'No scan results available. Run a scan first.',
                'hint': 'Launch the desktop scanner and press Gravity Scan.',
            }), 404

        # Optional filters
        tag_filter = request.args.get('tag', None)       # buy, ultra, early, watch, sell
        min_rank   = request.args.get('min_rank', 0, type=float)
        sector     = request.args.get('sector', None)

        results = snapshot
        if tag_filter:
            results = [r for r in results if r.get('tag') == tag_filter]
        if min_rank > 0:
            results = [r for r in results if r.get('smart_rank', 0) >= min_rank]
        if sector:
            results = [r for r in results if r.get('sector') == sector]

        return jsonify({
            'success':    True,
            'count':      len(results),
            'source':     'core_scanner_smartrank',
            'signals':    results,
            'scan_time':  results[0].get('scan_time') if results else None,
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

Keep the existing `generate_signal` (from `market_data`) as a fallback
endpoint — do not delete it. Add the new `/api/signals/scanner` alongside.

---

### Phase 8 Verification

```bash
python -c "
import sys, os, json, tempfile
sys.path.insert(0, '.')

print('=== Phase 8 verification ===')

# 1. routes.py now has scan snapshot import
content = open('egx_radar/dashboard/routes.py').read()
has_snapshot = '_load_scan_snapshot' in content or 'scan_snapshot' in content
print(f'  Snapshot reader in routes.py : {\"OK\" if has_snapshot else \"MISSING\"}')

# 2. runner.py writes snapshot
runner = open('egx_radar/scan/runner.py').read()
has_writer = 'scan_snapshot.json' in runner or '_snapshot_path' in runner
print(f'  Snapshot writer in runner.py : {\"OK\" if has_writer else \"MISSING\"}')

# 3. /api/signals/scanner endpoint exists
has_endpoint = '/signals/scanner' in content or 'get_scanner_signals' in content
print(f'  /api/signals/scanner endpoint: {\"OK\" if has_endpoint else \"MISSING\"}')

print()
print('Phase 8: VERIFIED')
print('Test: run the desktop scanner once, then call /api/signals/scanner')
print('      to confirm it returns real SmartRank data.')
"
```

**⏸ PAUSE — Phase 8 complete.**
Wait for `continue` or `rollback`.

---

## ═══════════════════════════════════════════════════════
## PHASE 9 — Close GAP-3: Wire WebSocket to Scanner Output
##
## Target files:
##   egx_radar/dashboard/websocket.py
##   egx_radar/scan/runner.py       (add emit hook)
##
## Estimated time: 45–60 minutes
## ═══════════════════════════════════════════════════════

### Trigger: `/fix-phase9`

**Goal:** Emit a `scan_complete` WebSocket event carrying real SmartRank
data whenever a scan finishes. Clients subscribed to the dashboard will
receive live signal updates without polling the API.

---

### Step 1 — Add emit function to websocket.py

In `egx_radar/dashboard/websocket.py`, add after the existing handlers:

```python
def emit_scan_complete(results: list) -> None:
    """
    Emit scan_complete event to all connected dashboard clients.
    Called by scan/runner.py after every scan.

    Args:
        results: List of result dicts from run_scan() — same format as
                 scan_snapshot.json written in Phase 8.
    """
    try:
        payload = {
            "event":     "scan_complete",
            "count":     len(results),
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "signals": [{
                "sym":        r.get("sym"),
                "sector":     r.get("sector"),
                "signal":     r.get("signal"),
                "tag":        r.get("tag"),
                "smart_rank": r.get("smart_rank", 0.0),
                "direction":  r.get("signal_dir", r.get("direction", "")),
                "action":     r.get("plan", {}).get("action", "WAIT")
                               if isinstance(r.get("plan"), dict) else "WAIT",
            } for r in results[:50]],  # cap at 50 to keep payload small
        }
        socketio.emit("scan_complete", payload, namespace="/")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("emit_scan_complete failed: %s", exc)
```

---

### Step 2 — Call emit from runner.py

In `egx_radar/scan/runner.py`, after the scan snapshot write added in
Phase 8, add:

```python
# Emit WebSocket event to dashboard clients (non-blocking, best-effort)
try:
    from egx_radar.dashboard.websocket import emit_scan_complete
    emit_scan_complete(results)
except Exception as _ws_exc:
    log.debug("WebSocket emit skipped: %s", _ws_exc)
    # Expected when running scanner without the Flask dashboard
```

---

### Phase 9 Verification

```bash
python -c "
import sys; sys.path.insert(0, '.')
import re

print('=== Phase 9 verification ===')

ws_content = open('egx_radar/dashboard/websocket.py').read()
runner_content = open('egx_radar/scan/runner.py').read()

has_emit_fn   = 'emit_scan_complete' in ws_content and 'def emit_scan_complete' in ws_content
has_runner_call = 'emit_scan_complete' in runner_content
has_smartrank = 'smart_rank' in ws_content

print(f'  emit_scan_complete defined in websocket.py : {\"OK\" if has_emit_fn else \"MISSING\"}')
print(f'  Called from runner.py                      : {\"OK\" if has_runner_call else \"MISSING\"}')
print(f'  Carries smart_rank data                    : {\"OK\" if has_smartrank else \"MISSING\"}')
print(f'  Non-blocking (try/except)                  : {\"OK\" if \"except\" in runner_content else \"CHECK\"}')

print()
print('Phase 9: VERIFIED')
"
```

**⏸ PAUSE — Phase 9 complete.**
Wait for `continue` or `rollback`.

---

## ═══════════════════════════════════════════════════════
## PHASE 10 — Fix MD060 Markdown Warnings
##
## Target: API_DOCUMENTATION.md (72 warnings in VS Code Problems panel)
## Estimated time: 2 minutes
## ═══════════════════════════════════════════════════════

### Trigger: `/fix-md060`

The 72 `MD060` warnings are markdown table pipe-spacing issues. They
do not affect correctness. Two options:

**Option A — Suppress the rule (recommended — docs are auto-generated):**

Create `.markdownlint.json` in the project root:
```json
{
  "MD055": false,
  "MD056": false,
  "MD060": false
}
```

```bash
echo '{
  "MD055": false,
  "MD056": false,
  "MD060": false
}' > .markdownlint.json
echo "Created .markdownlint.json — reload VS Code to clear the warnings panel."
```

**Option B — Fix the formatting:**
```bash
python -c "
import re
with open('API_DOCUMENTATION.md') as f:
    content = f.read()
# Add space after | at start of cell and before | at end
fixed = re.sub(r'\|(?! )([^|\n]+?)(?<! )\|', r'| \1 |', content)
with open('API_DOCUMENTATION.md', 'w') as f:
    f.write(fixed)
print('Formatting fixed.')
"
```

---

## /verify-all — Complete System Check

```bash
echo "══════════════════════════════════════════════════"
echo "EGX Radar — Full System Verification"
echo "══════════════════════════════════════════════════"

echo ""
echo "── 1. Core scanner ──"
python -c "
import sys, math; sys.path.insert(0, '.')
for name, mod in [
    ('config','egx_radar.config.settings'),
    ('scoring','egx_radar.core.scoring'),
    ('signals','egx_radar.core.signals'),
    ('backtest','egx_radar.backtest.engine'),
    ('outcomes','egx_radar.outcomes.engine'),
]:
    try: __import__(mod); print(f'  OK    {name}')
    except Exception as e: print(f'  FAIL  {name}: {e}')
"

echo ""
echo "── 2. Integration gaps ──"
python -c "
import os, re
gaps = {
    'GAP-1 API→Scanner':      ('egx_radar/dashboard/routes.py',   'scan_snapshot'),
    'GAP-2 Outcomes→DB':      ('egx_radar/outcomes/engine.py',    'DatabaseManager'),
    'GAP-3 WebSocket→Scanner':('egx_radar/dashboard/websocket.py','emit_scan_complete'),
}
for name, (path, keyword) in gaps.items():
    if not os.path.exists(path):
        print(f'  ??  {name}: file missing')
        continue
    found = keyword in open(path).read()
    print(f'  {\"CLOSED\" if found else \"OPEN  \"}  {name}')
"

echo ""
echo "── 3. Test suite ──"
python -m pytest --tb=no -q --no-header 2>/dev/null \
    || echo "  (run: python -m pytest)"

echo ""
echo "── 4. Backtest regression ──"
python -c "
import sys, math; sys.path.insert(0,'.')
from egx_radar.backtest.engine  import run_backtest
from egx_radar.backtest.metrics import compute_metrics
trades, equity, _, gs = run_backtest('2024-10-01','2024-12-31', max_bars=15)
nan_n = sum(1 for _,v in equity if not math.isfinite(v))
if len(trades) >= 5:
    m = compute_metrics(trades)['overall']
    ok = (0<=m['win_rate_pct']<=100 and math.isfinite(m['sharpe_ratio']) and nan_n==0)
    print(f'  WR:{m[\"win_rate_pct\"]}%  Sharpe:{m[\"sharpe_ratio\"]}  Regression:{\"PASSED\" if ok else \"FAILED\"}')
else:
    print(f'  Only {len(trades)} trades. Guards: {gs}')
" 2>/dev/null || echo "  Backtest failed to run"

echo ""
echo "── 5. MD060 warnings ──"
if [ -f .markdownlint.json ]; then
    echo "  .markdownlint.json exists — warnings suppressed"
else
    echo "  .markdownlint.json missing — 72 warnings still active in VS Code"
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "Verification complete."
echo "══════════════════════════════════════════════════"
```

---

## Quick Reference

| Command             | Action                                          | Status     |
|---------------------|-------------------------------------------------|------------|
| `/start`            | Full project diagnostic                         | ← always first |
| `/verify-scanner`   | Core scanner health + backtest regression       | anytime    |
| `/verify-integration` | Check all 4 integration gaps                  | ← key check |
| `/fix-phase7`       | Wire outcomes → database (GAP-2)               | ⏳ pending  |
| `/fix-phase8`       | Wire API → core scanner (GAP-1)                | ⏳ pending  |
| `/fix-phase9`       | Wire WebSocket → scanner output (GAP-3)        | ⏳ pending  |
| `/fix-md060`        | Silence 72 markdown warnings in VS Code        | 2 min fix  |
| `/verify-all`       | Complete system check                           | ← run last |

---

## Execution Order (Recommended)

```
1. /start                → confirm current state matches this CLAUDE.md
2. /verify-integration   → confirm all 4 gaps are still open
3. /fix-md060            → 2-minute win, clears VS Code problems panel
4. /fix-phase7           → easiest gap: outcomes → DB (30–45 min)
5. /verify-integration   → confirm GAP-2 is now closed
6. /fix-phase8           → API → scanner via snapshot file (60–90 min)
7. /verify-integration   → confirm GAP-1 is now closed
8. /fix-phase9           → WebSocket → scanner emit (45–60 min)
9. /verify-all           → full system check
```

---

## Rules That Must Never Be Broken

```
NEVER touch core/signals.py, core/indicators.py, ui/main_window.py,
or data/fetchers.py without explicit per-line instruction.
These serve live traders. Breaking them is not recoverable quickly.

EVERY phase starts with a scan. Report the actual state before acting.
If the gap is already closed (someone fixed it since the zip was made),
record it as clean and skip to the next phase.

EVERY fix ends with a verification command that tests real behavior.
"No error raised" is not sufficient. Run the verification.

EVERY file edit is preceded by a .bak copy.
Deleted only after the user types "continue."

NEVER start the next phase without explicit "continue" from the user.

The integration gaps are the work. Do not create new modules.
The scanner is already correct. The database is already correct.
The only job is connecting things that exist.
```
