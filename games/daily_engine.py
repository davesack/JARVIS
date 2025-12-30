# utils/games/daily_engine.py

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict

DATA_ROOT = Path("data/games")

DAILY_CURRENT = DATA_ROOT / "daily/current.json"
DAILY_HISTORY = DATA_ROOT / "daily/history.json"
USER_PROGRESS = DATA_ROOT / "progress/users.json"
AGG_STATS = DATA_ROOT / "stats/aggregates.json"
SUBSCRIPTIONS = DATA_ROOT / "games" / "daily" / "subscriptions.json"


def _load(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class DailyEngine:
    """
    Authoritative DAILY game engine.
    """

    def __init__(self):
        self.current = _load(DAILY_CURRENT, None)
        self.history = _load(DAILY_HISTORY, {})
        self.stats = _load(AGG_STATS, {})

    # -------------------------
    # Day rotation
    # -------------------------

    def rotate_day(self, game_registry: Dict[str, "DailyGame"]):
        today = date.today().isoformat()
        day_index = 1 if not self.current else self.current["day_index"] + 1

        games = {}

        for name, game in game_registry.items():
            seed = game.select_daily_seed(self.history.get(name, []))
            self.history.setdefault(name, []).append(seed)

            games[name] = {
                "seed": seed,
                "seed_id": f"{name}_{day_index}",
                "first_solve_user": None,
            }

        self.current = {
            "date": today,
            "day_index": day_index,
            "games": games,
        }

        self.stats.setdefault(today, {})

        _save(DAILY_CURRENT, self.current)
        _save(DAILY_HISTORY, self.history)
        _save(AGG_STATS, self.stats)

    # -------------------------
    # Gameplay
    # -------------------------

    def register_guess(self, user_id: str, game: "DailyGame", guess: str):
        progress = self._load_user_progress(user_id, game.name)
        before = progress.get("completed", False)

        result = game.apply_guess(progress, guess)
        self._save_user_progress(user_id, game.name, result)

        if result.get("completed") and not before:
            self._record_completion(user_id, game.name, result)

        return result

    # -------------------------
    # Stats
    # -------------------------

    def _record_completion(self, user_id: str, game_name: str, result: dict):
        today = self.current["date"]
        game_stats = self.stats[today].setdefault(game_name, {
            "plays": 0,
            "solves": 0,
            "first_solve": None,
            "best_guess_count": None,
            "best_guess_users": [],
        })

        game_stats["plays"] += 1

        if result.get("success"):
            game_stats["solves"] += 1
            guesses = len(result.get("guesses", []))

            if game_stats["first_solve"] is None:
                game_stats["first_solve"] = user_id
                self.current["games"][game_name]["first_solve_user"] = user_id
                _save(DAILY_CURRENT, self.current)

            best = game_stats["best_guess_count"]
            if best is None or guesses < best:
                game_stats["best_guess_count"] = guesses
                game_stats["best_guess_users"] = [user_id]
            elif guesses == best:
                game_stats["best_guess_users"].append(user_id)

        _save(AGG_STATS, self.stats)

    # -------------------------
    # User progress
    # -------------------------

    def _load_user_progress(self, user_id: str, game_name: str) -> dict:
        users = _load(USER_PROGRESS, {})
        return users.get(user_id, {}).get(game_name, {})

    def _save_user_progress(self, user_id: str, game_name: str, progress: dict):
        users = _load(USER_PROGRESS, {})
        users.setdefault(user_id, {})[game_name] = progress
        _save(USER_PROGRESS, users)


class DailyGame:
    name: str

    def select_daily_seed(self, history: list):
        raise NotImplementedError

    def apply_guess(self, progress: dict, guess: str):
        raise NotImplementedError
