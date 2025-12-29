from discord.ext import commands
import asyncio

from utils.tokens.daily_prompt import send_daily_prompt


class Tokens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prompt_task: asyncio.Task | None = None

    async def cog_load(self):
        # Called automatically when the cog is loaded
        self.prompt_task = asyncio.create_task(send_daily_prompt(self.bot))

    async def cog_unload(self):
        if self.prompt_task:
            self.prompt_task.cancel()


async def setup(bot):
    await bot.add_cog(Tokens(bot))
