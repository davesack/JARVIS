# utils/games/daily_scramble.py

from __future__ import annotations

import random
from typing import Dict, List

from utils.games.words import get_scramble_pool


class DailyScramble:
    """
    DAILY Scramble game.

    Rules:
    - One shared scrambled word per day
    - Unlimited attempts
    - First correct solve wins
    - Private thread only
    """

    name = "scramble"

    # -------------------------
    # Daily seed selection
    # -------------------------

    def select_daily_seed(self, history: List[str]) -> str:
        """
        Select a word not recently used.
        """
        pool = get_scramble_pool()

        unused = [w for w in pool if w not in history]
        if not unused:
            unused = pool

        return random.choice(unused)

    # -------------------------
    # Guess application
    # -------------------------

    def apply_guess(self, progress: Dict, guess: str) -> Dict:
        guess = guess.lower().strip()

        # Initialize progress
        if not progress:
            progress = {
                "guesses": [],
                "completed": False,
                "success": False,
            }

        if progress["completed"]:
            return progress

        if not guess.isalpha():
            progress["error"] = "Guess must be a word."
            return progress

        solution = self._get_solution()
        progress["guesses"].append(guess)

        if guess == solution:
            progress["completed"] = True
            progress["success"] = True

        return progress

    # -------------------------
    # Rendering
    # -------------------------

    def render_feedback(self, progress: Dict) -> str:
        attempts = len(progress.get("guesses", []))
        header = f"🔤 **Daily Scramble** — Attempts: {attempts}"

        if progress.get("completed"):
            return f"{header}\n\n✅ **Solved!**"

        scrambled = self._scramble_word(self._get_solution())
        return f"{header}\n\nScrambled word:\n`{scrambled}`"

    # -------------------------
    # Internal helpers
    # -------------------------

    def _get_solution(self) -> str:
        from utils.games.daily_engine import _load, DAILY_CURRENT

        current = _load(DAILY_CURRENT, {})
        return current["games"][self.name]["seed_id"].split("_")[0]

    def _scramble_word(self, word: str) -> str:
        letters = list(word)
        random.shuffle(letters)
        return "".join(letters)
