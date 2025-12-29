# cogs/media_people.py

from __future__ import annotations

import logging

import discord
from discord.ext import commands, tasks

from utils.mediawatcher.slug_engine import SlugEngine
from utils.mediawatcher.people_db_builder import (
    build_people_and_alias_db_from_rows,
)
from utils.rankings.loader import RankingsLoader

log = logging.getLogger(__name__)


class MediaPeople(commands.Cog):
    """
    MediaWatcher 3.0 – People / Slug identity auto-refresh.

    - Loads people.json & aliases.json from Google Sheets once every 24 hours.
    - Keeps bot.slug_engine up to date at all times.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Ensure a SlugEngine is available immediately (using whatever JSON exists)
        if not hasattr(bot, "slug_engine") or bot.slug_engine is None:
            bot.slug_engine = SlugEngine()

        self.refresh_people_db.start()

    def cog_unload(self):
        self.refresh_people_db.cancel()

    @tasks.loop(hours=24)
    async def refresh_people_db(self):
        try:
            log.info("[MediaWatcher] Refreshing people DB from Google Sheets...")

            # Use RankingsLoader to get the data
            loader = RankingsLoader()
            loader.load()
            
            if not loader.entries:
                log.warning("[MediaWatcher] No rankings data; skipping refresh.")
                return

            # Build header and rows from RankingEntry objects
            header = ["Name", "Slug", "Nationality", "State", "Notes"]
            rows = []
            for entry in loader.entries:
                row = [
                    entry.name,
                    entry.slug,
                    getattr(entry, 'nationality', ''),
                    getattr(entry, 'state', ''),
                    getattr(entry, 'notes', ''),
                ]
                rows.append(row)

            build_people_and_alias_db_from_rows(header, rows)

            # Reload SlugEngine with new JSON
            self.bot.slug_engine = SlugEngine()

            log.info("[MediaWatcher] People DB refresh complete and SlugEngine reloaded.")

        except Exception as e:
            log.exception("[MediaWatcher] Error refreshing people DB: %s", e)

    @refresh_people_db.before_loop
    async def before_refresh(self):
        log.info("[MediaWatcher] MediaPeople refresher waiting for bot ready...")
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(MediaPeople(bot))
