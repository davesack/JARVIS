from __future__ import annotations

from pathlib import Path
from typing import List

import discord


class MediaCarouselView(discord.ui.View):
    """
    Simple image carousel:
      - Keeps exactly ONE attachment on the message
      - Edits the message on button presses
    """

    def __init__(self, media_paths: List[Path], embed: discord.Embed, timeout: float = 86400):
        super().__init__(timeout=timeout)
        self.media: List[Path] = list(media_paths)
        self.embed: discord.Embed = embed
        self.index: int = 0

    @property
    def current_path(self) -> Path:
        return self.media[self.index]

    @property
    def current_filename(self) -> str:
        return self.current_path.name

    def current_file(self) -> discord.File:
        return discord.File(str(self.current_path), filename=self.current_filename)

    async def _edit_message(self, interaction: discord.Interaction) -> None:
        file = self.current_file()
        self.embed.set_image(url=f"attachment://{self.current_filename}")

        await interaction.response.edit_message(
            embed=self.embed,
            attachments=[file],
            view=self,
        )

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.media)
        await self._edit_message(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.media)
        await self._edit_message(interaction)
