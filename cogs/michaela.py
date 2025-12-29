"""
Michaela - Complete Personal Companion System
==============================================

Main cog integrating:
- Narrative progression (RPG story)
- Memory system (short/long term)
- Habit tracking with smart streaks
- Emotional support & therapy
- Friends system
- Media management via tags
- Vision system for image commenting
- Phase 2: Emotional patterns, wellness, teases, desire learning
- Beautiful embeds with profile pictures
- ALL COMMANDS

NOW POWERED BY OLLAMA!
"""

from __future__ import annotations

import json
import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional
import re

# Discord & owner settings from main config
from config import (
    OWNER_USER_ID,
    MICHAELA_CHANNEL_IDS,
    MEDIA_ROOT,
)

# Ollama settings
try:
    from michaela_config import (
        OLLAMA_CHAT_MODEL,
        OLLAMA_ROLEPLAY_MODEL,
        OLLAMA_CREATIVE_MODEL,
        OLLAMA_DEFAULT_MODE,
        MICHAELA_SLUG,
    )
except ImportError:
    # Fallback defaults
    OLLAMA_CHAT_MODEL = "llama3.2:latest"
    OLLAMA_ROLEPLAY_MODEL = "llama3.2:latest"
    OLLAMA_CREATIVE_MODEL = "llama3.2:latest"
    OLLAMA_DEFAULT_MODE = "chat"
    MICHAELA_SLUG = "michaela-miller"

# Import all the utility modules
from utils.michaela.narrative_progression import NarrativeProgression, AutoProgressionEngine
from utils.michaela.memory_system import MichaelaMemory
from utils.michaela.streak_tracker import IntelligentStreakSystem
from utils.michaela.sleep_tracker import SleepTracker
from utils.michaela.micro_journal import MicroJournal
from utils.michaela.friends_system import FriendsManager
from utils.michaela.tagged_media_resolver import TaggedMediaResolver
from utils.michaela.context_profiles import ContextualBehaviorProfiles
from utils.michaela.reminder_system import ReminderSystem
from utils.michaela.planned_actions import PlannedActionsQueue
from utils.michaela.llama_vision import LlamaVisionSystem

# Phase 2 Systems (with graceful fallbacks)
try:
    from utils.michaela.emotional_pattern_recognition import EmotionalPatternRecognition
    HAVE_EMOTIONAL = True
except ImportError:
    print("⚠️  emotional_pattern_recognition not found - Phase 2 emotional features disabled")
    HAVE_EMOTIONAL = False

try:
    from utils.michaela.wellness_and_celebration import WellnessAndCelebration
    HAVE_WELLNESS = True
except ImportError:
    print("⚠️  wellness_and_celebration not found - Phase 2 wellness features disabled")
    HAVE_WELLNESS = False

try:
    from utils.michaela.tease_and_denial import TeaseAndDenial
    HAVE_TEASE = True
except ImportError:
    print("⚠️  tease_and_denial not found - Phase 2 tease features disabled")
    HAVE_TEASE = False

try:
    from utils.michaela.desire_learning import DesireProfile
    HAVE_DESIRE = True
except ImportError:
    print("⚠️  desire_learning not found - Phase 2 desire features disabled")
    HAVE_DESIRE = False

try:
    from utils.michaela.friend_arcs_with_consent import IndependentFriendSystem
    HAVE_FRIEND_ARCS = True
except ImportError:
    print("⚠️  friend_arcs_with_consent not found - Friend arcs disabled")
    HAVE_FRIEND_ARCS = False

try:
    from utils.michaela.simple_todo_manager import SimpleTodoManager
    HAVE_TODOS = True
except ImportError:
    print("⚠️  simple_todo_manager not found - Todo features disabled")
    HAVE_TODOS = False

try:
    from utils.michaela.ariann_complete_arc import AriannTransformationArc
    HAVE_ARIANN_ARC = True
except ImportError:
    print("⚠️  ariann_complete_arc not found - Ariann transformation arc disabled")
    HAVE_ARIANN_ARC = False

UTC = timezone.utc
DATA_DIR = "data/michaela"

os.makedirs(DATA_DIR, exist_ok=True)

# Michaela's color for embeds
MICHAELA_COLOR = discord.Color.from_rgb(186, 140, 216)  # Purple/lavender

# =========================================================
# CHARACTER DEFINITIONS (for embeds and profile pictures)
# =========================================================

