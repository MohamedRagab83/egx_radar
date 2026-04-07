"""Fix incorrect status='LOSS' in trades_history.json."""
import json
import os
import shutil

HISTORY_FILE = "trades_history.json"
BACKUP_FILE  = "trades_history.json.bak_status_fix"

with open(HISTORY_FILE, "r", encoding="utf-8") as f:
    trades = json.load(f)

fixed = 0
for t in trades:
    entry      = float(t.get("entry") or 0)
    stop_price = float(t.get("stop")  or 0)
    target     = float(t.get("target") or 0)
    exit_price = float(t.get("exit_price") or 0)
    pnl        = float(t.get("pnl_pct") or 0)
    old_status = t.get("status", "")

    # Derive correct status from price geometry
    tol = target * 0.005 if target else 0   # 0.5% slippage tolerance
    if exit_price >= (target - tol) and pnl > 0:
        correct = "WIN"
    elif stop_price > 0 and exit_price <= (stop_price * 1.01):
        correct = "LOSS"
    else:
        correct = "TIMEOUT"

    if old_status != correct:
        print(f"  {t['sym']:10s} | {old_status} -> {correct} | pnl={pnl:+.2f}% | exit={exit_price:.2f} target={target:.2f} stop={stop_price:.2f}")
        t["status"] = correct
        fixed += 1

print(f"\nTotal fixes: {fixed} records")

if fixed > 0:
    # Backup original
    shutil.copy2(HISTORY_FILE, BACKUP_FILE)

    import tempfile
    dirpath = os.path.dirname(os.path.abspath(HISTORY_FILE)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp", prefix=".egx_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2)
    os.replace(tmp, HISTORY_FILE)
    print(f"Saved. Backup at: {BACKUP_FILE}")
else:
    print("No changes needed.")

# Show final tally
wins    = sum(1 for t in trades if t.get("status") == "WIN")
losses  = sum(1 for t in trades if t.get("status") == "LOSS")
timeout = sum(1 for t in trades if t.get("status") == "TIMEOUT")
print(f"\nFinal distribution: WIN={wins}  LOSS={losses}  TIMEOUT={timeout}")
