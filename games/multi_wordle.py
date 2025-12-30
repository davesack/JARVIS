# utils/games/multi_wordle.py

from typing import List

WORD_LENGTH = 5


def score_guess(guess: str, solution: str) -> List[str]:
    """
    Wordle-style scoring:
    🟩 correct position
    🟨 present elsewhere
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
