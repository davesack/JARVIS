from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

# =========================================================
# BASE PATH
# =========================================================
# Project structure:
# utils/
#   games/
#     game_stats.py   ← this file
# data/
#   game_stats.json

STATS_FILE = Path("data/game_stats.json")
STATS_FILE.parent.mkdir(parents=True, exist_ok=True)


# =========================================================
# INTERNAL LOAD / SAVE
# =========================================================

def _load_stats() -> Dict[str, Any]:
    if not STATS_FILE.exists():
        return {"users": {}}

    try:
        with STATS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Corrupted stats should never crash the bot
        return {"users": {}}


def _save_stats(data: Dict[str, Any]) -> None:
    with STATS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _get_user(stats: Dict[str, Any], user_id: int) -> Dict[str, int]:
    users = stats.setdefault("users", {})
    return users.setdefault(str(user_id), {})


# =========================================================
# PUBLIC API — SAFE, GENERIC, REUSABLE
# =========================================================

def increment(user_id: int, key: str, amount: int = 1) -> None:
    """
    Increment a stat value for a user.
    """
    stats = _load_stats()
    user = _get_user(stats, user_id)
    user[key] = user.get(key, 0) + amount
    _save_stats(stats)


def set_best(user_id: int, key: str, value: float) -> bool:
    """
    Set a stat only if it's better (lower is better).
    Returns True if a new record was set.
    """
    stats = _load_stats()
    user = _get_user(stats, user_id)

    current = user.get(key)
    if current is None or value < current:
        user[key] = value
        _save_stats(stats)
        return True

    return False


def get_user_stats(user_id: int) -> Dict[str, int]:
    """
    Get all stats for a single user.
    """
    stats = _load_stats()
    return stats.get("users", {}).get(str(user_id), {})


def get_all_stats() -> Dict[str, Dict[str, int]]:
    """
    Get stats for all users.
    """
    return _load_stats().get("users", {})
