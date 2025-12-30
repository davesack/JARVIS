# utils/rankings/cache.py
"""
Rankings Cache
==============

Local disk cache for Rankings METADATA loaded from Google Sheets.

Purpose:
- Avoid repeated Google Sheets API calls
- Improve bot startup and command latency
- Provide a single refresh point (admin-controlled)

Design:
- RankingsLoader remains the source of truth for parsing
- Cache stores fully-parsed RankingEntry objects
- Lazy refresh with TTL
"""

from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import List, Optional

from config import DATA_ROOT
from utils.rankings.loader import RankingsLoader
from utils.rankings.models import RankingEntry


# ================================================================
# CACHE PATHS & SETTINGS
# ================================================================

CACHE_DIR = DATA_ROOT / "rankings_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ENTRIES_FILE = CACHE_DIR / "entries.json"
META_FILE = CACHE_DIR / "meta.json"

# Default cache TTL (minutes)
CACHE_TTL_MINUTES = 1440  # 24 hours - prevents rate limiting


# ================================================================
# SERIALIZATION HELPERS
# ================================================================

def _date_to_str(d: Optional[datetime.date]) -> Optional[str]:
    return d.isoformat() if d else None


def _str_to_date(s: Optional[str]) -> Optional[datetime.date]:
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s)
    except Exception:
        return None


def serialize_entry(e: RankingEntry) -> dict:
    """
    Convert RankingEntry → JSON-serializable dict.
    """
    return {
        "name": e.name,
        "slug": e.slug,
        "group": e.group,
        "rank_raw": e.rank_raw,
        "birth_date": _date_to_str(e.birth_date),
        "death_date": _date_to_str(e.death_date),
        "birth_city": e.birth_city,
        "birth_state": e.birth_state,
        "birth_country": e.birth_country,
        "known_for": e.known_for,
        "known_for_label": e.known_for_label,
        "is_neverland": e.is_neverland,
        "gender": e.gender,
        "extra": e.extra,
    }


def deserialize_entry(data: dict) -> RankingEntry:
    """
    Convert cached dict → RankingEntry.
    """
    return RankingEntry(
        name=data["name"],
        slug=data.get("slug"),
        group=data["group"],
        rank_raw=data.get("rank_raw"),
        birth_date=_str_to_date(data.get("birth_date")),
        death_date=_str_to_date(data.get("death_date")),
        birth_city=data.get("birth_city"),
        birth_state=data.get("birth_state"),
        birth_country=data.get("birth_country"),
        known_for=data.get("known_for"),
        known_for_label=data.get("known_for_label", "Known For:"),
        is_neverland=data.get("is_neverland", False),
        gender=data.get("gender"),
        extra=data.get("extra", {}),
    )


# ================================================================
# CACHE CORE
# ================================================================

class RankingsCache:
    """
    Disk-backed cache for rankings metadata.

    Public API:
    - load()            → returns RankingsLoader (cached or refreshed)
    - refresh()         → force refresh from Google Sheets
    - is_cache_valid()  → TTL-based validity check
    """

    def __init__(self, ttl_minutes: int = CACHE_TTL_MINUTES):
        self.ttl = datetime.timedelta(minutes=ttl_minutes)

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def load(self) -> RankingsLoader:
        """
        Load rankings data.

        Uses cache if valid, otherwise refreshes from Sheets.
        """
        if self.is_cache_valid():
            loader = self._load_from_cache()
            if loader:
                return loader

        # Fallback to refresh
        return self.refresh()

    def refresh(self) -> RankingsLoader:
        """
        Force refresh from Google Sheets and overwrite cache.
        """
        loader = RankingsLoader()
        loader.load()

        self._write_cache(loader.entries)
        return loader

    # ------------------------------------------------------------
    # Cache state helpers
    # ------------------------------------------------------------

    def is_cache_valid(self) -> bool:
        """
        Check whether cache exists and is within TTL.
        """
        if not ENTRIES_FILE.exists() or not META_FILE.exists():
            return False

        try:
            meta = json.loads(META_FILE.read_text(encoding="utf-8"))
            ts = datetime.datetime.fromisoformat(meta["last_refresh"])
        except Exception:
            return False

        age = datetime.datetime.utcnow() - ts
        return age <= self.ttl

    # ------------------------------------------------------------
    # Internal IO
    # ------------------------------------------------------------

    def _load_from_cache(self) -> Optional[RankingsLoader]:
        """
        Load cached entries into a fresh RankingsLoader.
        """
        try:
            raw = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None

        loader = RankingsLoader()

        for item in raw:
            try:
                entry = deserialize_entry(item)
                loader.entries.append(entry)
                loader._index(entry)
            except Exception:
                # Skip corrupted rows
                continue

        return loader

    def _write_cache(self, entries: List[RankingEntry]) -> None:
        """
        Persist entries and metadata to disk.
        """
        payload = [serialize_entry(e) for e in entries]

        ENTRIES_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        meta = {
            "last_refresh": datetime.datetime.utcnow().isoformat(),
            "count": len(entries),
        }

        META_FILE.write_text(
            json.dumps(meta, indent=2),
            encoding="utf-8",
        )
