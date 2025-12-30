# utils/mediawatcher/tagging_prompter.py

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import discord

from config import (
    MEDIAWATCHER_TAGGING_MODE_ENABLED,
    MEDIAWATCHER_TAGGING_USER,
    DATA_ROOT,
)

# Try to import hard mode setting from config, default to False
try:
    from config import MEDIAWATCHER_TAGGING_HARD_MODE
    TAGGING_HARD_MODE = MEDIAWATCHER_TAGGING_HARD_MODE
except ImportError:
    TAGGING_HARD_MODE = False

from utils.mediawatcher.manual_tags import open_tagging_dm


SEEN_FILE = DATA_ROOT / "mediawatcher" / "tagging_seen.json"
SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)


# ===============================================================
# Seen-file tracking
# ===============================================================

def _load_seen() -> dict:
    if not SEEN_FILE.exists():
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_seen(data: dict):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def has_been_seen(path: Path) -> bool:
    # In hard mode, always return False (always prompt)
    if TAGGING_HARD_MODE:
        return False
    
    seen = _load_seen()
    return str(path) in seen


def mark_seen(path: Path):
    seen = _load_seen()
    seen[str(path)] = True
    _save_seen(seen)


# ===============================================================
# PUBLIC ENTRY POINT
# ===============================================================

async def maybe_offer_tag_prompt(
    message: discord.Message,
    media_files: List[Path],
    interaction: Optional[discord.Interaction] = None,
):
    """
    The global tagging entry point, called by send_interceptor.

    Behavior:
      - If DM from the bot → jump straight to tagging DM UI (ONCE per message)
      - If guild + interaction → real ephemeral prompt
      - If guild + no interaction → fake ephemeral prompt (DM with buttons)
      - Skip files that user has already rejected or tagged
    """

    if not MEDIAWATCHER_TAGGING_MODE_ENABLED:
        return

    if not media_files:
        return

    # Handle DM context (MediaAlerts DMs)
    if isinstance(message.channel, discord.DMChannel):
        user = message.channel.recipient
        if user and user.id == MEDIAWATCHER_TAGGING_USER:
            # Process ALL files (for birthday posts with multiple embeds, etc.)
            for media_file in media_files:
                if not has_been_seen(media_file):
                    # Mark as seen BEFORE opening the DM to prevent loop
                    # (the tagging DM itself will be intercepted and trigger this function again)
                    mark_seen(media_file)
                    await open_tagging_dm(user, media_file)
        return

    # GUILD CONTEXT --------------------------------------------------

    guild = message.guild
    if guild is None:
        return

    owner = guild.get_member(MEDIAWATCHER_TAGGING_USER)
    if owner is None:
        return

    # REAL EPHEMERAL PROMPT (slash command)
    if interaction is not None:
        await _send_real_ephemeral_prompt(interaction, media_files)
        return

    # FAKE EPHEMERAL PROMPT (auto-posted)
    await _send_fake_ephemeral_prompt(message, media_files, owner)


# ===============================================================
# Prompt Types
# ===============================================================

async def _send_real_ephemeral_prompt(
    interaction: discord.Interaction,
    media_files: List[Path],
):
    """Real ephemeral prompt—only visible to the tagging user."""

    # Process ALL files (for birthday posts with multiple embeds, etc.)
    for f in media_files:
        if has_been_seen(f):
            continue

        view = _PromptButtons(f)

        await interaction.followup.send(
            content=f"🖼️ New media posted: `{f.name}` — tag it?",
            view=view,
            ephemeral=True,
        )


async def _send_fake_ephemeral_prompt(
    message: discord.Message,
    media_files: List[Path],
    owner: discord.Member,
):
    """Fake ephemeral → DM the prompt directly to the owner."""
    # Process ALL files
    for f in media_files:
        if has_been_seen(f):
            continue

        view = _PromptButtons(f)

        try:
            await owner.send(
                f"🖼️ Media posted in #{message.channel.name}: `{f.name}` — tag it?",
                view=view,
            )
        except Exception:
            pass


# ===============================================================
# Prompt Buttons
# ===============================================================

class _PromptButtons(discord.ui.View):
    def __init__(self, media_path: Path):
        super().__init__(timeout=180)  # 3 minutes
        self.media_path = media_path

    @discord.ui.button(label="Tag", style=discord.ButtonStyle.green)
    async def tag_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await open_tagging_dm(interaction.user, self.media_path)
        mark_seen(self.media_path)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        mark_seen(self.media_path)
        await interaction.followup.send("Okay — I won't ask about this file again.", ephemeral=True)
        self.stop()