# cogs/bluesky_commands.py

from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import List

from config import DEV_GUILD_ID, DISCORD_OWNER_ID
from utils.bluesky.api import BlueskyAPI
from utils.bluesky.state import get_shared_state

DEFAULT_INTERVAL_MINUTES = 5


def _normalize_handle(handle: str) -> str:
    return handle.lstrip("@").lower()


class BlueskyCommands(commands.Cog):
    """
    Slash commands for managing Bluesky subscriptions.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BlueskyAPI()
        self.state = get_shared_state()

    # ============================================================
    # COMMAND GROUP
    # ============================================================
    bsky = app_commands.Group(name="bsky", description="Bluesky monitoring commands")

    # ============================================================
    # Autocomplete helper
    # ============================================================
    async def handle_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for subscribed handles"""
        handles = self.state.list_handles()
        current_lower = current.lower()
        matches = [h for h in handles if current_lower in h.lower()][:25]
        return [app_commands.Choice(name=h, value=h) for h in matches]

    async def slug_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for media folder slugs."""
        from config import MEDIA_ROOT
        from pathlib import Path
        
        # Get all directories in MEDIA_ROOT (excluding special folders)
        media_root = Path(MEDIA_ROOT)
        slugs = []
        
        if media_root.exists():
            for item in sorted(media_root.iterdir()):
                if item.is_dir() and not item.name.startswith("_") and not item.name == "events":
                    slugs.append(item.name)
        
        # Filter by current input
        current_lower = current.lower()
        filtered = [s for s in slugs if current_lower in s.lower()]
        
        return [
            app_commands.Choice(name=s, value=s)
            for s in filtered[:25]
        ]

    # ============================================================
    # /bsky add
    # ============================================================
    @bsky.command(name="add", description="Follow a Bluesky handle")
    @app_commands.describe(handle="Bluesky handle (e.g., user.bsky.social)")
    async def add(self, interaction: discord.Interaction, handle: str):
        """
        Subscribe to a Bluesky handle.
        
        - Run in CHANNEL: Creates new thread and posts latest
        - Run in THREAD: Adds handle to existing thread
        """
        if not self.api.enabled:
            await interaction.response.send_message(
                ":no_entry_sign: Bluesky is disabled (missing access token).",
                ephemeral=True,
            )
            return

        normalized = _normalize_handle(handle)
        
        await interaction.response.defer(ephemeral=True)
        
        # Validate handle exists
        try:
            did = await self.api.resolve_handle(normalized)
        except Exception as e:
            await interaction.followup.send(
                f":x: Could not resolve Bluesky handle `@{normalized}`: {e}",
                ephemeral=True,
            )
            return
        
        # CASE 1: Run in a CHANNEL - create new thread
        if isinstance(interaction.channel, (discord.TextChannel, discord.ForumChannel)):
            # Create thread
            thread_name = f"🦋 bsky - {normalized}"
            
            try:
                thread = await interaction.channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread,
                )
            except Exception as e:
                await interaction.followup.send(
                    f":x: Could not create thread: {e}",
                    ephemeral=True,
                )
                return
            
            # Tag the user who created it
            await thread.send(f"{interaction.user.mention} created this subscription")
            
            # Save guild and parent channel info (needed to find threads later!)
            if not self.state.guild_id:
                self.state.guild_id = interaction.guild.id
            if not self.state.parent_channel_id:
                self.state.parent_channel_id = interaction.channel.id
            self.state._save_subscriptions()
            
            # Add subscription (or update existing one to this thread)
            existing = self.state.get_subscription(normalized)
            if existing:
                # Handle already followed - update to this thread
                self.state.set_thread_id(normalized, thread.id)
            else:
                # New subscription
                self.state.add_subscription(
                    handle=normalized,
                    thread_id=thread.id,
                    interval_minutes=DEFAULT_INTERVAL_MINUTES,
                )
            
			# Fetch and post latest
            try:
                response = await self.api.get_author_feed(did, limit=100)
                
                # Check if response is valid BEFORE using .get()
                if not isinstance(response, dict):
                    print(f"[BSKY] API error for @{normalized}: {response}")
                elif "feed" in response:
                    # FIX: Use full feed items, not just posts
                    feed_items = response.get("feed", [])
                    # Filter to non-replies
                    non_reply_items = [
                        item for item in feed_items
                        if "reply" not in item.get("post", {}).get("record", {})
                    ]
                    
                    if non_reply_items:
                        latest_item = non_reply_items[0]
                        # Use post_handler to properly handle media
                        from utils.bluesky.post_handler import send_item_to_channel
                        await send_item_to_channel(thread, self.api, latest_item)
                    else:
                        await thread.send(f"✅ Now following `@{normalized}`, but no recent non-reply posts found in last 100 posts.")
            except Exception as e:
                import traceback
                print(f"[BSKY] Could not fetch latest for @{normalized}: {e}")
                print(f"[BSKY] Full traceback:")
                traceback.print_exc()
            
            await interaction.followup.send(
                f":white_check_mark: Created thread and following `@{normalized}`",
                ephemeral=True,
            )
        
        # CASE 2: Run in a THREAD - add to existing thread
        elif isinstance(interaction.channel, discord.Thread):
            # Save guild and parent channel info (needed to find threads later!)
            if not self.state.guild_id:
                self.state.guild_id = interaction.guild.id
            if not self.state.parent_channel_id:
                self.state.parent_channel_id = interaction.channel.parent_id
            self.state._save_subscriptions()
            
            # Add subscription (or update existing one to this thread)
            existing = self.state.get_subscription(normalized)
            if existing:
                # Handle already followed - update to this thread
                self.state.set_thread_id(normalized, interaction.channel.id)
            else:
                # New subscription
                self.state.add_subscription(
                    handle=normalized,
                    thread_id=interaction.channel.id,
                    interval_minutes=DEFAULT_INTERVAL_MINUTES,
                )
            
			# Fetch and post latest
            try:
                response = await self.api.get_author_feed(did, limit=100)
                
                # Check if response is valid BEFORE using .get()
                if not isinstance(response, dict):
                    print(f"[BSKY] API error for @{normalized}: {response}")
                elif "feed" in response:
                    # FIX: Use full feed items, not just posts
                    feed_items = response.get("feed", [])
                    # Filter to non-replies
                    non_reply_items = [
                        item for item in feed_items
                        if "reply" not in item.get("post", {}).get("record", {})
                    ]
                    
                    if non_reply_items:
                        latest_item = non_reply_items[0]
                        # Use post_handler to properly handle media
                        from utils.bluesky.post_handler import send_item_to_channel
                        await send_item_to_channel(interaction.channel, self.api, latest_item)
                    else:
                        await interaction.channel.send(f"✅ Now following `@{normalized}`, but no recent non-reply posts found in last 100 posts.")
            except Exception as e:
                import traceback
                print(f"[BSKY] Could not fetch latest for @{normalized}: {e}")
                print(f"[BSKY] Full traceback:")
                traceback.print_exc()
            
            await interaction.followup.send(
                f":white_check_mark: Now following `@{normalized}` in this thread",
                ephemeral=True,
            )
        
        else:
            await interaction.followup.send(
                ":warning: This command must be run in a channel or thread.",
                ephemeral=True,
            )

    # ============================================================
    # /bsky remove
    # ============================================================
    @bsky.command(name="remove", description="Unfollow a Bluesky handle")
    @app_commands.describe(handle="Handle to unfollow (optional in thread)")
    @app_commands.autocomplete(handle=handle_autocomplete)
    async def remove(self, interaction: discord.Interaction, handle: str | None = None):
        """Unfollow a handle."""
        if isinstance(interaction.channel, discord.Thread) and not handle:
            sub = self.state.get_subscription_by_thread(interaction.channel.id)
            if sub:
                handle = sub.handle

        if not handle:
            await interaction.response.send_message(
                ":warning: Specify a handle or run this in a Bluesky thread.",
                ephemeral=True,
            )
            return

        normalized = _normalize_handle(handle)

        if not self.state.get_subscription(normalized):
            await interaction.response.send_message(
                f":warning: `@{normalized}` is not currently followed.",
                ephemeral=True,
            )
            return

        self.state.remove_subscription(normalized)

        await interaction.response.send_message(
            f":wastebasket: Unfollowed `@{normalized}`.",
            ephemeral=True,
        )

    # ============================================================
    # /bsky list
    # ============================================================
    @bsky.command(name="list", description="List all followed Bluesky handles")
    async def list_handles(self, interaction: discord.Interaction):
        """Show all active Bluesky subscriptions."""
        handles = self.state.list_handles()
        
        if not handles:
            await interaction.response.send_message(
                ":information_source: No Bluesky handles are currently being followed.",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title=":satellite: Bluesky Subscriptions",
            color=discord.Color.blue(),
        )
        
        for handle in handles:
            sub = self.state.get_subscription(handle)
            if sub:
                # Try to get the actual thread
                thread_info = "No thread"
                if sub.thread_id:
                    try:
                        thread = self.bot.get_channel(sub.thread_id)
                        if thread:
                            thread_info = f"<#{sub.thread_id}>"
                        else:
                            thread_info = f"Thread {sub.thread_id} (not found)"
                    except:
                        thread_info = f"Thread {sub.thread_id} (not accessible)"
                
                interval = sub.interval_minutes or DEFAULT_INTERVAL_MINUTES
                embed.add_field(
                    name=f"@{handle}",
                    value=f"{thread_info} | Every {interval}min",
                    inline=False,
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================================================
    # /bsky latest
    # ============================================================
    @bsky.command(name="latest", description="Post the latest non-reply from a Bluesky handle")
    @app_commands.describe(handle="Handle (optional in thread)")
    @app_commands.autocomplete(handle=handle_autocomplete)
    async def latest(self, interaction: discord.Interaction, handle: str | None = None):
        """Post the most recent non-reply post from a handle."""
        if not self.api.enabled:
            await interaction.response.send_message(
                ":no_entry_sign: Bluesky is disabled.",
                ephemeral=True,
            )
            return
        
        # Infer handle from thread if not provided
        if isinstance(interaction.channel, discord.Thread) and not handle:
            sub = self.state.get_subscription_by_thread(interaction.channel.id)
            if sub:
                handle = sub.handle
        
        if not handle:
            await interaction.response.send_message(
                ":warning: Specify a handle or run this in a Bluesky thread.",
                ephemeral=True,
            )
            return
        
        normalized = _normalize_handle(handle)
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            did = await self.api.resolve_handle(normalized)
            response = await self.api.get_author_feed(did, limit=100)
            
            # Check if response is valid
            if not isinstance(response, dict):
                await interaction.followup.send(
                    f":x: Invalid response from Bluesky API for `@{normalized}`."
                )
                return
            
			# response might be a string error instead of dict
            if not isinstance(response, dict) or "feed" not in response:
                await interaction.followup.send(
                    f":x: Invalid response from Bluesky API for `@{normalized}`."
                )
                return
            
            # Get feed items (not just posts)
            feed_items = response.get("feed", [])
            
            # Filter out replies
            non_reply_items = [
                item for item in feed_items
                if "reply" not in item.get("post", {}).get("record", {})
            ]
            
            if not non_reply_items:
                await interaction.followup.send(
                    f":warning: No recent non-reply posts found for `@{normalized}` (checked last 100 posts)."
                )
                return
            
            latest_item = non_reply_items[0]
            post = latest_item.get("post") or {}
            
            # Debug: Check what we found
            print(f"[BSKY_LATEST] Found post: {post.get('uri')}")
            print(f"[BSKY_LATEST] Has reason (repost): {bool(latest_item.get('reason'))}")
            print(f"[BSKY_LATEST] Has reply: {bool(post.get('record', {}).get('reply'))}")
            
            # For /bsky latest, post directly without watermark check
            # Use send_item_to_channel but temporarily bypass watermark
            from utils.bluesky.post_handler import PostHandler
            
            try:
                handler = PostHandler(bot=self.bot, api=self.api)
                
                # Temporarily clear watermark for this handle
                author = post.get("author") or {}
                handle_from_post = author.get("handle", normalized).lower()
                original_watermark = handler.state.get_last_seen_uri(handle_from_post)
                
                # Clear it temporarily
                handler.state.set_last_seen_uri(handle_from_post, None)
                
                # Now post (will work because watermark is cleared)
                await handler.handle_feed_item(interaction.channel, latest_item)
                
                # Restore original watermark
                if original_watermark:
                    handler.state.set_last_seen_uri(handle_from_post, original_watermark)
                
                print(f"[BSKY_LATEST] Successfully posted")
                
            except Exception as e:
                print(f"[BSKY_LATEST] Error posting: {e}")
                import traceback
                traceback.print_exc()
                
                # Restore watermark on error too
                if original_watermark:
                    handler.state.set_last_seen_uri(handle_from_post, original_watermark)
                
                await interaction.followup.send(
                    f":x: Error posting: {e}",
                    ephemeral=True
                )
                return
            
            # Dismiss thinking state
            await interaction.followup.send(
                f"✅ Posted latest from `@{normalized}`",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f":x: Error fetching posts for `@{normalized}`: {e}"
            )


    # ============================================================
    # /bsky interval
    # ============================================================
    @bsky.command(name="interval", description="Set polling interval for a handle")
    @app_commands.describe(
        minutes="Polling interval in minutes",
        handle="Handle (optional in thread)",
    )
    @app_commands.autocomplete(handle=handle_autocomplete)
    async def interval(
        self,
        interaction: discord.Interaction,
        minutes: int,
        handle: str | None = None,
    ):
        """Adjust how often a handle is checked."""
        if minutes < 1:
            await interaction.response.send_message(
                ":warning: Interval must be at least 1 minute.",
                ephemeral=True,
            )
            return

        if isinstance(interaction.channel, discord.Thread) and not handle:
            sub = self.state.get_subscription_by_thread(interaction.channel.id)
            if sub:
                handle = sub.handle

        if not handle:
            await interaction.response.send_message(
                ":warning: Specify a handle or run this in a Bluesky thread.",
                ephemeral=True,
            )
            return

        normalized = _normalize_handle(handle)

        if not self.state.get_subscription(normalized):
            await interaction.response.send_message(
                f":warning: `@{normalized}` is not followed.",
                ephemeral=True,
            )
            return

        self.state.set_interval(normalized, minutes)

        await interaction.response.send_message(
            f":timer: Polling interval for `@{normalized}` set to {minutes} minutes.",
            ephemeral=True,
        )

    # ============================================================
    # /bsky status
    # ============================================================
    @bsky.command(name="status", description="Show status for a Bluesky subscription")
    @app_commands.describe(handle="Handle (optional in thread)")
    @app_commands.autocomplete(handle=handle_autocomplete)
    async def status(self, interaction: discord.Interaction, handle: str | None = None):
        """Show subscription state."""
        if isinstance(interaction.channel, discord.Thread) and not handle:
            sub = self.state.get_subscription_by_thread(interaction.channel.id)
            if sub:
                handle = sub.handle

        if not handle:
            await interaction.response.send_message(
                ":warning: Specify a handle or run this in a Bluesky thread.",
                ephemeral=True,
            )
            return

        normalized = _normalize_handle(handle)
        sub = self.state.get_subscription(normalized)

        if not sub:
            await interaction.response.send_message(
                f":warning: `@{normalized}` is not followed.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f":satellite: Bluesky Status - @{normalized}",
            color=discord.Color.blue(),
        )

        embed.add_field(name="Thread ID", value=str(sub.thread_id), inline=False)
        interval = sub.interval_minutes or DEFAULT_INTERVAL_MINUTES
        embed.add_field(name="Interval (min)", value=str(interval), inline=True)
        last_seen = self.state.get_last_seen_uri(normalized)
        embed.add_field(name="Last Seen URI", value=last_seen or "-", inline=False)
        
        if sub.next_check_ts:
            embed.add_field(name="Next Check", value=f"<t:{int(sub.next_check_ts)}:R>", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================================================
    # /bsky map
    # ============================================================
    @bsky.command(name="map", description="Map a Bluesky handle to a local media slug")
    @app_commands.describe(
        handle="Bluesky handle (leave empty to show all mappings)",
        slug="Local media folder slug (leave empty to remove mapping)"
    )
    @app_commands.autocomplete(handle=handle_autocomplete, slug=slug_autocomplete)
    async def bsky_map(
        self,
        interaction: discord.Interaction,
        handle: str = None,
        slug: str = None
    ):
        """
        Map a Bluesky handle to a local media folder slug.
        
        Usage:
          /bsky map handle.bsky.social person-slug  - Set mapping
          /bsky map handle.bsky.social               - Remove mapping
          /bsky map                                  - Show all mappings
        """
        # Show all mappings if no args
        if not handle:
            slug_map = self.state.get_slug_map()
            if not slug_map:
                await interaction.response.send_message(
                    ":warning: No handle-to-slug mappings configured.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🗺️ Bluesky Handle → Slug Mappings",
                color=discord.Color.blue()
            )
            
            for h, s in sorted(slug_map.items()):
                embed.add_field(
                    name=f"@{h}",
                    value=f"`{s}`",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        normalized = _normalize_handle(handle)
        
        # Remove mapping if no slug provided
        if not slug:
            if self.state.remove_slug(normalized):
                await interaction.response.send_message(
                    f":white_check_mark: Removed slug mapping for `@{normalized}`",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f":warning: No mapping found for `@{normalized}`",
                    ephemeral=True
                )
            return
        
        # Set mapping
        self.state.set_slug(normalized, slug)
        
        await interaction.response.send_message(
            f":white_check_mark: Mapped `@{normalized}` → `{slug}`",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BlueskyCommands(bot))
