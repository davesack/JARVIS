from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import List


class HelpView(discord.ui.View):
    """Paginated view for game help."""
    
    def __init__(self, embeds: List[discord.Embed]):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.current_page = 0
        self.max_pages = len(embeds)
        
        # Disable buttons if only one page
        if self.max_pages == 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True
    
    def update_buttons(self):
        """Update button states based on current page."""
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == self.max_pages - 1)
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(label="🏠 Overview", style=discord.ButtonStyle.blurple, row=1)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class GamesHelp(commands.Cog):
    """Comprehensive help system for all games."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="games_help", description="View help for all available games")
    async def games_help(self, interaction: discord.Interaction):
        """Display paginated help for all games."""
        embeds = self._create_help_embeds()
        view = HelpView(embeds)
        view.update_buttons()
        
        await interaction.response.send_message(embed=embeds[0], view=view)
    
    def _create_help_embeds(self) -> List[discord.Embed]:
        """Create all help embeds."""
        embeds = []
        
        # Overview page
        overview = discord.Embed(
            title="🎮 JARVIS Games - Complete Guide",
            description="Welcome to the JARVIS game suite! Use the buttons below to navigate through different game categories.",
            color=discord.Color.blue()
        )
        overview.add_field(
            name="📋 Game Categories",
            value=(
                "**Channel Games** - Collaborative games in any channel\n"
                "**Daily Games** - New puzzles every day\n"
                "**Session Games** - Auto-rotating quick games\n"
                "**Competitive Games** - Play against other users\n"
                "**Word Games** - Wordle, Hangman, and more"
            ),
            inline=False
        )
        overview.add_field(
            name="🏆 Stats & Leaderboards",
            value="Use `/games` to view your stats\nUse `/leaderboard` to see top players",
            inline=False
        )
        overview.set_footer(text="Page 1 | Use the buttons below to navigate")
        embeds.append(overview)
        
        # Channel Games
        channel_games = discord.Embed(
            title="📺 Channel Games",
            description="Start collaborative games that run continuously in a channel. Players take turns!",
            color=discord.Color.green()
        )
        channel_games.add_field(
            name="🔢 Counting",
            value=(
                "**How to Start:** `/start game:counting start_number:1`\n"
                "**Rules:** Count up from the starting number, one number per person\n"
                "**Important:** Players must alternate - you can't post twice in a row!\n"
                "**Example:** Player1: `1`, Player2: `2`, Player3: `3`..."
            ),
            inline=False
        )
        channel_games.add_field(
            name="🔤 Alphabet Game",
            value=(
                "**How to Start:** `/start game:alphabet`\n"
                "**Rules:** Post real words starting with each letter A→Z\n"
                "**Important:** Must be a real word, must alternate players\n"
                "**Example:** `Apple`, `Banana`, `Cat`, `Dog`..."
            ),
            inline=False
        )
        channel_games.add_field(
            name="🔗 Word Chain",
            value=(
                "**How to Start:** `/start game:word_chain`\n"
                "**Rules:** Each word must start with the last letter of the previous word\n"
                "**Important:** Must be a real word, must alternate players\n"
                "**Example:** `Hello` → `Orange` → `Eagle` → `Elephant`..."
            ),
            inline=False
        )
        channel_games.add_field(
            name="📄 Sentence Builder",
            value=(
                "**How to Start:** `/start game:sentence`\n"
                "**Rules:** Build a sentence one word at a time. End with `.` `!` or `?`\n"
                "**Important:** One word per person, must alternate players\n"
                "**Example:** `The` `quick` `brown` `fox` `jumped.`"
            ),
            inline=False
        )
        channel_games.set_footer(text="Page 2 | Channel games enforce strict turn order")
        embeds.append(channel_games)
        
        # Daily Games
        daily_games = discord.Embed(
            title="📅 Daily Games",
            description="Fresh puzzles every day! Play in private threads for a personalized experience.",
            color=discord.Color.purple()
        )
        daily_games.add_field(
            name="🟩 Daily Wordle",
            value=(
                "**Subscribe:** `/daily_subscribe game:wordle`\n"
                "**How to Play:** Guess the 5-letter word in 6 tries\n"
                "**Feedback:** 🟩 Correct spot | 🟨 Wrong spot | ⬛ Not in word\n"
                "**To Play:** Type `wordle [your guess]` in your private thread"
            ),
            inline=False
        )
        daily_games.add_field(
            name="🔀 Daily Scramble",
            value=(
                "**Subscribe:** `/daily_subscribe game:scramble`\n"
                "**How to Play:** Unscramble the daily word\n"
                "**Attempts:** Unlimited guesses\n"
                "**To Play:** Type `scramble [your answer]` in your private thread"
            ),
            inline=False
        )
        daily_games.add_field(
            name="🧠 Daily Absurdle",
            value=(
                "**Subscribe:** `/daily_subscribe game:absurdle`\n"
                "**How to Play:** Adversarial Wordle - the game tries to avoid your guesses!\n"
                "**Challenge:** Narrow down the word pool strategically\n"
                "**To Play:** Type `absurdle [your guess]` in your private thread"
            ),
            inline=False
        )
        daily_games.add_field(
            name="📊 Multi-Board Games",
            value=(
                "**Dordle** (2 boards, 7 guesses): `/daily_subscribe game:dordle`\n"
                "**Quordle** (4 boards, 9 guesses): `/daily_subscribe game:quordle`\n"
                "**Octordle** (8 boards, 16 guesses): `/daily_subscribe game:octordle`\n"
                "**Sequence** (8 boards solved one at a time): `/daily_subscribe game:wordle_sequence`"
            ),
            inline=False
        )
        daily_games.add_field(
            name="📏 Betweenle",
            value=(
                "**Subscribe:** `/daily_subscribe game:betweenle`\n"
                "**How to Play:** Guess the word that falls alphabetically between two words\n"
                "**To Play:** Type `betweenle [your guess]` in your private thread"
            ),
            inline=False
        )
        daily_games.add_field(
            name="🚫 Unsubscribe",
            value="Use `/daily_unsubscribe game:[game_name]` to stop receiving a daily game",
            inline=False
        )
        daily_games.set_footer(text="Page 3 | Daily games reset every 24 hours")
        embeds.append(daily_games)
        
        # Session & Competitive Games
        session_games = discord.Embed(
            title="⚡ Session & Competitive Games",
            description="Quick-play games and head-to-head matches!",
            color=discord.Color.orange()
        )
        session_games.add_field(
            name="🔄 Auto-Rotating Sessions",
            value=(
                "**Start:** `/start_sessions`\n"
                "**Games in Rotation:**\n"
                "• Alphabet Race - Speed through A-Z with real words\n"
                "• Word Scramble - Unscramble the word first\n"
                "• Guess the Number - Find the mystery number (1-10,000)\n"
                "**Auto-Advance:** Games automatically cycle after completion"
            ),
            inline=False
        )
        session_games.add_field(
            name="🔴🟡 Connect 4",
            value=(
                "**Start:** `/connect4_start`\n"
                "**How to Play:** Get 4 in a row horizontally, vertically, or diagonally\n"
                "**Lobby:** Wait for an opponent to accept (60 second timeout)\n"
                "**Turn Timer:** 60 seconds per turn with 10 second warning\n"
                "**Controls:** Click column buttons to drop your piece"
            ),
            inline=False
        )
        session_games.add_field(
            name="🪢 Hangman",
            value=(
                "**Start:** `/hangman difficulty:[easy/medium/hard] players:[1-3]`\n"
                "**How to Play:** Guess letters to reveal the word\n"
                "**Lives:** 6 wrong guesses allowed\n"
                "**Controls:** Type a single letter to guess\n"
                "**Turn-Based:** Players must alternate guesses"
            ),
            inline=False
        )
        session_games.set_footer(text="Page 4 | Competitive games track wins and losses")
        embeds.append(session_games)
        
        # Standalone & Creative Games
        creative_games = discord.Embed(
            title="🎨 Creative & Standalone Games",
            description="Express yourself and play at your own pace!",
            color=discord.Color.gold()
        )
        creative_games.add_field(
            name="🎨 Drawing Prompts",
            value=(
                "**Start:** `/start_drawing`\n"
                "**How It Works:** Receive creative drawing prompts every 24 hours\n"
                "**No Rules:** Draw traditionally, digitally, or silly - all welcome!\n"
                "**Share:** Post your art directly in the channel\n"
                "**Auto-Rotation:** New prompt appears automatically"
            ),
            inline=False
        )
        creative_games.add_field(
            name="🟩 Standalone Wordle",
            value=(
                "**Start:** `/wordle`\n"
                "**How to Play:** Co-op Wordle in any channel\n"
                "**Attempts:** 6 guesses shared by all players\n"
                "**Random Word:** Different from the daily Wordle\n"
                "**Type:** Post a 5-letter word to guess"
            ),
            inline=False
        )
        creative_games.set_footer(text="Page 5 | Creative games are for fun and expression")
        embeds.append(creative_games)
        
        # Stats & Tips
        stats_tips = discord.Embed(
            title="📊 Stats, Leaderboards & Pro Tips",
            description="Track your progress and master the games!",
            color=discord.Color.red()
        )
        stats_tips.add_field(
            name="📈 View Your Stats",
            value=(
                "**Command:** `/games user:[optional @user]`\n"
                "**Shows:** All your game statistics organized by game type\n"
                "**Tracks:** Wins, words played, best times, completion rates, and more"
            ),
            inline=False
        )
        stats_tips.add_field(
            name="🏆 Leaderboards",
            value=(
                "**Command:** `/leaderboard stat:[stat_key]`\n"
                "**Examples:**\n"
                "• `alphabet_race.best_time` - Fastest completion\n"
                "• `counting_numbers` - Most numbers counted\n"
                "• `word_chain_words` - Most word chain contributions\n"
                "• `scramble.wins` - Most scramble wins"
            ),
            inline=False
        )
        stats_tips.add_field(
            name="💡 Pro Tips",
            value=(
                "**Channel Games:**\n"
                "• You MUST alternate with other players\n"
                "• Invalid moves are deleted immediately with warnings\n"
                "• Words must be real and match the rules\n\n"
                "**Daily Games:**\n"
                "• Subscribe to multiple games for variety\n"
                "• Race to be the first solver for glory\n"
                "• Private threads keep your guesses secret\n\n"
                "**Competitive Games:**\n"
                "• Watch the timer - forfeits count as losses\n"
                "• Practice different difficulties in Hangman\n"
                "• Connect 4 rewards strategic thinking"
            ),
            inline=False
        )
        stats_tips.add_field(
            name="⚠️ Common Issues",
            value=(
                "**My message was deleted!** You either:\n"
                "• Went twice in a row (must alternate)\n"
                "• Posted an invalid word or number\n"
                "• Didn't follow the game rules\n\n"
                "**Can't subscribe?** Make sure you're spelling the game name correctly"
            ),
            inline=False
        )
        stats_tips.set_footer(text="Page 6 | Have fun and play fair!")
        embeds.append(stats_tips)
        
        return embeds


async def setup(bot: commands.Bot):
    await bot.add_cog(GamesHelp(bot))
