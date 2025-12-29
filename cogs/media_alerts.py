# cogs/media_alerts.py
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks

from config import DISCORD_OWNER_ID
from utils.mediawatcher.event_logger import (
    read_events_since,
    get_current_offset,
)
from utils.mediawatcher.tag_extractor import get_manual_tags_for_file  # ✅ FIXED IMPORT
from utils.mediawatcher.tagging_prompter import maybe_offer_tag_prompt


class MediaAlerts(commands.Cog):
    """
    Watches the MediaWatcher event log and DMs the bot owner when new
    media is ingested, along with tags and a thumbnail if available.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.alert_task.start()

    def cog_unload(self):
        self.alert_task.cancel()

    # ---------------------------- Event Loop ----------------------------

    @tasks.loop(seconds=5)
    async def alert_task(self):
        """
        Every 5 seconds check event log for new ingest successes.
        """
        try:
            offset = get_current_offset()
            events = read_events_since(offset)

            if not events:
                return

            owner = self.bot.get_user(DISCORD_OWNER_ID)
            if not owner:
                return

            for evt in events:
                if evt.get("event") != "ingest_success":
                    continue

                file_path = Path(evt["final_path"])
                slug = evt.get("slug", "unknown")
                tags = get_manual_tags_for_file(file_path, slug)  # ✅ CORRECT USAGE

                await self._send_alert(owner, file_path, slug, tags)

                # Offer tagging prompt through global interceptor system
                await maybe_offer_tag_prompt(
                    owner, [file_path], None
                )

        except Exception as exc:
            print(f"[MediaAlerts] alert_task loop error: {exc}")

    # ---------------------------- Helper ----------------------------

    async def _send_alert(
        self,
        user: discord.User,
        path: Path,
        slug: str,
        tags: list[str],
    ):
        """
        Sends a DM to the bot owner with media file info, tags, and thumbnail.
        """
        embed = discord.Embed(
            title="📁 New Media Ingested",
            description=f"`{path.name}`\nSlug: **{slug}**",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Tags",
            value=", ".join(tags) if tags else "*None*",
            inline=False,
        )

        # Attach thumbnail if exists
        thumb_dir = path.parent / "thumbnails"
        thumb = thumb_dir / f"{path.stem}-thumb.jpg"

        files = None
        if thumb.exists():
            embed.set_image(url=f"attachment://{thumb.name}")
            files = [discord.File(thumb, filename=thumb.name)]

        try:
            await user.send(embed=embed, files=files)
        except Exception as exc:
            print(f"[MediaAlerts] Failed to DM owner: {exc}")

    # ---------------------------- Startup Wait ----------------------------

    @alert_task.before_loop
    async def before_alert_task(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(MediaAlerts(bot))