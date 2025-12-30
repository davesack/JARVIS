from __future__ import annotations

from typing import Dict, Set
import random

from utils.games.words import get_wordle_pool
from utils.games.daily_wordle import DailyWordle


WORD_LENGTH = 5
TOTAL_BOARDS = 8
TOTAL_GUESSES = 16


class DailyWordleSequence:
    """
    Daily Wordle Sequence

    Rules:
    - 8 Wordle boards, solved sequentially
    - Only one board visible at a time
    - 16 total guesses shared across all boards
    - Letter information propagates forward ONLY after a board is solved
    """

    name = "wordle_sequence"

    # Optional aliases (safe even if GamesDaily ignores them)
    aliases = {"sequence", "ws"}


    # -------------------------
    # Daily Seed Selection
    # -------------------------

    def select_daily_seed(self, history: List[str]) -> str:
        """
        Select 8 words for the sequence.
        Returns a comma-separated string of words.
        """
        pool = get_wordle_pool("medium")
        
        # Filter out recently used sequences
        unused = [w for w in pool if w not in history]
        if len(unused) < TOTAL_BOARDS:
            unused = pool  # Reset if not enough words
        
        # Select 8 unique words
        selected = random.sample(unused, TOTAL_BOARDS)
        return ",".join(selected)
    # -------------------------
    # Initialization
    # -------------------------

    def initialize_progress(self) -> Dict:
        pool = get_wordle_pool("medium")
        solutions = random.sample(pool, TOTAL_BOARDS)

        return {
            "solutions": solutions,
            "current_board": 0,
            "remaining_guesses": TOTAL_GUESSES,
            "boards": [None] * TOTAL_BOARDS,
            "constraints": {
                "greens": {},     # position -> letter
                "yellows": {},    # letter -> forbidden positions
                "grays": set(),   # soft exclusions
            },
            "completed": False,
            "success": False,
        }

    # -------------------------
    # Guess application
    # -------------------------

    def apply_guess(self, progress: Dict, guess: str) -> Dict:
        if not progress:
            progress = self.initialize_progress()

        if progress["completed"]:
            return progress

        if progress["remaining_guesses"] <= 0:
            progress["completed"] = True
            progress["success"] = False
            return progress

        board_idx = progress["current_board"]

        if board_idx >= TOTAL_BOARDS:
            progress["completed"] = True
            progress["success"] = True
            return progress

        # Ensure board progress exists
        if not progress["boards"][board_idx]:
            progress["boards"][board_idx] = {}

        wordle = DailyWordle()

        # Force solution for this board
        wordle._get_solution = lambda: progress["solutions"][board_idx]

        board_progress = progress["boards"][board_idx]
        new_board_progress = wordle.apply_guess(board_progress, guess)

        progress["boards"][board_idx] = new_board_progress
        progress["remaining_guesses"] -= 1

        # Board solved â†’ extract constraints and advance
        if new_board_progress.get("completed") and new_board_progress.get("success"):
            extracted = self._extract_constraints(new_board_progress)
            self._merge_constraints(progress["constraints"], extracted)
            progress["current_board"] += 1

            if progress["current_board"] >= TOTAL_BOARDS:
                progress["completed"] = True
                progress["success"] = True

        # Out of guesses
        if progress["remaining_guesses"] <= 0 and not progress["completed"]:
            progress["completed"] = True
            progress["success"] = False

        return progress

    # -------------------------
    # Stats compatibility
    # -------------------------

    def get_guess_count(self, progress: Dict) -> int:
        """
        Used by DailyEngine for stats.
        """
        return TOTAL_GUESSES - progress["remaining_guesses"]

    # -------------------------
    # Constraint handling
    # -------------------------

    def _extract_constraints(self, board_progress: Dict) -> Dict:
        greens: Dict[int, str] = {}
        yellows: Dict[str, Set[int]] = {}
        grays: Set[str] = set()

        for entry in board_progress.get("guesses", []):
            guess = entry["guess"]
            score = entry["score"]

            for idx, (char, mark) in enumerate(zip(guess, score)):
                if mark == "ðŸŸ©":
                    greens[idx] = char
                elif mark == "ðŸŸ¨":
                    yellows.setdefault(char, set()).add(idx)
                elif mark == "â¬›":
                    grays.add(char)

        # Remove invalid grays
        for char in list(grays):
            if char in yellows or char in greens.values():
                grays.discard(char)

        return {
            "greens": greens,
            "yellows": yellows,
            "grays": grays,
        }

    def _merge_constraints(self, existing: Dict, new: Dict):
        # Greens override everything
        for idx, char in new["greens"].items():
            existing["greens"][idx] = char
            existing["yellows"].pop(char, None)
            existing["grays"].discard(char)

        # Yellows
        for char, positions in new["yellows"].items():
            if char in existing["greens"].values():
                continue
            existing["yellows"].setdefault(char, set()).update(positions)
            existing["grays"].discard(char)

        # Grays (soft exclusions)
        for char in new["grays"]:
            if (
                char not in existing["greens"].values()
                and char not in existing["yellows"]
            ):
                existing["grays"].add(char)

    # -------------------------
    # Rendering
    # -------------------------

    def render_feedback(self, progress: Dict) -> str:
        lines = []

        board_num = min(progress["current_board"] + 1, TOTAL_BOARDS)
        lines.append(f"Wordle Sequence â€” Board {board_num} / {TOTAL_BOARDS}")
        lines.append(f"Remaining guesses: {progress['remaining_guesses']}")
        lines.append("")

        c = progress["constraints"]

        if c["greens"] or c["yellows"] or c["grays"]:
            lines.append("Known from previous boards:")

            if c["greens"]:
                row = ["_"] * WORD_LENGTH
                for idx, char in c["greens"].items():
                    row[idx] = char.upper()
                lines.append("ðŸŸ© " + " ".join(row))

            for char, positions in c["yellows"].items():
                pos_list = ", ".join(str(p + 1) for p in sorted(positions))
                lines.append(f"ðŸŸ¨ {char.upper()} (not {pos_list})")

            if c["grays"]:
                lines.append("â¬› Not used: " + " ".join(sorted(c["grays"])))

            lines.append("")

        board_idx = progress["current_board"]
        board_progress = (
            progress["boards"][board_idx]
            if board_idx < TOTAL_BOARDS
            else None
        )

        if board_progress:
            for entry in board_progress.get("guesses", []):
                lines.append("".join(entry["score"]))

        if progress.get("completed"):
            lines.append("")
            if progress.get("success"):
                lines.append("ðŸ† **Sequence complete!**")
            else:
                lines.append("âŒ **Out of guesses.**")

        return "\n".join(lines)
