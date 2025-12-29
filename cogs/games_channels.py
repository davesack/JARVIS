from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import discord
from discord import app_commands
from discord.ext import commands

from config import DATA_ROOT
from utils.games.words import is_real_word
from utils.games.game_stats import increment

# ============================================================
# STORAGE
# ============================================================

GAMES_ROOT = DATA_ROOT / "games" / "channels"
GAMES_ROOT.mkdir(parents=True, exist_ok=True)

STATE_FILE = GAMES_ROOT / "state.json"

# ============================================================
# HELPERS
# ============================================================

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ============================================================
# COG
# ============================================================

class GamesChannels(commands.Cog):
    """
    Channel-locked counting and word games with strict enforcement.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state: Dict = load_json(STATE_FILE, {})

    # ========================================================
    # SLASH COMMANDS
    # ========================================================

    @app_commands.command(name="start", description="Start a channel game")
    @app_commands.describe(
        game="Game type",
        start_number="Starting number (counting only)",
    )
    @app_commands.choices(
        game=[
            app_commands.Choice(name="counting", value="counting"),
            app_commands.Choice(name="alphabet", value="alphabet"),
            app_commands.Choice(name="word_chain", value="word_chain"),
            app_commands.Choice(name="sentence", value="sentence"),
        ]
    )
    async def start(
        self,
        interaction: discord.Interaction,
        game: app_commands.Choice[str],
        start_number: int = 1,
    ):
        channel_id = str(interaction.channel_id)

        if channel_id in self.state:
            await interaction.response.send_message(
                "⚠️ A game is already active in this channel.",
                ephemeral=True,
            )
            return

        if game.value == "counting":
            self.state[channel_id] = {
                "type": "counting",
                "current": start_number - 1,
                "last_user": None,
            }
            msg = f"🔢 **Counting started at {start_number}!**"

        elif game.value == "alphabet":
            self.state[channel_id] = {
                "type": "alphabet",
                "current": "a",
                "last_user": None,
            }
            msg = "🔤 **Alphabet game started!**\nNext letter: **A**"

        elif game.value == "word_chain":
            self.state[channel_id] = {
                "type": "word_chain",
                "last_letter": None,
                "last_word": None,
                "last_user": None,
            }
            msg = "🔗 **Word Chain started!**\nAny real word may start the chain."

        else:  # sentence
            self.state[channel_id] = {
                "type": "sentence",
                "words": [],
                "last_user": None,
            }
            msg = "📄 **Sentence Builder started!**\nOne real word per person."

        save_json(STATE_FILE, self.state)
        await interaction.response.send_message(msg)

    @app_commands.command(name="stop_game", description="[ADMIN] Stop the current channel game")
    @app_commands.checks.has_permissions(administrator=True)
    async def stop_game(self, interaction: discord.Interaction):
        channel_id = str(interaction.channel_id)
        
        if channel_id not in self.state:
            await interaction.response.send_message(
                "⚠️ No game is active in this channel.",
                ephemeral=True,
            )
            return
        
        game_type = self.state[channel_id]["type"]
        del self.state[channel_id]
        save_json(STATE_FILE, self.state)
        
        await interaction.response.send_message(
            f"🛑 **{game_type.replace('_', ' ').title()} game stopped.**"
        )

    @stop_game.error
    async def stop_game_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need administrator permissions to stop games.",
                ephemeral=True
            )

    # ========================================================
    # MESSAGE LISTENER
    # ========================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        channel_id = str(message.channel.id)
        if channel_id not in self.state:
            return

        game = self.state[channel_id]
        user_id = str(message.author.id)
        content = message.content.strip()

        # Enforce alternating turns
        if game.get("last_user") == user_id:
            await message.delete()
            await message.channel.send(
                f"⚠️ {message.author.mention} You can't go twice in a row! Wait for someone else to play.",
                delete_after=5
            )
            return

        # ----------------------------------------------------
        # COUNTING
        # ----------------------------------------------------
        if game["type"] == "counting":
            # Must be a number
            if not content.isdigit():
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Please only post numbers in this counting game.",
                    delete_after=5
                )
                return

            number = int(content)
            expected = game["current"] + 1
            
            # Must be the correct next number
            if number != expected:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Wrong number! Expected **{expected}**, but you posted **{number}**.",
                    delete_after=5
                )
                return

            # Valid - update state
            game["current"] = number
            game["last_user"] = user_id
            increment(message.author.id, "counting_numbers")

        # ----------------------------------------------------
        # ALPHABET
        # ----------------------------------------------------
        elif game["type"] == "alphabet":
            word = content.lower()

            # Must be alphabetic only
            if not word.isalpha():
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Please only post alphabetic words (no numbers or symbols).",
                    delete_after=5
                )
                return

            # Must be a real word
            if not is_real_word(word):
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} **'{word}'** is not a valid word!",
                    delete_after=5
                )
                return

            expected_letter = game["current"]
            
            # Must start with the correct letter
            if word[0] != expected_letter:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Word must start with **{expected_letter.upper()}**! You posted **'{word}'** which starts with **{word[0].upper()}**.",
                    delete_after=5
                )
                return

            # Valid - update state
            game["current"] = chr(((ord(game["current"]) - 97 + 1) % 26) + 97)
            game["last_user"] = user_id
            increment(message.author.id, "alphabet_words")

        # ----------------------------------------------------
        # WORD CHAIN
        # ----------------------------------------------------
        elif game["type"] == "word_chain":
            word = content.lower()

            # Must be alphabetic only
            if not word.isalpha():
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Please only post alphabetic words (no numbers or symbols).",
                    delete_after=5
                )
                return

            # Must be a real word
            if not is_real_word(word):
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} **'{word}'** is not a valid word!",
                    delete_after=5
                )
                return

            # If there's a previous word, must start with its last letter
            if game["last_letter"] is not None:
                if word[0] != game["last_letter"]:
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ {message.author.mention} Word must start with **{game['last_letter'].upper()}** (last letter of **'{game['last_word']}'**)! You posted **'{word}'** which starts with **{word[0].upper()}**.",
                        delete_after=7
                    )
                    return

            # Valid - update state
            game["last_letter"] = word[-1]
            game["last_word"] = word
            game["last_user"] = user_id
            increment(message.author.id, "word_chain_words")

        # ----------------------------------------------------
        # SENTENCE
        # ----------------------------------------------------
        elif game["type"] == "sentence":
            # Must be a single word
            if " " in content:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Only one word at a time!",
                    delete_after=5
                )
                return

            # Extract word (remove punctuation for validation)
            word = content.rstrip(".!?").lower()
            
            # Must be a real word
            if not is_real_word(word):
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} **'{word}'** is not a valid word!",
                    delete_after=5
                )
                return

            # Valid - add to sentence
            game["words"].append(content)
            game["last_user"] = user_id
            increment(message.author.id, "sentence_words")

            # Check if sentence is complete
            if content[-1] in ".!?":
                sentence = " ".join(game["words"])
                await self._post_finished_sentence(message.guild, sentence)
                del self.state[channel_id]

        save_json(STATE_FILE, self.state)

    # ========================================================
    # HELPERS
    # ========================================================

    async def _post_finished_sentence(self, guild: discord.Guild, sentence: str):
        channel = discord.utils.get(guild.text_channels, name="finished-sentences")
        if channel is None:
            channel = await guild.create_text_channel("finished-sentences")

        await channel.send(f"📄 **Finished Sentence:**\n{sentence}")

# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesChannels(bot))
