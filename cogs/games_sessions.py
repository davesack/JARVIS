from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Dict

import discord
from discord import app_commands
from discord.ext import commands

from config import DATA_ROOT
from utils.games.words import (
    is_real_word,
    pick_scramble_word,
)
from utils.games.game_stats import increment, set_best

# ============================================================
# PATHS
# ============================================================

ROOT = DATA_ROOT / "games" / "sessions"
ROOT.mkdir(parents=True, exist_ok=True)

STATE_FILE = ROOT / "state.json"

ROTATION = ["alphabet_race", "scramble", "number"]
MAX_NUMBER = 10_000

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


def scramble_word(word: str) -> str:
    letters = list(word)
    random.shuffle(letters)
    return "".join(letters)

# ============================================================
# COG
# ============================================================

class GamesSessions(commands.Cog):
    """Auto-rotating session games"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state: Dict[str, Dict] = load_json(STATE_FILE, {})

    # ========================================================
    # SLASH COMMANDS
    # ========================================================

    @app_commands.command(name="start_sessions", description="Start auto-rotating session games")
    async def start_sessions(self, interaction: discord.Interaction):
        cid = str(interaction.channel_id)

        if cid in self.state:
            await interaction.response.send_message(
                "⚠️ Games are already running in this channel.",
                ephemeral=True,
            )
            return

        self.state[cid] = {
            "rotation": ROTATION,
            "index": 0,
            "game": None,
            "last_user": None,
            "data": {},
        }

        save_json(STATE_FILE, self.state)

        await interaction.response.send_message(
            "🎮 **Game Sessions started!**\n"
            "Alphabet Race → Word Scramble → Guess the Number"
        )

        await self._start_next_game(interaction.channel)

    @app_commands.command(name="stop_sessions", description="[ADMIN] Stop auto-rotating session games")
    @app_commands.checks.has_permissions(administrator=True)
    async def stop_sessions(self, interaction: discord.Interaction):
        cid = str(interaction.channel_id)
        
        if cid not in self.state:
            await interaction.response.send_message(
                "⚠️ No session games are running in this channel.",
                ephemeral=True,
            )
            return
        
        del self.state[cid]
        save_json(STATE_FILE, self.state)
        
        await interaction.response.send_message(
            "🛑 **Session games stopped.**"
        )

    @stop_sessions.error
    async def stop_sessions_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need administrator permissions to stop session games.",
                ephemeral=True
            )

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

        session = self.state[cid]
        game = session["game"]

        if not game:
            return

        if session["last_user"] == str(message.author.id):
            await message.delete()
            return

        handler = {
            "alphabet_race": self._handle_alphabet_race,
            "scramble": self._handle_scramble,
            "number": self._handle_number,
        }.get(game)

        if handler:
            finished = await handler(message, session)
            if finished:
                await self._finish_game(message.channel)

        save_json(STATE_FILE, self.state)

    # ========================================================
    # GAME HANDLERS
    # ========================================================

    async def _handle_alphabet_race(self, message, session) -> bool:
        word = message.content.strip().lower()
        expected = session["data"]["next"]

        if not word.isalpha() or not is_real_word(word):
            await message.delete()
            return False

        if word[0] != expected:
            await message.delete()
            return False

        session["data"]["next"] = chr(ord(expected) + 1)
        session["data"]["players"].append(message.author.id)
        session["last_user"] = str(message.author.id)

        increment(message.author.id, "alphabet_race.words")

        if expected == "z":
            session["data"]["end"] = time.time()
            return True

        return False

    async def _handle_scramble(self, message, session) -> bool:
        guess = message.content.strip().lower()

        if guess != session["data"]["word"]:
            return False

        session["data"]["winner"] = message.author.id
        increment(message.author.id, "scramble.wins")
        return True

    async def _handle_number(self, message, session) -> bool:
        try:
            guess = int(message.content.strip())
        except ValueError:
            return False

        target = session["data"]["number"]
        session["last_user"] = str(message.author.id)

        if guess < target:
            await message.channel.send("⬆️ Higher")
        elif guess > target:
            await message.channel.send("⬇️ Lower")
        else:
            increment(message.author.id, "number.wins")
            return True

        return False

    # ========================================================
    # GAME FLOW
    # ========================================================

    async def _start_next_game(self, channel: discord.TextChannel):
        cid = str(channel.id)
        session = self.state[cid]

        game = session["rotation"][session["index"]]
        session["game"] = game
        session["last_user"] = None
        session["data"] = {}

        session["index"] = (session["index"] + 1) % len(session["rotation"])

        if game == "alphabet_race":
            session["data"] = {
                "next": "a",
                "players": [],
                "start": time.time(),
            }
            await channel.send("🏁 **Alphabet Race started!**\nType a real word starting with **A**.")

        elif game == "scramble":
            word = pick_scramble_word(min_length=5)
            session["data"] = {"word": word}
            await channel.send(
                f"🔀 **Word Scramble**\n"
                f"`{scramble_word(word).upper()}`"
            )

        elif game == "number":
            number = random.randint(1, MAX_NUMBER)
            session["data"] = {"number": number}
            await channel.send(
                f"🎲 **Guess the Number**\n"
                f"I'm thinking of a number between **1 and {MAX_NUMBER}**."
            )

    async def _finish_game(self, channel: discord.TextChannel):
        cid = str(channel.id)
        session = self.state[cid]
        game = session["game"]

        if game == "alphabet_race":
            elapsed = round(session["data"]["end"] - session["data"]["start"], 2)
            players = set(session["data"]["players"])

            for uid in players:
                increment(uid, "alphabet_race.games")

            record = set_best(
                min(players),
                "alphabet_race.best_time",
                elapsed,
            )

            await channel.send(
                f"🏁 **Alphabet Race finished!**\n"
                f"Time: **{elapsed}s**\n"
                f"Players: **{len(players)}**"
            )

            if record:
                await channel.send("🏆 **New server record!**")

        elif game == "scramble":
            await channel.send(
                f"🎉 **Solved!** Word was **{session['data']['word']}**"
            )

        elif game == "number":
            await channel.send(
                f"🎯 **Correct!** Number was **{session['data']['number']}**"
            )

        await channel.send("⏭️ Next game starting...")
        await self._start_next_game(channel)

# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesSessions(bot))
