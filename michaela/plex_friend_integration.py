"""
Plex Friend Integration
========================

Integrates Plex video streaming into the friend/Michaela system.

CRITICAL SECURITY:
- Only works in MICHAELA_CHANNEL (private adult content)
- NEVER posts Plex content elsewhere
- Checks channel before EVERY Plex operation
"""

import discord
from typing import Optional, Dict
import random

from plex_integration import PlexIntegration, PlexMediaMapper


# CRITICAL: Define the ONLY channel allowed for Plex content
MICHAELA_CHANNEL_ID = 1321863653203390584  # Your private Michaela channel


class PlexFriendIntegration:
    """
    Handles Plex video integration for friend characters
    
    Security:
    - Channel gating on every operation
    - Only works in Michaela's private channel
    - Never posts adult content elsewhere
    """
    
    def __init__(self):
        self.plex = PlexIntegration()
        self.mapper = PlexMediaMapper()
        
        # Test connection on init
        if self.plex.test_connection():
            print("[PLEX_FRIENDS] ✅ Connected to Plex")
        else:
            print("[PLEX_FRIENDS] ⚠️ Plex connection failed")
    
    def _is_safe_channel(self, channel: discord.TextChannel) -> bool:
        """
        CRITICAL SECURITY CHECK
        
        Only allow Plex content in Michaela's channel
        """
        return channel.id == MICHAELA_CHANNEL_ID
    
    async def send_plex_video(
        self,
        channel: discord.TextChannel,
        celebrity_slug: str,
        celebrity_name: str,
        nsfw: bool = True,
        tag: str = None,
        context: str = "sent you a video"
    ) -> bool:
        """
        Send a Plex video from a celebrity
        
        Args:
            channel: Discord channel
            celebrity_slug: Celebrity identifier
            celebrity_name: Display name
            nsfw: Send NSFW or SFW video
            tag: Optional tag filter
            context: Message context
            
        Returns:
            True if sent, False if failed
        """
        
        # CRITICAL: Check channel first
        if not self._is_safe_channel(channel):
            print(f"[PLEX_FRIENDS] ❌ Blocked Plex send in non-Michaela channel: {channel.name}")
            return False
        
        # Get random video for this celebrity
        rating_key = self.mapper.get_random_video(
            celebrity_slug=celebrity_slug,
            nsfw=nsfw,
            tag=tag
        )
        
        if not rating_key:
            print(f"[PLEX_FRIENDS] No videos found for {celebrity_slug}")
            return False
        
        # Get stream URL
        stream_url = self.plex.get_direct_play_url(rating_key)
        
        if not stream_url:
            print(f"[PLEX_FRIENDS] Failed to get stream URL for {rating_key}")
            return False
        
        # Get video info
        media_info = self.plex.get_media_info(rating_key)
        
        if media_info:
            duration_min = media_info['duration'] // 60
            title = media_info.get('title', 'Untitled')
        else:
            duration_min = 0
            title = "Video"
        
        # Build message
        message = f"🎬 **{celebrity_name}** {context}\n"
        
        if duration_min > 0:
            message += f"*{title}* ({duration_min} min)\n"
        
        message += f"\n{stream_url}"
        
        # Send to channel
        try:
            await channel.send(message)
            print(f"[PLEX_FRIENDS] ✅ Sent Plex video from {celebrity_name} (key: {rating_key})")
            return True
        except Exception as e:
            print(f"[PLEX_FRIENDS] Error sending: {e}")
            return False
    
    async def send_random_plex(
        self,
        channel: discord.TextChannel,
        celebrity_slug: str,
        celebrity_name: str
    ) -> bool:
        """Convenience method for sending random video"""
        
        contexts = [
            "sent you something special",
            "wants to show you this",
            "thought you'd like this",
            "made this for you",
            "has been thinking about you"
        ]
        
        context = random.choice(contexts)
        
        return await self.send_plex_video(
            channel=channel,
            celebrity_slug=celebrity_slug,
            celebrity_name=celebrity_name,
            nsfw=True,
            context=context
        )
    
    def has_plex_content(self, celebrity_slug: str) -> bool:
        """Check if celebrity has Plex videos available"""
        return self.mapper.has_videos(celebrity_slug)
    
    def get_plex_count(self, celebrity_slug: str, nsfw: bool = True) -> int:
        """Get count of Plex videos for celebrity"""
        return self.mapper.get_video_count(celebrity_slug, nsfw)