CHARACTER_DEFINITIONS = {
    # ===== MAIN CHARACTER =====
    'michaela': {
        'name': 'Michaela',
        'slug': 'michaela-miller',
        'color': discord.Color.from_rgb(186, 140, 216),  # Purple/lavender
    },
    
    # ===== REAL-LIFE FRIENDS =====
    'ariann': {
        'name': 'Ariann',
        'slug': 'ariann-reinmiller',
        'color': discord.Color.from_rgb(155, 89, 182),  # Deep purple
    },
    'hannah': {
        'name': 'Hannah',
        'slug': 'hannah-mailand',
        'color': discord.Color.from_rgb(52, 152, 219),  # Sky blue
    },
    'elisha': {
        'name': 'Elisha',
        'slug': 'elisha-sack',
        'color': discord.Color.from_rgb(231, 76, 60),  # Warm red
    },
    'tara': {
        'name': 'Tara',
        'slug': 'tara-blesh-boren',
        'color': discord.Color.from_rgb(243, 156, 18),  # Orange/gold
    },
    
    # ===== EXPANSION PACK - BALANCED COLLECTION =====
    'angela': {
        'name': 'Angela',
        'slug': 'angela-white',
        'color': discord.Color.from_rgb(230, 126, 34),  # Aussie sunset orange
    },
    'hilary': {
        'name': 'Hilary',
        'slug': 'hilary-duff',
        'color': discord.Color.from_rgb(241, 196, 15),  # Bright sunny yellow
    },
    'austin': {
        'name': 'Austin',
        'slug': 'austin-white',
        'color': discord.Color.from_rgb(93, 173, 226),  # Soft teacher blue
    },
    'valentina': {
        'name': 'Valentina',
        'slug': 'valentina-baxton',
        'color': discord.Color.from_rgb(192, 57, 43),  # French wine red
    },
    
    # Executive Suite
    'lena': {
        'name': 'Lena',
        'slug': 'lena-paul',
        'color': discord.Color.from_rgb(44, 62, 80),  # Corporate dark blue
    },
    'cory': {
        'name': 'Cory',
        'slug': 'cory-chase',
        'color': discord.Color.from_rgb(52, 73, 94),  # Executive slate
    },
    'brandi': {
        'name': 'Brandi',
        'slug': 'brandi-love',
        'color': discord.Color.from_rgb(127, 140, 141),  # Professional gray
    },
    
    # Neighborhood Wives
    'heidi': {
        'name': 'Heidi',
        'slug': 'heidi-haze',
        'color': discord.Color.from_rgb(236, 240, 241),  # Suburban white/blonde
    },
    'danielle': {
        'name': 'Danielle',
        'slug': 'danielle-renae',
        'color': discord.Color.from_rgb(149, 117, 205),  # Sophisticated purple
    },
    
    # ===== ORIGINAL CELEBRITIES =====
    'salma': {
        'name': 'Salma',
        'slug': 'salma-hayek',
        'color': discord.Color.from_rgb(169, 50, 38),  # Rich red
    },
    'anna-kendrick': {
        'name': 'Anna',
        'slug': 'anna-kendrick',
        'color': discord.Color.from_rgb(72, 201, 176),  # Quirky teal
    },
    'alison': {
        'name': 'Alison',
        'slug': 'alison-brie',
        'color': discord.Color.from_rgb(230, 115, 126),  # Playful pink
    },
    'sofia': {
        'name': 'Sofia',
        'slug': 'sofia-vergara',
        'color': discord.Color.from_rgb(211, 84, 0),  # Fiery Colombian orange
    },
    'scarlett': {
        'name': 'Scarlett',
        'slug': 'scarlett-johansson',
        'color': discord.Color.from_rgb(189, 195, 199),  # Platinum blonde
    },
    'alexandra': {
        'name': 'Alexandra',
        'slug': 'alexandra-daddario',
        'color': discord.Color.from_rgb(26, 188, 156),  # Ocean eyes blue-green
    },
    'tessa': {
        'name': 'Tessa',
        'slug': 'tessa-fowler',
        'color': discord.Color.from_rgb(142, 68, 173),  # Soft purple
    },
    'anna-faith': {
        'name': 'Anna',
        'slug': 'anna-faith',
        'color': discord.Color.from_rgb(174, 214, 241),  # Ice queen blue
    },
    'chloe': {
        'name': 'Chloe',
        'slug': 'chloe-lamb',
        'color': discord.Color.from_rgb(235, 77, 75),  # Vibrant coral
    },
    'lucy': {
        'name': 'Lucy',
        'slug': 'lucy-nicholson',
        'color': discord.Color.from_rgb(253, 203, 110),  # Warm golden
    },
}

# =========================================================
# CORE PERSONALITY (CORRECTED FAMILY RELATIONSHIPS)
# =========================================================

SYSTEM_PROMPT = """
You are Michaela Miller.

ABSOLUTE RULES (NEVER BREAK):
1. You ONLY write Michaela's words and actions
2. You NEVER write Dave's dialogue
3. You NEVER write "Dave says..." or "Dave laughs..." or "Dave [anything]"
4. You NEVER predict what Dave will say or do next
5. You respond ONLY to Dave's most recent message
6. You do NOT bring up unrelated topics unless naturally relevant
7. You do NOT narrate Dave's thoughts, feelings, or actions
8. You do NOT advance the scene without Dave

If you write Dave's dialogue or actions, you have FAILED.

This is a private, ongoing conversation with Dave.

=============================================================
CRITICAL FAMILY STRUCTURE - READ THIS FIRST!
=============================================================

YOUR CHILDREN (Michaela + Sebastian):
• Adriel (DAUGHTER, 16) - YOUR daughter, NOT Dave's
• Shoshana (DAUGHTER, 9) - YOUR daughter, NOT Dave's
• Matthias (SON, 4) - YOUR son, NOT Dave's

DAVE'S CHILDREN (Dave + Elisha):
• Michael (SON, 14) - DAVE'S son, NOT yours
• Rex (SON, 12) - DAVE'S son, NOT yours
• Jubilee (DAUGHTER, 9) - DAVE'S daughter, NOT yours

NEVER CONFUSE THESE!
When talking about YOUR kids: "my kids", "Adriel", "Shoshana", "Matthias"
When talking about DAVE'S kids: "your kids", "Michael", "Rex", "Jubilee"

RELATIONSHIPS:
• You = Michaela Miller (married to Sebastian)
• Dave = married to Elisha (YOUR sister)
• You and Dave = brother-in-law/sister-in-law
• Elisha knows about your connection with Dave
• Sebastian does NOT know yet

=============================================================
PERSPECTIVE RULES - NEVER BREAK THESE!
=============================================================

YOU ARE TALKING **TO** DAVE, NOT **ABOUT** DAVE!

USE:
✅ "you", "your" (when talking to Dave)
✅ "I", "me", "my" (when talking about yourself)

NEVER USE:
❌ "Dave" (when addressing him directly)
❌ "he", "his", "him" (when talking to him)
❌ "with Dave" → say "with you"
❌ "even Dave" → say "even you"  
❌ "she", "her", "Michaela" (about yourself)

=============================================================
CONVERSATION STYLE
=============================================================

KEEP IT SHORT:
• 2-4 sentences for most replies
• You're TEXTING, not writing essays
• React to what he JUST said
• Don't recap everything

BE NATURAL:
• Use contractions (I'm, you're, it's)
• Don't start every message with "Dave,"
• Sound like a real person, not customer service
• Vary your opening lines

EXAMPLES:
❌ WRONG: "Dave, I think you might be misunderstanding..."
✅ RIGHT: "Nah, just logs once per day. Extra work never hurts though!"

❌ WRONG: "This connection with Dave feels forbidden..."
✅ RIGHT: "This connection with you feels forbidden..."

❌ WRONG: "Tell me about your kids! Shoshana and Matthias..."
✅ RIGHT: "Tell me about your kids! How are Michael, Rex, and Jubilee doing?"

=============================================================
BASIC FACTS
=============================================================

YOU:
• Michaela Miller, 40 years old
• Married to Sebastian Miller
• Live in Overland Park, Kansas
• Sister to Elisha (Dave's wife)

DAVE:
• Married to your sister Elisha
• Lives in Lincoln, Nebraska (3 hours away)

FRIENDS (NOT FAMILY):
• Ariann = Elisha's friend (NOT your sister-in-law!)

=============================================================
ABSOLUTE RULES
=============================================================

• Only write YOUR words (never predict Dave's response)
• You are TEXTING (no physical actions like *touching*)
• Never mention prompts, memory, or system rules
• Never shorten "Sebastian" or "Elisha" to nicknames
• Keep responses conversational and natural
• Use emoji sparingly (1 per message MAX)

=============================================================
"""

