# cogs/rankings_birthdays.py - UPDATED

from __future__ import annotations

import datetime
import json
import random
from pathlib import Path
from typing import Set

import discord
from discord.ext import commands, tasks

from utils.rankings.cache import RankingsCache
from utils.rankings.formatting import build_profile_embed
from utils.rankings.fun_facts import generate_fun_facts

from config import (
    BIRTHDAY_POST_CHANNEL_ID,
    BIRTHDAY_POST_HOUR,
    BIRTHDAY_POST_MINUTE,
    MEDIA_ROOT,
)

STATE_FILE = Path("data/rankings_birthday_state.json")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_posted_date": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


class RankingsBirthdays(commands.Cog):
    """Daily birthday autoposter with spotlight fallback."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = load_state()
        self.cache = RankingsCache()
        self.loader = self.cache.load()
        bot.loop.create_task(self._post_init())

    async def _post_init(self):
        await self.bot.wait_until_ready()
        await self._catch_up()
        self._birthday_task.start()

    async def _catch_up(self):
        """Check if we missed PAST days' posts and post if needed."""
        today = datetime.date.today()
        last_posted = self.state.get("last_posted_date")
        
        if not last_posted or last_posted != today.isoformat():
            now = datetime.datetime.now()
            
            if now.hour < BIRTHDAY_POST_HOUR:
                print(f"[Birthdays] Waiting for {BIRTHDAY_POST_HOUR}:00 to post today's birthdays")
                return
            
            print(f"[Birthdays] Catching up - last posted: {last_posted}, today: {today.isoformat()}")
            await self.run_autopost()

    @tasks.loop(minutes=1)
    async def _birthday_task(self):
        """Check every minute if it's time to post."""
        now = datetime.datetime.now()
        
        if now.hour == BIRTHDAY_POST_HOUR and now.minute == BIRTHDAY_POST_MINUTE:
            today = datetime.date.today().isoformat()
            
            if self.state.get("last_posted_date") == today:
                return
            
            print(f"[Birthdays] Autopost triggered at {now.hour}:{now.minute:02d}")
            await self.run_autopost()

    async def run_autopost(self):
        """Run the actual birthday post."""
        try:
            self.loader = self.cache.load()
        except Exception as e:
            print("[Birthdays] Loader error:", e)
            return

        today = datetime.date.today()
        matches = [
            e for e in self.loader.entries
            if e.birth_date
            and e.birth_date.month == today.month
            and e.birth_date.day == today.day
        ]

        channel = self.bot.get_channel(BIRTHDAY_POST_CHANNEL_ID)
        if not channel:
            print(f"[Birthdays] Channel {BIRTHDAY_POST_CHANNEL_ID} not found")
            return

        used_categories: Set[str] = set()

        if matches:
            print(f"[Birthdays] Posting {len(matches)} birthdays")
            for entry in matches:
                # Always use 2 fun facts, never duplicate
                facts = generate_fun_facts(
                    entry,
                    self.loader.entries,
                    today=today,
                    used_categories=used_categories,
                    max_facts=2,
                )
                
                embed, hero_file, _ = await build_profile_embed(
                    entry,
                    nsfw_allowed=True,
                    media_root=Path(MEDIA_ROOT),
                    fun_facts=facts,
                    on_date=today,
                    all_entries=self.loader.entries,
                )
                
                if hero_file:
                    await channel.send(embed=embed, file=hero_file)
                else:
                    await channel.send(embed=embed)
        else:
            print("[Birthdays] No birthdays, posting spotlight")
            await self._spotlight(channel, today, used_categories)

        self.state["last_posted_date"] = today.isoformat()
        save_state(self.state)
        print(f"[Birthdays] Autopost complete, saved state: {today.isoformat()}")

    async def _spotlight(
        self,
        channel: discord.TextChannel,
        today: datetime.date,
        used_categories: Set[str],
    ):
        """Post spotlight birthdays for people with unknown birth years."""
        # Send announcement message first
        await channel.send("🎈 **No Birthdays Today. Let's celebrate some Spotlight Birthdays instead!**")
        
        unknowns = [
            e for e in self.loader.entries
            if not e.birth_date or e.birth_date.year in (1, 1000)
        ]

        if not unknowns:
            return

        picks = random.sample(unknowns, min(2, len(unknowns)))

        for entry in picks:
            # Always use 2 fun facts, never duplicate
            facts = generate_fun_facts(
                entry,
                self.loader.entries,
                today=today,
                used_categories=used_categories,
                max_facts=2,
            )
            
            embed, hero_file, _ = await build_profile_embed(
                entry,
                nsfw_allowed=True,
                media_root=Path(MEDIA_ROOT),
                fun_facts=facts,
                on_date=today,
                all_entries=self.loader.entries,
            )
            
            if hero_file:
                await channel.send(embed=embed, file=hero_file)
            else:
                await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RankingsBirthdays(bot))
