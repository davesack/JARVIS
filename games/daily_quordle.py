# utils/games/daily_quordle.py

from typing import Dict, List
import random

from utils.games.words import get_wordle_pool
from utils.games.multi_wordle import score_guess

WORD_LENGTH = 5
MAX_GUESSES = 9


class DailyQuordle:
    name = "quordle"
    BOARDS = 4

    def select_daily_seed(self, history: List[str]) -> List[str]:
        pool = get_wordle_pool("medium")
        return random.sample(pool, self.BOARDS)

    def apply_guess(self, progress: Dict, guess: str) -> Dict:
        guess = guess.lower().strip()

        if not progress:
            progress = {
                "solutions": self.select_daily_seed([]),
                "guesses": [],
                "completed": False,
                "success": False,
            }

        if progress["completed"]:
            return progress

        if len(guess) != WORD_LENGTH or not guess.isalpha():
            progress["error"] = "Guess must be a valid 5-letter word."
            return progress

        scores = [
            "".join(score_guess(guess, sol))
            for sol in progress["solutions"]
        ]

        progress["guesses"].append(scores)

        solved = [guess == sol for sol in progress["solutions"]]

        if all(solved):
            progress["completed"] = True
            progress["success"] = True
        elif len(progress["guesses"]) >= MAX_GUESSES:
            progress["completed"] = True
            progress["success"] = False

        return progress

    def render_feedback(self, progress: Dict) -> str:
        lines = []

        for row in progress["guesses"]:
            lines.append("   ".join(row))

        footer = f"\n🔢 Guesses: {len(progress['guesses'])}/{MAX_GUESSES}"

        if progress["completed"]:
            footer += "\n🏆 **Solved!**" if progress["success"] else "\n❌ **Out of guesses.**"

        return "\n".join(lines) + footer
