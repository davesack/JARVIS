from __future__ import annotations

from typing import Callable, Generic, List, Sequence, TypeVar

import discord

T = TypeVar("T")


# ============================================================
# PAGINATION VIEW
# ============================================================

class PaginatedView(discord.ui.View, Generic[T]):
    """
    Generic paginator for Rankings embeds.

    - Buttons only appear if multiple pages exist
    - Page size defaults to 25
    - Each page renders a fresh embed + attachments
    - Hero image updates to show the top person on each page
    - Stats calculated once from full list
    """

    def __init__(
        self,
        *,
        items: Sequence[T],
        page_size: int = 25,
        render_page: Callable[
            [List[T], int, int],
            tuple[discord.Embed, List[discord.File]],
        ],
        timeout: float = 86400,
        full_list_stats: dict | None = None,
    ):
        super().__init__(timeout=timeout)

        if page_size <= 0:
            raise ValueError("page_size must be > 0")

        self.items: List[T] = list(items)
        self.page_size = page_size
        self.render_page = render_page
        self.message: discord.Message | None = None
        self.full_list_stats = full_list_stats

        self.page_index: int = 0
        self.page_count: int = max(
            1,
            (len(self.items) + page_size - 1) // page_size,
        )

        # Disable buttons if pagination unnecessary
        if self.page_count <= 1:
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True

    # --------------------------------------------------------
    # PAGE SLICING
    # --------------------------------------------------------

    def _get_page_items(self) -> List[T]:
        start = self.page_index * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    async def _render(self, interaction: discord.Interaction):
        # Defer first to acknowledge interaction
        await interaction.response.defer()
        
        # Render the new page
        embed, files = await self.render_page(
            self._get_page_items(),
            self.page_index + 1,
            self.page_count,
        )

        # Delete old message FIRST, then send new one
        old_message = self.message
        
        self.message = await interaction.channel.send(
            embed=embed,
            files=files,
            view=self,
        )
        
        # Delete old message after new one is sent
        if old_message:
            try:
                await old_message.delete()
            except:
                pass  # Message might already be deleted

    # --------------------------------------------------------
    # BUTTONS - Using Unicode symbols that Discord supports
    # --------------------------------------------------------

    @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.page_index == 0:
            await interaction.response.defer()
            return

        self.page_index = 0
        await self._render(interaction)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.page_index <= 0:
            await interaction.response.defer()
            return

        self.page_index -= 1
        await self._render(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.page_index >= self.page_count - 1:
            await interaction.response.defer()
            return

        self.page_index += 1
        await self._render(interaction)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.page_index == self.page_count - 1:
            await interaction.response.defer()
            return

        self.page_index = self.page_count - 1
        await self._render(interaction)


# ============================================================
# ENTRYPOINT
# ============================================================

async def send_paginated(
    interaction: discord.Interaction,
    *,
    items: Sequence[T],
    render_page: Callable[
        [List[T], int, int],
        tuple[discord.Embed, List[discord.File]],
    ],
    page_size: int = 25,
    ephemeral: bool = False,
):
    """
    Sends a paginated Rankings message.
    """

    if not items:
        await interaction.response.send_message(
            "No results found.",
            ephemeral=True,
        )
        return

    view = PaginatedView(
        items=items,
        page_size=page_size,
        render_page=render_page,
    )

    embed, files = await render_page(
        items[:page_size],
        1,
        view.page_count,
    )

    # Only add view if there's more than 1 page
    kwargs = {
        "embed": embed,
        "files": files,
        "ephemeral": ephemeral,
    }
    if view.page_count > 1:
        kwargs["view"] = view
    
    # Check if interaction has already been responded to (e.g., from defer)
    if interaction.response.is_done():
        view.message = await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)
        view.message = await interaction.original_response()