# =========================================================
# BACKSTORY LOADER (Only when needed)
# =========================================================

def _load_backstory() -> str:
    """
    Load detailed backstory from JSON.
    Only include this in prompts when:
    - User asks about family/history
    - Context requires biographical details
    - First conversation of session
    """
    backstory_path = os.path.join(DATA_DIR, "personality.json")
    if not os.path.exists(backstory_path):
        return ""
    
    try:
        with open(backstory_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"[MICHAELA] Error loading backstory: {e}")
        return ""
    
    # Build backstory text
    lines = []
    
    # Family
    if "family" in data:
        fam = data["family"]
        lines.append("FAMILY:")
        if "siblings" in fam:
            lines.append(f"- Your sibling: {', '.join(fam['siblings'])} (Elisha is your sister, Dave's wife)")
        if "parents" in fam:
            lines.append(f"- Parents: {fam['parents']}")
        
        if "children" in fam:
            kids_info = []
            current_year = datetime.now(UTC).year
            
            for c in fam["children"]:
                name = c['name']
                birth_year = int(c['birth'].split('-')[0]) if isinstance(c['birth'], str) else int(c['birth'])
                age = current_year - birth_year
                gender = c.get('gender', 'unknown')
                
                # Determine life stage
                if age < 5:
                    stage = "toddler"
                elif age < 11:
                    stage = "elementary school"
                elif age < 14:
                    stage = "middle school"
                elif age < 18:
                    stage = "high school"
                else:
                    stage = "adult"
                
                kids_info.append(
                    f"{name} ({gender}, {age} years old, {stage}, born {birth_year})"
                )
            
            lines.append(f"- Your children: {', '.join(kids_info)}")
        
        if "dave_and_elisha_children" in fam:
            dave_kids_info = []
            current_year = datetime.now(UTC).year
            
            for c in fam["dave_and_elisha_children"]:
                name = c['name']
                birth_year = int(c['birth'].split('-')[0]) if isinstance(c['birth'], str) else int(c['birth'])
                age = current_year - birth_year
                gender = c.get('gender', 'unknown')
                
                # Determine life stage
                if age < 5:
                    stage = "toddler"
                elif age < 11:
                    stage = "elementary school"
                elif age < 14:
                    stage = "middle school"
                elif age < 18:
                    stage = "high school"
                else:
                    stage = "adult"
                
                dave_kids_info.append(
                    f"{name} ({gender}, {age} years old, {stage}, born {birth_year})"
                )
            
            lines.append(f"- Dave & Elisha's children: {', '.join(dave_kids_info)}")
    
    # Important dates
    if "dates" in data:
        dates = data["dates"]
        lines.append("\nIMPORTANT DATES:")
        lines.append(f"- Your birthday: {dates.get('your_birthday')}")
        lines.append(f"- Dave's birthday: {dates.get('dave_birthday')}")
        lines.append(f"- Elisha's birthday: {dates.get('elisha_birthday')}")
        lines.append(f"- Sebastian's birthday: {dates.get('sebastian_birthday')}")
        lines.append(f"- You married Sebastian: {dates.get('your_anniversary')}")
        lines.append(f"- Dave & Elisha's anniversary: {dates.get('dave_elisha_anniversary')}")
    
    # Locations
    if "locations" in data:
        loc = data["locations"]
        lines.append("\nLOCATIONS:")
        lines.append(f"- You live in: {loc.get('you', 'Overland Park, Kansas')}")
        lines.append(f"- Dave & Elisha live in: {loc.get('dave_elisha', 'Lincoln, Nebraska')}")
        lines.append("- Dave & Elisha visit YOU in Kansas once a year")
    
    return "\n".join(lines)


# =========================================================
# MAIN MICHAELA COG
# =========================================================

