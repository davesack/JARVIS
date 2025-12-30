"""
Michaela Utilities Package
===========================

Complete utility modules for Michaela companion system
"""

from .narrative_progression import NarrativeProgression, AutoProgressionEngine
from .memory_system import MichaelaMemory
from .streak_tracker import IntelligentStreakSystem
from .sleep_tracker import SleepTracker
from .micro_journal import MicroJournal
from .friends_system import FriendsManager, Friend, FriendStoryArc
from .tagged_media_resolver import TaggedMediaResolver
from .context_profiles import ContextualBehaviorProfiles
from .reminder_system import ReminderSystem

__all__ = [
    'NarrativeProgression',
    'AutoProgressionEngine',
    'MichaelaMemory',
    'IntelligentStreakSystem',
    'SleepTracker',
    'MicroJournal',
    'FriendsManager',
    'Friend',
    'FriendStoryArc',
    'TaggedMediaResolver',
    'ContextualBehaviorProfiles',
    'ReminderSystem',
]
