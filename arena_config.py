# arena_config.py
"""
JARVIS Arena - Configuration
Centralized config for Arena discovery, scrapers, and battle system
"""
from __future__ import annotations

import os
from pathlib import Path
from config import GOOGLE_SHEETS

# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "arena"
OUTPUT_DIR = DATA_DIR / "outputs"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# TMDB API CONFIGURATION
# ============================================================
TMDB_API_KEY = "f2e82b5cfaf9d31c097c65180d0f359a"
TMDB_READ_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJmMmU4MmI1Y2ZhZjlkMzFjMDk3YzY1MTgwZDBmMzU5YSIsIm5iZiI6MTc2Mzk0NzgzMy4zMTcsInN1YiI6IjY5MjNiNTM5NTA3NDM1OGE5MjE4NzM2OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.w8Cl1zxmfolc3zj1b97YTo3IOj4Ne5aJbQW5984O46w"

# ============================================================
# SCRAPING SETTINGS
# ============================================================
REQUEST_DELAY = 2.0  # seconds between requests
MAX_RETRIES = 3
REQUEST_TIMEOUT = 20
INCLUDE_ADULT_SOURCES = True  # Include IAFD and Data18

# ============================================================
# DISCOVERY THRESHOLDS
# ============================================================
MIN_DISCOVERY_SCORE = float(os.getenv("ARENA_MIN_DISCOVERY_SCORE", 100))
MIN_SOURCE_COUNT = int(os.getenv("ARENA_MIN_SOURCE_COUNT", 2))
HIGH_CONFIDENCE_THRESHOLD = 85

# ============================================================
# GOOGLE SHEETS (REUSED FROM CONFIG)
# ============================================================
ARENA_INTAKE_SHEET = GOOGLE_SHEETS["arena_intake"]
METADATA_SHEET = GOOGLE_SHEETS["rankings"]

# ============================================================
# PIPELINE SETTINGS
# ============================================================
PIPELINE_ENABLED = os.getenv("ARENA_PIPELINE_ENABLED", "true").lower() == "true"
PIPELINE_DRY_RUN = os.getenv("ARENA_PIPELINE_DRY_RUN", "false").lower() == "true"

# ============================================================
# WEEKLY SCRAPING SCHEDULE
# ============================================================
SCRAPE_SCHEDULE = {
    'enabled': True,
    'day': 'Sunday',  # Day of week to run
    'hour': 2,  # 2 AM
    'sources': [
        'celebbattles',
        'celeb_economy', 
        'battle_league',
        'sexiest_league',
        'metadata_sources'  # Includes all: Celebrity Inside, Boobpedia, BodySizeX, TMDB, Wikipedia, IAFD, Data18
    ]
}

# ============================================================
# EXPORT SETTINGS
# ============================================================
EXPORT_FORMAT = 'csv'  # For Google Sheets compatibility
INCLUDE_METADATA_TEMPLATE = True
AUTO_ENRICH_METADATA = True  # Auto-scrape measurements when possible
