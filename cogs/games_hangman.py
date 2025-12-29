from __future__ import annotations

import json
import random
import string
from pathlib import Path
from typing import Dict, Set

import discord
from discord import app_commands
from discord.ext import commands

from config import DATA_ROOT

# ============================================================
# STORAGE
# ============================================================

ROOT = DATA_ROOT / "games" / "hangman"
ROOT.mkdir(parents=True, exist_ok=True)

STATE_FILE = ROOT / "state.json"

# TEMP WORD LISTS (replace later)
WORDS = {
    "easy": ["apple", "house", "tiger", "pizza", "smile"],
    "medium": ["monster", "holiday", "sandbox", "elephant"],
    "hard": ["xylophone", "awkward", "buzzword", "knapsack"]
}

MAX_WRONG = 6

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


# ============================================================
# COG
# ============================================================

class GamesHangman(commands.Cog):
    """Turn-based Hangman"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state: Dict = load_json(STATE_FILE, {})

    # ========================================================
    # SLASH COMMANDS
    # ========================================================

    @app_commands.describe(
        difficulty="Difficulty",
        players="Number of players (1-3)"
    )
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name="easy", value="easy"),
            app_commands.Choice(name="medium", value="medium"),
            app_commands.Choice(name="hard", value="hard"),
        ]
    )
    async def hangman(
        self,
        interaction: discord.Interaction,
        difficulty: app_commands.Choice[str],
        players: int = 1,
    ):
        channel_id = str(interaction.channel_id)

        if channel_id in self.state:
            await interaction.response.send_message(
                "âŒ A Hangman game is already running here.",
                ephemeral=True,
            )
            return

        if not (1 <= players <= 3):
            await interaction.response.send_message(
                "Players must be between 1 and 3.",
                ephemeral=True,
            )
            return

        word = random.choice(WORDS[difficulty.value])
        self.state[channel_id] = {
            "word": word,
            "guessed": [],
            "wrong": 0,
            "last_user": None,
            "players": [],
            "max_players": players,
            "difficulty": difficulty.value,
        }

        save_json(STATE_FILE, self.state)

        await interaction.response.send_message(
            f"ðŸŽ® **Hangman started!**\n"
            f"Difficulty: **{difficulty.value.title()}**\n"
            f"Players: **{players}**\n"
            f"Type a letter to guess!"
        )

        await self._post_state(interaction.channel)

    # ========================================================
    # MESSAGE LISTENER
    # ========================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        cid = str(message.channel.id)
        if cid not in self.state:
            return

        game = self.state[cid]
        user_id = str(message.author.id)
        content = message.content.lower().strip()

        # Join players automatically
        if user_id not in game["players"]:
            if len(game["players"]) >= game["max_players"]:
                await message.delete()
                return
            game["players"].append(user_id)

        # Turn enforcement
        if game["last_user"] == user_id:
            await message.delete()
            return

        # Single letter only
        if len(content) != 1 or content not in string.ascii_lowercase:
            await message.delete()
            return

        if content in game["guessed"]:
            await message.delete()
            return

        game["guessed"].append(content)
        game["last_user"] = user_id

        if content not in game["word"]:
            game["wrong"] += 1

        # Check win/loss
        if self._is_won(game):
            await message.channel.send(
                f"ðŸŽ‰ **You won!** The word was **{game['word']}**"
            )
            del self.state[cid]
        elif game["wrong"] >= MAX_WRONG:
            await message.channel.send(
                f"ðŸ’€ **Game over!** The word was **{game['word']}**"
            )
            del self.state[cid]
        else:
            await self._post_state(message.channel)

        save_json(STATE_FILE, self.state)

    # ========================================================
    # HELPERS
    # ========================================================

    async def _post_state(self, channel: discord.TextChannel):
        game = self.state[str(channel.id)]
        display = " ".join(
            c if c in game["guessed"] else "_" for c in game["word"]
        )
        await channel.send(
            f"ðŸª¢ **Hangman**\n"
            f"`{display}`\n"
            f"Wrong guesses: {game['wrong']} / {MAX_WRONG}"
        )

    def _is_won(self, game) -> bool:
        return all(c in game["guessed"] for c in game["word"])


# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesHangman(bot))
