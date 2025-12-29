# cogs/rankings_favorites.py
"""
Tracks 🔥 reactions on rankings media.

Rules:
- Only canonical media files receive favorites
- Video previews NEVER receive favorites
- Favorites are keyed by canonical relative path
- NOW WORKS WITH BOTH ATTACHMENTS AND EMBED IMAGES
"""

from __future__ import annotations

import json
from typing import Dict, Optional
from pathlib import Path

import discord
from discord.ext import commands

from config import DATA_ROOT, MEDIA_ROOT

DATA_FILE = DATA_ROOT / "rankings_favorites.json"


# ============================================================
# STORAGE
# ============================================================

def _load_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            pass
    return {
        "files": {},     # rel_path -> count
        "people": {},   # slug -> total count
    }


def _save_data(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))


# ============================================================
# PATH HELPERS
# ============================================================

def _canonical_media_path(path: Path) -> Optional[Path]:
    """
    Convert previews to canonical files.
    previews/*.webp → videos/<stem>.<ext>
    """
    if "videos/previews" in str(path):
        videos_dir = path.parents[2]
        for ext in (".mp4", ".mov", ".webm"):
            candidate = videos_dir / f"{path.stem}{ext}"
            if candidate.exists():
                return candidate
        return None

    return path


def _extract_media_from_message(message: discord.Message) -> Optional[Path]:
    """
    Extract media file path from a message.
    Checks both attachments and embed images (birthday posts use embeds!).
    """
    # Try attachments first
    if message.attachments:
        filename = message.attachments[0].filename
        for p in Path(MEDIA_ROOT).rglob(filename):
            if p.is_file():
                return p
    
    # Try embed images (used by birthday posts and /rank commands)
    if message.embeds:
        for embed in message.embeds:
            # Check main image
            if embed.image and embed.image.url:
                url = embed.image.url
                # Extract filename from attachment:// URL or regular URL
                if "attachment://" in url:
                    filename = url.split("attachment://")[-1]
                else:
                    filename = url.split("/")[-1].split("?")[0]
                
                for p in Path(MEDIA_ROOT).rglob(filename):
                    if p.is_file():
                        return p
            
            # Check thumbnail
            if embed.thumbnail and embed.thumbnail.url:
                url = embed.thumbnail.url
                if "attachment://" in url:
                    filename = url.split("attachment://")[-1]
                else:
                    filename = url.split("/")[-1].split("?")[0]
                
                for p in Path(MEDIA_ROOT).rglob(filename):
                    if p.is_file():
                        return p
    
    return None


def _slug_from_path(path: Path) -> Optional[str]:
    try:
        rel = path.relative_to(MEDIA_ROOT)
        return rel.parts[0]
    except Exception:
        return None


def _relative_path(path: Path) -> str:
    """Get relative path from MEDIA_ROOT with forward slashes (cross-platform)."""
    rel = path.relative_to(MEDIA_ROOT)
    # Always use forward slashes for consistency across platforms
    return rel.as_posix()


# ============================================================
# COG
# ============================================================

class RankingsFavorites(commands.Cog):
    """Tracks 🔥 emoji favorites on rankings media."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = _load_data()

    # --------------------------------------------------------
    # EVENT LISTENER
    # --------------------------------------------------------

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "🔥":
            return

        if payload.user_id == self.bot.user.id:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden):
            return

        raw_path = _extract_media_from_message(message)
        if not raw_path:
            print(f"[FAVORITES] No media found in message {payload.message_id}")
            return

        canonical = _canonical_media_path(raw_path)
        if not canonical:
            print(f"[FAVORITES] Could not resolve canonical path for {raw_path}")
            return

        slug = _slug_from_path(canonical)
        if not slug:
            print(f"[FAVORITES] Could not extract slug from {canonical}")
            return

        rel_path = _relative_path(canonical)

        # Increment counts
        self.data["files"][rel_path] = self.data["files"].get(rel_path, 0) + 1
        self.data["people"][slug] = self.data["people"].get(slug, 0) + 1

        _save_data(self.data)
        
        print(f"[FAVORITES] Tracked 🔥 for {slug}: {rel_path} (now {self.data['files'][rel_path]})")


async def setup(bot: commands.Cog):
    await bot.add_cog(RankingsFavorites(bot))
