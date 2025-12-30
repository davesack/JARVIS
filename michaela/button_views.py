"""
Button Views for Interactive Logging
=====================================

Discord UI components for one-click logging:
- Sleep quality (1-5 stars)
- Mood tracking (1-5 emoji scale)
- Journal choices (full vs micro)
- Feeling picker (multi-select)

All integrate with Michaela's tracking systems.
"""

import discord
from discord.ui import View, Button, Select, Modal, TextInput
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cogs.michaela import Michaela


# =========================================================
# SLEEP RATING VIEW (5-star system)
# =========================================================

class SleepRatingView(View):
    """
    Five-button sleep quality rating
    
    User clicks star rating → Logs to sleep tracker → Michaela responds
    """
    
    def __init__(self, michaela_cog: 'Michaela'):
        super().__init__(timeout=10800)  # 3 hours to respond
        self.michaela = michaela_cog
    
    @discord.ui.button(label="⭐", style=discord.ButtonStyle.danger, custom_id="sleep_1")
    async def sleep_poor(self, interaction: discord.Interaction, button: Button):
        await self._log_sleep(interaction, 1, "poor")
    
    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, custom_id="sleep_2")
    async def sleep_fair(self, interaction: discord.Interaction, button: Button):
        await self._log_sleep(interaction, 2, "fair")
    
    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.primary, custom_id="sleep_3")
    async def sleep_good(self, interaction: discord.Interaction, button: Button):
        await self._log_sleep(interaction, 3, "good")
    
    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.success, custom_id="sleep_4")
    async def sleep_great(self, interaction: discord.Interaction, button: Button):
        await self._log_sleep(interaction, 4, "great")
    
    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.success, custom_id="sleep_5")
    async def sleep_excellent(self, interaction: discord.Interaction, button: Button):
        await self._log_sleep(interaction, 5, "excellent")
    
    async def _log_sleep(self, interaction: discord.Interaction, rating: int, quality: str):
        """
        Log sleep quality and generate Michaela's response
        """
        
        # Log to sleep tracker (only 'quality' parameter - no 'rating')
        self.michaela.sleep.log_sleep(quality=quality)
        
        # Update message to show logged
        await interaction.response.edit_message(
            content=f"✅ Logged: {quality.title()} sleep ({rating}/5 stars)",
            view=None  # Remove buttons
        )
        
        # Generate Michaela's response based on rating
        response = await self.michaela.generate_sleep_response(rating, quality)
        
        # Send response
        await interaction.channel.send(response)


# =========================================================
# MOOD RATING VIEW (5-emoji system)
# =========================================================

class MoodRatingView(View):
    """
    Five-emoji mood scale
    
    User clicks emoji → Logs to mood tracker → Michaela responds
    Offers journal prompt if mood is low (1-3)
    """
    
    def __init__(self, michaela_cog: 'Michaela'):
        super().__init__(timeout=10800)  # 3 hours to respond
        self.michaela = michaela_cog
    
    @discord.ui.button(emoji="😫", label="1 - Struggling", style=discord.ButtonStyle.danger)
    async def mood_struggling(self, interaction: discord.Interaction, button: Button):
        await self._log_mood(interaction, 1, "struggling")
    
    @discord.ui.button(emoji="😕", label="2 - Low", style=discord.ButtonStyle.secondary)
    async def mood_low(self, interaction: discord.Interaction, button: Button):
        await self._log_mood(interaction, 2, "low")
    
    @discord.ui.button(emoji="😐", label="3 - Okay", style=discord.ButtonStyle.secondary)
    async def mood_okay(self, interaction: discord.Interaction, button: Button):
        await self._log_mood(interaction, 3, "okay")
    
    @discord.ui.button(emoji="🙂", label="4 - Good", style=discord.ButtonStyle.success)
    async def mood_good(self, interaction: discord.Interaction, button: Button):
        await self._log_mood(interaction, 4, "good")
    
    @discord.ui.button(emoji="😊", label="5 - Great", style=discord.ButtonStyle.success)
    async def mood_great(self, interaction: discord.Interaction, button: Button):
        await self._log_mood(interaction, 5, "great")
    
    async def _log_mood(self, interaction: discord.Interaction, rating: int, label: str):
        """
        Log mood and optionally offer journal prompt
        """
        
        # Log to mood tracker (if you have one, otherwise journal system)
        from datetime import datetime
        
        # Store in journal system using add_entry (not add_mood_entry!)
        self.michaela.journal.add_entry(
            text=f"Mood check-in: {label}",
            mood=label,
            energy=rating * 2  # Convert 1-5 rating to 2-10 energy scale
        )
        
        # Update message
        await interaction.response.edit_message(
            content=f"✅ Logged: Feeling {label} today ({rating}/5)",
            view=None
        )
        
        # Generate empathetic response
        response = await self.michaela.generate_mood_response(rating, label)
        await interaction.channel.send(response)
        
        # Offer journal if mood is low (1-3)
        if rating <= 3:
            journal_view = JournalChoiceView(self.michaela)
            await interaction.channel.send(
                "Would you like to journal about your day?",
                view=journal_view
            )


