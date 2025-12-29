"""
Michaela V2.0 - Central Configuration
======================================

Edit this file to customize all system settings in one place.
After editing, follow the CONFIGURATION_EDIT_GUIDE.md to update references.
"""

import os
from typing import List

def _int_list(env_var: str) -> List[int]:
    """Parse comma-separated list of integers from env var"""
    if not env_var:
        return []
    return [int(x.strip()) for x in env_var.split(',')]

# ============================================================================
# PERSON SLUGS
# ============================================================================
# These MUST match your media folder names exactly

MICHAELA_SLUG = "michaela-miller"
ARIANN_SLUG = "ariann-reinmiller"
HANNAH_SLUG = "hannah-mailand"
TARA_SLUG = "tara-blesh-boren"
ELISHA_SLUG = "elisha-sack"

# Celebrity slugs
SALMA_SLUG = "salma-hayek"
ANNA_SLUG = "anna-kendrick"
ALISON_SLUG = "alison-brie"

# Unknown slug for sex acts
UNKNOWN_SLUG = "unknown"

# ============================================================================
# MEDIA PATHS
# ============================================================================

MEDIA_ROOT = "media"  # Root media directory
TAGS_DATABASE_PATH = "data/media/tags_database.json"  # Tags database location

# Profile images (for friends and Michaela)
PROFILE_IMAGE_FILENAME = "profile.webp"  # Standard filename for profile pics

# ============================================================================
# DISCORD SETTINGS
# ============================================================================

# Channel IDs where Michaela operates
MICHAELA_CHANNEL_IDS: list[int] = _int_list(os.getenv("MICHAELA_CHANNEL_IDS"))

# ============================================================================
# OLLAMA API SETTINGS
# ============================================================================

# Ollama Multi-Model Setup
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_CHAT_ENDPOINT = "http://localhost:11434/api/chat"

# Models (CORRECTED TO MATCH YOUR INSTALL)
OLLAMA_CHAT_MODEL = "fluffy/l3-8b-stheno-v3.2:latest"
OLLAMA_ROLEPLAY_MODEL = "fluffy/l3-8b-stheno-v3.2:latest"
OLLAMA_CREATIVE_MODEL = "mistral-nemo:12b-instruct-2407-q4_K_M"
OLLAMA_VISION_MODEL = "llama3.2-vision:latest"

OLLAMA_DEFAULT_MODE = "chat"

# ============================================================================
# UNKNOWN CATEGORIES (Sex Acts)
# ============================================================================

UNKNOWN_CATEGORIES = [
    "airtight",
    "anal",
    "blacked",
    "blowbang",
    "blowjob",
    "bukkake",
    "cuckold",
    "cum",
    "cum-face",
    "cum-swallow",
    "deepthroat",
    "dp",
    "frotting",
    "gangbang",
    "gloryhole",
    "spitroast",
]

# ============================================================================
# FRIEND PACK SETTINGS
# ============================================================================

# Default friend pack to auto-load on first run
DEFAULT_FRIEND_PACK = "core_friends"

# Friend pack directory
FRIEND_PACKS_DIR = "data/michaela/friend_packs"

# ============================================================================
# DATA STORAGE PATHS
# ============================================================================

MICHAELA_DATA_DIR = "data/michaela"
HABITS_DATA_PATH = f"{MICHAELA_DATA_DIR}/habits.json"
NARRATIVE_DATA_PATH = f"{MICHAELA_DATA_DIR}/narrative_state.json"
MEMORY_DATA_PATH = f"{MICHAELA_DATA_DIR}/memory.json"
JOURNAL_DATA_PATH = f"{MICHAELA_DATA_DIR}/journal.json"
SLEEP_DATA_PATH = f"{MICHAELA_DATA_DIR}/sleep.json"
CONTEXTS_DATA_PATH = f"{MICHAELA_DATA_DIR}/contexts.json"
FRIENDS_DATA_PATH = f"{MICHAELA_DATA_DIR}/friends.json"

# ============================================================================
# SCHEDULING SETTINGS
# ============================================================================

# Morning routine (runs once per day)
MORNING_ROUTINE_START_HOUR = 7  # 7 AM
MORNING_ROUTINE_END_HOUR = 9    # 9 AM