class PlexCommands:
    """
    Discord commands for managing Plex integration
    
    Admin commands to map videos to celebrities
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.plex = PlexIntegration()
        self.mapper = PlexMediaMapper()
    
    async def map_plex_video(
        self,
        ctx,
        celebrity_slug: str,
        rating_key: int,
        nsfw: bool = True,
        tags: str = None
    ):
        """
        Map a Plex video to a celebrity
        
        Usage: !map_plex chloe-lamb 111992 nsfw "topless,solo"
        """
        
        # Check it's in Michaela channel
        if ctx.channel.id != MICHAELA_CHANNEL_ID:
            await ctx.send("❌ Plex commands only work in Michaela's channel")
            return
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
        
        # Add to mapper
        self.mapper.add_video(
            celebrity_slug=celebrity_slug,
            rating_key=rating_key,
            nsfw=nsfw,
            tags=tag_list
        )
        
        # Get video info
        info = self.plex.get_media_info(rating_key)
        
        if info:
            await ctx.send(
                f"✅ Mapped **{info['title']}** to `{celebrity_slug}`\n"
                f"Tags: {', '.join(tag_list) if tag_list else 'None'}\n"
                f"NSFW: {nsfw}"
            )
        else:
            await ctx.send(f"✅ Mapped video {rating_key} to `{celebrity_slug}`")
    
    async def list_plex_libraries(self, ctx):
        """List all Plex libraries"""
        
        if ctx.channel.id != MICHAELA_CHANNEL_ID:
            await ctx.send("❌ Plex commands only work in Michaela's channel")
            return
        
        libraries = self.plex.get_libraries()
        
        if libraries:
            msg = "📚 **Plex Libraries:**\n"
            for lib in libraries:
                msg += f"- **{lib['title']}** (key: {lib['key']}, type: {lib['type']})\n"
            await ctx.send(msg)
        else:
            await ctx.send("❌ No libraries found")
    
    async def search_plex(self, ctx, library_key: int, query: str):
        """
        Search Plex library
        
        Usage: !search_plex 1 "chloe"
        """
        
        if ctx.channel.id != MICHAELA_CHANNEL_ID:
            await ctx.send("❌ Plex commands only work in Michaela's channel")
            return
        
        results = self.plex.search_library(library_key, query, limit=10)
        
        if results:
            msg = f"🔍 **Search results for '{query}':**\n\n"
            for result in results[:10]:
                msg += f"**{result['title']}** ({result.get('year', 'N/A')})\n"
                msg += f"  Rating Key: `{result['rating_key']}`\n"
                msg += f"  Duration: {result['duration'] // 60} min\n\n"
            
            await ctx.send(msg)
        else:
            await ctx.send(f"❌ No results found for '{query}'")
    
    async def test_plex_video(self, ctx, rating_key: int):
        """
        Test a Plex video stream URL
        
        Usage: !test_plex 111992
        """
        
        if ctx.channel.id != MICHAELA_CHANNEL_ID:
            await ctx.send("❌ Plex commands only work in Michaela's channel")
            return
        
        # Get stream URL
        stream_url = self.plex.get_direct_play_url(rating_key)
        
        if stream_url:
            info = self.plex.get_media_info(rating_key)
            
            if info:
                await ctx.send(
                    f"✅ **{info['title']}**\n"
                    f"Duration: {info['duration'] // 60} min\n"
                    f"Year: {info.get('year', 'N/A')}\n\n"
                    f"🎬 Stream URL:\n{stream_url}"
                )
            else:
                await ctx.send(f"🎬 Stream URL:\n{stream_url}")
        else:
            await ctx.send(f"❌ Failed to get stream URL for {rating_key}")
    
    async def show_celebrity_plex(self, ctx, celebrity_slug: str):
        """
        Show Plex video count for a celebrity
        
        Usage: !show_plex chloe-lamb
        """
        
        if ctx.channel.id != MICHAELA_CHANNEL_ID:
            await ctx.send("❌ Plex commands only work in Michaela's channel")
            return
        
        nsfw_count = self.mapper.get_video_count(celebrity_slug, nsfw=True)
        sfw_count = self.mapper.get_video_count(celebrity_slug, nsfw=False)
        
        await ctx.send(
            f"📊 **{celebrity_slug}**\n"
            f"NSFW videos: {nsfw_count}\n"
            f"SFW videos: {sfw_count}\n"
            f"Total: {nsfw_count + sfw_count}"
        )


# Integration helper for Michaela cog
async def maybe_send_plex_video(
    plex_integration: PlexFriendIntegration,
    channel: discord.TextChannel,
    celebrity_slug: str,
    celebrity_name: str,
    probability: float = 0.5
) -> bool:
    """
    Helper function to maybe send a Plex video
    
    Checks if celebrity has Plex content and sends randomly
    
    Returns True if sent, False otherwise
    """
    
    # Check if celebrity has Plex videos
    if not plex_integration.has_plex_content(celebrity_slug):
        return False
    
    # Random chance to send
    if random.random() > probability:
        return False
    
    # Send the video
    return await plex_integration.send_random_plex(
        channel=channel,
        celebrity_slug=celebrity_slug,
        celebrity_name=celebrity_name
    )