# =========================================================
# JOURNAL CHOICE VIEW (Full vs Micro)
# =========================================================

class JournalChoiceView(View):
    """
    Choice between full journal or micro-journal
    
    Full: Opens text modal for paragraphs
    Micro: Opens feeling picker
    """
    
    def __init__(self, michaela_cog: 'Michaela'):
        super().__init__(timeout=1800)  # 30 min to decide
        self.michaela = michaela_cog
    
    @discord.ui.button(label="📝 Full Journal", style=discord.ButtonStyle.primary)
    async def full_journal(self, interaction: discord.Interaction, button: Button):
        """Open modal for full journal entry"""
        modal = FullJournalModal(self.michaela)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="💭 Micro Journal", style=discord.ButtonStyle.secondary)
    async def micro_journal(self, interaction: discord.Interaction, button: Button):
        """Show feeling picker"""
        feeling_view = FeelingPickerView(self.michaela)
        await interaction.response.edit_message(
            content="How are you feeling? (Pick all that apply)",
            view=feeling_view
        )
    
    @discord.ui.button(label="❌ Not Right Now", style=discord.ButtonStyle.danger)
    async def skip(self, interaction: discord.Interaction, button: Button):
        """Skip journaling"""
        await interaction.response.edit_message(
            content="No problem! I'm here whenever you need to talk.",
            view=None
        )


# =========================================================
# FULL JOURNAL MODAL (Text entry)
# =========================================================

class FullJournalModal(Modal, title="Journal Entry"):
    """
    Modal for full journal entry (up to 2000 characters)
    """
    
    journal_text = TextInput(
        label="How are you feeling? What happened today?",
        style=discord.TextStyle.paragraph,
        placeholder="Write as much or as little as you want...",
        required=True,
        max_length=2000
    )
    
    def __init__(self, michaela_cog: 'Michaela'):
        super().__init__()
        self.michaela = michaela_cog
    
    async def on_submit(self, interaction: discord.Interaction):
        """Save journal entry and respond"""
        
        # Get entry text
        entry_text = self.journal_text.value
        
        # Save to journal system
        self.michaela.journal.add_entry(entry_text)
        
        # Confirm to user
        await interaction.response.send_message(
            "✅ Journal entry saved",
            ephemeral=True
        )
        
        # Michaela responds with empathy
        response = await self.michaela.generate_journal_response(entry_text)
        await interaction.channel.send(response)


# =========================================================
# FEELING PICKER VIEW (Multi-select)
# =========================================================

