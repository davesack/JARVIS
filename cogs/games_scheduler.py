from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import discord
from discord.ext import commands, tasks

from config import DATA_ROOT

ROOT = DATA_ROOT / "games" / "wordle"
STATE_FILE = ROOT / "state.json"
WORDS_FILE = ROOT / "daily_words.txt"

POST_HOUR = 9  # change if you want

def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


class GamesScheduler(commands.Cog):
    """Daily Wordle Scheduler"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_word.start()

    @tasks.loop(hours=24)
    async def daily_word(self):
        today = date.today().isoformat()
        words = [
            w.strip()
            for w in WORDS_FILE.read_text(encoding="utf-8").splitlines()
            if len(w.strip()) == 5
        ]

        if not words:
            return

        word = random.choice(words)

        # Post to all guilds' wordle channels
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.name == "wordle":
                    await channel.send(
                        "🟩 **Daily Wordle**\n"
                        "Guess the 5-letter word!"
                    )

    @daily_word.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        run = now.replace(hour=POST_HOUR, minute=0, second=0, microsecond=0)
        if run <= now:
            run += timedelta(days=1)
        await discord.utils.sleep_until(run)


async def setup(bot: commands.Bot):
    await bot.add_cog(GamesScheduler(bot))
