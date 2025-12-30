from __future__ import annotations

from datetime import datetime
from typing import Optional

import discord


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

VIDEO_TOO_LARGE_NOTICE = "⚠️ Video too large to attach on Discord"
VIDEO_ATTACHED_NOTICE = "🎬 Video attached in reply"


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def build_post_embed(
    handle: str,
    post: dict,
    *,
    has_video: bool = False,
    video_too_large: bool = False,
) -> discord.Embed:
    """
    Build a deterministic Discord embed for a Bluesky post.

    This function MUST remain pure:
      - No I/O
      - No side effects
      - Same input = same output
    """

    record = post.get("record") or {}
    author = post.get("author") or {}

    display_name = author.get("displayName") or handle
    handle = handle.lower()

    text = record.get("text", "").strip()
    created_at = record.get("createdAt")

    embed = discord.Embed(
        description=text or None,
        timestamp=_parse_timestamp(created_at),
        color=discord.Color.blurple(),
    )

    # --------------------------------------------------------------
    # Author
    # --------------------------------------------------------------

    embed.set_author(
        name=f"{display_name} (@{handle})",
        url=_build_profile_url(handle),
    )

    # --------------------------------------------------------------
    # Post URL
    # --------------------------------------------------------------

    post_uri = post.get("uri")
    if post_uri:
        embed.url = _build_post_url(post_uri)

    # --------------------------------------------------------------
    # Post type indicators
    # --------------------------------------------------------------

    indicators = []

    if record.get("reply"):
        indicators.append("💬 Reply")
    elif post.get("reason"):
        indicators.append("🔁 Repost")
    elif record.get("embed"):
        # FIX: Only show "Quote" if it actually has a quoted record
        # Regular posts with images/video also have an embed, but no record
        embed_data = record.get("embed", {})
        if embed_data.get("record"):
            indicators.append("💬 Quote")

    if video_too_large:
        indicators.append(VIDEO_TOO_LARGE_NOTICE)
    elif has_video:
        indicators.append(VIDEO_ATTACHED_NOTICE)
    
    # Always add View Post link
    if post_uri:
        post_url = _build_post_url(post_uri)
        indicators.append(f"🔗 [View Post]({post_url})")

    if indicators:
        embed.add_field(
            name=" ",
            value=" • ".join(indicators),
            inline=False,
        )

    # --------------------------------------------------------------
    # Footer
    # --------------------------------------------------------------

    embed.set_footer(text="Bluesky")

    return embed


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _build_profile_url(handle: str) -> str:
    return f"https://bsky.app/profile/{handle}"


def _build_post_url(uri: str) -> str:
    """
    Convert at:// URI → bsky.app URL
    """
    try:
        _, _, did, _, rkey = uri.split("/", 4)
        return f"https://bsky.app/profile/{did}/post/{rkey}"
    except Exception:
        return "https://bsky.app"
