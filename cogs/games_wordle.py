from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from typing import Dict, List

import discord
from discord import app_commands
from discord.ext import commands

from config import DATA_ROOT

# ============================================================
# PATHS
# ============================================================

ROOT = DATA_ROOT / "games" / "wordle"
ROOT.mkdir(parents=True, exist_ok=True)

STATE_FILE = ROOT / "state.json"
STATS_FILE = ROOT / "stats.json"
WORDS_FILE = ROOT / "daily_words.txt"  # big list (we'll fill later)

MAX_ATTEMPTS = 6
WORD_LENGTH = 5

# ============================================================
# UTIL
# ============================================================

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_words() -> List[str]:
    if not WORDS_FILE.exists():
        return []
    return [
        w.strip().lower()
        for w in WORDS_FILE.read_text(encoding="utf-8").splitlines()
        if len(w.strip()) == WORD_LENGTH
    ]


def score_guess(guess: str, target: str) -> str:
    """Return emoji score string."""
    result = []
    used = [False] * WORD_LENGTH

    for i, c in enumerate(guess):
        if c == target[i]:
            result.append("ðŸŸ©")
            used[i] = True
        else:
            result.append(None)

    for i, c in enumerate(guess):
        if result[i]:
            continue
        if c in target:
            for j, tc in enumerate(target):
                if tc == c and not used[j]:
                    result[i] = "ðŸŸ¨"
                    used[j] = True
                    break
        if not result[i]:
            result[i] = "â¬›"

    return "".join(result)

# ============================================================
# COG
# ============================================================

class GamesWordle(commands.Cog):
    """Daily + Co-op Wordle"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state: Dict = load_json(STATE_FILE, {})
        self.stats: Dict = load_json(STATS_FILE, {})
        self.words = load_words()

    # ========================================================
    # SLASH COMMANDS
    # ========================================================

    async def wordle(self, interaction: discord.Interaction):
        cid = str(interaction.channel_id)

        if cid in self.state:
            await interaction.response.send_message(
                "âŒ A Wordle game is already running here.",
                ephemeral=True,
            )
            return

        if not self.words:
            await interaction.response.send_message(
                "âŒ Word list not available.",
                ephemeral=True,
            )
            return

        target = random.choice(self.words)

        self.state[cid] = {
            "word": target,
            "guesses": [],
            "players": [],
            "daily": False,
        }

        save_json(STATE_FILE, self.state)

        await interaction.response.send_message(
            "ðŸŸ© **Wordle started!**\n"
            f"Guess a **{WORD_LENGTH}-letter** word.\n"
            f"You have **{MAX_ATTEMPTS} attempts**."
        )

    # ========================================================
    # MESSAGE HANDLER
    # ========================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        cid = str(message.channel.id)
        if cid not in self.state:
            return

        game = self.state[cid]
        guess = message.content.lower().strip()

        if len(guess) != WORD_LENGTH or not guess.isalpha():
            return

        if guess in game["guesses"]:
            return

        game["guesses"].append(guess)

        uid = str(message.author.id)
        if uid not in game["players"]:
            game["players"].append(uid)

        grid = score_guess(guess, game["word"])
        await message.channel.send(f"`{guess}` â†’ {grid}")

        if guess == game["word"]:
            await self._finish_game(message.channel, win=True)
        elif len(game["guesses"]) >= MAX_ATTEMPTS:
            await self._finish_game(message.channel, win=False)

        save_json(STATE_FILE, self.state)

    # ========================================================
    # GAME END
    # ========================================================

    async def _finish_game(self, channel: discord.TextChannel, win: bool):
        cid = str(channel.id)
        game = self.state[cid]

        word = game["word"]
        attempts = len(game["guesses"])

        for uid in game["players"]:
            self._update_stats(uid, win, attempts)

        if win:
            await channel.send(
                f"ðŸŽ‰ **Solved!** The word was **{word}**\n"
                f"Attempts: {attempts}/{MAX_ATTEMPTS}"
            )
        else:
            await channel.send(
                f"ðŸ’€ **Failed!** The word was **{word}**"
            )

        del self.state[cid]
        save_json(STATE_FILE, self.state)
        save_json(STATS_FILE, self.stats)

    def _update_stats(self, user_id: str, win: bool, attempts: int):
        stats = self.stats.setdefault(user_id, {
            "wins": 0,
            "losses": 0,
            "played": 0,
        })

        stats["played"] += 1
        if win:
            stats["wins"] += 1
        else:
            stats["losses"] += 1


# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesWordle(bot))
