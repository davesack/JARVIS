from __future__ import annotations

from typing import Dict, List
from utils.games.words import get_betweenle_pool
from utils.games.daily_engine import _load, DAILY_CURRENT

MAX_GUESSES = 20


class DailyBetweenle:
    name = "betweenle"

    # -------------------------
    # Daily seed selection
    # -------------------------

    def select_daily_seed(self, history: List[str]) -> str:
        pool = sorted(get_betweenle_pool())
        unused = [w for w in pool if w not in history]
        return unused[0] if unused else pool[0]

    # -------------------------
    # Guess application
    # -------------------------

    def apply_guess(self, progress: Dict, guess: str) -> Dict:
        guess = guess.lower().strip()

        if not progress:
            pool = sorted(get_betweenle_pool())
            secret = self._get_secret()

            progress = {
                "secret": secret,
                "lo": pool[0],
                "hi": pool[-1],
                "guesses": [],
                "completed": False,
                "success": False,
                "max_guesses": MAX_GUESSES,
            }

        if progress["completed"]:
            return progress

        if not self._is_valid_guess(guess):
            progress["error"] = "Guess must be a valid 5-letter word."
            return progress

        lo, hi, secret = progress["lo"], progress["hi"], progress["secret"]

        if not (lo < guess < hi):
            progress["error"] = f"Guess must be between **{lo}** and **{hi}**."
            return progress

        if guess == secret:
            progress["guesses"].append({"guess": guess, "result": "🎉 correct"})
            progress["completed"] = True
            progress["success"] = True
            return progress

        if guess < secret:
            direction = "after"
            progress["lo"] = guess
        else:
            direction = "before"
            progress["hi"] = guess

        closer = self._closer(secret, progress["lo"], progress["hi"])

        progress["guesses"].append(
            {"guess": guess, "result": f"{direction} · closer to {closer}"}
        )

        if len(progress["guesses"]) >= MAX_GUESSES:
            progress["completed"] = True
            progress["success"] = False

        return progress

    # -------------------------
    # Rendering
    # -------------------------

    def render_feedback(self, progress: Dict) -> str:
        lines = [
            f"**{g['guess']}** → {g['result']}"
            for g in progress.get("guesses", [])
        ]

        footer = (
            f"\n📉 Range: **{progress['lo']} — {progress['hi']}**"
            f"\n🔢 Guesses: {len(progress['guesses'])}/{progress['max_guesses']}"
        )

        if progress["completed"]:
            footer += (
                "\n\n🏆 **Solved!**"
                if progress["success"]
                else f"\n\n❌ **Out of guesses.** Word was **{progress['secret']}**"
            )

        return "\n".join(lines) + footer

    # -------------------------
    # Helpers
    # -------------------------

    def _get_secret(self) -> str:
        current = _load(DAILY_CURRENT, {})
        return current["games"][self.name]["seed"]

    def _is_valid_guess(self, word: str) -> bool:
        return len(word) == 5 and word.isalpha() and not word.endswith("s")

    def _closer(self, secret: str, lo: str, hi: str) -> str:
        return "top" if secret < (lo + hi) // 2 else "bottom"
