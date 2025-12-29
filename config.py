"""
================================================================
 JARVIS CONFIGURATION MODULE
================================================================
 Loads all environment variables, paths, and settings used by the
 bot. This is the *single* source of truth for IDs, keys, and
 directory structure.
================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import logging
log = logging.getLogger(__name__)

# ================================================================
# HELPERS
# ================================================================

def _int(env_value: str | None, default: int = 0) -> int:
    """Safely convert an environment variable to int."""
    try:
        return int(env_value) if env_value else default
    except ValueError:
        return default


def _int_list(env_value: str | None) -> list[int]:
    """Convert comma-separated lists of integers into Python list[int]."""
    if not env_value:
        return []
    return [
        int(x.strip())
        for x in env_value.split(",")
        if x.strip().isdigit()
    ]


"""
Everything below this is exactly your config, just with the helpers moved
to the top and the duplicate _int_list removed.
"""

# ================================================================
# PATHS â€” BASE PROJECT STRUCTURE
# ================================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_ROOT = BASE_DIR / "data"
MEDIA_ROOT = BASE_DIR / "media"

# Ensure required folders exist
DATA_ROOT.mkdir(exist_ok=True)
MEDIA_ROOT.mkdir(exist_ok=True)

# ================================================================
# DISCORD CORE SETTINGS
# ================================================================

TOKEN: str | None = os.getenv("DISCORD_TOKEN")

DISCORD_OWNER_ID: int = _int(os.getenv("DISCORD_OWNER_ID"))
DEV_GUILD_ID: int = _int(os.getenv("DEV_GUILD_ID"))

# Backwards compatibility for cogs that import OWNER_USER_ID
OWNER_USER_ID = DISCORD_OWNER_ID

# API Keys
GIPHY_API_KEY: str | None = os.getenv("GIPHY_API_KEY", "")

# ================================================================
# MEDIAWATCHER â€” DIRECTORIES & SETTINGS
# ================================================================

# Special pipeline directories
MEDIA_INCOMING = MEDIA_ROOT / "_incoming"
MEDIA_PROCESSED = MEDIA_ROOT / "_processed"
MEDIA_REVIEW = MEDIA_ROOT / "_review"

# Subfolders inside _review
MEDIA_REVIEW_BAD_SLUG = MEDIA_REVIEW / "bad_slug"
MEDIA_REVIEW_BAD_VIDEO = MEDIA_REVIEW / "bad_video"
MEDIA_REVIEW_UNSUPPORTED = MEDIA_REVIEW / "unsupported"
MEDIA_REVIEW_UNKNOWN = MEDIA_REVIEW / "unknown"

# Ensure folders exist
for folder in (
    MEDIA_INCOMING,
    MEDIA_PROCESSED,
    MEDIA_REVIEW,
    MEDIA_REVIEW_BAD_SLUG,
    MEDIA_REVIEW_BAD_VIDEO,
    MEDIA_REVIEW_UNSUPPORTED,
    MEDIA_REVIEW_UNKNOWN,
):
    folder.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------
# METADATA (people + aliases + event logs)
# ---------------------------------------------------------------
MEDIAWATCHER_DATA = DATA_ROOT / "mediawatcher"
MEDIAWATCHER_DATA.mkdir(parents=True, exist_ok=True)

MEDIA_PEOPLE_FILE = MEDIAWATCHER_DATA / "people.json"
MEDIA_ALIASES_FILE = MEDIAWATCHER_DATA / "aliases.json"
MEDIA_EVENTS_LOG = MEDIAWATCHER_DATA / "events.jsonl"

# ---------------------------------------------------------------
# SIZE LIMITS
# ---------------------------------------------------------------
MAX_DISCORD_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------
# GIF / VIDEO PROCESSING
# ---------------------------------------------------------------
CONVERT_GIF_TO_WEBP: bool = True

TOOLS_DIR = BASE_DIR / "tools"
TOOLS_ROOT = TOOLS_DIR

FFMPEG_PATH = TOOLS_DIR / "ffmpeg.exe"
FFPROBE_PATH = TOOLS_DIR / "ffprobe.exe"
HANDBRAKE_PATH = TOOLS_DIR / "HandBrakeCLI.exe"

# ---------------------------------------------------------------
# SLUG & NSFW CATEGORY SETTINGS
# ---------------------------------------------------------------
SLUG_CONFIDENCE_THRESHOLD: float = 0.70

NSFW_UNKNOWN_CATEGORIES = [
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

# ---------------------------------------------------------------
# DROPBOX WATCH FOLDER
# ---------------------------------------------------------------
DROPBOX_WATCH_ROOT = Path(r"D:\Dropbox\Apps\MediaWatcher")

# ================================================================
# CHANNELS / ACCESS TIERS
# ================================================================

CHANNEL_PUBLIC: list[int] = _int_list(os.getenv("CHANNEL_PUBLIC"))
CHANNEL_FAMILY: list[int] = _int_list(os.getenv("CHANNEL_FAMILY"))
CHANNEL_SFW: list[int] = _int_list(os.getenv("CHANNEL_SFW"))
CHANNEL_COFFEE: list[int] = _int_list(os.getenv("CHANNEL_COFFEE"))
CHANNEL_NSFW: list[int] = _int_list(os.getenv("CHANNEL_NSFW"))
CHANNEL_NO_GROUP1: list[int] = _int_list(os.getenv("CHANNEL_NO_GROUP1"))

BIRTHDAY_POST_CHANNEL_ID: int = _int(os.getenv("BIRTHDAY_POST_CHANNEL_ID"))
BIRTHDAY_POST_HOUR = 10
BIRTHDAY_POST_MINUTE = 0

# Convenience aliases (for cleaner imports in cogs)
NSFW_CHANNEL_IDS = CHANNEL_NSFW
NO_GROUP1_CHANNEL_IDS = CHANNEL_NO_GROUP1

PRIVATE_HABITS_CHANNEL_ID: list[int] = _int_list(os.getenv("PRIVATE_HABITS_CHANNEL_ID"))
PERSONA_CHAT_CHANNELS: dict = {
    "michaela": _int_list(os.getenv("MICHAELA_CHAT_CHANNELS")),
}
# Michaela conversational channels
MICHAELA_CHANNEL_IDS: list[int] = _int_list(os.getenv("MICHAELA_CHANNEL_IDS"))

# Ollama Multi-Model Setup
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_CHAT_ENDPOINT = "http://localhost:11434/api/chat"

# Models (CORRECTED TO MATCH YOUR INSTALL)
OLLAMA_CHAT_MODEL = "fluffy/l3-8b-stheno-v3.2:latest"
OLLAMA_ROLEPLAY_MODEL = "fluffy/l3-8b-stheno-v3.2:latest"
OLLAMA_CREATIVE_MODEL = "mistral-nemo:12b-instruct-2407-q4_K_M"
OLLAMA_VISION_MODEL = "llama3.2-vision:latest"

OLLAMA_DEFAULT_MODE = "chat"

# ================================================================
# BLUESKY SETTINGS
# ================================================================

BSKY_HANDLE: str | None = os.getenv("BSKY_HANDLE")
BSKY_PASSWORD: str | None = os.getenv("BSKY_PASSWORD")
BSKY_APP_PASSWORD: str | None = os.getenv("BSKY_APP_PASSWORD")

BSKY_THREAD_CATEGORY: int = _int(os.getenv("BSKY_THREAD_CATEGORY"))
BSKY_DATABASE: str = os.getenv("BSKY_DATABASE", "data/bsky_posts.db")
BSKY_SUBSCRIPTIONS = Path(os.getenv("BSKY_SUBSCRIPTIONS", DATA_ROOT / "bsky" / "bsky_subscriptions.json"))

# Bluesky media cache retention (no .env)
# Number of days cached Bluesky media stays before auto-cleanup
BLUESKY_CACHE_RETENTION_DAYS: int = 7

# ================================================================
# MEDIAWATCHER â€” TAGGING MODE
# ================================================================

MEDIAWATCHER_TAGGING_MODE_ENABLED: bool = True  # default ON

MEDIAWATCHER_TAGGING_CHANNELS: list[int] = _int_list(
    os.getenv("MEDIAWATCHER_TAGGING_CHANNELS", "")
)

MEDIAWATCHER_TAGGING_USER: int = DISCORD_OWNER_ID

MEDIAWATCHER_TAGGING_HASH_ALGO: str = "sha1"

# ================================================================
# RANKINGS / GOOGLE SHEETS
# ================================================================
RANKINGS_SHEET_ID: str | None = os.getenv("RANKINGS_SHEET_ID")

GOOGLE_SHEETS = {
    "rankings": {
        "spreadsheet_id": RANKINGS_SHEET_ID,
        "sheet_name": os.getenv("RANKINGS_SHEET_TAB", "METADATA"),
        "header_row": 1,
        "data_row_start": 2,
        "columns": {
            "name": "A",
            "rank": "B",
            "group": "C",
            "birthdate": "D",
            "place_of_birth": "E",
            "gender": "F",
            "images_start": "G",
            "images_end": "I",
            "date_of_death": "J",
            "instagram": "N",
            "twitter": "O",
            "tiktok": "R",
            "known_for": "AR",
            "bluesky": "AS",
            "slug": "AT",
            # NEW: notes column added at AB
            "notes": "AB",
            # Physical description columns (AC-AQ) - shifted by 1
            "height": "AC",
            "build_description": "AD",
            "frame_description": "AE",
            "shoulders_description": "AF",
            "chest_description": "AG",
            "waist_description": "AH",
            "hips_description": "AI",
            "glutes_description": "AJ",
            "leg_proportions": "AK",
            "facial_shape": "AL",
            "eyes_description": "AM",
            "nose_description": "AN",
            "lips_description": "AO",
            "hair_description": "AP",
            "distinguishing_features": "AQ",
            # Measurements columns - shifted by 1
            "measurements": "AV",
            "bust": "AW",
            "waist": "AX",
            "hips": "AY",
            "bra_size": "AZ",
            "cup_size": "BA",
            "weight": "BB",
            "ethnicity": "BC",
            "nationality": "W",
            "hair_color": "BD",
            "eye_color": "BE",
            "biography": "BK",
            "years_active": "BL",
            "body_type": "BM",
            "boobs": "BN",
            "shown": "BO",
            "special": "BP",
            "occupations": "X",
        },
    },
    "arena_intake": {
        "spreadsheet_id": RANKINGS_SHEET_ID,
        "sheet_name": "ARENA_INTAKE",
        "header_row": 1,
        "data_row_start": 2,
        "columns": {
            "name": "A",
            "discovery_score": "B",
            "source_count": "C",
            "height": "D",
            "measurements": "E",
            "ethnicity": "F",
            "nationality": "G",
            "hair_color": "H",
            "eye_color": "I",
            "tags": "J",
            "timestamp": "K",
            "status": "L",
        }
    },
    "metadata_enriched": {
        "spreadsheet_id": RANKINGS_SHEET_ID,
        "sheet_name": "METADATA_ENRICHED",
        "header_row": 1,
        "data_row_start": 2,
        "columns": {
            "name": "A",
            "height": "B",
            "measurements": "C",
            "bust": "D",
            "waist": "E",
            "hips": "F",
            "bra_size": "G",
            "cup_size": "H",
            "weight": "I",
            "ethnicity": "J",
            "nationality": "K",
            "hair_color": "L",
            "eye_color": "M",
            "birthdate": "N",
            "birthplace": "O",
            "tags": "P",
            "sources": "Q",
            "last_updated": "R",
            "biography": "S",
            "years_active": "T",
            "body_type": "U",
            "boobs": "V",
            "shown": "W",
            "special": "X",
        }
    }
}

# ================================================================
# SHEETS LOADER CONFIG
# ================================================================
SHEETS_LOADER = {
    "spreadsheet_id": GOOGLE_SHEETS["rankings"]["spreadsheet_id"],
    "sheet_name": GOOGLE_SHEETS["rankings"]["sheet_name"],
    "name_column": GOOGLE_SHEETS["rankings"]["columns"]["name"],
    "data_row_start": GOOGLE_SHEETS["rankings"]["data_row_start"],
}


GOOGLE_SERVICE_ACCOUNT_FILE = BASE_DIR / "utils" / "sheets" / "service_account.json"

# ================================================================
# EVENTS MODULE
# ================================================================
from pathlib import Path

# Where recurring events database will live
EVENTS_DB = DATA_ROOT / "events_db.json"

# Root folder that contains subfolders:
#   events/
#       birthday/
#       anniversary/
#       <custom>/
EVENTS_MEDIA_ROOT = MEDIA_ROOT / "events"

# ===================================================================
# TAGGING HARD MODE
# ===================================================================
# When True, you'll get tagging prompts even for images you've already
# been prompted for before. Useful for re-tagging everything.
# 
# Normal mode (False): Only prompt once per image
# Hard mode (True): Always prompt, ignore the "seen" list
#
# Set to True when you want to re-tag all images in birthday posts.
# Set back to False once you're done.
# ===================================================================

MEDIAWATCHER_TAGGING_HARD_MODE = True  # Change to False after re-tagging

# ================================================================
# POOPROCK MODULE
# ================================================================

POOPROCK_CONFIG = {
    "enabled": True,
    "guild_id": DEV_GUILD_ID,      # your server ID
    "channel_id": CHANNEL_FAMILY,    # where posts go

    "data_dir": "data/pooprock",

    # Reminder system
    "reminder_days": 7,
    "repeat_reminders": True,
    "allow_savage": True,

    # Recaps
    "monthly_recap": True,
    "quarterly_recap": True,
    "yearly_recap": True,

    # Tone weights (used for text + GIF selection)
    "tone_weights": {
        "gentle": 0.4,
        "mocking": 0.4,
        "savage": 0.2,
    },
}


# ================================================================
# END OF CONFIG
# ================================================================
