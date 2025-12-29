from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict

from utils.games.game_stats import (
    get_user_stats,
    get_all_stats,
)

# ============================================================
# COG
# ============================================================

class GamesStats(commands.Cog):
    """Game stats and leaderboards"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    # ========================================================
    # /games stats
    # ========================================================

    @app_commands.command(name="games", description="View game stats for a user")
    @app_commands.describe(user="User to view stats for")
    async def stats(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        user = user or interaction.user
        stats = get_user_stats(user.id)

        if not stats:
            await interaction.response.send_message(
                f"🔄Š **{user.display_name} has no game stats yet.**",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"ðŸŽ® Game Stats â€” {user.display_name}",
            color=discord.Color.blurple(),
        )

        grouped: Dict[str, Dict[str, int]] = {}

        for key, value in stats.items():
            if "." in key:
                game, stat = key.split(".", 1)
            else:
                game, stat = "other", key

            grouped.setdefault(game, {})[stat] = value

        for game, values in sorted(grouped.items()):
            lines = [
                f"**{name.replace('_', ' ').title()}**: {val}"
                for name, val in sorted(values.items())
            ]
            embed.add_field(
                name=game.replace("_", " ").title(),
                value="\n".join(lines),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    # ========================================================
    # /games leaderboard
    # ========================================================

    @app_commands.command(name="leaderboard", description="View top players for a stat")
    @app_commands.describe(
        stat="Stat key (example: alphabet_race.best_time)"
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        stat: str,
    ):
        all_stats = get_all_stats()

        entries = []

        for user_id, stats in all_stats.items():
            if stat in stats:
                entries.append((int(user_id), stats[stat]))

        if not entries:
            await interaction.response.send_message(
                "âŒ No data found for that stat.",
                ephemeral=True,
            )
            return

        # Determine sort direction
        lower_is_better = "time" in stat or "best" in stat
        entries.sort(key=lambda x: x[1], reverse=not lower_is_better)

        embed = discord.Embed(
            title=f"ðŸ† Leaderboard â€” {stat.replace('.', ' ').title()}",
            color=discord.Color.gold(),
        )

        for i, (uid, value) in enumerate(entries[:10], start=1):
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            embed.add_field(
                name=f"#{i} â€” {name}",
                value=str(value),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesStats(bot))
