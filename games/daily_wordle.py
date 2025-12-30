from __future__ import annotations

from typing import Dict, List
import random

from utils.games.words import get_wordle_pool


WORD_LENGTH = 5
MAX_GUESSES = 6


class DailyWordle:
    """
    DAILY Wordle implementation.

    Engine guarantees:
    - one shared solution per day
    - no public guessing
    - first solve tracking
    """

    name = "wordle"

    # -------------------------
    # Daily seed selection
    # -------------------------

    def select_daily_seed(self, history: List[str]) -> str:
        """
        Pick a word that has not been used recently.
        Falls back gracefully if pool is exhausted.
        """
        pool = get_wordle_pool("medium")

        unused = [w for w in pool if w not in history]
        if not unused:
            unused = pool  # unavoidable repeats

        return random.choice(unused)

    # -------------------------
    # Guess application
    # -------------------------

    def apply_guess(self, progress: Dict, guess: str) -> Dict:
        """
        Applies a guess and returns updated progress.
        Progress schema is owned by this game.
        """
        guess = guess.lower().strip()

        # Initialize progress if new
        if not progress:
            progress = {
                "guesses": [],
                "completed": False,
                "success": False,
                "letter_status": {},  # Track: correct, present, absent
            }

        if progress["completed"]:
            return progress

        if len(guess) != WORD_LENGTH or not guess.isalpha():
            progress["error"] = "Guess must be a valid 5-letter word."
            return progress

        # Check for duplicate guesses
        previous_guesses = [g["guess"] for g in progress.get("guesses", [])]
        if guess in previous_guesses:
            progress["error"] = f"You already guessed '{guess}'!"
            return progress

        solution = self._get_solution()

        score = self._score_guess(guess, solution)
        
        # Update letter tracking
        self._update_letter_status(progress, guess, score)
        
        progress["guesses"].append(
            {
                "guess": guess,
                "score": score,
            }
        )

        if guess == solution:
            progress["completed"] = True
            progress["success"] = True
        elif len(progress["guesses"]) >= MAX_GUESSES:
            progress["completed"] = True
            progress["success"] = False

        return progress

    # -------------------------
    # Rendering
    # -------------------------

    def render_feedback(self, progress: Dict) -> str:
        """
        Render Wordle-style feedback with helpful letter tracking.
        """
        if progress.get("error"):
            return f"❌ {progress['error']}"
        
        rows = []
        
        # Show all previous guesses with their feedback
        for entry in progress.get("guesses", []):
            guess_word = entry["guess"].upper()
            emoji_row = "".join(entry["score"])
            rows.append(f"`{guess_word}` {emoji_row}")

        # Letter status summary
        letter_status = progress.get("letter_status", {})
        correct = [k.upper() for k, v in letter_status.items() if v == "correct"]
        present = [k.upper() for k, v in letter_status.items() if v == "present"]
        absent = [k.upper() for k, v in letter_status.items() if v == "absent"]

        rows.append("")  # Blank line
        
        if correct:
            rows.append(f"🟩 Correct: {' '.join(sorted(correct))}")
        if present:
            rows.append(f"🟨 Present: {' '.join(sorted(present))}")
        if absent:
            rows.append(f"⬛ Eliminated: {' '.join(sorted(absent))}")

        # Game status footer
        guesses_left = MAX_GUESSES - len(progress.get("guesses", []))
        rows.append(f"\n📊 Guesses remaining: {guesses_left}/{MAX_GUESSES}")

        footer = ""
        if progress.get("completed"):
            if progress.get("success"):
                footer = "\n\n🎉 **Solved!**"
            else:
                solution = self._get_solution()
                footer = f"\n\n❌ **Out of guesses.** The word was **{solution.upper()}**"

        return "\n".join(rows) + footer

    # -------------------------
    # Internal helpers
    # -------------------------

    def _get_solution(self) -> str:
        """
        Engine guarantees the same seed for all users.
        We re-derive it deterministically per day.
        """
        from utils.games.daily_engine import _load, DAILY_CURRENT

        current = _load(DAILY_CURRENT, {})
        return current["games"][self.name]["seed"]

    def _score_guess(self, guess: str, solution: str) -> List[str]:
        """
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

    def _update_letter_status(self, progress: Dict, guess: str, score: List[str]):
        """
        Track letter status: correct (in right spot), present (wrong spot), absent
        """
        letter_status = progress.get("letter_status", {})
        
        for i, (char, mark) in enumerate(zip(guess, score)):
            current_status = letter_status.get(char)
            
            # Priority: correct > present > absent
            if mark == "🟩":
                letter_status[char] = "correct"
            elif mark == "🟨" and current_status != "correct":
                letter_status[char] = "present"
            elif mark == "⬛" and current_status not in ["correct", "present"]:
                letter_status[char] = "absent"
        
        progress["letter_status"] = letter_status
