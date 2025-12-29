"""
===============================================================
   JARVIS â€” SAFE AUTORELOAD SYSTEM
===============================================================
 - Watches project files for changes
 - Restarts bot cleanly with NO duplicate processes
 - Prevents overlapping reloads and race conditions
 - Ignores media + attachments + __pycache__
===============================================================
"""

import os
import time
import subprocess
from pathlib import Path

# ------------------------------------------------------------
# FOLDERS / FILES TO WATCH
# ------------------------------------------------------------
WATCH_PATHS = [
    "bot.py",
    "config.py",
    "cogs",
    "utils",
]

# Folders to ignore entirely
IGNORE_FOLDERS = {
    "attachments",
    "media",
    "__pycache__",
}

# Prevent rapid-fire reloads (seconds)
DEBOUNCE_SECONDS = 1.5

# Root of project
PROJECT_ROOT = Path(__file__).resolve().parent


# ------------------------------------------------------------
# Should we track this file?
# ------------------------------------------------------------
def should_watch(path: Path) -> bool:
    for part in path.parts:
        if part.lower() in IGNORE_FOLDERS:
            return False
    return True


# ------------------------------------------------------------
# Take a snapshot of file modification timestamps
# ------------------------------------------------------------
def take_snapshot(paths):
    snapshot = {}

    for root in paths:
        p = PROJECT_ROOT / root

        # Track single files
        if p.is_file() and should_watch(p):
            snapshot[p] = p.stat().st_mtime

        # Track directories
        elif p.is_dir():
            for file in p.rglob("*.py"):
                if should_watch(file):
                    try:
                        snapshot[file] = file.stat().st_mtime
                    except FileNotFoundError:
                        continue

    return snapshot


# ------------------------------------------------------------
# Launch the bot as a subprocess
# ------------------------------------------------------------
def launch_bot():
    python = "python"
    return subprocess.Popen(
        [python, "bot.py"],
        cwd=str(PROJECT_ROOT),
        creationflags=0  # IMPORTANT: no new process group, clean termination
    )


# ------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------
def main():
    print("[AUTORELOAD] Starting autoreload…")

    bot = launch_bot()
    last_snapshot = take_snapshot(WATCH_PATHS)
    last_reload = 0

    while True:
        time.sleep(0.75)

        current_snapshot = take_snapshot(WATCH_PATHS)
        changed_file = None

        # Detect file-change
        for path, timestamp in current_snapshot.items():
            if last_snapshot.get(path) != timestamp:
                changed_file = path
                break

        # If a change is found AND not too soon since last reload
        if changed_file and (time.time() - last_reload >= DEBOUNCE_SECONDS):
            print(f"[AUTORELOAD][{time.strftime('%H:%M:%S')}] Change detected in: {changed_file}")
            print("[AUTORELOAD] Restarting bot…")

            last_reload = time.time()

            # CLEAN TERMINATION â€” no ghost processes, no duplicates
            bot.kill()
            try:
                bot.wait(timeout=3)  # ensure the old bot is completely dead
            except subprocess.TimeoutExpired:
                print("[AUTORELOAD] Warning: old bot process didn't exit in time")

            time.sleep(0.3)

            # RELAUNCH NEW BOT
            bot = launch_bot()
            last_snapshot = current_snapshot
        else:
            last_snapshot = current_snapshot


if __name__ == "__main__":
    main()