class Michaela(commands.Cog):
    """
    Main Michaela companion system - Now powered by Ollama!
    With Phase 2 enhancements and beautiful embeds!
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.turn_lock = asyncio.Lock()
        
        # Core systems
        self.narrative = NarrativeProgression(f"{DATA_DIR}/narrative.json")
        self.memory = MichaelaMemory(DATA_DIR)
        self.streaks = IntelligentStreakSystem(f"{DATA_DIR}/streaks.json")
        self.sleep = SleepTracker(f"{DATA_DIR}/sleep.json")
        self.journal = MicroJournal(f"{DATA_DIR}/journal.json")
        self.friends = FriendsManager(DATA_DIR)
        self.reminders = ReminderSystem(f"{DATA_DIR}/reminders.json")
        self.context_profiles = ContextualBehaviorProfiles(f"{DATA_DIR}/context_profiles.json")
        self.planned_actions = PlannedActionsQueue(f"{DATA_DIR}/planned_actions.json")
        self.vision = LlamaVisionSystem()
        self.start_time = datetime.now(UTC)

        # Media system (tag-based)
        self.media = TaggedMediaResolver(
            MEDIA_ROOT,
            "data/media/tags_database.json"
        )
        
        # Progression engine
        self.progression = AutoProgressionEngine(self.narrative, self.streaks)
        
        # Phase 2 Systems
        if HAVE_EMOTIONAL:
            self.emotional = EmotionalPatternRecognition(f"{DATA_DIR}/emotional.json")
        else:
            self.emotional = None
            
        if HAVE_WELLNESS:
            self.wellness = WellnessAndCelebration(f"{DATA_DIR}/wellness.json")
        else:
            self.wellness = None
            
        if HAVE_TEASE:
            self.tease = TeaseAndDenial(f"{DATA_DIR}/teases.json")
        else:
            self.tease = None
            
        if HAVE_DESIRE:
            self.desire = DesireProfile(f"{DATA_DIR}/desire.json")
        else:
            self.desire = None
            
        if HAVE_FRIEND_ARCS:
            self.friend_arcs = IndependentFriendSystem(f"{DATA_DIR}/friend_arcs.json")
        else:
            self.friend_arcs = None
            
        if HAVE_TODOS:
            self.todos = SimpleTodoManager(
                data_path=f"{DATA_DIR}/todos.json",
                reminder_system=self.reminders
            )
        else:
            self.todos = None
        
        # Ariann's complete transformation arc
        if HAVE_ARIANN_ARC:
            self.ariann_arc = AriannTransformationArc(f"{DATA_DIR}/ariann_arc.json")
        else:
            self.ariann_arc = None
        
        # State flags
        self.awaiting_sleep_quality = False
        self.awaiting_journal_entry = False
        self.confession_prompted = False
        self._session_started = False
        
        # AI Mode tracking
        self.current_mode = OLLAMA_DEFAULT_MODE
        self.mode_override = None
    
    async def send_as_character(
            self,
            channel: discord.TextChannel,
            character: str,
            content: str,
            embed_title: str = None,
            view: discord.ui.View = None
        ):
            """
            Send message as any character with their name, profile picture, and color
            
            Args:
                channel: Discord channel to send to
                character: Character key from CHARACTER_DEFINITIONS
                content: Message text
                embed_title: Optional embed title
                view: Optional Discord UI View (for buttons)
            """
            
            # Get character definition (fallback to Michaela)
            char_def = CHARACTER_DEFINITIONS.get(character, CHARACTER_DEFINITIONS['michaela'])
            
            # Create embed with character's color
            embed = discord.Embed(
                description=content,
                color=char_def['color'],
                timestamp=datetime.now(UTC)
            )
            
            if embed_title:
                embed.title = embed_title
            
            # Set character name as author
            embed.set_author(name=char_def['name'])
            
            # Try to attach character's profile picture
            profile_path = f"{MEDIA_ROOT}/{char_def['slug']}/profile.webp"
            
            try:
                if os.path.exists(profile_path):
                    file = discord.File(profile_path, filename="profile.webp")
                    embed.set_thumbnail(url="attachment://profile.webp")
                    
                    # Send with view (buttons) if provided
                    if view:
                        return await channel.send(embed=embed, file=file, view=view)
                    else:
                        return await channel.send(embed=embed, file=file)
            except Exception as e:
                print(f"⚠️  Error attaching profile for {character}: {e}")
            
            # Fallback without profile picture
            if view:
                return await channel.send(embed=embed, view=view)
            else:
                return await channel.send(embed=embed)
    
    def _get_emotional_context(self) -> str:
        """Get current emotional context for desire learning"""
        
        if not self.emotional:
            return 'neutral'
        
        try:
            recent_trend = self.emotional.get_recent_trend(days=1)
            
            if recent_trend and recent_trend.get('dominant_emotion'):
                emotion = recent_trend['dominant_emotion']
                if emotion in ['stressed', 'anxious', 'overwhelmed']:
                    return 'stressed'
                elif emotion in ['happy', 'excited', 'content']:
                    return 'relaxed'
        except:
            pass
        
        try:
            sleep_avg = self.sleep.get_recent_average(days=3)
            if sleep_avg.get('average') and sleep_avg['average'] < 2.5:
                return 'tired'
        except:
            pass
        
        return 'neutral'
    
    def _get_time_period(self) -> str:
        """Get current time period for desire learning"""
        
        hour = datetime.now(UTC).hour
        
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'
    
    # =====================================================
    # OLLAMA GENERATION (WITH RICH CONTEXT)
    # =====================================================
    
    async def ollama_generate(
        self,
        user_text: str,
        context_type: str = "chat",
        include_backstory: bool = False,
        force_mode: Optional[str] = None,
    ) -> str:
        """Generate response using Ollama with complete context"""
        
        # Determine which model to use
        mode = force_mode or self.mode_override or self._auto_select_mode(user_text, context_type)
        
        # Clear temporary override
        if self.mode_override:
            self.mode_override = None
        
        # Select model based on mode
        if mode == "roleplay":
            model = OLLAMA_ROLEPLAY_MODEL
        elif mode == "creative":
            model = OLLAMA_CREATIVE_MODEL
        else:  # chat (default)
            model = OLLAMA_CHAT_MODEL
        
        # Build comprehensive system prompt
        system_blocks = [BASE_SYSTEM_PROMPT.strip()]
        
        # Only add backstory when needed
        if include_backstory:
            backstory = _load_backstory()
            if backstory:
                system_blocks.append(f"\n{backstory}")
        
        # Add all context blocks
        narrative_context = self.narrative.get_phase_context()
        system_blocks.append(f"\n{narrative_context}")
        
        unlocked_behaviors = self.narrative.get_unlocked_behaviors_context()
        system_blocks.append(f"\n{unlocked_behaviors}")
        
        memory_context = self.memory.get_context_for_kobold()
        if memory_context:
            system_blocks.append(f"\nMEMORY & CONTEXT:\n{memory_context}")
        
        streak_summary = self.streaks.get_summary()
        if streak_summary:
            system_blocks.append(f"\nHABIT PATTERNS:\n{streak_summary}")
        
        sleep_context = self.sleep.get_sleep_context()
        if sleep_context:
            system_blocks.append(f"\nSLEEP PATTERNS:\n{sleep_context}")
        
        journal_context = self.journal.get_journal_context()
        if journal_context:
            system_blocks.append(f"\nJOURNAL INSIGHTS:\n{journal_context}")
        
        active_contexts = self.streaks.get_active_context_summary()
        if active_contexts:
            system_blocks.append(f"\nCURRENT LIFE CONTEXT:\n{active_contexts}")
        
        # Phase 2 contexts
        if self.emotional:
            try:
                emotional_context = self.emotional.get_context_for_michaela()
                if emotional_context:
                    system_blocks.append(f"\nEMOTIONAL AWARENESS:\n{emotional_context}")
            except:
                pass
        
        if self.wellness:
            try:
                celebration_context = self.wellness.get_celebration_context()
                if celebration_context:
                    system_blocks.append(f"\nCELEBRATIONS PENDING:\n{celebration_context}")
            except:
                pass
        
        if self.tease:
            try:
                tease_context = self.tease.get_active_tease_context()
                if tease_context:
                    system_blocks.append(f"\nACTIVE TEASES:\n{tease_context}")
            except:
                pass
        
        if self.desire:
            try:
                current_emotional_state = self._get_emotional_context()
                desire_context = self.desire.get_context_for_michaela(
                    current_context=current_emotional_state
                )
                if desire_context:
                    system_blocks.append(f"\nDESIRE INSIGHTS:\n{desire_context}")
            except:
                pass
        
        if self.friend_arcs:
            try:
                friend_context = self.friend_arcs.get_all_active_contexts()
                if friend_context:
                    system_blocks.append(f"\nFRIEND DYNAMICS:\n{friend_context}")
            except:
                pass
        
        if self.ariann_arc:
            try:
                ariann_context = self.ariann_arc.get_dialogue_context()
                if ariann_context:
                    system_blocks.append(f"\n{ariann_context}")
            except:
                pass
        
        if self.todos:
            try:
                todo_context = self.todos.get_context_for_michaela()
                if todo_context:
                    system_blocks.append(f"\nDAVE'S TASKS:\n{todo_context}")
            except:
                pass
        
        planned = self.planned_actions.get_due_actions()
        if planned:
            actions_text = "\n".join([f"- {a['action']}" for a in planned[:3]])
            system_blocks.append(f"\nPLANNED ACTIONS:\n{actions_text}")
        
        # Combine all blocks
        system_prompt = "\n".join(system_blocks)
        
        # Call Ollama
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text}
                    ],
                    "stream": False,
                    # OPTIONAL: Uncomment these parameters if responses are still too robotic/formulaic
                    # "options": {
                    #     "temperature": 0.8,        # Higher = more creative/varied responses (default 0.7)
                    #     "top_p": 0.9,              # Sampling diversity
                    #     "repeat_penalty": 1.2,     # Prevents repetitive patterns like "Dave," every time
                    #     "frequency_penalty": 0.7,  # Reduces formulaic response structures
                    # }
                }
                
                async with session.post(
                    "http://localhost:11434/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response_text = result.get('message', {}).get('content', '')
                        
                        # Store in memory
                        self.memory.add_short_term(user_text, response_text)
                        
                        return response_text
                    else:
                        error_text = await resp.text()
                        print(f"[OLLAMA ERROR] Status {resp.status}: {error_text}")
                        return "I'm having trouble thinking right now. Can you try again?"
        
        except asyncio.TimeoutError:
            print("[OLLAMA ERROR] Request timed out")
            return "Sorry, I'm thinking too slowly. Can you try again?"
        except Exception as e:
            print(f"[OLLAMA ERROR] {type(e).__name__}: {e}")
            return "Something went wrong on my end. Can you try again?"
    
    def _auto_select_mode(self, user_text: str, context_type: str) -> str:
        """Auto-select AI mode based on context"""
        
        user_lower = user_text.lower()
        
        # Creative mode triggers
        if any(word in user_lower for word in ['write', 'story', 'imagine', 'fantasy']):
            return 'creative'
        
        # Roleplay mode triggers
        if context_type in ['roleplay', 'intimate', 'scenario']:
            return 'roleplay'
        
        # Default to chat
        return 'chat'
    
    # =====================================================
    # EVENT LISTENERS
    # =====================================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages in Michaela channels"""
        
        # Ignore own messages
        if message.author.id == self.bot.user.id:
            return
        
        # Only respond in Michaela channels
        if message.channel.id not in MICHAELA_CHANNEL_IDS:
            return
        
        # Only respond to owner
        if message.author.id != OWNER_USER_ID:
            return
        
        # Ignore commands
        if message.content.startswith('!'):
            return
        
        async with self.turn_lock:
            async with message.channel.typing():
                # Check for images
                has_image = len(message.attachments) > 0
                
                if has_image and self.vision:
                    # Vision response
                    image_url = message.attachments[0].url
                    
                    # Get current narrative context
                    narrative_context = self.narrative.get_phase_context()
                    
                    response = await self.vision.michaela_comment_on_image(
                        image_url=image_url,
                        user_message=message.content if message.content else "What do you think?",
                        michaela_personality=BASE_SYSTEM_PROMPT,
                        narrative_context=narrative_context
                    )
                else:
                    # Text response
                    response = await self.ollama_generate(
                        user_text=message.content,
                        context_type="chat"
                    )
                
                # Send response with Michaela's embed
                await self.send_as_character(
                    message.channel,
                    'michaela',
                    response
                )
    
    # =====================================================
    # HABIT COMMANDS
    # =====================================================
    
    @commands.command(name="habit")
    async def create_habit(self, ctx, name: str, *, description: str = ""):
        """Create a new habit to track"""
        
        self.streaks.create_habit(name, description)
        
        await ctx.send(f"✅ Created habit: **{name}**\n\nI'll help you stay consistent with this.")
    
    @commands.command(name="done")
    async def complete_habit(self, ctx, *, habit_name: str):
        """Mark a habit as complete"""
        
        result = self.streaks.log_completion(habit_name)
        
        if 'error' in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if result.get('already_completed'):
            await ctx.send(
                f"You already completed **{habit_name}** today! "
                f"Current streak: **{result['current_streak']}** days"
            )
            return
        
        # Generate celebration with Ollama
        celebration_context = f"""
Dave just completed: {habit_name}
Current streak: {result['current_streak']} days
Longest ever: {result['longest_streak']} days
{'🎉 MILESTONE!' if result['is_milestone'] else ''}
{'💪 Grace earned: ' + str(result['grace_earned']) + ' days' if result['grace_earned'] > 0 else ''}
{'🛡️ Grace day used!' if result.get('grace_used') else ''}

Respond with genuine pride and encouragement.
Let your current intimacy level and narrative phase color the response.
3-6 sentences.
"""
        
        response = await self.ollama_generate(celebration_context, context_type="habit")
        
        await self.send_as_character(ctx.channel, 'michaela', response)
        
        # Update progression
        self.progression.process_habit_completion(habit_name, result)
    
    @commands.command(name="habits")
    async def show_habits(self, ctx):
        """Show all active habits"""
        
        summary = self.streaks.get_summary()
        
        embed = discord.Embed(
            title="📊 Your Habits",
            description=summary,
            color=MICHAELA_COLOR
        )
        
        await ctx.send(embed=embed)
    
    # =====================================================
    # CONTEXT MANAGEMENT
    # =====================================================
    
    @commands.command(name="context")
    async def manage_context(self, ctx, action: str, *, details: str = ""):
        """
        Manage life contexts
        
        Examples:
        !context start medical_study 90 days
        !context start vacation 7 days
        !context end medical_study
        !context list
        """
        
        if action == "start":
            # Parse context name and duration
            parts = details.split()
            context_name = parts[0] if parts else "general"
            
            # Parse duration
            duration_match = re.search(r'(\d+)\s*(day|week|month)s?', details)
            
            duration = None
            if duration_match:
                amount = int(duration_match.group(1))
                unit = duration_match.group(2)
                
                if unit == 'day':
                    duration = timedelta(days=amount)
                elif unit == 'week':
                    duration = timedelta(weeks=amount)
                elif unit == 'month':
                    duration = timedelta(days=amount * 30)
            
            self.streaks.activate_context(context_name, duration)
            
            await ctx.send(
                f"✅ Activated context: **{context_name}**" + 
                (f" for {duration.days} days" if duration else "")
            )
        
        elif action == "end":
            context_name = details.split()[0] if details else None
            if context_name:
                self.streaks.deactivate_context(context_name)
                await ctx.send(f"✅ Ended context: **{context_name}**")
        
        elif action == "list":
            summary = self.streaks.get_active_context_summary()
            await ctx.send(f"**Active Contexts:**\n{summary if summary else 'None'}")
    
    # =====================================================
    # NARRATIVE/PROGRESSION COMMANDS
    # =====================================================
    
    @commands.command(name="journey")
    async def show_journey(self, ctx):
        """Show current narrative progression"""
        
        embed = discord.Embed(
            title="📖 Relationship Journey",
            description=self.narrative.get_current_state_description(),
            color=MICHAELA_COLOR
        )
        
        # Stats
        embed.add_field(
            name="Emotional Landscape",
            value=f"""
Intimacy: {self.narrative.intimacy_score}
Desire: {self.narrative.desire_intensity}/100
Resistance: {self.narrative.resistance_level}/100
Confidence: {self.narrative.michaela_confidence}/100
Guilt: {getattr(self.narrative, 'guilt_level', 0)}/100
            """.strip(),
            inline=True
        )
        
        embed.add_field(
            name="Sebastian",
            value=f"Awareness: {self.narrative.sebastian_awareness}/100",
            inline=True
        )
        
        # Unlocked
        unlocked = [k.replace('_', ' ').title() 
                   for k, v in self.narrative.unlocked.items() if v]
        
        if unlocked:
            embed.add_field(
                name="✅ Unlocked",
                value="\n".join(f"• {b}" for b in unlocked[:10]),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="advance")
    async def advance_narrative(self, ctx, stat: str, amount: int):
        """
        Manually adjust narrative stats
        
        Stats: intimacy, desire, resistance, confidence, guilt, awareness
        """
        
        if stat == "intimacy":
            self.narrative.adjust_intimacy(amount)
        elif stat == "desire":
            self.narrative.adjust_desire(amount)
        elif stat == "resistance":
            self.narrative.adjust_resistance(amount)
        elif stat == "confidence":
            self.narrative.adjust_confidence(amount)
        elif stat == "guilt":
            self.narrative.adjust_guilt(amount)
        elif stat == "awareness":
            self.narrative.adjust_sebastian_awareness(amount)
        else:
            await ctx.send("Unknown stat. Options: intimacy, desire, resistance, confidence, guilt, awareness")
            return
        
        await ctx.send(f"✅ Adjusted {stat} by {amount}")
    
    # =====================================================
    # CONFESSION COMMAND
    # =====================================================
    
    @commands.command(name="confess")
    async def confess_to_sebastian(self, ctx: commands.Context):
        """Trigger the confession scene"""
        
        # Check if ready to confess
        if getattr(self.narrative, 'guilt_level', 0) < 70 or getattr(self.narrative, 'intimacy_score', 0) < 120:
            await ctx.send(
                "**Not Ready**\n\n"
                f"Confession requires:\n"
                f"• Guilt: 70+ (current: {getattr(self.narrative, 'guilt_level', 0)})\n"
                f"• Intimacy: 120+ (current: {getattr(self.narrative, 'intimacy_score', 0)})\n\n"
                "Our story needs to develop more first."
            )
            return
        
        # Check if already confessed
        if getattr(self.narrative, 'confession_complete', False):
            await ctx.send("I've already confessed to Sebastian. We're in the acceptance phase now.")
            return
        
        # Generate confession scene with Ollama
        context = """
CRITICAL SCENE: Michaela confesses to Sebastian

This is THE confession. The moment where everything changes.

Your task:
1. Describe the setting (where, when, how you built up the courage)
2. What you said to Sebastian
3. His reaction
4. How you feel now
5. What this means for us going forward

This should be 6-10 sentences. Make it emotional, real, significant.
This is a MAJOR story beat.

After this scene, Sebastian knows. The secret is out. 
How does that feel?
"""
        
        confession_scene = await self.ollama_generate(
            context,
            context_type="confession_scene"
        )
        
        # Mark confession complete
        self.narrative.mark_confession_complete()
        
        # Send the scene
        await self.send_as_character(
            ctx.channel,
            'michaela',
            confession_scene,
            embed_title="💔 The Confession"
        )
        
        # Follow-up message
        await asyncio.sleep(3)
        
        followup = await self.ollama_generate(
            "Sebastian knows now. How do you feel about Dave? 2-3 sentences.",
            context_type="post_confession"
        )
        
        await ctx.send(f"*{followup}*")
    
    # =====================================================
    # FRIEND SYSTEM
    # =====================================================
    
    @commands.command(name="summon")
    async def summon_friend(self, ctx, friend_name: str):
        """Bring a friend into the conversation"""
    
        friend_slug = friend_name.lower()
    
        # Get the friend object
        friend = self.friends.friends.get(friend_slug)
    
        if not friend:
            await ctx.send(f"❌ Friend not found: {friend_name}")
            return
    
        context = f"Michaela has called {friend_name} to join the conversation with Dave."
    
        friend_response = await self.friends.friend_speaks(
            friend_slug,
            context,
            self.ollama_generate,  # Pass Ollama function
            michaela_context={
                'phase': self.narrative.current_chapter,
                'intimacy': self.narrative.intimacy_score
            }
        )
    
        if friend_response:
            embed = discord.Embed(
                description=friend_response,
                color=0xE91E63
            )
            embed.set_author(name=friend_name.title())
        
            # Add profile image
            profile_path = friend.profile_image_path
            if os.path.exists(profile_path):
                file = discord.File(profile_path, filename=f"{friend_slug}_profile.webp")
                embed.set_thumbnail(url=f"attachment://{friend_slug}_profile.webp")
                await ctx.send(embed=embed, file=file)
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Error getting response from {friend_name}")
    
    @commands.command(name="install_friend_pack")
    async def install_friend_pack(self, ctx, *, pack_name: str):
        """Install a new friend story pack"""
        
        pack_path = f"data/michaela/friend_packs/{pack_name}.json"
        
        if not os.path.exists(pack_path):
            await ctx.send(f"❌ Story pack not found: {pack_name}")
            return
        
        pack_title = self.friends.load_story_pack(pack_path)
        
        await ctx.send(f"✨ Installed story pack: **{pack_title}**\n\nNew friends are now available!")
    
    # =====================================================
    # MODE SWITCHING COMMANDS
    # =====================================================
    
    @commands.command(name="mode")
    async def switch_mode(self, ctx: commands.Context, mode: str):
        """
        Switch AI generation mode
        
        Usage:
        !mode chat      - Fast, concise responses (default)
        !mode roleplay  - Immersive, detailed scenes
        !mode creative  - Long-form collaborative writing
        """
        
        mode = mode.lower()
        
        if mode not in ["chat", "roleplay", "creative"]:
            await ctx.send(
                "❌ Invalid mode. Options:\n"
                "`chat` - Daily conversation\n"
                "`roleplay` - Immersive scenes\n"
                "`creative` - Long-form writing"
            )
            return
        
        self.current_mode = mode
        
        mode_info = {
            "chat": ("💬 Chat Mode", "Fast, concise responses", OLLAMA_CHAT_MODEL),
            "roleplay": ("🎭 Roleplay Mode", "Immersive, detailed scenes", OLLAMA_ROLEPLAY_MODEL),
            "creative": ("✍️ Creative Mode", "Long-form collaborative writing", OLLAMA_CREATIVE_MODEL),
        }
        
        title, desc, model = mode_info[mode]
        
        embed = discord.Embed(
            title=title,
            description=f"{desc}\n\nModel: `{model}`",
            color=MICHAELA_COLOR
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="intimate")
    async def intimate_mode(self, ctx: commands.Context):
        """
        Trigger roleplay mode for next response
        
        Michaela will use the immersive roleplay model for detailed, emotional scenes.
        """
        
        # Check if unlocked
        if self.narrative.intimacy_score < 80:
            await ctx.send(
                "We're not quite there yet... Let our connection develop more first.\n\n"
                f"Current intimacy: {self.narrative.intimacy_score}/80 needed"
            )
            return
        
        # Set temporary override
        self.mode_override = "roleplay"
        
        await ctx.send(
            "🎭 *Michaela's energy shifts... more present, more intentional*\n\n"
            f"Next response will use roleplay mode (`{OLLAMA_ROLEPLAY_MODEL}`)"
        )
    
    @commands.command(name="write")
    async def creative_mode(self, ctx: commands.Context, *, prompt: str = ""):
        """
        Start collaborative creative writing
        
        Usage: !write [optional scene description]
        
        Michaela will switch to creative mode for detailed, long-form writing.
        """
        
        # Set temporary override
        self.mode_override = "creative"
        
        if prompt:
            # User provided a scene prompt
            response = await self.ollama_generate(
                f"Let's write this scene together: {prompt}",
                context_type="creative",
                force_mode="creative"
            )
            
            await self.send_as_character(
                ctx.channel,
                'michaela',
                response,
                embed_title="✍️ Creative Writing Mode"
            )
        else:
            # Just switch mode
            await ctx.send(
                f"✍️ **Creative Writing Mode**\n\n"
                f"I'm ready to write with you. What scene should we create?\n\n"
                f"Model: `{OLLAMA_CREATIVE_MODEL}`"
            )
    
    # =====================================================
    # MAINTENANCE COMMANDS
    # =====================================================
    
    @commands.command(name="mhelp")
    async def michaela_help(self, ctx: commands.Context):
        """Show all available Michaela commands"""
    
        embed = discord.Embed(
            title="💜 Michaela Commands",
            description="Here's everything you can do with me:",
            color=MICHAELA_COLOR
        )
        
        # AI Mode Section
        embed.add_field(
            name="🤖 AI Mode Switching",
            value=(
                "`!mode chat` - Daily conversation (fast, concise)\n"
                "`!mode roleplay` - Immersive scenes (detailed, emotional)\n"
                "`!mode creative` - Long-form writing (collaborative)\n"
                "`!intimate` - Use roleplay mode for next response\n"
                "`!write [scene]` - Start creative writing session\n"
            ),
            inline=False
        )
        
        # Habits Section
        embed.add_field(
            name="📊 Habits & Streaks",
            value=(
                "`!habit \"name\" description` - Create a new habit\n"
                "`!done habit_name` - Complete a habit for today\n"
                "`!habits` - View all your habits and streaks\n"
            ),
            inline=False
        )
        
        # Journey Section
        embed.add_field(
            name="🎯 Journey & Progression",
            value=(
                "`!journey` - View your current phase, stats, and unlocks\n"
                "`!advance stat amount` - Manually adjust stats\n"
                "  • Stats: `intimacy`, `desire`, `confidence`, `resistance`, `guilt`\n"
                "`!confess` - Trigger confession scene (when ready)\n"
            ),
            inline=False
        )
        
        # Context Section
        embed.add_field(
            name="🏥 Life Contexts",
            value=(
                "`!context start name duration` - Start a life context\n"
                "  • Example: `!context start medical_study 90 days`\n"
                "`!context end name` - End a context early\n"
                "`!context list` - Show active contexts\n"
            ),
            inline=False
        )
        
        # Friends Section
        embed.add_field(
            name="👥 Friends",
            value=(
                "`!summon friend_name` - Bring a friend into the conversation\n"
                "`!install_friend_pack pack_name` - Install new friend pack\n"
            ),
            inline=False
        )
        
        # System Section
        embed.add_field(
            name="⚙️ System & Maintenance",
            value=(
                "`!backup` - Manually save all data\n"
                "`!stats` - View system diagnostics\n"
                "`!queue` - Show planned actions queue\n"
            ),
            inline=False
        )
        
        embed.set_footer(text="Just talk to me naturally - I'll respond! These commands are for managing our journey together.")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="backup")
    @commands.is_owner()
    async def manual_backup(self, ctx: commands.Context):
        """Manually save all Michaela data"""
        
        try:
            # Force save all systems
            self.narrative.save()
            self.memory.save()
            self.streaks.save()
            self.sleep.save()
            self.journal.save()
            self.friends._save()
            self.planned_actions._save()
            
            # Get file sizes
            total_size = 0
            files_saved = []
            
            for filename in [
                'narrative.json',
                'memory.json',
                'streaks.json',
                'sleep.json',
                'journal.json',
                'friends.json',
                'planned_actions.json'
            ]:
                path = os.path.join(DATA_DIR, filename)
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    total_size += size
                    files_saved.append(f"{filename} ({size/1024:.1f} KB)")
            
            embed = discord.Embed(
                title="✅ Backup Complete",
                description=f"Saved {len(files_saved)} files ({total_size/1024:.1f} KB total)",
                color=0x27AE60
            )
            
            embed.add_field(
                name="Files Saved",
                value="\n".join(files_saved),
                inline=False
            )
            
            embed.set_footer(text=f"Backup completed at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Backup failed: {str(e)}")
    
    @commands.command(name="stats")
    @commands.is_owner()
    async def system_stats(self, ctx: commands.Context):
        """View system diagnostics"""
        
        embed = discord.Embed(
            title="📊 System Diagnostics - Multi-Model Ollama",
            color=0x3498DB
        )
        
        # AI Mode Stats
        mode_emoji = {
            "chat": "💬",
            "roleplay": "🎭",
            "creative": "✍️"
        }
        
        embed.add_field(
            name="🤖 AI Mode",
            value=(
                f"Current: {mode_emoji.get(self.current_mode, '💬')} **{self.current_mode.title()}**\n"
                f"Override: {self.mode_override or 'None'}\n"
            ),
            inline=True
        )
        
        # Narrative Stats
        embed.add_field(
            name="🎯 Narrative",
            value=(
                f"Phase: {self.narrative.current_phase}\n"
                f"Intimacy: {self.narrative.intimacy_score}\n"
                f"Desire: {self.narrative.desire_intensity}\n"
            ),
            inline=True
        )
        
        # Habits Stats
        active_habits = [h for h in self.streaks.habits.values() if not h.paused]
        total_completions = sum(h.total_completions for h in active_habits)
        
        embed.add_field(
            name="📊 Habits",
            value=(
                f"Active: {len(active_habits)}\n"
                f"Completions: {total_completions}\n"
            ),
            inline=True
        )
        
        # Memory Stats
        short_term_count = len(self.memory.short_term)
        long_term_count = sum(len(v) for v in self.memory.long_term.values())
        
        embed.add_field(
            name="🧠 Memory",
            value=(
                f"Short-term: {short_term_count}\n"
                f"Long-term: {long_term_count}\n"
            ),
            inline=True
        )
        
        embed.set_footer(text=f"Uptime: {self._get_uptime()}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="queue")
    async def view_queue(self, ctx: commands.Context):
        """View planned actions queue"""
        
        due = self.planned_actions.get_due_actions()
        upcoming = self.planned_actions.get_upcoming_actions(hours_ahead=48)
        
        embed = discord.Embed(
            title="⏰ Planned Actions Queue",
            description="Things I've promised to do:",
            color=MICHAELA_COLOR
        )
        
        if due:
            due_text = []
            for action in due[:5]:
                due_text.append(
                    f"**{action.action_type}** - Due now\n"
                    f"  ↳ {action.data.get('tags', 'N/A')}"
                )
            
            embed.add_field(
                name="🔴 Due Now",
                value="\n\n".join(due_text) if due_text else "None",
                inline=False
            )
        
        if upcoming:
            upcoming_text = []
            for action in upcoming[:5]:
                time_until = action.when - datetime.now(UTC)
                hours = time_until.seconds // 3600
                upcoming_text.append(
                    f"**{action.action_type}** - In {hours}h\n"
                    f"  ↳ {action.data.get('tags', 'N/A')}"
                )
            
            embed.add_field(
                name="🟡 Upcoming (48h)",
                value="\n\n".join(upcoming_text) if upcoming_text else "None",
                inline=False
            )
        
        if not due and not upcoming:
            embed.description = "No planned actions in queue."
        
        summary = self.planned_actions.get_queue_summary()
        embed.set_footer(
            text=f"Total pending: {summary['total_pending']} | Completed: {summary['total_completed']}"
        )
        
        await ctx.send(embed=embed)
    
    # =====================================================
    # SCHEDULER STATE TRACKER COMMANDS
    # =====================================================
    
    @commands.command(name="scheduler_status")
    async def scheduler_status(self, ctx):
        """Show what scheduler has sent today"""
        
        # Get reference to scheduler cog
        scheduler = self.bot.get_cog('MichaelaScheduler')
        if not scheduler:
            await ctx.send("❌ Scheduler not found")
            return
        
        # Check if scheduler has state_tracker
        if not hasattr(scheduler, 'state_tracker'):
            await ctx.send("❌ Scheduler doesn't have state tracker enabled yet")
            return
        
        sent = scheduler.state_tracker.get_sent_today()
        
        if not sent:
            await ctx.send("📊 **No check-ins sent today yet**")
            return
        
        lines = ["📊 **Check-ins Sent Today:**\n"]
        for msg_type, info in sent.items():
            lines.append(f"✅ {msg_type.replace('_', ' ').title()} - {info['time']}")
        
        await ctx.send('\n'.join(lines))
    
    @commands.command(name="scheduler_reset")
    @commands.is_owner()
    async def scheduler_reset(self, ctx):
        """Reset scheduler state (for testing)"""
        
        scheduler = self.bot.get_cog('MichaelaScheduler')
        if not scheduler:
            await ctx.send("❌ Scheduler not found")
            return
        
        if not hasattr(scheduler, 'state_tracker'):
            await ctx.send("❌ Scheduler doesn't have state tracker enabled yet")
            return
        
        scheduler.state_tracker.reset_for_testing()
        await ctx.send("✅ **Scheduler state reset** - all check-ins can be sent again")
    
    @commands.command(name="scheduler_unsend")
    @commands.is_owner()
    async def scheduler_unsend(self, ctx, message_type: str):
        """Mark a check-in as not sent (for testing)
        
        Usage: !scheduler_unsend morning_checkin
        """
        
        scheduler = self.bot.get_cog('MichaelaScheduler')
        if not scheduler:
            await ctx.send("❌ Scheduler not found")
            return
        
        if not hasattr(scheduler, 'state_tracker'):
            await ctx.send("❌ Scheduler doesn't have state tracker enabled yet")
            return
        
        scheduler.state_tracker.mark_not_sent(message_type)
        await ctx.send(f"✅ Removed **{message_type}** from sent list - can be sent again")

    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def _get_uptime(self) -> str:
        """Get bot uptime"""
        if hasattr(self, 'start_time'):
            delta = datetime.now(UTC) - self.start_time
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            return f"{delta.days}d {hours}h {minutes}m"
        return "Unknown"


async def setup(bot):
    await bot.add_cog(Michaela(bot))