class FeelingPickerView(View):
    """
    Multi-select feeling picker for micro-journal
    
    User can toggle multiple feelings, then submit
    """
    
    def __init__(self, michaela_cog: 'Michaela'):
        super().__init__(timeout=1800)
        self.michaela = michaela_cog
        self.selected_feelings = []
    
    # Row 1: Negative feelings
    @discord.ui.button(emoji="😰", label="Anxious", style=discord.ButtonStyle.secondary, row=0)
    async def feeling_anxious(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "anxious")
    
    @discord.ui.button(emoji="😔", label="Sad", style=discord.ButtonStyle.secondary, row=0)
    async def feeling_sad(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "sad")
    
    @discord.ui.button(emoji="😤", label="Frustrated", style=discord.ButtonStyle.secondary, row=0)
    async def feeling_frustrated(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "frustrated")
    
    @discord.ui.button(emoji="😴", label="Tired", style=discord.ButtonStyle.secondary, row=0)
    async def feeling_tired(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "tired")
    
    # Row 2: More feelings
    @discord.ui.button(emoji="😞", label="Lonely", style=discord.ButtonStyle.secondary, row=1)
    async def feeling_lonely(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "lonely")
    
    @discord.ui.button(emoji="😣", label="Stressed", style=discord.ButtonStyle.secondary, row=1)
    async def feeling_stressed(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "stressed")
    
    @discord.ui.button(emoji="🤔", label="Confused", style=discord.ButtonStyle.secondary, row=1)
    async def feeling_confused(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "confused")
    
    @discord.ui.button(emoji="😑", label="Numb", style=discord.ButtonStyle.secondary, row=1)
    async def feeling_numb(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "numb")
    
    # Row 3: Positive feelings
    @discord.ui.button(emoji="😌", label="Peaceful", style=discord.ButtonStyle.secondary, row=2)
    async def feeling_peaceful(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "peaceful")
    
    @discord.ui.button(emoji="😊", label="Happy", style=discord.ButtonStyle.secondary, row=2)
    async def feeling_happy(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "happy")
    
    @discord.ui.button(emoji="💪", label="Motivated", style=discord.ButtonStyle.secondary, row=2)
    async def feeling_motivated(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "motivated")
    
    @discord.ui.button(emoji="🤗", label="Loved", style=discord.ButtonStyle.secondary, row=2)
    async def feeling_loved(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feeling(interaction, button, "loved")
    
    # Row 4: Submit button
    @discord.ui.button(label="✅ Submit Feelings", style=discord.ButtonStyle.success, row=3)
    async def submit_feelings(self, interaction: discord.Interaction, button: Button):
        """Submit selected feelings"""
        
        if not self.selected_feelings:
            await interaction.response.send_message(
                "Please select at least one feeling!",
                ephemeral=True
            )
            return
        
        # Log feelings to journal
        self.michaela.journal.log_micro_entry(self.selected_feelings)
        
        # Update message
        feelings_text = ", ".join(self.selected_feelings)
        await interaction.response.edit_message(
            content=f"✅ Logged feelings: {feelings_text}",
            view=None
        )
        
        # Michaela responds with empathy
        response = await self.michaela.generate_feeling_response(self.selected_feelings)
        await interaction.channel.send(response)
    
    async def _toggle_feeling(self, interaction: discord.Interaction, button: Button, feeling: str):
        """
        Toggle feeling selection
        
        Selected feelings turn primary color
        Unselected stay secondary
        """
        
        if feeling in self.selected_feelings:
            # Deselect
            self.selected_feelings.remove(feeling)
            button.style = discord.ButtonStyle.secondary
        else:
            # Select
            self.selected_feelings.append(feeling)
            button.style = discord.ButtonStyle.primary
        
        # Update view to show selection
        await interaction.response.edit_message(view=self)


# =========================================================
# HELPER: Generate Responses
# =========================================================

# These will be added to michaela.py as methods:

"""
async def generate_sleep_response(self, rating: int, quality: str) -> str:
    '''Generate empathetic response to sleep rating'''
    
    if rating <= 2:
        # Poor/fair sleep
        prompt = f"Dave slept poorly last night ({quality}). Respond with empathy and support."
    elif rating <= 3:
        # Good sleep
        prompt = f"Dave slept okay last night ({quality}). Respond positively but casually."
    else:
        # Great/excellent sleep
        prompt = f"Dave slept really well last night ({quality}). Respond happily."
    
    response = await self.ollama_generate(
        prompt,
        context_type="checkin",
        include_backstory=False
    )
    
    return response


async def generate_mood_response(self, rating: int, label: str) -> str:
    '''Generate empathetic response to mood rating'''
    
    if rating <= 2:
        # Struggling/low
        prompt = f"Dave is feeling {label} today. Offer support and empathy."
    elif rating == 3:
        # Okay
        prompt = f"Dave is feeling {label} today. Check in casually."
    else:
        # Good/great
        prompt = f"Dave is feeling {label} today! Respond positively."
    
    response = await self.ollama_generate(
        prompt,
        context_type="checkin",
        include_backstory=False
    )
    
    return response


async def generate_journal_response(self, entry_text: str) -> str:
    '''Generate empathetic response to journal entry'''
    
    prompt = f"Dave just shared a journal entry with you. Respond with empathy and support. Entry: {entry_text[:500]}"
    
    response = await self.ollama_generate(
        prompt,
        context_type="journal",
        include_backstory=False
    )
    
    return response


async def generate_feeling_response(self, feelings: list) -> str:
    '''Generate empathetic response to selected feelings'''
    
    feelings_text = ", ".join(feelings)
    prompt = f"Dave is feeling: {feelings_text}. Respond with empathy and validation."
    
    response = await self.ollama_generate(
        prompt,
        context_type="journal",
        include_backstory=False
    )
    
    return response
"""
