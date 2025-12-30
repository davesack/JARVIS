from __future__ import annotations

from typing import Dict, List, Tuple
from collections import defaultdict

from utils.games.words import get_absurdle_pool

WORD_LENGTH = 5


class DailyAbsurdle:
    """
    DAILY Absurdle implementation.

    - Adversarial pruning
    - Unlimited guesses
    - 5-letter words only
    - No plurals
    - Shared daily pool
    """

    name = "absurdle"

    # -------------------------
    # Daily seed selection
    # -------------------------

    def select_daily_seed(self, history: List[str]) -> str:
        """
        Absurdle doesn't use a traditional seed.
        We just tag the day for determinism.
        """
        return "absurdle_pool_v1"

    # -------------------------
    # Guess application
    # -------------------------

    def apply_guess(self, progress: Dict, guess: str) -> Dict:
        guess = guess.lower().strip()

        # Initialize progress
        if not progress:
            progress = {
                "guesses": [],
                "remaining": self._initial_pool(),
                "completed": False,
                "success": False,
            }

        if progress["completed"]:
            return progress

        if not self._is_valid_guess(guess):
            progress["error"] = "Guess must be a valid 5-letter word."
            return progress

        pool = progress["remaining"]

        # Partition pool by score pattern
        partitions = defaultdict(list)
        for word in pool:
            score = self._score_guess(guess, word)
            partitions[tuple(score)].append(word)

        # Choose the most evil partition (largest)
        worst_score, worst_pool = max(
            partitions.items(),
            key=lambda item: len(item[1])
        )

        progress["guesses"].append(
            {
                "guess": guess,
                "score": list(worst_score),
                "remaining": len(worst_pool),
            }
        )

        progress["remaining"] = worst_pool

        # Win condition: only one word left AND guess matches it
        if len(worst_pool) == 1 and guess == worst_pool[0]:
            progress["completed"] = True
            progress["success"] = True

        return progress

    # -------------------------
    # Rendering
    # -------------------------

    def render_feedback(self, progress: Dict) -> str:
        rows = []

        for entry in progress.get("guesses", []):
            grid = "".join(entry["score"])
            rows.append(f"{grid}  🧠 {entry['remaining']} remaining")

        footer = ""
        if progress.get("completed") and progress.get("success"):
            footer = "🏆 **You beat Absurdle. Respect.**"

        return "\n".join(rows) + ("\n\n" + footer if footer else "")

    # -------------------------
    # Internal helpers
    # -------------------------

    def _initial_pool(self) -> List[str]:
        """
        Deterministic starting pool for the day.
        """
        return list(get_absurdle_pool())

    def _is_valid_guess(self, word: str) -> bool:
        return (
            len(word) == WORD_LENGTH
            and word.isalpha()
        )

    def _score_guess(self, guess: str, solution: str) -> List[str]:
        """
        Wordle-style scoring:
        🟩 correct
        🟨 present
        ⬛ absent
        """
        result = ["⬛"] * WORD_LENGTH
        solution_chars = list(solution)

        # Greens
        for i, char in enumerate(guess):
            if char == solution[i]:
                result[i] = "🟩"
                solution_chars[i] = None

        # Yellows
        for i, char in enumerate(guess):
            if result[i] == "🟩":
                continue
            if char in solution_chars:
                result[i] = "🟨"
                solution_chars[solution_chars.index(char)] = None

        return result
