# utils/mediawatcher/send_interceptor.py

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from contextvars import ContextVar

import discord

from utils.mediawatcher.tagging_prompter import maybe_offer_tag_prompt


# Context variable to prevent recursive interception
_skip_interception = ContextVar("skip_interception", default=False)


def install_send_interceptor(bot: discord.Client):
    """
    Globally intercept all outgoing send_message / followup.send / channel.send calls
    so we can discover when local files are posted and run the tagging prompter.
    """

    # ===============================================================
    # Patch InteractionResponse.send_message
    # ===============================================================
    orig_send_message = discord.InteractionResponse.send_message

    async def patched_send_message(self, *args, **kwargs):
        interaction: discord.Interaction = self._parent

        files = _extract_files_from_kwargs(**kwargs)
        msg = await orig_send_message(self, *args, **kwargs)

        if files:
            # real ephemeral prompt
            await maybe_offer_tag_prompt(msg or interaction, files, interaction=interaction)

        return msg

    discord.InteractionResponse.send_message = patched_send_message

    # ===============================================================
    # Patch Webhook.send (used for followup)
    # ===============================================================
    orig_webhook_send = discord.Webhook.send

    async def patched_webhook_send(self, *args, **kwargs):
        # Skip interception if we're already in a tagging flow
        if _skip_interception.get():
            return await orig_webhook_send(self, *args, **kwargs)
        
        interaction: Optional[discord.Interaction] = getattr(self, "interaction", None)

        files = _extract_files_from_kwargs(**kwargs)
        msg = await orig_webhook_send(self, *args, **kwargs)

        if files:
            # still real ephemeral prompt when interaction exists
            await maybe_offer_tag_prompt(msg, files, interaction=interaction)

        return msg

    discord.Webhook.send = patched_webhook_send

    # ===============================================================
    # Patch channel.send for ALL other messages
    # ===============================================================
    orig_channel_send = discord.abc.Messageable.send

    async def patched_channel_send(self, *args, **kwargs):
        # Skip interception if we're already in a tagging flow
        if _skip_interception.get():
            return await orig_channel_send(self, *args, **kwargs)
        
        files = _extract_files_from_kwargs(**kwargs)
        msg = await orig_channel_send(self, *args, **kwargs)

        if files:
            # guild messages get fake ephemeral prompt (DM to owner)
            # DM messages get immediate tag UI
            await maybe_offer_tag_prompt(msg, files, interaction=None)

        return msg

    discord.abc.Messageable.send = patched_channel_send


# ===============================================================
# Helper: Send without triggering interception
# ===============================================================

async def send_without_interception(target, *args, **kwargs):
    """Send a message without triggering the tagging prompt interceptor."""
    token = _skip_interception.set(True)
    try:
        return await target.send(*args, **kwargs)
    finally:
        _skip_interception.reset(token)


# ===============================================================
# Helper: detect outgoing file attachments
# ===============================================================

def _extract_files_from_kwargs(**kwargs) -> List[Path]:
    """
    Extract Path objects from discord.File attachments (file= or files=[...]).
    """
    out: List[Path] = []

    file_obj = kwargs.get("file")
    if isinstance(file_obj, discord.File):
        if hasattr(file_obj.fp, "name"):
            out.append(Path(file_obj.fp.name))

    file_list = kwargs.get("files")
    if isinstance(file_list, (list, tuple)):
        for f in file_list:
            if isinstance(f, discord.File) and hasattr(f.fp, "name"):
                out.append(Path(f.fp.name))

    return out