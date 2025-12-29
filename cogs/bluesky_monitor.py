# cogs/bluesky_monitor.py

from __future__ import annotations

import asyncio
from typing import List

import discord
from discord.ext import commands, tasks

from config import DEV_GUILD_ID
from utils.bluesky.state import get_shared_state  # Use singleton getter
from utils.bluesky.api import BlueskyAPI
from utils.bluesky.post_handler import send_item_to_channel
from utils.bluesky.media import cleanup_bluesky_cache


DEFAULT_INTERVAL_MINUTES = 5


class BlueskyMonitor(commands.Cog):
    """Background task that checks Bluesky feeds at individual intervals."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = BlueskyAPI()
        self.state = get_shared_state()  # FIXED: Use singleton instead of creating new instance
        self._monitor_loop.start()
        self._cache_cleanup_loop.start()

    # ------------------------------------------------------------
    # MONITOR LOOP
    # ------------------------------------------------------------
    @tasks.loop(seconds=30)
    async def _monitor_loop(self):
        """Each subscribed handle is checked when its own interval expires."""
        now_ts = discord.utils.utcnow().timestamp()

        due_subs = self.state.get_due_subscriptions(now_ts)
        if not due_subs:
            return

        for sub in due_subs:
            try:
                await self._check_subscription(sub)
            except Exception as e:
                print(f"[BSKY_MONITOR] Error checking @{sub.handle}: {e}")
            finally:
                # Always update next check time
                self.state.update_next_check(
                    sub.handle,
                    now_ts,
                    DEFAULT_INTERVAL_MINUTES,
                )

    # ------------------------------------------------------------
    # BEFORE LOOP
    # ------------------------------------------------------------
    @_monitor_loop.before_loop
    async def before_monitor_loop(self):
        """Runs once before the monitor starts."""
        await self.bot.wait_until_ready()
        self.state.initialize_intervals(DEFAULT_INTERVAL_MINUTES)
        print("[BSKY_MONITOR] Interval scheduler initialized.")

    # ------------------------------------------------------------
    # SEND ITEMS TO THREAD
    # ------------------------------------------------------------
    async def _send_items_to_thread(self, handle: str, items: List[dict]) -> None:
        if not items:
            return

        thread_id = self.state.get_thread_id(handle)
        if not thread_id:
            print(f"[BSKY_MONITOR] No thread mapped for @{handle}")
            return

        guild = self.bot.get_guild(self.state.guild_id or DEV_GUILD_ID)
        if not guild:
            print(f"[BSKY_MONITOR] Guild not found")
            return

        thread = guild.get_thread(thread_id)
        if not isinstance(thread, discord.Thread):
            print(f"[BSKY_MONITOR] Invalid thread ID for @{handle}")
            return

        # Auto-unarchive
        if thread.archived:
            try:
                await thread.edit(archived=False)
            except Exception as e:
                print(f"[BSKY_MONITOR] Failed to unarchive thread: {e}")

        # Post in chronological order
        for item in items:
            try:
                await send_item_to_channel(thread, self.api, item)
            except discord.HTTPException as e:
                # Discord API errors
                post = item.get("post", {})
                uri = post.get("uri")
                
                if e.code == 40005:  # Payload Too Large
                    print(f"[BSKY_MONITOR] Skipping large post for @{handle} (413)")
                elif e.code == 10003:  # Unknown Channel
                    print(f"[BSKY_MONITOR] Thread deleted for @{handle}, skipping")
                else:
                    print(f"[BSKY_MONITOR] Discord error for @{handle}: {e}")
                
                # Always mark as seen to prevent infinite loops
                if uri:
                    self.state.set_last_seen_uri(handle, uri)
                    
            except Exception as e:
                # Any other error
                print(f"[BSKY_MONITOR] Error posting for @{handle}: {e}")
                
                # Always mark as seen to prevent infinite loops
                post = item.get("post", {})
                uri = post.get("uri")
                if uri:
                    self.state.set_last_seen_uri(handle, uri)

    # ------------------------------------------------------------
    # CHECK ONE SUBSCRIPTION (SIMPLIFIED LOGIC)
    # ------------------------------------------------------------
    async def _check_subscription(self, sub):
        """
        Check a single subscription for new posts.
        
        SIMPLIFIED ALGORITHM:
        1. Fetch feed (newest posts first)
        2. Filter to non-replies only
        3. If no last_seen: post newest 5 and mark newest as seen
        4. If have last_seen: find it in feed, post everything newer
        5. If last_seen not in feed: post newest 5 (resync)
        """
        handle = sub.handle

        # Fetch feed (newest -> oldest)
        try:
            feed_response = await self.api.get_author_feed(handle, limit=100)  # Increased to handle reply-heavy accounts
        except Exception as e:
            print(f"[BSKY_MONITOR] API error for @{handle}: {e}")
            return

        # Validate response
        if not feed_response:
            print(f"[BSKY_MONITOR] Empty response for @{handle}")
            return
        
        # Handle both dict and list responses
        if isinstance(feed_response, dict):
            feed_items = feed_response.get("feed", [])
        elif isinstance(feed_response, list):
            feed_items = feed_response
        else:
            print(f"[BSKY_MONITOR] Invalid feed format for @{handle}: {type(feed_response)}")
            return
        
        if not feed_items:
            return

        # Filter to non-reply items only
        non_reply_items: List[dict] = []
        for item in feed_items:
            if not isinstance(item, dict):
                continue
            
            post = item.get("post") or {}
            record = post.get("record") or {}
            
            # Skip replies - check if "reply" key exists in record at all
            # (presence of the key means it's a reply, regardless of value)
            if "reply" in record:
                continue
                
            non_reply_items.append(item)

        if not non_reply_items:
            return

        # Get last seen URI
        last_seen = self.state.get_last_seen_uri(handle)

        # Case 1: No last seen - initial sync
        if not last_seen:
            print(f"[BSKY_MONITOR] Initial sync for @{handle}: posting 5 newest")
            catch_up_items = non_reply_items[:5]
            
            # Mark newest as seen
            newest = non_reply_items[0]
            newest_uri = newest.get("post", {}).get("uri")
            if newest_uri:
                self.state.set_last_seen_uri(handle, newest_uri)
            
            await self._send_items_to_thread(handle, catch_up_items)
            return

        # Case 2: Find last_seen in current feed
        last_seen_index = None
        for i, item in enumerate(non_reply_items):
            uri = item.get("post", {}).get("uri")
            if uri == last_seen:
                last_seen_index = i
                break

        # Case 3: last_seen not in feed - resync
        if last_seen_index is None:
            print(f"[BSKY_MONITOR] Resync for @{handle}: last_seen not in feed")
            catch_up_items = non_reply_items[:5]
            
            # Mark newest as seen
            newest = non_reply_items[0]
            newest_uri = newest.get("post", {}).get("uri")
            if newest_uri:
                self.state.set_last_seen_uri(handle, newest_uri)
            
            await self._send_items_to_thread(handle, catch_up_items)
            return

        # Case 4: Found last_seen - post everything newer
        new_items = non_reply_items[:last_seen_index]
        
        if not new_items:
            return  # No new posts

        print(f"[BSKY_MONITOR] Found {len(new_items)} new posts for @{handle}")

        # Mark newest as seen BEFORE posting (prevent double-post on error)
        newest = new_items[0]
        newest_uri = newest.get("post", {}).get("uri")
        if newest_uri:
            self.state.set_last_seen_uri(handle, newest_uri)

        # Post in chronological order (oldest first)
        new_items.reverse()
        await self._send_items_to_thread(handle, new_items)

    # ------------------------------------------------------------
    # BLUESKY CACHE CLEANUP LOOP
    # ------------------------------------------------------------
    @tasks.loop(hours=24)
    async def _cache_cleanup_loop(self):
        deleted = cleanup_bluesky_cache()
        if deleted:
            print(f"[BSKY_MONITOR] Cleaned {deleted} cached Bluesky media files.")

    @_cache_cleanup_loop.before_loop
    async def before_cache_cleanup(self):
        await self.bot.wait_until_ready()

    # ------------------------------------------------------------
    # SHUTDOWN CLEANUP
    # ------------------------------------------------------------
    def cog_unload(self):
        self._monitor_loop.cancel()
        self._cache_cleanup_loop.cancel()


async def setup(bot: commands.Bot):
    await bot.add_cog(BlueskyMonitor(bot))
