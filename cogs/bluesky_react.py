# cogs/bluesky_react.py

"""
Bluesky React & Save — MediaWatcher 4.0 Integration

React with 🍑, 💾, or 🔞 on Bluesky posts to save media.
This cog is USER-INITIATED ONLY and never posts to channels.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, List

import discord
from discord.ext import commands

from config import DISCORD_OWNER_ID, MEDIA_ROOT, MEDIAWATCHER_DATA, DROPBOX_WATCH_ROOT
from utils.bluesky.api import BlueskyAPI
from utils.bluesky.media import download_media_for_feed_item
from utils.mediawatcher.mediawatcher import create_mediawatcher

# Shared state (handle → slug mapping)
from utils.bluesky.state import get_shared_state

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Emoji triggers
# ──────────────────────────────────────────────────────────────
PEACH_EMOJI = "🍑"   # Full UI prompt
FLOPPY_EMOJI = "💾"  # Quick save (SFW)
NSFW_EMOJI = "🔞"    # Quick save (NSFW)


class BlueskyReactCog(commands.Cog):
    """
    React to Bluesky embeds in Discord and save media via MediaWatcher.

    This cog:
      • Listens for reactions
      • Resolves Bluesky post → feed item
      • Downloads media
      • Hands files to MediaWatcher

    It NEVER posts content or modifies monitor state.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BlueskyAPI()
        self.state = get_shared_state()

        self.mediawatcher = create_mediawatcher(
            media_root=MEDIA_ROOT,
            data_root=MEDIAWATCHER_DATA,
            incoming_dir=MEDIA_ROOT / "_incoming",
            dropbox_dir=DROPBOX_WATCH_ROOT,
        )

        logger.info("[BlueskyReact] Initialized with MediaWatcher")

    # ──────────────────────────────────────────────────────────
    # REACTION LISTENER
    # ──────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Owner-only safety
        if payload.user_id != DISCORD_OWNER_ID:
            return

        emoji = str(payload.emoji)
        if emoji not in {PEACH_EMOJI, FLOPPY_EMOJI, NSFW_EMOJI}:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Must be a Bluesky embed
        if not message.embeds:
            return

        embed = message.embeds[0]
        if not embed.title or "🦋" not in embed.title:
            return

        post_url = self._extract_post_url(embed)
        if not post_url:
            logger.warning("[BlueskyReact] No post URL found in embed")
            return

        handle = self._extract_handle_from_url(post_url)
        if not handle:
            logger.warning("[BlueskyReact] Failed to parse handle from URL")
            return

        user = self.bot.get_user(payload.user_id)
        if not user:
            return

        if emoji == PEACH_EMOJI:
            await self._handle_peach(user, message, handle, post_url)
        elif emoji == FLOPPY_EMOJI:
            await self._handle_quick_save(user, message, handle, post_url, nsfw=False)
        elif emoji == NSFW_EMOJI:
            await self._handle_quick_save(user, message, handle, post_url, nsfw=True)

    # ──────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _extract_post_url(embed: discord.Embed) -> Optional[str]:
        for field in embed.fields:
            if "View Post" in field.name and field.value:
                match = re.search(r"\((https?://[^)]+)\)", field.value)
                if match:
                    return match.group(1)
        return None

    @staticmethod
    def _extract_handle_from_url(url: str) -> Optional[str]:
        # https://bsky.app/profile/{handle}/post/{rkey}
        parts = url.split("/")
        if len(parts) >= 6:
            return parts[4]
        return None

    async def _fetch_feed_item(self, handle: str, post_url: str) -> Optional[dict]:
        feed_response = await self.api.get_author_feed(handle, limit=50)
        
        # Handle both dict and list responses
        if isinstance(feed_response, dict):
            feed_items = feed_response.get("feed", [])
        elif isinstance(feed_response, list):
            feed_items = feed_response
        else:
            return None
        
        from utils.bluesky.embed_builder import build_bsky_url

        for item in feed_items:
            post = item.get("post") or {}
            if build_bsky_url(post) == post_url:
                return item
        return None

    # ──────────────────────────────────────────────────────────
    # 🍑 FULL UI FLOW
    # ──────────────────────────────────────────────────────────
    async def _handle_peach(self, user, message, handle, post_url):
        try:
            feed_item = await self._fetch_feed_item(handle, post_url)
            if not feed_item:
                await user.send("⚠️ Could not locate this post on Bluesky.")
                return

            images, videos, thumb, _, _ = await download_media_for_feed_item(
                self.api, feed_item
            )

            if not images and not videos:
                await user.send("⚠️ No media found in this post.")
                return

        except Exception as e:
            logger.exception("[BlueskyReact] Peach flow failed")
            await user.send(f"❌ Error fetching media: {e}")
            return

        view = BlueskyDownloadView(
            self.mediawatcher,
            handle,
            post_url,
            feed_item,
            images,
            videos,
            thumb,
            original_message=message,
            original_user=user,
        )

        embed = discord.Embed(
            title="📥 Save Bluesky Media",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Handle", value=f"`@{handle}`", inline=True)
        embed.add_field(name="Media Files", value=str(len(images) + len(videos)), inline=True)
        embed.add_field(name="Post", value=f"[View on Bluesky]({post_url})", inline=False)

        if thumb and thumb.exists():
            file = discord.File(thumb, filename=thumb.name)
            embed.set_thumbnail(url=f"attachment://{thumb.name}")
            await user.send(embed=embed, file=file, view=view)
        else:
            await user.send(embed=embed, view=view)

    # ──────────────────────────────────────────────────────────
    # 💾 / 🔞 QUICK SAVE FLOW
    # ──────────────────────────────────────────────────────────
    async def _handle_quick_save(self, user, message, handle, post_url, nsfw: bool):
        normalized = handle.lstrip("@").lower()
        slug = self.state.slug_map.get(normalized)

        if not slug:
            await user.send(
                f"⚠️ `@{normalized}` is not mapped yet.\n"
                "Use `/bsky map add` before using quick-save reactions."
            )
            return

        try:
            feed_item = await self._fetch_feed_item(handle, post_url)
            if not feed_item:
                await user.send("⚠️ Could not locate this post.")
                return

            images, videos, _, _, post_uri = await download_media_for_feed_item(
                self.api, feed_item
            )

        except Exception as e:
            await user.send(f"❌ Error fetching media: {e}")
            return

        files = images + videos
        if not files:
            await user.send("⚠️ No media found.")
            return

        results = []
        post_id = post_uri.split("/")[-1] if post_uri else "unknown"

        for file in files:
            results.append(
                self.mediawatcher.ingest_from_bluesky(
                    file_path=file,
                    handle=normalized,
                    post_url=post_url,
                    post_id=post_id,
                    slug=slug,
                    nsfw=nsfw,
                )
            )

        success = sum(1 for r in results if r.success)
        errors = len(results) - success

        embed = discord.Embed(
            title="✅ Quick Save Complete" if errors == 0 else "⚠️ Quick Save Partial",
            color=discord.Color.green() if errors == 0 else discord.Color.orange(),
        )
        embed.add_field(name="Success", value=str(success), inline=True)
        embed.add_field(name="Errors", value=str(errors), inline=True)

        await user.send(embed=embed)

        try:
            await message.remove_reaction(NSFW_EMOJI if nsfw else FLOPPY_EMOJI, user)
        except discord.Forbidden:
            pass


# ──────────────────────────────────────────────────────────────
# UI CLASSES - COMPLETE IMPLEMENTATION
# ──────────────────────────────────────────────────────────────

class BlueskyDownloadView(discord.ui.View):
    """
    Full UI for selecting slug and saving media from Bluesky posts.
    
    Features:
    - Slug selection dropdown
    - NSFW toggle
    - Save button
    - Cancel button
    """

    def __init__(self, mediawatcher, handle, post_url, feed_item,
                 image_paths, video_paths, thumb_path,
                 original_message=None, original_user=None):
        super().__init__(timeout=300)
        self.mediawatcher = mediawatcher
        self.handle = handle
        self.post_url = post_url
        self.feed_item = feed_item
        self.image_paths = image_paths
        self.video_paths = video_paths
        self.thumb_path = thumb_path
        self.original_message = original_message
        self.original_user = original_user
        
        self.selected_slug: Optional[str] = None
        self.nsfw: bool = False
        
        # Add slug selector
        self.add_item(SlugSelector(mediawatcher))

    @discord.ui.button(label="NSFW", style=discord.ButtonStyle.secondary, emoji="🔞")
    async def toggle_nsfw(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle NSFW flag"""
        self.nsfw = not self.nsfw
        
        # Update button style
        if self.nsfw:
            button.style = discord.ButtonStyle.danger
            button.label = "NSFW ✓"
        else:
            button.style = discord.ButtonStyle.secondary
            button.label = "NSFW"
        
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="💾")
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Save the media files"""
        if not self.selected_slug:
            await interaction.response.send_message(
                "⚠️ Please select a slug first!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Process files
        files = self.image_paths + self.video_paths
        post = self.feed_item.get("post") or {}
        post_uri = post.get("uri", "")
        post_id = post_uri.split("/")[-1] if post_uri else "unknown"
        
        results = []
        for file_path in files:
            result = self.mediawatcher.ingest_from_bluesky(
                file_path=file_path,
                handle=self.handle,
                post_url=self.post_url,
                post_id=post_id,
                slug=self.selected_slug,
                nsfw=self.nsfw,
            )
            results.append(result)
        
        # Build result embed
        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count
        
        embed = discord.Embed(
            title="✅ Save Complete" if error_count == 0 else "⚠️ Save Partial",
            color=discord.Color.green() if error_count == 0 else discord.Color.orange(),
        )
        embed.add_field(name="Slug", value=self.selected_slug, inline=True)
        embed.add_field(name="NSFW", value="Yes" if self.nsfw else "No", inline=True)
        embed.add_field(name="Success", value=str(success_count), inline=True)
        embed.add_field(name="Errors", value=str(error_count), inline=True)
        
        # Show errors if any
        if error_count > 0:
            error_msgs = []
            for r in results:
                if not r.success and r.error:
                    error_msgs.append(f"• {r.original_path.name}: {r.error}")
            
            if error_msgs:
                embed.add_field(
                    name="Error Details",
                    value="\n".join(error_msgs[:5]),  # Max 5 errors
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Clean up reactions
        if self.original_message:
            try:
                await self.original_message.remove_reaction(PEACH_EMOJI, self.original_user)
            except:
                pass
        
        # Disable view
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the operation"""
        await interaction.response.send_message("❌ Cancelled", ephemeral=True)
        self.stop()


class SlugSelector(discord.ui.Select):
    """Dropdown for selecting which slug to save media under"""
    
    def __init__(self, mediawatcher):
        # Get all available slugs
        all_slugs = mediawatcher.get_all_slugs()
        
        # Create options (Discord limit: 25 max)
        options = []
        for slug in all_slugs[:25]:
            options.append(
                discord.SelectOption(
                    label=slug,
                    value=slug,
                    description=f"Save as {slug}"
                )
            )
        
        if not options:
            options.append(
                discord.SelectOption(
                    label="No slugs available",
                    value="none",
                    description="Add people to your database first"
                )
            )
        
        super().__init__(
            placeholder="Select a slug...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Update parent view's selected slug
        view: BlueskyDownloadView = self.view
        view.selected_slug = self.values[0]
        
        await interaction.response.send_message(
            f"✅ Selected: `{self.values[0]}`",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BlueskyReactCog(bot))
