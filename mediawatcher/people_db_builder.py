# utils/mediawatcher/people_db_builder.py

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple
import logging

import config
from utils.mediawatcher.slug_engine import PEOPLE_PATH, ALIASES_PATH

log = logging.getLogger(__name__)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def slugify_name(name: str) -> str:
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    out = []
    for ch in name.lower():
        out.append(ch if ch.isalnum() else "-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def normalize_alias_key(alias: str) -> str:
    alias = (alias or "").strip()
    if not alias:
        return ""
    alias = unicodedata.normalize("NFKD", alias)
    alias = "".join(c for c in alias if not unicodedata.combining(c))
    cleaned = []
    for ch in alias.lower():
        if ch.isalnum() or ch in {" ", "_", "@"}:
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    cleaned = " ".join("".join(cleaned).split())
    return cleaned


def _lower_header_index(header: Sequence[str]) -> Dict[str, int]:
    idx = {}
    for i, col in enumerate(header):
        if col:
            idx[col.strip().lower()] = i
    return idx


def _get(row: Sequence[str], idx: Dict[str, int], key: str) -> str:
    i = idx.get(key.lower())
    if i is None or i >= len(row):
        return ""
    val = row[i]
    return val.strip() if isinstance(val, str) else str(val)


# ------------------------------------------------------------
# MAIN BUILDER
# ------------------------------------------------------------

def build_people_and_alias_db_from_rows(
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """
    Build people.json + aliases.json from Google Sheets metadata.
    """
    if not header:
        raise ValueError("Header row is empty.")

    header_idx = _lower_header_index(header)

    people: Dict[str, Dict[str, Any]] = {}
    aliases: Dict[str, str] = {}

    for row in rows:
        row = list(row) + [""] * (len(header) - len(row))
        name = _get(row, header_idx, "name")
        if not name:
            continue

        slug = slugify_name(name)
        if not slug:
            continue

        person = people.get(slug, {"slug": slug, "primary_name": name})

        # Basic fields
        person["rank"] = _get(row, header_idx, "rank") or person.get("rank")
        group_raw = _get(row, header_idx, "group")
        if group_raw:
            try:
                person["group"] = int(group_raw)
            except:
                person["group"] = group_raw

        # Details field (AS1)
        details = _get(row, header_idx, "details")
        if details:
            person["details"] = details

        # Bluesky handles (AT1)
        bluesky_raw = _get(row, header_idx, "bluesky")
        if bluesky_raw:
            handles = [h.strip() for h in bluesky_raw.split(",") if h.strip()]
            person["bluesky_handles"] = sorted(
                set(person.get("bluesky_handles", [])) | set(handles)
            )

        # Optional metadata fields
        optional_fields = [
            "birthdate", "place_of_birth", "gender",
            "tmdb_id", "imdb_id", "wikidata_qid", "instagram", "twitter",
            "facebook", "youtube", "tiktok", "official_site", "iafd_url",
            "fansly", "onlyfans", "nationality", "occupations",
            "known_for", "wikipedia_url", "reddit_subs", "summary_tags",
            "notes", "height", "build", "frame", "shoulders", "chest",
            "waist", "hips", "glutes", "leg_proportions", "facial_shape",
            "eyes", "nose", "lips", "hair", "distinguishing_features",
        ]

        for f in optional_fields:
            v = _get(row, header_idx, f)
            if v:
                person[f] = v

        # Auto-generated aliases
        alias_set = set(person.get("aliases", []))
        alias_set.add(name)
        alias_set.add(name.replace("-", " "))
        alias_set.add(name.replace("'", ""))
        alias_set.add(slug.replace("-", " "))

        # Also add Bluesky handles as aliases
        for h in person.get("bluesky_handles", []):
            alias_set.add(h)
            seg = h.split("/")[-1]
            seg = seg.split("?")[0]
            alias_set.add(seg)
            if ".bsky." in seg:
                alias_set.add(seg.split(".")[0])

        person["aliases"] = sorted(a for a in alias_set if a)

        people[slug] = person

    # Build alias lookup table
    for slug, person in people.items():
        for a in person.get("aliases", []):
            key = normalize_alias_key(a)
            if not key:
                continue
            if key not in aliases:  # first one wins
                aliases[key] = slug

    # ------------------------------------------------------------
    # BACKUP OLD FILES (this is the CORRECT place for backup)
    # ------------------------------------------------------------
    backup_people = PEOPLE_PATH.with_suffix(".json.bak")
    backup_aliases = ALIASES_PATH.with_suffix(".json.bak")

    try:
        if PEOPLE_PATH.exists():
            PEOPLE_PATH.replace(backup_people)
        if ALIASES_PATH.exists():
            ALIASES_PATH.replace(backup_aliases)
    except Exception as e:
        log.warning(f"[MediaWatcher] Backup creation failed but continuing: {e}")

    # ------------------------------------------------------------
    # WRITE NEW FILES
    # ------------------------------------------------------------
    PEOPLE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with PEOPLE_PATH.open("w", encoding="utf-8") as f:
        json.dump(people, f, indent=2, ensure_ascii=False)

    with ALIASES_PATH.open("w", encoding="utf-8") as f:
        json.dump(aliases, f, indent=2, ensure_ascii=False)

    log.info(
        "[MediaWatcher] Wrote %d people and %d aliases.",
        len(people), len(aliases)
    )

    return people, aliases
