from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import discord

from config import MAX_DISCORD_FILE_SIZE_BYTES
from utils.bluesky.api import BlueskyAPI
from utils.bluesky.media import download_media_for_feed_item
from utils.bluesky.state import get_shared_state
from utils.bluesky.embed_builder import build_post_embed
from utils.ui.media_carousel import MediaCarouselView

log = logging.getLogger("bluesky.post_handler")

DISCORD_MAX_BYTES = MAX_DISCORD_FILE_SIZE_BYTES * 1024 * 1024


class PostHandler:
    """
    High-level orchestrator for posting Bluesky content to Discord.

    Responsibilities:
    - Enforce watermark / loop protection
    - Coordinate media download + embed construction
    - Use carousel for multiple images
    - Post videos in reply messages
    """

    def __init__(self, bot: discord.Client, api: BlueskyAPI):
        self.bot = bot
        self.api = api
        self.state = get_shared_state()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def handle_feed_item(
        self,
        channel: discord.TextChannel | discord.Thread,
        feed_item: dict,
    ) -> None:
        """
        Process a single feed item deterministically.
        """

        # --------------------------------------------------------------
        # Validate payload
        # --------------------------------------------------------------

        post = feed_item.get("post")
        if not isinstance(post, dict):
            return

        uri = post.get("uri")
        if not uri:
            return

        author = post.get("author") or {}
        handle = author.get("handle", "unknown").lower()

        # --------------------------------------------------------------
        # Watermark protection (CRITICAL)
        # --------------------------------------------------------------

        last_seen = self.state.get_last_seen_uri(handle)
        if last_seen and uri <= last_seen:
            log.debug("Skipping already-seen post %s", uri)
            return

        # --------------------------------------------------------------
        # Media download
        # --------------------------------------------------------------

        image_paths, video_paths, thumbnail_path, _, _ = (
            await download_media_for_feed_item(self.api, feed_item)
        )

        # --------------------------------------------------------------
        # Build embed
        # --------------------------------------------------------------

        has_video = bool(video_paths)
        video_too_large = any(p.stat().st_size > DISCORD_MAX_BYTES for p in video_paths)

        embed = build_post_embed(
            handle=handle,
            post=post,
            has_video=has_video,
            video_too_large=video_too_large,
        )

        # --------------------------------------------------------------
        # IMAGES: Use carousel for multiple, direct attach for single
        # --------------------------------------------------------------

        main_message = None

        if len(image_paths) > 1:
            # Multiple images → Use carousel
            view = MediaCarouselView(media_paths=image_paths, embed=embed)
            
            # Set first image
            first_file = discord.File(str(image_paths[0]), filename=image_paths[0].name)
            embed.set_image(url=f"attachment://{image_paths[0].name}")
            
            main_message = await channel.send(
                embed=embed,
                file=first_file,
                view=view,
            )
            
        elif len(image_paths) == 1:
            # Single image → Direct attach
            file = discord.File(str(image_paths[0]), filename=image_paths[0].name)
            embed.set_image(url=f"attachment://{image_paths[0].name}")
            
            main_message = await channel.send(
                embed=embed,
                file=file,
            )
            
        else:
            # No images → Just embed
            main_message = await channel.send(embed=embed)

        # --------------------------------------------------------------
        # VIDEOS: Post in reply to main message
        # --------------------------------------------------------------

        if video_paths and main_message:
            video_files = []
            
            for path in video_paths:
                try:
                    if path.stat().st_size <= DISCORD_MAX_BYTES:
                        video_files.append(discord.File(path))
                    else:
                        log.warning("Video too large for Discord: %s", path)
                except Exception:
                    log.exception("Failed attaching video %s", path)
            
            if video_files:
                try:
                    await main_message.reply(files=video_files)
                except Exception:
                    log.exception("Failed posting video reply")

        # --------------------------------------------------------------
        # Advance watermark AFTER successful send
        # --------------------------------------------------------------

        self.state.set_last_seen_uri(handle, uri)


# ==================================================================
# FUNCTIONAL ADAPTER – REQUIRED BY bluesky_monitor
# ==================================================================

async def send_item_to_channel(
    channel: discord.TextChannel | discord.Thread,
    api: BlueskyAPI,
    feed_item: dict,
) -> None:
    """
    Stateless wrapper used by the Bluesky monitor loop.
    """
    bot = channel.guild._state._get_client()
    handler = PostHandler(bot=bot, api=api)
    await handler.handle_feed_item(channel, feed_item)
