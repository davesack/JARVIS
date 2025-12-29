# bot.py
from __future__ import annotations
import os
import asyncio
import logging
import traceback
import discord
from discord.ext import commands
from config import TOKEN  # single source of truth

# =========================
# LOGGING SETUP
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("jarvis")

# =========================
# BOT SETUP
# =========================
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=INTENTS,
)

# =========================
# DAILY GAMES WIRING
# =========================
async def setup_daily_games(bot: commands.Bot):
    """
    Creates the GamesDaily cog and registers all daily games.
    This is the ONLY place daily games are wired together.
    """
    print("🎮 Setting up daily games...")
    
    from cogs.games_daily import GamesDaily
    from utils.games.daily_wordle import DailyWordle
    from utils.games.daily_scramble import DailyScramble
    from utils.games.daily_absurdle import DailyAbsurdle
    from utils.games.daily_betweenle import DailyBetweenle
    from utils.games.daily_dordle import DailyDordle
    from utils.games.daily_quordle import DailyQuordle
    from utils.games.daily_octordle import DailyOctordle
    from utils.games.daily_wordle_sequence import DailyWordleSequence
    
    games = [
        DailyWordle(),
        DailyScramble(),
        DailyAbsurdle(),
        DailyBetweenle(),
        DailyDordle(),
        DailyQuordle(),
        DailyOctordle(),
        DailyWordleSequence(),
    ]
    
    games_cog = GamesDaily(bot)
    for game in games:
        try:
            games_cog.register_game(game)
            print(f"  ✅ Registered {game.__class__.__name__}")
        except Exception as e:
            print(f"  ❌ Failed to register {game.__class__.__name__}: {e}")
    
    await bot.add_cog(games_cog)
    print("🎮 Daily games ready.")

# =========================
# COG LOADING
# =========================
async def load_cogs(bot: commands.Bot):
    """
    Auto-load all cogs except GamesDaily (handled manually).
    Provides detailed load output.
    """
    print("🔌 Loading cogs...")
    loaded = []
    failed = []
    
    for filename in sorted(os.listdir("./cogs")):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue
        if filename == "games_daily.py":
            continue  # handled explicitly
        
        ext = f"cogs.{filename[:-3]}"
        try:
            await bot.load_extension(ext)
            loaded.append(ext)
            print(f"  ✅ Loaded {ext}")
        except Exception as e:
            failed.append((ext, e))
            print(f"  ❌ Failed {ext}: {e}")
    
    print("\n🔄 Cog load summary")
    print(f"  Loaded: {len(loaded)}")
    if failed:
        print(f"  Failed: {len(failed)}")
        for ext, err in failed:
            print(f"    - {ext}: {err}")

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"✅ Logged in as {bot.user}")
    print(f"🆔 User ID: {bot.user.id}")
    print(f"🌐 Guilds: {len(bot.guilds)}")
    print(f"🔄 Cogs: {len(bot.cogs)}")
    print(f"🔧 Slash Commands: {len(bot.tree.get_commands())}")
    print("=" * 60)
    
    # Install send interceptor for manual tagging
    try:
        from utils.mediawatcher.send_interceptor import install_send_interceptor
        install_send_interceptor(bot)
        print("✅ Send interceptor installed for manual tagging")
    except ImportError as e:
        print(f"⚠️ Could not install send interceptor: {e}")
    
    # Start Arena discovery background scheduler
    from utils.arena.discovery_scheduler import start_arena_scheduler
    if not getattr(bot, "_arena_scheduler_started", False):
        bot._arena_scheduler_started = True
        asyncio.create_task(start_arena_scheduler(bot))
        print("⚙️ Arena scheduler started")

# =========================
# COMPREHENSIVE ERROR HANDLERS
# =========================
@bot.event
async def on_error(event: str, *args, **kwargs):
    """Catch all unhandled errors in events"""
    logger.error(f"❌ ERROR in event '{event}':")
    logger.error(traceback.format_exc())
    print(f"\n❌ ERROR in event '{event}':")
    print(traceback.format_exc())

@bot.event
async def on_command_error(ctx, error):
    """Catch prefix command errors"""
    logger.error(f"❌ COMMAND ERROR: {error}")
    logger.error(traceback.format_exc())
    print(f"\n❌ COMMAND ERROR: {error}")
    print(traceback.format_exc())

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Catch slash command errors - MOST IMPORTANT"""
    cmd_name = interaction.command.name if interaction.command else "unknown"
    
    logger.error("=" * 60)
    logger.error(f"❌ SLASH COMMAND ERROR: /{cmd_name}")
    logger.error(f"   User: {interaction.user} ({interaction.user.id})")
    logger.error(f"   Guild: {interaction.guild}")
    logger.error(f"   Channel: {interaction.channel}")
    logger.error(f"   Error Type: {type(error).__name__}")
    logger.error(f"   Error: {error}")
    logger.error("   Full Traceback:")
    logger.error(traceback.format_exc())
    logger.error("=" * 60)
    
    # Also print to console for immediate visibility
    print("\n" + "=" * 60)
    print(f"❌ SLASH COMMAND ERROR: /{cmd_name}")
    print(f"   User: {interaction.user}")
    print(f"   Error: {error}")
    print(f"   Full Traceback:")
    print(traceback.format_exc())
    print("=" * 60 + "\n")
    
    # Try to respond to user
    error_msg = f"❌ Command failed: {type(error).__name__}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)
    except Exception as e:
        logger.error(f"   Could not send error to user: {e}")

@bot.event
async def on_disconnect():
    """Log when bot disconnects"""
    logger.warning("⚠️  Bot disconnected from Discord")
    print("\n⚠️ Bot disconnected from Discord")

@bot.event
async def on_resumed():
    """Log when bot reconnects"""
    logger.info("✅ Bot reconnected to Discord")
    print("\n✅ Bot reconnected to Discord")

# =========================
# MAIN ENTRY
# =========================
async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in environment or config.py")
    
    async with bot:
        await load_cogs(bot)
        await setup_daily_games(bot)
        
        try:
            await bot.start(TOKEN)
        except Exception as e:
            logger.critical(f"❌ FATAL ERROR: Bot crashed!")
            logger.critical(traceback.format_exc())
            print("\n❌ FATAL ERROR: Bot crashed!")
            print(traceback.format_exc())
            raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down JARVIS...")
    except Exception as e:
        print(f"\n❌ FATAL: {e}")
        print(traceback.format_exc())
