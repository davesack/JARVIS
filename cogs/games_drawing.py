from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Dict

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import DATA_ROOT

# ============================================================
# CONFIG
# ============================================================

PROMPT_INTERVAL_HOURS = 24

PROMPTS = [
    "A dragon who is afraid of fire",
    "Your favorite animal as a superhero",
    "A house made out of candy",
    "A robot learning to cook",
    "A magical tree with glowing leaves",
    "A pirate cat",
    "A castle in the clouds",
    "An underwater city",
    "A monster who just wants a hug",
    "A flying school bus",
    "A dinosaur at a birthday party",
    "A wizard who lost their wand",
    "A snowman on vacation",
    "A time-traveling hamster",
]

# ============================================================
# STORAGE
# ============================================================

ROOT = DATA_ROOT / "games" / "drawing"
ROOT.mkdir(parents=True, exist_ok=True)

STATE_FILE = ROOT / "state.json"

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

class GamesDrawing(commands.Cog):
    """Daily rotating drawing prompt game"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state: Dict[str, Dict] = load_json(STATE_FILE, {})
        self.prompt_loop.start()

    def cog_unload(self):
        self.prompt_loop.cancel()

    # ========================================================
    # SLASH COMMAND
    # ========================================================

    async def start_drawing(self, interaction: discord.Interaction):
        cid = str(interaction.channel_id)

        if cid in self.state:
            await interaction.response.send_message(
                "âŒ A drawing game is already running here.",
                ephemeral=True,
            )
            return

        prompt = random.choice(PROMPTS)

        self.state[cid] = {
            "prompt": prompt,
            "last_post": time.time(),
        }

        save_json(STATE_FILE, self.state)

        await interaction.response.send_message(
            "ðŸŽ¨ **Drawing Prompt Game Started!**"
        )

        await interaction.channel.send(self._format_prompt(prompt))

    # ========================================================
    # LOOP
    # ========================================================

    @tasks.loop(minutes=10)
    async def prompt_loop(self):
        now = time.time()
        changed = False

        for cid, data in list(self.state.items()):
            if now - data["last_post"] < PROMPT_INTERVAL_HOURS * 3600:
                continue

            channel = self.bot.get_channel(int(cid))
            if not channel:
                continue

            prompt = random.choice(PROMPTS)
            data["prompt"] = prompt
            data["last_post"] = now

            await channel.send(self._format_prompt(prompt))
            changed = True

        if changed:
            save_json(STATE_FILE, self.state)

    @prompt_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    # ========================================================
    # HELPERS
    # ========================================================

    def _format_prompt(self, prompt: str) -> str:
        return (
            "ðŸ–Œï¸ **New Drawing Prompt!**\n\n"
            f"ðŸŽ¨ **{prompt}**\n\n"
            "Draw it however you like and post your art here!\n"
            "Traditional, digital, silly â€” everything is welcome ðŸ’›"
        )

# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesDrawing(bot))
