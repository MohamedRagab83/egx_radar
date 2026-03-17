"""
EGX Radar — Automated Backup Script
=====================================
Backs up code to GitHub and data files to a local backup folder.

Usage:
    python backup.py              # full backup (code + data)
    python backup.py --code-only  # git push only
    python backup.py --data-only  # data files only
    python backup.py --check      # show status without backing up

Schedule (Windows Task Scheduler or cron):
    Daily at market close: python backup.py
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from datetime import datetime
from pathlib import Path


# ── Configuration ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
BACKUP_DIR   = PROJECT_ROOT.parent / "egx_radar_backups"   # adjust if needed

# Data files to back up locally (NOT pushed to git)
DATA_FILES = [
    "brain_state.json",
    "brain_state.db",
    "trades_log.json",
    "trades_history.json",
    "egx_radar.db",
    "scan_snapshot.json",
    "source_settings.json",
    "paper_trading_tracker.xlsx",
    "rejected_symbols.csv",
]

# Git commit message format
COMMIT_MSG_TEMPLATE = "Auto-backup {date} — {changed} files changed"


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO") -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "✓", "WARN": "⚠", "ERROR": "✗", "HEAD": "═"}.get(level, "•")
    print(f"  [{timestamp}] {prefix}  {msg}")


def run(cmd: list, cwd=None, capture=True) -> tuple[int, str]:
    """Run a shell command. Returns (returncode, output)."""
    result = subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        capture_output=capture,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


# ── Core functions ────────────────────────────────────────────────────────────

def check_git() -> dict:
    """Check git status and return info dict."""
    code, out = run(["git", "status", "--porcelain"])
    if code != 0:
        return {"ok": False, "error": "Not a git repository or git not installed"}

    changed = [l for l in out.split("\n") if l.strip()]
    code2, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    code3, remote  = run(["git", "remote", "get-url", "origin"])

    return {
        "ok":      True,
        "changed": len(changed),
        "branch":  branch if code2 == 0 else "unknown",
        "remote":  remote if code3 == 0 else "none",
        "files":   changed,
    }


def backup_code() -> bool:
    """Commit and push all code changes to GitHub."""
    print()
    log("CODE BACKUP — GitHub", "HEAD")

    status = check_git()
    if not status["ok"]:
        log(f"Git error: {status['error']}", "ERROR")
        return False

    if status["remote"] == "none":
        log("No remote configured. Run: git remote add origin <your-repo-url>", "ERROR")
        return False

    if status["changed"] == 0:
        log("Nothing to commit — code is up to date")
        return True

    log(f"Branch  : {status['branch']}")
    log(f"Remote  : {status['remote']}")
    log(f"Changed : {status['changed']} file(s)")

    # Stage all changes
    code, out = run(["git", "add", "."])
    if code != 0:
        log(f"git add failed: {out}", "ERROR")
        return False

    # Commit
    msg = COMMIT_MSG_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        changed=status["changed"],
    )
    code, out = run(["git", "commit", "-m", msg])
    if code != 0:
        log(f"git commit failed: {out}", "ERROR")
        return False
    log(f"Committed: {msg}")

    # Push
    log("Pushing to GitHub...")
    code, out = run(["git", "push", "origin", status["branch"]])
    if code != 0:
        log(f"git push failed: {out}", "ERROR")
        log("Tip: check your internet connection and GitHub credentials", "WARN")
        return False

    log("Push successful ✓")
    return True


def backup_data() -> bool:
    """Copy data files to a timestamped local backup folder."""
    print()
    log("DATA BACKUP — Local folder", "HEAD")

    # Create backup directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = BACKUP_DIR / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)
    log(f"Backup folder: {backup_path}")

    copied = 0
    missing = 0

    for filename in DATA_FILES:
        src = PROJECT_ROOT / filename
        dst = backup_path / filename

        if src.exists():
            shutil.copy2(src, dst)
            size = src.stat().st_size
            log(f"Copied: {filename} ({size:,} bytes)")
            copied += 1
        else:
            log(f"Skipped (not found): {filename}", "WARN")
            missing += 1

    # Save backup manifest
    manifest = {
        "timestamp":    timestamp,
        "project_root": str(PROJECT_ROOT),
        "files_copied": copied,
        "files_missing": missing,
        "filenames":    DATA_FILES,
    }
    with open(backup_path / "_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    log(f"Done: {copied} files copied, {missing} skipped")

    # Clean up old backups — keep last 14
    _cleanup_old_backups(BACKUP_DIR, keep=14)
    return True


def _cleanup_old_backups(backup_dir: Path, keep: int = 14) -> None:
    """Delete oldest backups, keeping only the last `keep` copies."""
    if not backup_dir.exists():
        return
    backups = sorted(
        [d for d in backup_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    to_delete = backups[:-keep] if len(backups) > keep else []
    for old in to_delete:
        shutil.rmtree(old, ignore_errors=True)
        log(f"Removed old backup: {old.name}", "WARN")


def show_status() -> None:
    """Print current backup status without doing anything."""
    print()
    log("STATUS CHECK", "HEAD")

    # Git status
    status = check_git()
    if status["ok"]:
        log(f"Git branch  : {status['branch']}")
        log(f"Git remote  : {status['remote']}")
        log(f"Uncommitted : {status['changed']} file(s)")
        if status["files"]:
            for f in status["files"][:5]:
                log(f"  {f}", "WARN")
            if len(status["files"]) > 5:
                log(f"  ... and {len(status['files'])-5} more", "WARN")
    else:
        log(f"Git: {status['error']}", "ERROR")

    # Data files
    print()
    log("Data files:")
    for filename in DATA_FILES:
        path = PROJECT_ROOT / filename
        if path.exists():
            size = path.stat().st_size
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            log(f"  {filename} ({size:,} bytes, modified {mtime})")
        else:
            log(f"  {filename} — not found", "WARN")

    # Last backup
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.iterdir(), key=lambda d: d.name)
        if backups:
            last = backups[-1]
            log(f"Last data backup: {last.name}")
        else:
            log("No data backups found", "WARN")
    else:
        log(f"Backup folder not created yet: {BACKUP_DIR}", "WARN")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EGX Radar automated backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backup.py              Full backup (code + data)
  python backup.py --code-only  Git commit + push only
  python backup.py --data-only  Data files only
  python backup.py --check      Status report only
        """,
    )
    parser.add_argument("--code-only", action="store_true", help="Git backup only")
    parser.add_argument("--data-only", action="store_true", help="Data files only")
    parser.add_argument("--check",     action="store_true", help="Status only, no backup")
    args = parser.parse_args()

    print()
    print("  ════════════════════════════════════════")
    print("  EGX Radar — Backup")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  ════════════════════════════════════════")

    if args.check:
        show_status()
        return

    success = True

    if not args.data_only:
        success &= backup_code()

    if not args.code_only:
        success &= backup_data()

    print()
    if success:
        print("  ✅ Backup complete")
    else:
        print("  ⚠️  Backup finished with errors — check output above")
    print()


if __name__ == "__main__":
    main()
