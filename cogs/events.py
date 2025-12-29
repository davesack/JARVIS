from __future__ import annotations

import asyncio
from datetime import datetime, date
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.events.events_db import (
    add_event,
    delete_event,
    list_events,
    get_events_for_date,
    update_event,
)
from utils.events.events_scheduler import (
    build_event_embed,
    post_events_for_date,
)


class Events(commands.Cog):
    """
    Celebration-focused recurring event system.
    Posts events on the day they occur (birthdays, anniversaries, etc.).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_check.start()

    # ---------------------------------------------------------
    # Slash command group: /event ...
    # ---------------------------------------------------------
    event = app_commands.Group(
        name="event",
        description="Manage recurring celebration events.",
    )

    # -----------------------------
    # /event add
    # -----------------------------
    @event.command(name="add", description="Add a recurring event.")
    @app_commands.describe(
        name="Person or event name.",
        event_type="Type of event (birthday, anniversary, etc.).",
        date_str="Date in MM-DD format (e.g. 11-28).",
        start_year="Year the event started (used for age or years).",
        channel="Channel to post in (defaults to this channel).",
        notes="Optional notes or custom message.",
        show_age="Whether to display age/years in the post.",
    )
    async def event_add(
        self,
        interaction: discord.Interaction,
        name: str,
        event_type: str,
        date_str: str,
        start_year: int,
        channel: Optional[discord.TextChannel] = None,
        notes: Optional[str] = None,
        show_age: bool = True,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Parse MM-DD
        try:
            parsed = datetime.strptime(date_str, "%m-%d")
            month = parsed.month
            day = parsed.day
        except ValueError:
            await interaction.followup.send(
                "❌ Invalid date format. Please use **MM-DD**, e.g. `11-28`.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.followup.send(
                "❌ Events can only be created inside a server.",
                ephemeral=True,
            )
            return

        target_channel = channel or interaction.channel
        if target_channel is None:
            await interaction.followup.send(
                "❌ Could not determine which channel to use.",
                ephemeral=True,
            )
            return

        try:
            event = add_event(
                guild_id=interaction.guild.id,
                name=name,
                event_type=event_type,
                month=month,
                day=day,
                start_year=start_year,
                channel_id=target_channel.id,
                created_by=interaction.user.id,
                notes=notes,
                show_age=show_age,
            )
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        msg = (
            f"✅ **Event created!**\n\n"
            f"**Name:** {event.name}\n"
            f"**Type:** `{event.type}`\n"
            f"**Date:** `{event.date}`\n"
            f"**Start Year:** `{event.start_year}`\n"
            f"**Show Age:** `{event.show_age}`\n"
            f"**Channel:** {target_channel.mention}\n"
            f"**ID:** `{event.id[:8]}`"
        )

        await interaction.followup.send(msg, ephemeral=True)

    # -----------------------------
    # /event list
    # -----------------------------
    @event.command(name="list", description="List all recurring events for this server.")
    async def event_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if interaction.guild is None:
            await interaction.followup.send(
                "❌ This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        events = list_events(guild_id=interaction.guild.id)
        if not events:
            await interaction.followup.send(
                "There are no events registered for this server yet.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📅 Registered Events",
            description=f"Total: **{len(events)}**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        lines = []
        for e in events:
            lines.append(
                f"`{e.id[:8]}` • **{e.name}** "
                f"(`{e.type}`) • `{e.date}` • "
                f"Started `{e.start_year}` • "
                f"<#{e.channel_id}>"
            )

        embed.add_field(
            name="Events",
            value="\n".join(lines[:25]),
            inline=False,
        )

        if len(lines) > 25:
            embed.add_field(
                name="Note",
                value="Showing first 25 events only.",
                inline=False,
            )

        embed.set_footer(text="Use /event edit or /event delete with the event ID.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # -----------------------------
    # /event edit
    # -----------------------------
    @event.command(name="edit", description="Edit an existing event.")
    @app_commands.describe(
        event_id="The event ID or ID prefix.",
        name="New name for the event.",
        start_year="New start year.",
        notes="New notes or message.",
        show_age="Toggle age/years display.",
    )
    async def event_edit(
        self,
        interaction: discord.Interaction,
        event_id: str,
        name: Optional[str] = None,
        start_year: Optional[int] = None,
        notes: Optional[str] = None,
        show_age: Optional[bool] = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if interaction.guild is None:
            await interaction.followup.send(
                "❌ This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        # Resolve full ID from prefix
        events = list_events(guild_id=interaction.guild.id)
        full_id = next(
            (e.id for e in events if e.id == event_id or e.id.startswith(event_id)),
            None,
        )

        if full_id is None:
            await interaction.followup.send(
                "❌ Event not found. Use `/event list` to view IDs.",
                ephemeral=True,
            )
            return

        updated = update_event(
            full_id,
            name=name,
            start_year=start_year,
            notes=notes,
            show_age=show_age,
        )

        if not updated:
            await interaction.followup.send(
                "❌ Failed to update event.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "✅ Event updated successfully.",
            ephemeral=True,
        )

    # -----------------------------
    # /event delete
    # -----------------------------
    @event.command(name="delete", description="Delete an event by its ID.")
    async def event_delete(self, interaction: discord.Interaction, event_id: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if interaction.guild is None:
            await interaction.followup.send(
                "❌ This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        events = list_events(guild_id=interaction.guild.id)
        full_id = next(
            (e.id for e in events if e.id == event_id or e.id.startswith(event_id)),
            None,
        )

        if full_id is None:
            await interaction.followup.send(
                "❌ Event not found.",
                ephemeral=True,
            )
            return

        if delete_event(full_id, guild_id=interaction.guild.id):
            await interaction.followup.send("✅ Event deleted.", ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ Failed to delete event.",
                ephemeral=True,
            )

    # -----------------------------
    # /event test
    # -----------------------------
    @event.command(name="test", description="Preview today's events in this channel.")
    async def event_test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if interaction.guild is None or interaction.channel is None:
            await interaction.followup.send(
                "❌ This command must be used in a server text channel.",
                ephemeral=True,
            )
            return

        today = date.today()
        events = [
            e for e in get_events_for_date(today)
            if e.guild_id == interaction.guild.id
        ]

        if not events:
            await interaction.followup.send(
                "No events for today on this server.",
                ephemeral=True,
            )
            return

        for e in events:
            embed = build_event_embed(e, today)
            await interaction.channel.send(embed=embed)

        await interaction.followup.send(
            f"✅ Posted **{len(events)}** event(s) in this channel.",
            ephemeral=True,
        )

    # ---------------------------------------------------------
    # Daily background task
    # ---------------------------------------------------------
    @tasks.loop(hours=24)
    async def daily_check(self):
        await post_events_for_date(self.bot)

    @daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

        now = datetime.now()
        first_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if first_run <= now:
            from datetime import timedelta
            first_run += timedelta(days=1)

        await asyncio.sleep((first_run - now).total_seconds())

    # ---------------------------------------------------------
    # Cog teardown
    # ---------------------------------------------------------
    def cog_unload(self):
        self.daily_check.cancel()


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
