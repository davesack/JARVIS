
from __future__ import annotations

import sys
import platform
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import DEV_GUILD_ID, DISCORD_OWNER_ID

# Project root: .../JARVIS
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"


# ------------------------------------------------------------
# Owner check
# ------------------------------------------------------------
def _is_owner(interaction: discord.Interaction) -> bool:
    return bool(interaction.user and interaction.user.id == DISCORD_OWNER_ID)


def owner_only():
    return app_commands.check(_is_owner)


# ============================================================
#                         ADMIN COG
# ============================================================
class Admin(commands.Cog):
    """
    Hybrid-mode admin tools:

      - /admin sync_guild       â†’ sync commands to the dev guild only
      - /admin sync_global      â†’ sync commands globally
      - /admin reload <cog>     â†’ reload a specific cog
      - /admin reload_all       â†’ reload all cogs
      - /admin load <cog>       â†’ load a cog
      - /admin unload <cog>     â†’ unload a cog
      - /admin restart          â†’ close the bot (autoreload restarts)
      - /admin shutdown         â†’ clean close
      - /admin nuke_commands    â†’ wipe ALL GLOBAL commands + auto-restore dev commands
      - /admin logs_list        â†’ list log files
      - /admin logs_get         â†’ fetch a specific log file
      - /admin check            â†’ quick health check
    """

    admin = app_commands.Group(
        name="admin",
        description="Owner-only administration tools",
        guild_ids=[DEV_GUILD_ID],
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --------------------------------------------------------
    # Error handling
    # --------------------------------------------------------
    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            if interaction.response.is_done():
                await interaction.followup.send(
                    "You are not allowed to use this command.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "You are not allowed to use this command.",
                    ephemeral=True,
                )
        else:
            msg = f"An error occurred: {error}"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

    # --------------------------------------------------------
    # /admin sync_guild
    # --------------------------------------------------------
    @admin.command(
        name="sync_guild",
        description="Sync application commands to the dev guild only.",
    )
    @owner_only()
    async def sync_guild(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild or discord.Object(id=DEV_GUILD_ID)
        synced = await self.bot.tree.sync(guild=guild)

        await interaction.followup.send(
            f"✅ Synced **{len(synced)}** commands to guild `{guild.id}`.",
            ephemeral=True,
        )

    # --------------------------------------------------------
    # /admin sync_global
    # --------------------------------------------------------
    @admin.command(
        name="sync_global",
        description="Sync application commands globally (may take time).",
    )
    @owner_only()
    async def sync_global(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        synced = await self.bot.tree.sync()

        await interaction.followup.send(
            f"🌍 Synced **{len(synced)}** commands globally.\n"
            f"Global updates may take up to 1 hour unless nuked first.",
            ephemeral=True,
        )

    # --------------------------------------------------------
    # /admin reload
    # --------------------------------------------------------
    @admin.command(
        name="reload",
        description="Reload a specific cog, e.g. 'bluesky_commands'.",
    )
    @owner_only()
    async def reload_cog(self, interaction: discord.Interaction, cog: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        ext = cog if cog.startswith("cogs.") else f"cogs.{cog}"
        try:
            await self.bot.reload_extension(ext)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(ext)
            await interaction.followup.send(
                f"ðŸ†• Cog `{ext}` was not loaded; loaded it now.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to reload `{ext}`: `{e}`",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(f"🔄 Reloaded `{ext}`.", ephemeral=True)

    # --------------------------------------------------------
    # /admin reload_all
    # --------------------------------------------------------
    @admin.command(
        name="reload_all",
        description="Reload all currently loaded cogs.",
    )
    @owner_only()
    async def reload_all(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        results = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
                results.append(f"✅ {ext}")
            except Exception as e:
                results.append(f"❌ {ext} â†’ {e}")

        msg = "**Reloaded cogs:**\n" + "\n".join(results)
        await interaction.followup.send(msg, ephemeral=True)

    # --------------------------------------------------------
    # /admin load
    # --------------------------------------------------------
    @admin.command(
        name="load",
        description="Load a cog by name.",
    )
    @owner_only()
    async def load_cog(self, interaction: discord.Interaction, cog: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        ext = cog if cog.startswith("cogs.") else f"cogs.{cog}"
        try:
            await self.bot.load_extension(ext)
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to load `{ext}`: `{e}`",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(f"🔄¥ Loaded `{ext}`.", ephemeral=True)

    # --------------------------------------------------------
    # /admin unload
    # --------------------------------------------------------
    @admin.command(
        name="unload",
        description="Unload a cog by name.",
    )
    @owner_only()
    async def unload_cog(self, interaction: discord.Interaction, cog: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        ext = cog if cog.startswith("cogs.") else f"cogs.{cog}"
        try:
            await self.bot.unload_extension(ext)
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to unload `{ext}`: `{e}`",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(f"🔄¤ Unloaded `{ext}`.", ephemeral=True)

    # --------------------------------------------------------
    # /admin restart
    # --------------------------------------------------------
    @admin.command(
        name="restart",
        description="Restart the bot. (Autoreloader will bring it back.)",
    )
    @owner_only()
    async def restart(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("🔄 Restarting bot…", ephemeral=True)
        await self.bot.close()

    # --------------------------------------------------------
    # /admin shutdown
    # --------------------------------------------------------
    @admin.command(
        name="shutdown",
        description="Shut down the bot cleanly.",
    )
    @owner_only()
    async def shutdown(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("🛑 Shutting down…", ephemeral=True)
        await self.bot.close()

    # --------------------------------------------------------
    # /admin nuke_commands  (FIXED VERSION)
    # --------------------------------------------------------
    @admin.command(
        name="nuke_commands",
        description="Delete ALL GLOBAL commands, then immediately restore dev guild commands.",
    )
    @owner_only()
    async def nuke_commands(
        self,
        interaction: discord.Interaction,
        confirm: bool = False,
    ) -> None:

        if not confirm:
            await interaction.response.send_message(
                "⚠️ This will DELETE **ALL GLOBAL SLASH COMMANDS**.\n"
                "Guild commands (dev server) will stay intact.\n\n"
                "**To proceed:** `/admin nuke_commands confirm:true`",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        # Get application info
        app_info = await self.bot.application_info()
        app_id = app_info.id

        # -------------------------------------------
        # 1) WIPE GLOBAL COMMANDS (correct HTTP method)
        # -------------------------------------------
        try:
            await self.bot.http.bulk_upsert_global_commands(app_id, [])
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Failed to wipe global commands: `{e}`",
                ephemeral=True,
            )

        # -------------------------------------------
        # 2) Immediately restore dev guild commands
        # -------------------------------------------
        try:
            guild_obj = discord.Object(id=DEV_GUILD_ID)
            synced = await self.bot.tree.sync(guild=guild_obj)
        except Exception as e:
            return await interaction.followup.send(
                f"☢ Global commands nuked, but dev guild sync failed: `{e}`.\n"
                f"If commands do not reappear, restart the bot.",
                ephemeral=True,
            )

        await interaction.followup.send(
            f"☢️ **Nuked ALL global commands.**\n"
            f"🤔 Restored **{len(synced)}** commands to dev guild `{DEV_GUILD_ID}`.\n\n"
            f"Use `/admin sync_global` to republish globally when you're ready.",
            ephemeral=True,
        )

    # --------------------------------------------------------
    # /admin logs_list
    # --------------------------------------------------------
    @admin.command(
        name="logs_list",
        description="List log files.",
    )
    @owner_only()
    async def logs_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        files = [p for p in LOGS_DIR.iterdir() if p.is_file()]

        if not files:
            return await interaction.followup.send("No log files found.", ephemeral=True)

        lines = []
        for p in sorted(files):
            size_kb = p.stat().st_size / 1024
            lines.append(f"â€¢ `{p.name}` â€” {size_kb:.1f} KB")

        await interaction.followup.send("\n".join(lines), ephemeral=True)

    # --------------------------------------------------------
    # /admin logs_get
    # --------------------------------------------------------
    @admin.command(
        name="logs_get",
        description="Upload a specific log file.",
    )
    @owner_only()
    async def logs_get(self, interaction: discord.Interaction, filename: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        path = (LOGS_DIR / filename).resolve()

        # Prevent directory traversal attacks
        if LOGS_DIR.resolve() not in path.parents and path.parent != LOGS_DIR.resolve():
            return await interaction.followup.send(
                "❌ Invalid filename.",
                ephemeral=True,
            )

        if not path.is_file():
            return await interaction.followup.send(
                f"❌ Log file `{filename}` not found.",
                ephemeral=True,
            )

        await interaction.followup.send(
            content=f"🔄„ Log file `{filename}`:",
            file=discord.File(str(path), filename=path.name),
            ephemeral=True,
        )

    # --------------------------------------------------------
    # /admin check
    # --------------------------------------------------------
    @admin.command(
        name="check",
        description="Show a quick health summary.",
    )
    @owner_only()
    async def check(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        latency = round(self.bot.latency * 1000, 1)  # ms
        guild_count = len(self.bot.guilds)
        cog_count = len(self.bot.cogs)
        cmd_count = len(self.bot.tree.get_commands())

        embed = discord.Embed(
            title="ðŸ›  JARVIS Health Check",
            color=discord.Color.green(),
        )

        embed.add_field(name="Latency", value=f"{latency} ms")
        embed.add_field(name="Guilds", value=str(guild_count))
        embed.add_field(name="Cogs", value=str(cog_count))
        embed.add_field(name="Slash Commands", value=str(cmd_count))
        embed.add_field(name="Python", value=platform.python_version())
        embed.add_field(name="discord.py", value=discord.__version__)

        await interaction.followup.send(embed=embed, ephemeral=True)


    # --------------------------------------------------------
    # /admin refresh_rankings
    # --------------------------------------------------------
    @admin.command(
        name="refresh_rankings",
        description="Manually refresh rankings data from Google Sheets",
    )
    @owner_only()
    async def refresh_rankings(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            from utils.rankings.cache import RankingsCache
            
            cache = RankingsCache()
            loader = cache.refresh()
            
            count = len(loader.entries)
            
            msg = f"\u2705 Refreshed {count} entries from Google Sheets.\nCache will be valid for 24 hours."
            
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            msg = f"\u274c Failed to refresh rankings: `{e}`"
            await interaction.followup.send(msg, ephemeral=True)


# ------------------------------------------------------------
# Cog setup
# ------------------------------------------------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
