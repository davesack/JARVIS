"""
Rankings favorites storage & query helpers.

This module is intentionally "dumb":
- No Discord logic
- No reaction handling
- No preview resolution
- No slug guessing

It simply reads the canonical favorites data written by
cogs/rankings_favorites.py.

Data model (JSON):
{
  "files": {
    "slug-name/images/foo.webp": 5,
    "slug-name/videos/bar.mp4": 12
  },
  "people": {
    "slug-name": 17
  }
}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from config import DATA_ROOT, MEDIA_ROOT


# ============================================================
# STORAGE
# ============================================================

FAVORITES_FILE = DATA_ROOT / "rankings_favorites.json"


def _load() -> dict:
    if FAVORITES_FILE.exists():
        try:
            return json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "files": {},    # rel_path -> count
        "people": {},  # slug -> total count
    }


def _save(data: dict) -> None:
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    FAVORITES_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ============================================================
# READ API (USED BY RANKINGS COMMANDS)
# ============================================================

def get_file_favorites() -> Dict[str, int]:
    """
    Return mapping of relative media path -> favorite count.
    """
    data = _load()
    return dict(data.get("files", {}))


def get_person_favorite_totals() -> Dict[str, int]:
    """
    Return mapping of slug -> total favorites across all media.
    """
    data = _load()
    return dict(data.get("people", {}))


def get_favorites_for_slug(slug: str) -> List[Tuple[Path, int]]:
    """
    Get all favorited media files for a specific person (slug).
    
    Returns:
        List of (absolute_path, count), sorted by count DESC.
        Missing files are silently skipped.
    """
    data = _load()
    results: List[Tuple[Path, int]] = []
    
    for rel_path, count in data.get("files", {}).items():
        # Handle both forward slash (/) and backslash (\) for cross-platform compatibility
        # Normalize to forward slash for comparison
        normalized_path = rel_path.replace("\\", "/")
        
        if not normalized_path.startswith(f"{slug}/"):
            continue
        
        # Use original rel_path for file lookup (Path handles platform differences)
        full_path = MEDIA_ROOT / rel_path
        if full_path.exists():
            results.append((full_path, count))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def get_top_favorited_media(limit: int = 10) -> List[Tuple[Path, int]]:
    """
    Get the top favorited media files across ALL people.
    
    Returns:
        List of (absolute_path, count), sorted DESC.
    """
    data = _load()
    items: List[Tuple[Path, int]] = []
    
    for rel_path, count in data.get("files", {}).items():
        full_path = MEDIA_ROOT / rel_path
        if full_path.exists():
            items.append((full_path, count))
    
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:limit]


def get_top_favorited_people(limit: int = 10) -> List[Tuple[str, int]]:
    """
    Get the most favorited people by total ðŸ”¥ count.
    
    Returns:
        List of (slug, total_count), sorted DESC.
    """
    data = _load()
    people = list(data.get("people", {}).items())
    people.sort(key=lambda x: x[1], reverse=True)
    return people[:limit]




def get_top_favorited_by_type(media_type: str, limit: int = 10) -> List[Tuple[Path, int]]:
    """
    Get the top favorited media files of a specific type.
    
    Args:
        media_type: 'images', 'gifs', or 'videos'
        limit: Maximum number of results
    
    Returns:
        List of (absolute_path, count), sorted DESC.
    """
    data = _load()
    items: List[Tuple[Path, int]] = []
    
    for rel_path, count in data.get("files", {}).items():
        full_path = MEDIA_ROOT / rel_path
        if not full_path.exists():
            continue
        
        # Check if path matches the media type
        path_str = str(full_path).lower()
        
        if media_type == "images":
            # Images are in /images/ folder and not .gif
            if "/images/" in path_str and not path_str.endswith(".gif"):
                items.append((full_path, count))
        
        elif media_type == "gifs":
            # GIFs are in /gifs/ folder OR end with .gif
            if "/gifs/" in path_str or path_str.endswith(".gif"):
                items.append((full_path, count))
        
        elif media_type == "videos":
            # Videos are in /videos/ folder
            if "/videos/" in path_str:
                items.append((full_path, count))
    
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:limit]


def get_favorite_stats_overview() -> Dict[str, int]:
    """
    Get overview statistics of all favorites.
    
    Returns:
        Dictionary with stats:
        - total_slugs: Number of people with favorites
        - total_files: Total number of favorited files
        - total_favorites: Sum of all favorite counts
        - most_favorites: Highest single-file favorite count
    """
    data = _load()
    
    stats = {
        "total_slugs": len(data.get("people", {})),
        "total_files": len(data.get("files", {})),
        "total_favorites": sum(data.get("people", {}).values()),
        "most_favorites": max(data.get("files", {}).values(), default=0),
    }
    
    return stats


# Alias for backwards compatibility
def get_top_favorited_files(limit: int = 10) -> List[Tuple[Path, int]]:
    """
    Alias for get_top_favorited_media().
    
    Get the top favorited media files across ALL people.
    
    Returns:
        List of (absolute_path, count), sorted DESC.
    """
    return get_top_favorited_media(limit)


# ============================================================
# MAINTENANCE / DEBUG HELPERS (OPTIONAL)
# ============================================================

def clear_all_favorites() -> None:
    """
    DANGER: Completely reset all favorites.
    Intended for admin/debug use only.
    """
    _save(
        {
            "files": {},
            "people": {},
        }
    )
