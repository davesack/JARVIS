from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Dict
from datetime import date, timedelta

from utils.games.daily_engine import (
    DailyEngine,
    DailyGame,
    _load,
    _save,
    AGG_STATS,
    SUBSCRIPTIONS,
)

GAMES_CHANNEL_NAME = "games"
DAILY_TAG_HOURS = (15, 20)


class GamesDaily(commands.Cog):
    """
    Discord-facing wrapper for the Daily Game Engine.

    Responsibilities:
    - Rotate daily games
    - Post daily recap
    - Handle subscriptions & threads
    - Route guesses to engine
    - Announce first solves
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.engine = DailyEngine()
        self.games: Dict[str, DailyGame] = {}

        self.daily_rotation.start()
        self.daily_reminders.start()

    # -----------------------------
    # Game registration
    # -----------------------------

    def register_game(self, game: DailyGame):
        self.games[game.name] = game

    # -----------------------------
    # Scheduler tasks
    # -----------------------------

    @tasks.loop(hours=24)
    async def daily_rotation(self):
        """
        Runs once per day:
        1) Post yesterday recap
        2) Rotate daily games
        3) Announce new dailies
        """
        await self._post_daily_recap()

        self.engine.rotate_day(self.games)

        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=GAMES_CHANNEL_NAME)
            if not channel:
                continue

            for game in self.games.values():
                await channel.send(
                    f"🎯 **Daily {game.name.title()} is live!**\n"
                    f"Subscribe with `/daily_subscribe {game.name}` to play."
                )

    @tasks.loop(minutes=30)
    async def daily_reminders(self):
        """Reserved for reminder / streak logic."""
        now = discord.utils.utcnow()
        if now.hour not in DAILY_TAG_HOURS:
            return

    # -----------------------------
    # Daily recap
    # -----------------------------

    async def _post_daily_recap(self):
        """
        Posts recap for yesterday's daily games using aggregate stats.
        """
        stats = _load(AGG_STATS, {})
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        if yesterday not in stats:
            return

        lines = ["📊 **Yesterday's Daily Games Recap**\n"]

        for game_name, data in stats[yesterday].items():
            lines.append(f"**{game_name.title()}**")

            plays = data.get("plays", 0)
            solves = data.get("solves", 0)

            if solves == 0:
                lines.append("• ❌ Nobody solved it 😢")
                lines.append("")
                continue

            lines.append(f"• Solved by **{solves}** / {plays} players")

            first = data.get("first_solve")
            if first:
                lines.append(f"• 🏆 First solve: <@{first}>")

            best = data.get("best_guess_count")
            best_users = data.get("best_guess_users", [])
            if best is not None and best_users:
                mentions = ", ".join(f"<@{u}>" for u in best_users)
                lines.append(f"• 🎯 Best score: **{best} guesses** ({mentions})")

            lines.append("")

        message = "\n".join(lines)

        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=GAMES_CHANNEL_NAME)
            if channel:
                await channel.send(message)

    # -----------------------------
    # Slash commands
    # -----------------------------

    async def game_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for game names."""
        games = list(self.games.keys())
        return [
            app_commands.Choice(name=game.capitalize(), value=game)
            for game in games
            if current.lower() in game.lower()
        ][:25]  # Discord limits to 25 choices

    @commands.hybrid_command(name="daily_subscribe")
    @app_commands.autocomplete(game=game_autocomplete)
    async def subscribe(self, ctx: commands.Context, game: str):
        if game not in self.games:
            await ctx.reply("❌ Unknown game.")
            return

        subs = self._load_subs()
        subs.setdefault(str(ctx.author.id), set()).add(game)
        self._save_subs(subs)

        thread = await ctx.channel.create_thread(
            name=f"{ctx.author.display_name} | Daily {game}",
            type=discord.ChannelType.private_thread,
            invitable=False,
        )
        await thread.add_user(ctx.author)

        await ctx.reply(f"✅ Subscribed to **{game}**! Your private thread is ready.")

    @commands.hybrid_command(name="daily_unsubscribe")
    @app_commands.autocomplete(game=game_autocomplete)
    async def unsubscribe(self, ctx: commands.Context, game: str):
        subs = self._load_subs()
        user_games = subs.get(str(ctx.author.id), set())

        if game not in user_games:
            await ctx.reply("You're not subscribed to that game.")
            return

        user_games.remove(game)
        self._save_subs(subs)

        await ctx.reply(f"🗑️ Unsubscribed from **{game}**.")

    # -----------------------------
    # Message listener
    # -----------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Only process messages in threads
        if not isinstance(message.channel, discord.Thread):
            return

        content = message.content.strip().lower()

        # Check if this is a daily game thread by checking the thread name
        thread_name = message.channel.name.lower()
        
        game_name = None
        for name in self.games.keys():
            if f"daily {name}" in thread_name:
                game_name = name
                break
        
        if not game_name:
            return  # Not a daily game thread
        
        game = self.games[game_name]
        
        # In threads, the entire message is the guess (no game name prefix needed)
        guess = content

        result = self.engine.register_guess(
            user_id=str(message.author.id),
            game=game,
            guess=guess,
        )

        await message.reply(game.render_feedback(result))

        if result.get("completed") and result.get("success"):
            await self._announce_first_solve(game_name, message.author)

    # -----------------------------
    # Announcements
    # -----------------------------

    async def _announce_first_solve(self, game_name: str, user: discord.User):
        state = self.engine.current["games"][game_name]
        if state["first_solve_user"] != str(user.id):
            return

        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=GAMES_CHANNEL_NAME)
            if channel:
                await channel.send(
                    f"🏆 **{user.mention} is the first to solve today's {game_name.title()}!**"
                )

    # -----------------------------
    # Persistence helpers
    # -----------------------------

    def _load_subs(self) -> dict:
        raw = _load(SUBSCRIPTIONS, {})
        return {k: set(v) for k, v in raw.items()}

    def _save_subs(self, subs: dict):
        _save(SUBSCRIPTIONS, {k: list(v) for k, v in subs.items()})


async def setup(bot: commands.Bot):
    await bot.add_cog(GamesDaily(bot))
