
## ═══════════════════════════════════════════════════════
## /backup — Automated Backup (GitHub + Local Data)
##
## Files: backup.py (project root)  ·  .gitignore (project root)
## ═══════════════════════════════════════════════════════

### Trigger: `/backup`

Run this command at the end of every working session:

```bash
python backup.py
```

This does two things in one command:
1. Commits and pushes all code changes to GitHub
2. Copies all data files to a local timestamped backup folder

---

### Other backup commands

```bash
python backup.py --check      # show status without backing up
python backup.py --code-only  # git push only (no data files)
python backup.py --data-only  # data files only (no git)
```

---

### What gets backed up where

| Type | Where | Command |
|------|--------|---------|
| Python code | GitHub (private repo) | `python backup.py` |
| brain_state.json | Local backup folder | `python backup.py` |
| trades_log.json | Local backup folder | `python backup.py` |
| trades_history.json | Local backup folder | `python backup.py` |
| egx_radar.db | Local backup folder | `python backup.py` |
| scan_snapshot.json | Local backup folder | `python backup.py` |

Data files are kept for the **last 14 backups** automatically.
Older ones are deleted to save disk space.

---

### First-time setup (run once)

```bash
# 1. Initialize git (if not already done)
git init
git add .
git commit -m "EGX Radar v2 - initial commit"

# 2. Connect to GitHub
git remote add origin https://github.com/YOUR_USERNAME/egx_radar.git
git branch -M main
git push -u origin main

# 3. Confirm backup works
python backup.py --check
python backup.py
```

---

### Rules for backup

```
ALWAYS run python backup.py --check before starting a session.
ALWAYS run python backup.py at the end of every session.
NEVER push .env, source_settings.json, or *.db to GitHub.
The .gitignore file handles this automatically.
```
