from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from typing import Set, List
import json
import random

# =========================================================
# BASE PATHS
# =========================================================

# Legacy / general games
DOCS_WORDS_ROOT = Path("docs/words")

# Daily games (Wordle, Scramble, Absurdle)
DAILY_WORDS_ROOT = Path("data/games/words")


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _load_word_file(path: Path) -> Set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing word file: {path}")

    with path.open("r", encoding="utf-8") as f:
        return {
            line.strip().lower()
            for line in f
            if line.strip() and not line.startswith("#")
        }


def _load_json_words(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON word file: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# =========================================================
# DICTIONARY (GENERAL VALIDATION)
# =========================================================

@lru_cache(maxsize=1)
def get_dictionary_5() -> set[str]:
    return set(_load_json_words(DAILY_WORDS_ROOT / "dictionary_5.json"))


@lru_cache(maxsize=1)
def get_full_english_dictionary() -> Set[str]:
    """
    Comprehensive English dictionary for general word validation.
    This is separate from Wordle/game-specific dictionaries.
    Used by channel games (alphabet, word chain, etc.)
    """
    dict_path = DAILY_WORDS_ROOT / "english_dictionary.txt"
    
    if dict_path.exists():
        # Load full dictionary
        with dict_path.open("r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}
    
    # Fallback: use 5-letter dictionary + other game dictionaries
    words = set()
    words.update(get_dictionary_5())
    try:
        words.update(get_scramble_pool())
    except:
        pass
    try:
        words.update(get_betweenle_pool())
    except:
        pass
    return words


def is_real_word(word: str) -> bool:
    """Validate if a word is real English (for channel games, not Wordle)."""
    return bool(word) and word.lower() in get_full_english_dictionary()


# =========================================================
# WORDLE (LEGACY / NON-DAILY)
# =========================================================

@lru_cache(maxsize=1)
def get_wordle_daily_words() -> List[str]:
    return sorted(_load_word_file(DOCS_WORDS_ROOT / "wordle_daily.txt"))


@lru_cache(maxsize=3)
def get_wordle_pool(difficulty: str) -> List[str]:
    file_map = {
        "easy": "wordle_easy.txt",
        "medium": "wordle_medium.txt",
        "hard": "wordle_hard.txt",
    }

    if difficulty not in file_map:
        raise ValueError("Invalid Wordle difficulty")

    return list(_load_word_file(DOCS_WORDS_ROOT / file_map[difficulty]))


# =========================================================
# HANGMAN
# =========================================================

@lru_cache(maxsize=3)
def get_hangman_words(difficulty: str) -> List[str]:
    file_map = {
        "easy": "hangman_easy.txt",
        "medium": "hangman_medium.txt",
        "hard": "hangman_hard.txt",
    }

    if difficulty not in file_map:
        raise ValueError("Invalid Hangman difficulty")

    return list(_load_word_file(DOCS_WORDS_ROOT / file_map[difficulty]))


def pick_hangman_word(difficulty: str) -> str:
    return random.choice(get_hangman_words(difficulty))


# =========================================================
# SCRAMBLE (LEGACY)
# =========================================================

@lru_cache(maxsize=1)
def get_scramble_words() -> List[str]:
    return list(_load_word_file(DOCS_WORDS_ROOT / "scramble.txt"))


def pick_scramble_word(min_length: int = 5) -> str:
    candidates = [w for w in get_scramble_words() if len(w) >= min_length]
    if not candidates:
        raise RuntimeError("No scramble words meet the minimum length")
    return random.choice(candidates)


# =========================================================
# DAILY GAME DICTIONARIES (AUTHORITATIVE)
# =========================================================

@lru_cache(maxsize=None)
def get_daily_wordle_pool(difficulty: str) -> List[str]:
    if difficulty == "common":
        return _load_json_words(DAILY_WORDS_ROOT / "wordle_common.json")
    if difficulty == "medium":
        return _load_json_words(DAILY_WORDS_ROOT / "wordle_medium.json")
    raise ValueError("Unknown daily Wordle difficulty")


@lru_cache(maxsize=None)
def get_daily_scramble_pool() -> List[str]:
    return _load_json_words(DAILY_WORDS_ROOT / "scramble_full.json")


@lru_cache(maxsize=None)
def get_absurdle_pool() -> List[str]:
    return _load_json_words(DAILY_WORDS_ROOT / "absurdle_full.json")


@lru_cache(maxsize=None)
def get_betweenle_dictionary() -> List[str]:
    """
    MUST be alphabetically sorted.
    """
    return _load_json_words(DAILY_WORDS_ROOT / "betweenle_full.json")


@lru_cache(maxsize=None)
def get_betweenle_pool() -> List[str]:
    return _load_json_words(DAILY_WORDS_ROOT / "betweenle_full.json")


# =========================
# PUBLIC POOLS (duplicated for compatibility)
# =========================

def get_wordle_pool(tier: str = "common") -> list[str]:
    if tier == "common":
        return _load_json_words(DAILY_WORDS_ROOT / "wordle_common.json")
    if tier == "medium":
        return _load_json_words(DAILY_WORDS_ROOT / "wordle_medium.json")
    raise ValueError(f"Unknown Wordle tier: {tier}")


def get_scramble_pool() -> list[str]:
    """
    8–12 letter words, no plurals.
    Used by DailyScramble.
    """
    return _load_json_words(DAILY_WORDS_ROOT / "scramble_full.json")


def get_betweenle_pool() -> list[str]:
    return _load_json_words(DAILY_WORDS_ROOT / "betweenle_full.json")


def get_absurdle_pool() -> list[str]:
    return _load_json_words(DAILY_WORDS_ROOT / "absurdle_full.json")
