import subprocess, shutil, json, os
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).parent
BACKUP_DIR = PROJECT.parent / "egx_radar_backups"
DATA_FILES = [
    "brain_state.json", "brain_state.db",
    "trades_log.json", "trades_history.json",
    "egx_radar.db", "scan_snapshot.json",
    "source_settings.json", "paper_trading_tracker.xlsx",
]

def backup_code():
    print("── Code backup (git) ──")
    r1 = subprocess.run(["git","add","."], cwd=PROJECT, capture_output=True, text=True)
    r2 = subprocess.run(["git","status","--porcelain"], cwd=PROJECT, capture_output=True, text=True)
    changed = len([l for l in r2.stdout.split("\n") if l.strip()])
    if changed == 0:
        print("  Nothing to commit"); return True
    msg = f"Auto-backup {datetime.now().strftime('%Y-%m-%d %H:%M')} — {changed} files"
    r3 = subprocess.run(["git","commit","-m",msg], cwd=PROJECT, capture_output=True, text=True)
    if r3.returncode != 0:
        print(f"  Commit failed: {r3.stderr}"); return False
    r4 = subprocess.run(["git","push","origin","main"], cwd=PROJECT, capture_output=True, text=True)
    if r4.returncode != 0:
        print(f"  Push failed — add remote first: git remote add origin <url>")
        print(f"  Committed locally: OK"); return True
    print(f"  Pushed: {msg}"); return True

def backup_data():
    print("── Data backup (local) ──")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    dst = BACKUP_DIR / ts
    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in DATA_FILES:
        src = PROJECT / f
        if src.exists():
            shutil.copy2(src, dst / f)
            print(f"  Copied: {f}")
            copied += 1
        else:
            print(f"  Skipped: {f}")
    # Keep last 14 backups only
    backups = sorted(BACKUP_DIR.iterdir())
    for old in backups[:-14]:
        shutil.rmtree(old, ignore_errors=True)
    print(f"  Done: {copied} files → {dst}")

if __name__ == "__main__":
    print(f"\n  EGX Radar Backup — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("  ══════════════════════════════════")
    backup_code()
    backup_data()
    print("  ══════════════════════════════════")
    print("  ✅ Backup complete\n")
