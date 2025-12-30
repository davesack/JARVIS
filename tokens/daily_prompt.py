import asyncio
from datetime import datetime
from utils.tokens.chores import list_chores
from utils.tokens.transactions import add_transaction
from utils.tokens.config import DAILY_STREAK_BONUS

async def send_daily_prompt(bot):
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now()
        if now.hour == 19:  # configurable
            for guild in bot.guilds:
                channel = next(
                    (c for c in guild.text_channels if c.name == "parent-prompts"),
                    None
                )
                if not channel:
                    continue

                chores = list_chores()
                msg = "**Daily Chore Check**\n\n"
                for name, value in chores:
                    msg += f"• {name} ({value} tokens)\n"

                prompt = await channel.send(msg)
                await prompt.add_reaction("✅")
                await prompt.add_reaction("❌")

            await asyncio.sleep(3600)

        await asyncio.sleep(60)