# Habit reminder check interval (minutes)
HABIT_REMINDER_INTERVAL = 30

# Planned action check interval (minutes)
PLANNED_ACTION_INTERVAL = 5

# ============================================================================
# NARRATIVE PROGRESSION SETTINGS
# ============================================================================

# How often to auto-save narrative state (messages)
NARRATIVE_AUTOSAVE_INTERVAL = 10

# Intimacy decay rate (points per day of inactivity)
INTIMACY_DECAY_RATE = 2

# Desire decay rate (points per day of inactivity)
DESIRE_DECAY_RATE = 1

# ============================================================================
# MEDIA SENDING SETTINGS
# ============================================================================

# Cooldown between media sends (minutes)
MEDIA_SEND_COOLDOWN = 30

# Probability modifiers
BASE_SEND_PROBABILITY = 0.7  # Base chance she'll send when asked
RESISTANCE_MODIFIER = -0.05  # How much resistance reduces probability (per point)
DESIRE_MODIFIER = 0.02       # How much desire increases probability (per point)

# ============================================================================
# TODO MANAGER & CALENDAR SETTINGS
# ============================================================================

TODO_DATA_PATH = f"{MICHAELA_DATA_DIR}/todos.json"

# Calendar settings
GOOGLE_SERVICE_ACCOUNT_FILE = "utils/sheets/service_account.json"
CALENDAR_CHECK_INTERVAL = 5  # minutes

# Support reminder timing
DEFAULT_REMINDER_MINUTES = 30
POST_EVENT_CHECKIN_MIN = 15  # Wait at least 15 min after event
POST_EVENT_CHECKIN_MAX = 30  # Check-in within 30 min

# Free block detection
MIN_FREE_BLOCK_MINUTES = 60  # 1 hour minimum to count as "free"
EVENING_START_HOUR = 17  # 5 PM

# Random check-in probability modifiers
FREE_BLOCK_MULTIPLIER = 2.0   # 2x more likely during free time
BUSY_BLOCK_MULTIPLIER = 0.1   # 10% normal probability when busy
EVENING_FREE_MULTIPLIER = 3.0 # 3x for intimate initiations

# ============================================================================
# ADVANCED SETTINGS
# ============================================================================

# Enable debug logging
DEBUG_MODE = False

# Enable memory compression (keeps memory manageable)
ENABLE_MEMORY_COMPRESSION = True

# Memory compression threshold (number of entries before compression)
MEMORY_COMPRESSION_THRESHOLD = 100

# Event tracking enabled
ENABLE_EVENT_TRACKING = True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_person_media_path(slug: str) -> str:
    """Get media path for a person"""
    return f"{MEDIA_ROOT}/{slug}"

def get_unknown_category_path(category: str, media_type: str = "images") -> str:
    """Get path for unknown category"""
    return f"{MEDIA_ROOT}/{UNKNOWN_SLUG}/{media_type}/nsfw/{category}"

def get_michaela_private_path() -> str:
    """Get Michaela's private folder path"""
    return f"{MEDIA_ROOT}/{MICHAELA_SLUG}/private"

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration on import"""
    import os
    
    errors = []
    
    # Check media root exists
    if not os.path.exists(MEDIA_ROOT):
        errors.append(f"Media root directory not found: {MEDIA_ROOT}")
    
    # Check Michaela folder exists
    michaela_path = get_person_media_path(MICHAELA_SLUG)
    if not os.path.exists(michaela_path):
        errors.append(f"Michaela media folder not found: {michaela_path}")
    
    # Check channel IDs configured
    if not MICHAELA_CHANNEL_IDS:
        errors.append("No channel IDs configured in MICHAELA_CHANNEL_IDS")
    
    if errors:
        print("⚠️  Configuration warnings:")
        for error in errors:
            print(f"   - {error}")
        print("   Update michaela_config.py to fix these issues.")
    else:
        print("✅ Michaela configuration validated")

# Auto-validate when imported
if __name__ != "__main__":
    # Only validate if not running as script
    # validate_config()  # Uncomment after initial setup
    pass
