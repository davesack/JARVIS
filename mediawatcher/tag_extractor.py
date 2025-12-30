# utils/mediawatcher/tag_extractor.py
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import List, Optional

from config import MEDIAWATCHER_DATA, MEDIAWATCHER_TAGGING_HASH_ALGO

# Where we store manual tags
TAGS_FILE = MEDIAWATCHER_DATA / "manual_tags.json"
TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)


# ================================================================
# HASH CALCULATION
# ================================================================

def compute_file_hash(path: Path, algo: str = "sha1") -> str:
    """Compute file hash for tag storage key."""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


# ================================================================
# STORAGE (JSON-based)
# ================================================================

def _load_tags_db() -> dict:
    """Load the tags database from JSON."""
    if not TAGS_FILE.exists():
        return {}
    try:
        with open(TAGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_tags_db(db: dict):
    """Save the tags database to JSON."""
    with open(TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


# ================================================================
# PUBLIC API
# ================================================================

def get_manual_tags_for_file(path: Path, slug: Optional[str] = None) -> List[str]:
    """
    Get manual tags for a file.
    
    Returns tags from two sources:
    1. File-specific tags (keyed by file hash)
    2. Slug-level tags (if slug provided)
    """
    db = _load_tags_db()
    tags = []
    
    # File-specific tags (by hash)
    if path.exists():
        file_hash = compute_file_hash(path, MEDIAWATCHER_TAGGING_HASH_ALGO)
        file_tags = db.get("by_file", {}).get(file_hash, [])
        tags.extend(file_tags)
    
    # Slug-level tags
    if slug:
        slug_tags = db.get("by_slug", {}).get(slug, [])
        tags.extend(slug_tags)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    
    return unique_tags


def save_updated_tags(
    path: Path,
    add: Optional[List[str]] = None,
    remove: Optional[List[str]] = None,
    slug: Optional[str] = None
):
    """
    Add or remove manual tags for a file.
    
    Handles comma-separated input:
    "tag1, tag2, tag3" → ["tag1", "tag2", "tag3"]
    """
    db = _load_tags_db()
    
    if "by_file" not in db:
        db["by_file"] = {}
    if "by_slug" not in db:
        db["by_slug"] = {}
    
    # Process comma-separated tags
    if add:
        processed_add = []
        for tag in add:
            # Split by comma and strip whitespace
            for subtag in tag.split(","):
                cleaned = subtag.strip().lower()
                if cleaned:
                    processed_add.append(cleaned)
        add = processed_add
    
    if remove:
        processed_remove = []
        for tag in remove:
            for subtag in tag.split(","):
                cleaned = subtag.strip().lower()
                if cleaned:
                    processed_remove.append(cleaned)
        remove = processed_remove
    
    # File-specific tags
    if path.exists():
        file_hash = compute_file_hash(path, MEDIAWATCHER_TAGGING_HASH_ALGO)
        current_tags = set(db["by_file"].get(file_hash, []))
        
        if add:
            current_tags.update(add)
        if remove:
            current_tags.difference_update(remove)
        
        db["by_file"][file_hash] = sorted(current_tags)
    
    # Slug-level tags
    if slug:
        current_slug_tags = set(db["by_slug"].get(slug, []))
        
        if add:
            current_slug_tags.update(add)
        if remove:
            current_slug_tags.difference_update(remove)
        
        db["by_slug"][slug] = sorted(current_slug_tags)
    
    _save_tags_db(db)


def get_existing_tags(path: Path) -> List[str]:
    """
    Wrapper for backward compatibility.
    Same as get_manual_tags_for_file but without slug.
    """
    return get_manual_tags_for_file(path, slug=None)


# ================================================================
# TAG BUILDING HELPERS
# ================================================================

def build_base_tags(
    *,
    media_type: str,
    rating: str,
    slug: str,
    sex_act: Optional[str] = None,
) -> List[str]:
    """
    Build the baseline tag set for a media file.
    """
    tags: List[str] = []
    
    if media_type:
        tags.append(media_type.lower())
    if rating:
        tags.append(rating.lower())
    if slug:
        tags.append(slug.lower())
    if sex_act:
        tags.append(sex_act.lower())
    
    # Remove duplicates while preserving order
    cleaned: List[str] = []
    for t in tags:
        t = t.strip().lower()
        if t and t not in cleaned:
            cleaned.append(t)
    
    return cleaned


def merge_ai_tags(base_tags: List[str], ai_suggested: List[str]) -> List[str]:
    """Merge AI-suggested tags with base tags."""
    merged = list(base_tags)
    
    for tag in ai_suggested or []:
        t = (tag or "").strip().lower()
        if not t:
            continue
        if t not in merged:
            merged.append(t)
    
    return merged


def merge_manual_tags(
    base_tags: List[str],
    file_path: Path,
    slug: Optional[str]
) -> List[str]:
    """Merge manual tags with base tags."""
    merged = list(base_tags)
    
    manual = get_manual_tags_for_file(file_path, slug)
    
    for tag in manual:
        t = (tag or "").strip().lower()
        if not t:
            continue
        if t not in merged:
            merged.append(t)
    
    return merged