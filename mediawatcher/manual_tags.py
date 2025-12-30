# utils/mediawatcher/manual_tags.py

from __future__ import annotations

from pathlib import Path
import discord
from discord.ui import View, Button, Modal, TextInput

# -----------------------------------------------------------
# SAFE IMPORT PATTERN (avoids circular imports)
# -----------------------------------------------------------

def _get_tags_api():
    """Delayed import to avoid circular dependency."""
    from utils.mediawatcher import tag_extractor
    return tag_extractor


# -----------------------------------------------------------
# PUBLIC FUNCTIONS CALLED BY OTHER MODULES
# -----------------------------------------------------------

async def open_tagging_dm(user: discord.User, file_path: Path):
    """Send the tagging UI DM with thumbnail."""
    # Lazy import to avoid circular dependency
    from utils.mediawatcher.send_interceptor import send_without_interception
    
    tag_api = _get_tags_api()

    # Get/create thumbnail
    thumb = await _ensure_thumbnail(file_path)

    # Build embed
    embed = discord.Embed(
        title="📌 Tag Media",
        description=f"**File:** `{file_path.name}`\n\n*Add tags separated by commas:*\n`tag1, tag2, tag3`",
        color=discord.Color.blurple(),
    )

    existing = tag_api.get_manual_tags_for_file(file_path)
    if existing:
        embed.add_field(
            name="Current Tags",
            value=", ".join(existing),
            inline=False,
        )
    else:
        embed.add_field(
            name="Current Tags",
            value="*No tags yet*",
            inline=False,
        )

    view = TaggingView(file_path)

    # Attach thumbnail
    files = []
    if thumb and thumb.exists():
        embed.set_thumbnail(url=f"attachment://{thumb.name}")
        files.append(discord.File(str(thumb), filename=thumb.name))

    # Send without triggering the interceptor to prevent double DMs
    await send_without_interception(user, embed=embed, view=view, files=files if files else None)


async def merge_manual_tags(file_path: Path, tags: list[str]):
    """Called by ingest to merge manual tags with auto-tags."""
    tag_api = _get_tags_api()
    tag_api.save_updated_tags(file_path, add=tags)


# -----------------------------------------------------------
# Thumbnail helper
# -----------------------------------------------------------

async def _ensure_thumbnail(file_path: Path) -> Path | None:
    """Generate thumbnail for videos/gifs. For images, return the image itself."""
    # For images, just return the image path as the thumbnail
    if file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
        if file_path.exists():
            return file_path
        return None
    
    # For videos, generate thumbnail
    if file_path.suffix.lower() not in {".mp4", ".mov", ".mkv"}:
        return None
    
    from utils.mediawatcher.ffmpeg_tools import extract_thumbnail
    
    thumb = file_path.parent / "thumbnails" / f"{file_path.stem}-thumb.jpg"
    thumb.parent.mkdir(parents=True, exist_ok=True)
    
    if thumb.exists():
        return thumb
    
    try:
        extract_thumbnail(file_path, thumb)
        return thumb
    except Exception:
        return None


# -----------------------------------------------------------
# UI View
# -----------------------------------------------------------

class TaggingView(View):
    def __init__(self, file_path: Path):
        super().__init__(timeout=300)
        self.file_path = file_path

    @discord.ui.button(label="Add Tag", style=discord.ButtonStyle.success)
    async def add_tag(self, interaction, button):
        modal = AddTagModal(self.file_path)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Remove Tag", style=discord.ButtonStyle.danger)
    async def remove_tag(self, interaction, button):
        modal = RemoveTagModal(self.file_path)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.primary)
    async def save(self, interaction, button):
        await interaction.response.send_message("Tags saved!", ephemeral=True)
        self.stop()


# -----------------------------------------------------------
# Modals
# -----------------------------------------------------------

class AddTagModal(Modal, title="Add Tag"):
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path
        self.tag_input = TextInput(
            label="New Tag(s)",
            placeholder="ex: nsfw, blowjob, bikini",
            required=True,
        )
        self.add_item(self.tag_input)

    async def on_submit(self, interaction):
        tag_api = _get_tags_api()
        tag = self.tag_input.value.strip()
        if tag:
            tag_api.save_updated_tags(self.file_path, add=[tag])
        await interaction.response.send_message(
            f"Added tag(s): `{tag}`.", ephemeral=True
        )


class RemoveTagModal(Modal, title="Remove Tag"):
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path
        self.tag_input = TextInput(
            label="Tag to remove",
            placeholder="Type exactly",
            required=True,
        )
        self.add_item(self.tag_input)

    async def on_submit(self, interaction):
        tag_api = _get_tags_api()
        tag = self.tag_input.value.strip()
        if tag:
            tag_api.save_updated_tags(self.file_path, remove=[tag])
        await interaction.response.send_message(
            f"Removed tag: `{tag}`.", ephemeral=True
        )