# utils/rankings/formatting.py

from __future__ import annotations

import datetime
import calendar
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from collections import Counter

import discord

from .models import RankingEntry

try:
    from PIL import Image  # optional, for true dimension checking
except ImportError:  # pragma: no cover
    Image = None


JARVIS_FOOTER = "✨ JARVIS Rankings"

# Tolerance for treating an image as "square"
SQUARE_TOLERANCE_PX = 5


# ================================================================
# Small helpers
# ================================================================

def _get_rank_label(entry: RankingEntry) -> str:
    """Return the correct human-friendly rank label."""
    group = entry.group
    raw = entry.rank_raw

    if not raw:
        return "?"

    raw = str(raw).strip()

    # Group 1 uses letter ranks directly
    if group == 1:
        return raw.upper()

    # Otherwise numeric rank with '#' prefix
    # Remove accidental leading '#'
    num = raw.lstrip("#")
    if not num.isdigit():
        return "?"
    return f"#{num}"


def _get_birthplace(entry: RankingEntry) -> Optional[str]:
    bp = getattr(entry, "birthplace_display", None)
    if isinstance(bp, str) and bp.strip():
        return bp.strip()
    return None


def _get_gender(entry: RankingEntry) -> str:
    gender = getattr(entry, "gender", None) or getattr(entry, "sex", None)
    if not isinstance(gender, str):
        return "X"
    g = gender.strip().upper()
    if g.startswith("F"):
        return "F"
    if g.startswith("M"):
        return "M"
    return "X"


def _pronouns(entry: RankingEntry) -> tuple[str, str, str]:
    """
    Returns (subject, object, contraction):
      F -> ("she", "her", "she's")
      M -> ("he", "him", "he's")
      X -> ("they", "them", "they're")
    """
    g = _get_gender(entry)
    if g == "F":
        return ("she", "her", "she's")
    if g == "M":
        return ("he", "him", "he's")
    return ("they", "them", "they're")


def _format_full_date(d: Optional[datetime.date]) -> str:
    if not d:
        return "Unknown"
    return d.strftime("%B %d, %Y")


def _format_birthdate_compact(d: Optional[datetime.date]) -> str:
    if not d:
        return "????/??/??"
    return d.strftime("%Y/%m/%d")


def _age_on(entry: RankingEntry, on_date: datetime.date) -> Optional[int]:
    b = getattr(entry, "birth_date", None)
    if not isinstance(b, datetime.date):
        return None
    # Special year 1000 = unknown age (partial date)
    if b.year == 1000:
        return None
    years = on_date.year - b.year
    if (on_date.month, on_date.day) < (b.month, b.day):
        years -= 1
    return years


def _top_n_from_counter(counter: Counter, n: int = 5) -> list[tuple[str, int]]:
    return counter.most_common(n)


def _death_date(entry: RankingEntry) -> Optional[datetime.date]:
    for attr in ("date_of_death", "death_date", "dod"):
        val = getattr(entry, attr, None)
        if isinstance(val, datetime.date):
            return val
    return None


MONTH_NAMES = {
    "1": "January", "2": "February", "3": "March", "4": "April",
    "5": "May", "6": "June", "7": "July", "8": "August",
    "9": "September", "10": "October", "11": "November", "12": "December",
}

def _fix_month_names(text: str) -> str:
    # turn "month 11" or "month 11," or "month 11)" -> November
    import re
    def repl(match):
        num = match.group(1)
        return MONTH_NAMES.get(num, f"month {num}")
    return re.sub(r"month\s+(\d{1,2})", repl, text)


def _format_birthdate_for_list(d: Optional[datetime.date]) -> str:
    """
    LIST embed birthdate rules:
    - None → UNKNOWN
    - Year 1000 → MM/DD
    - Otherwise → YYYY/MM/DD
    """
    if not d:
        return "UNKNOWN"
    if d.year == 1000:
        return d.strftime("%m/%d")
    return d.strftime("%Y/%m/%d")


# ================================================================
# NEW: Enhanced profile helpers
# ================================================================

def _get_rank_tier_color(entry: RankingEntry) -> discord.Color:
    """Get color based on rank tier."""
    if entry.group == 1:
        return discord.Color.gold()  # Elite tier
    
    if entry.numeric_rank:
        if entry.numeric_rank <= 50:
            return discord.Color.from_rgb(255, 69, 0)  # Red-orange for top 50
        elif entry.numeric_rank <= 100:
            return discord.Color.purple()  # Purple for top 100
    
    return discord.Color.blue()  # Default


def _count_media_files(slug: str, media_root: Path, nsfw_allowed: bool) -> dict:
    """Count media files for a person."""
    person_root = media_root / slug
    counts = {"images": 0, "gifs": 0, "videos": 0, "favorites": 0}
    
    for media_type in ["images", "gifs", "videos"]:
        folder = person_root / media_type
        if folder.exists():
            counts[media_type] += len([f for f in folder.iterdir() if f.is_file()])
        
        if nsfw_allowed:
            nsfw_folder = folder / "nsfw"
            if nsfw_folder.exists():
                counts[media_type] += len([f for f in nsfw_folder.iterdir() if f.is_file()])
    
    # Get favorites count
    try:
        from utils.rankings.favorites import get_person_favorite_totals
        totals = get_person_favorite_totals()
        counts["favorites"] = totals.get(slug, 0)
    except Exception:
        pass  # Favorites system not available
    
    return counts


def _calculate_days_old_rank(entry: RankingEntry, all_entries: List[RankingEntry]) -> Optional[Tuple[int, int, bool]]:
    """
    Calculate rank by age in days.
    
    Returns:
        (rank, total, use_youngest) where:
        - rank: position in age ranking
        - total: total people with known ages
        - use_youngest: True if should display as "youngest" instead of "oldest"
    """
    if not entry.birth_date or entry.birth_date.year == 1000:
        return None
    
    today = datetime.date.today()
    entry_days = (today - entry.birth_date).days
    
    # Get all people with known birth dates
    aged_people = [
        e for e in all_entries
        if e.birth_date and e.birth_date.year != 1000
    ]
    
    if not aged_people:
        return None
    
    # Sort by age (oldest first)
    aged_people.sort(key=lambda e: (today - e.birth_date).days, reverse=True)
    
    total = len(aged_people)
    oldest_rank = aged_people.index(entry) + 1  # 1-based
    
    # Halfway point: switch from "oldest" to "youngest"
    halfway = total / 2
    
    if oldest_rank <= halfway:
        # In older half - use "oldest"
        return (oldest_rank, total, False)
    else:
        # In younger half - use "youngest"
        youngest_rank = total - oldest_rank + 1
        return (youngest_rank, total, True)


def _calculate_percentile(entry: RankingEntry, all_entries: List[RankingEntry]) -> Optional[float]:
    """Calculate what percentile this person ranks in."""
    if entry.group == 1 or not entry.numeric_rank:
        return None
    
    # Count numeric ranks only
    numeric_entries = [e for e in all_entries if e.numeric_rank]
    if not numeric_entries:
        return None
    
    total = len(numeric_entries)
    better_than = total - entry.numeric_rank
    
    return (better_than / total) * 100


def _get_location_rank(entry: RankingEntry, all_entries: List[RankingEntry]) -> Optional[str]:
    """Get ranking within location (city/state/country)."""
    if not entry.birth_city and not entry.birth_state and not entry.birth_country:
        return None
    
    # Try to find others from same location
    location = entry.birth_city or entry.birth_state or entry.birth_country
    same_location = [
        e for e in all_entries
        if (e.birth_city == location or e.birth_state == location or e.birth_country == location)
        and e.numeric_rank
    ]
    
    if len(same_location) <= 1:
        return None
    
    # Sort by rank
    same_location.sort(key=lambda e: (e.group, e.numeric_rank or 99999))
    
    try:
        rank = same_location.index(entry) + 1
        if rank == 1:
            return f"Highest ranked from {location}"
        else:
            return f"#{rank} of {len(same_location)} from {location}"
    except ValueError:
        return None


# ================================================================
# Hero image selection (dimension-based, 5px tolerance)
# ================================================================

def _is_squareish(path: Path) -> bool:
    if Image is None:
        # If Pillow is not installed, just treat everything as usable.
        return True
    try:
        with Image.open(path) as im:
            w, h = im.size
        return abs(w - h) <= SQUARE_TOLERANCE_PX
    except Exception:
        return False


def _gather_media_files(person_root: Path, nsfw_allowed: bool) -> List[Path]:
    """Collect candidate media files for a person."""
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    type_dirs = ["images", "ai", "gifs"]
    candidates: List[Path] = []

    for t in type_dirs:
        base = person_root / t
        if base.is_dir():
            for p in base.iterdir():
                if p.is_file() and p.suffix.lower() in exts:
                    candidates.append(p)

            if nsfw_allowed:
                nsfw_dir = base / "nsfw"
                if nsfw_dir.is_dir():
                    for p in nsfw_dir.iterdir():
                        if p.is_file() and p.suffix.lower() in exts:
                            candidates.append(p)

    return candidates


def _pick_hero_file(
    entry: RankingEntry,
    nsfw_allowed: bool,
    media_root: Optional[Path],
) -> Optional[discord.File]:
    """
    Pick a random square-ish hero file for this person, based on dimensions.

    - Prefer square-ish images (± 5px tolerance).
    - If no square-ish images exist, fall back to any image.
    - If no media at all exists, fall back to media/defaults/no-image.*.
    """
    if media_root is None:
        return None

    slug = getattr(entry, "slug", None)
    person_root = Path(media_root) / slug if slug else None

    candidates: List[Path] = []
    if person_root and person_root.is_dir():
        candidates = _gather_media_files(person_root, nsfw_allowed)

    # If nothing found yet, try global default
    if not candidates:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            default_path = Path(media_root) / "defaults" / f"no-image{ext}"
            if default_path.is_file():
                return discord.File(str(default_path), filename=default_path.name)
        return None  # last resort: no file

    import random
    squareish = [p for p in candidates if _is_squareish(p)]
    pool = squareish or candidates
    chosen = random.choice(pool)
    return discord.File(str(chosen), filename=chosen.name)


def _pick_profile_thumbnail(
    entry: RankingEntry,
    media_root: Optional[Path],
) -> Optional[discord.File]:
    """
    Pick profile thumbnail (profile.jpg, profile.png, profile.webp).
    This shows in the top-right corner of the embed.
    """
    if media_root is None:
        return None
        
    slug = getattr(entry, "slug", None)
    if not slug:
        return None
        
    person_root = Path(media_root) / slug
    
    for ext in [".webp", ".png", ".jpg", ".jpeg"]:
        profile_path = person_root / f"profile{ext}"
        if profile_path.exists():
            return discord.File(str(profile_path), filename=f"profile{ext}")
    
    return None


# ================================================================
# Profile and birthday embeds
# ================================================================

async def build_profile_embed(
    entry: RankingEntry,
    *,
    nsfw_allowed: bool,
    media_root: Optional[Path] = None,
    fun_facts: Optional[List[str]] = None,
    kobold_insights: Optional[List[str]] = None,
    on_date: Optional[datetime.date] = None,
    all_entries: Optional[List[RankingEntry]] = None,
) -> Tuple[discord.Embed, Optional[discord.File], Optional[discord.File]]:
    """
    Build a profile-style embed with enhanced stats.

    Returns: (embed, hero_file, thumbnail_file)
    - If on_date is provided -> birthday layout (used by /rank today & autopost).
    - Otherwise -> generic profile layout (used by search/view/random).
    """
    rank_label = _get_rank_label(entry)
    name = getattr(entry, "name", "Unknown")
    birthplace = _get_birthplace(entry)

    today = on_date or datetime.date.today()
    birth_date = getattr(entry, "birth_date", None)
    death = _death_date(entry)
    age = _age_on(entry, today)
    subj, obj, be = _pronouns(entry)

    # Get tier color
    color = _get_rank_tier_color(entry)

    # ---------------- Birthday / memorial layout ----------------
    if on_date is not None:
        if death:
            title_prefix = "🕊"
        else:
            title_prefix = "🎉"

        title = f"{title_prefix} {name} • Rank {rank_label}"
        embed = discord.Embed(title=title, color=color)

        lines: List[str] = []

        if birth_date:
            # Year unknown: 1000/MM/DD
            if birth_date.year == 1000:
                lines.append("🎉 Her exact age is unknown, but today *is* her birthday!")
            else:
                if death:
                    death_str = _format_full_date(death)
                    if age is not None:
                        lines.append(
                            f"🕯 Born {birth_date.year} — Died {death_str}, {subj} would have turned {age} today. Rest in peace."
                        )
                    else:
                        lines.append(
                            f"🕯 Born {birth_date.year} — Died {death_str}. Rest in peace."
                        )
                else:
                    if age is not None:
                        lines.append(f"🎂 Born in {birth_date.year}, {be} turning {age} today!")
                    else:
                        lines.append("🎉 Birthday today!")

        if birthplace:
            lines.append(f"📍 *Born in {birthplace}*")

        embed.description = "\n".join(lines)

    # ---------------- Generic profile layout ----------------
    else:
        # Enhanced title with emoji
        group_emoji = "👑" if entry.group == 1 else "🏆"
        title = f"{group_emoji} Rank {rank_label} • {name}"
        embed = discord.Embed(title=title, color=color)

        if birth_date:
            born_str = _format_full_date(birth_date)
            if death and age is not None:
                age_text = f"{born_str} — Died: {_format_full_date(death)} (they would be {age})"
            elif age is not None:
                age_text = f"{born_str} (currently {age})"
            else:
                age_text = born_str

            embed.add_field(name="Age — Born:", value=age_text, inline=False)

        if birthplace:
            embed.add_field(name="From:", value=birthplace, inline=False)

    # ---------------- Fun Facts ----------------
    if fun_facts:
        subj, obj, be = _pronouns(entry)
        name = getattr(entry, "name", "")

        processed = []
        for fact in fun_facts:
            # Replace name with pronoun
            f = fact.replace(name, subj)
            f = _fix_month_names(f)
            
            # Strip any existing bullets (including corrupted UTF-8 ones)
            f = f.lstrip('•\u2022\u00e2\u20ac\u00a2 ').strip()
            
            # Add clean bullet
            processed.append(f"• {f}")

        embed.add_field(name="Fun Facts", value="\n".join(processed), inline=False)

    # ---------------- Kobold Insights (optional) ----------------
    if kobold_insights:
        insights_text = "\n".join(f"• {t}" for t in kobold_insights)
        embed.add_field(name="Kobold Insights", value=insights_text, inline=False)


    # ---------------- NEW: Media Gallery Stats ----------------
    if media_root:
        slug = getattr(entry, "slug", None)
        if slug:
            media_counts = _count_media_files(slug, media_root, nsfw_allowed)
            
            media_parts = []
            if media_counts["images"] > 0:
                media_parts.append(f"{media_counts['images']} images")
            if media_counts["gifs"] > 0:
                media_parts.append(f"{media_counts['gifs']} GIFs")
            if media_counts["videos"] > 0:
                media_parts.append(f"{media_counts['videos']} videos")
            if media_counts["favorites"] > 0:
                media_parts.append(f"❤️ {media_counts['favorites']} favorites")
            
            if media_parts:
                media_text = " • ".join(media_parts)
                # Add line break before header for mobile spacing
                embed.add_field(name="\n📸 Media Gallery", value=media_text, inline=False)

    # Build footer with JARVIS branding first, then days old
    footer_parts: List[str] = []
    if JARVIS_FOOTER:
        footer_parts.append(JARVIS_FOOTER)
              
    if birth_date and birth_date.year != 1000 and all_entries:
        death_date = getattr(entry, "death_date", None)
        if death_date and death_date.year != 1:
            # Deceased: show age at death
            days_lived = (death_date - birth_date).days
            footer_parts.append(f"Lived {days_lived:,} days")
        else:
            # Living: show current age and rank
            days_old = (today - birth_date).days
            age_rank_data = _calculate_days_old_rank(entry, all_entries)
            if age_rank_data:
                rank, total, use_youngest = age_rank_data
                if use_youngest:
                    footer_parts.append(f"{days_old:,} days old (#{rank} youngest)")
                else:
                    footer_parts.append(f"{days_old:,} days old (#{rank} oldest)")
            else:
                footer_parts.append(f"{days_old:,} days old")
    
    footer_text = " • ".join(footer_parts) if footer_parts else ""
    embed.set_footer(text=footer_text)

    # Get hero image only (no thumbnail)
    hero_file = _pick_hero_file(entry, nsfw_allowed=nsfw_allowed, media_root=media_root)
    thumbnail_file = None  # Never use thumbnails
    
    if hero_file is not None:
        embed.set_image(url=f"attachment://{hero_file.filename}")

    return embed, hero_file, thumbnail_file


# ================================================================
# LIST EMBEDS (for /rank born, /rank country, etc.)
# ================================================================

def _rank_sort_key(entry: RankingEntry):
    """
    Sort key used for list embeds.

    - Primary: group (1–8)
    - Secondary: rank within group
        * Group 1 uses letter ranks A–Z.
        * Groups 2+ use numeric rank_raw (e.g. '5', '#12').
    - Tertiary: name (for stability)
    """
    group = getattr(entry, "group", 99) or 99
    rank_raw = getattr(entry, "rank_raw", None)
    name = getattr(entry, "name", "") or ""

    num = 99999

    if group == 1 and isinstance(rank_raw, str):
        s = rank_raw.strip().upper()
        if len(s) == 1 and "A" <= s <= "Z":
            num = ord(s) - ord("A") + 1
    else:
        try:
            s = str(rank_raw or "")
            # accept "5", "#5", "05", etc.
            s = s.lstrip("#")
            num = int(s)
        except Exception:
            num = 99999

    return (group, num, name.upper())


def _group_entries_by_age(
    entries: List[RankingEntry],
    *,
    on_date: datetime.date,
) -> dict[int, List[RankingEntry]]:
    """
    Group entries by exact age.

    - Age calculated using _age_on
    - Entries with unknown age are skipped
    - Buckets sorted oldest → youngest
    """
    buckets: dict[int, List[RankingEntry]] = {}

    for e in entries:
        age = _age_on(e, on_date)
        if age is None:
            continue
        buckets.setdefault(age, []).append(e)

    # Oldest first
    return dict(sorted(buckets.items(), reverse=True))


def _paginate_age_buckets(
    entries: List[RankingEntry],
    *,
    on_date: datetime.date,
    page_size: int = 25,
) -> List[List[Tuple[int, List[RankingEntry]]]]:
    """
    Paginate entries grouped by exact age WITHOUT splitting age buckets.

    Returns:
        pages -> [
            [ (age, [entries...]), (age, [entries...]) ],   # page 1
            [ (age, [entries...]) ],                        # page 2
            ...
        ]

    Rules:
    - Age buckets = exact age numbers
    - Bucket order = youngest → oldest
    - Entries inside each bucket = rank-sorted
    - A bucket is never split across pages
    - A page may exceed page_size if a single bucket is larger
    """

    # Step 1: group by age
    buckets = _group_entries_by_age(entries, on_date=on_date)

    # We want youngest → oldest for display
    ordered_ages = sorted(buckets.keys())

    # Step 2: sort entries inside each bucket by rank
    for age in ordered_ages:
        buckets[age].sort(key=_rank_sort_key)

    pages: List[List[Tuple[int, List[RankingEntry]]]] = []
    current_page: List[Tuple[int, List[RankingEntry]]] = []
    current_count = 0

    for age in ordered_ages:
        bucket = buckets[age]
        bucket_size = len(bucket)

        # If adding this bucket would overflow the page,
        # start a new page (unless page is empty)
        if current_page and current_count + bucket_size > page_size:
            pages.append(current_page)
            current_page = []
            current_count = 0

        current_page.append((age, bucket))
        current_count += bucket_size

    if current_page:
        pages.append(current_page)

    return pages

def compute_age_stats(
    entries: list[RankingEntry],
    *,
    on_date: datetime.date,
) -> dict:
    ages: list[tuple[int, RankingEntry]] = []

    for e in entries:
        age = _age_on(e, on_date)
        if age is not None:
            ages.append((age, e))

    if not ages:
        return {
            "ages": [],
            "youngest": None,
            "oldest": None,
        }

    return {
        "ages": ages,
        "youngest": min(ages, key=lambda x: x[0]),
        "oldest": max(ages, key=lambda x: x[0]),
    }

async def build_list_embed(
    entries: Iterable[RankingEntry],
    *,
    title: str,
    nsfw_allowed: bool,
    media_root: Optional[Path] = None,
    context: str = "default",
    full_list_stats: Optional[dict] = None,
) -> Tuple[discord.Embed, Optional[discord.File]]:
    """
    Build the list-style embed with stats header and aligned formatting.

    Supports:
    - Rank (default)
    - Date sorting (handled upstream)
    - Age grouping (handled via full_list_stats + caller intent)
    """

    entries_list = list(entries)

    if not entries_list:
        embed = discord.Embed(title=title, description="*(no results)*")
        if JARVIS_FOOTER:
            embed.set_footer(text=JARVIS_FOOTER)
        return embed, None

    today = datetime.date.today()

    # --------------------------------------------------
    # HIGHEST-RANKED ENTRY (GLOBAL, NOT PAGE-LOCAL)
    # --------------------------------------------------

    highest_entry = None

    if entries_list:
        highest_entry = min(
            entries_list,
            key=lambda e: e.sort_key_rank_only
        )

    # ------------------------------------------------------------
    # Header
    # ------------------------------------------------------------

    header_lines: List[str] = []

    month_counts = None
    year_counts = None

    if full_list_stats:
        month_counts = full_list_stats.get("month_counts")
        year_counts = full_list_stats.get("year_counts")

    # DEFAULT list embeds
    if context == "default":
        if month_counts:
            month, count = month_counts.most_common(1)[0]
            header_lines.append(
                f"🎂 **Most Common Month:** {month} ({count} people)"
            )

        if year_counts:
            decades = Counter((y // 10) * 10 for y in full_list_stats.get("birth_years", []))
            decade_str = ", ".join(
                f"{d}s ({c})" for d, c in sorted(decades.items())
            )
            header_lines.append(
                f"📊 **Decades:** {decade_str}"
            )

    # /rank month
    elif context == "month":
        if year_counts:
            year, count = year_counts.most_common(1)[0]
            header_lines.append(
                f"📅 **Most Common Year:** {year} ({count} people)"
            )

        if year_counts:
            decades = Counter((y // 10) * 10 for y in full_list_stats.get("birth_years", []))
            decade_str = ", ".join(
                f"{d}s ({c})" for d, c in sorted(decades.items())
            )
            header_lines.append(
                f"📊 **Decades:** {decade_str}"
            )

    # /rank year - NO year/decade stats
    elif context == "year":
        if month_counts:
            month_num, count = month_counts.most_common(1)[0]
            month = calendar.month_name[month_num]
            header_lines.append(
                f"🎂 **Most Common Month:** {month} ({count} people)"
            )

    # /rank decade
    elif context == "decade":
        if month_counts:
            month_num, count = month_counts.most_common(1)[0]
            month = calendar.month_name[month_num]
            header_lines.append(
                f"🎂 **Most Common Month:** {month} ({count} people)"
            )

        if year_counts:
            year, count = year_counts.most_common(1)[0]
            header_lines.append(
                f"📅 **Most Common Year:** {year} ({count} people)"
            )

    # /rank born before|after - Show year/decade stats
    elif context in ("born_before", "born_after"):
        if month_counts:
            month_num, count = month_counts.most_common(1)[0]
            month = calendar.month_name[month_num]
            header_lines.append(
                f"🎂 **Most Common Month:** {month} ({count} people)"
            )

        if year_counts:
            year, count = year_counts.most_common(1)[0]
            header_lines.append(
                f"📅 **Most Common Year:** {year} ({count} people)"
            )

        if year_counts:
            decades = Counter((y // 10) * 10 for y in full_list_stats.get("birth_years", []))
            decade_str = ", ".join(
                f"{d}s ({c})" for d, c in sorted(decades.items())
            )
            header_lines.append(
                f"📊 **Decades:** {decade_str}"
            )

    # Youngest / Oldest (always shown if available)
    if full_list_stats:
        youngest = full_list_stats.get("youngest")
        oldest = full_list_stats.get("oldest")

        if youngest:
            age, entry = youngest
            header_lines.append(
                f"\n🌟 **Youngest:** {entry.name} ({age})"
            )

        if oldest:
            age, entry = oldest
            header_lines.append(
                f"🌙 **Oldest:** {entry.name} ({age})"
            )

        if full_list_stats:
            month_counts = full_list_stats.get("month_counts")
            year_counts = full_list_stats.get("year_counts")    

    # ------------------------------------------------------------
    # STATE / PROVINCE HEADER STATS
    # ------------------------------------------------------------
    if context == "state" and full_list_stats:
        total_people = full_list_stats.get("total_people", 0)
        states = full_list_stats.get("states", [])
        
        if header_lines:
            header_lines.append("")

        header_lines.append(
            f"🌎 **{total_people} people** • 🗺️ **{len(set(states))} states/provinces**"
        )

        state_counts = Counter(states)
        top_states = _top_n_from_counter(state_counts, 5)

        if top_states:
            header_lines.append("")  # spacing
            header_lines.append("**Top States / Provinces**")
            for name, count in top_states:
                header_lines.append(f"`{name:<20} {count:>3} people`")

    # ------------------------------------------------------------
    # Body (rank-ordered flat list)
    # ------------------------------------------------------------

    list_lines: List[str] = []

    RANK_SECTION_WIDTH = 5
    FIXED_NAME_WIDTH = 24

    for e in entries_list:
        rank_label = _get_rank_label(e)
        name = e.name
        date_str = _format_birthdate_for_list(getattr(e, "birth_date", None))

        if not rank_label.startswith("#"):
            rank_label = f"#{rank_label}"

        if len(name) > FIXED_NAME_WIDTH:
            name = name[: FIXED_NAME_WIDTH - 1] + "…"

        rank_padded = rank_label.ljust(RANK_SECTION_WIDTH)
        name_padded = name.ljust(FIXED_NAME_WIDTH)

        mono = f"{rank_padded} {name_padded} {date_str}"
        list_lines.append(f"`{mono}`")

    # ------------------------------------------------------------
    # Assemble embed
    # ------------------------------------------------------------

    description = (
        "\n".join(header_lines) + "\n\n" + "\n".join(list_lines)
        if header_lines
        else "\n".join(list_lines)
    )

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue(),
    )

    footer_parts: List[str] = []

    if JARVIS_FOOTER:
        footer_parts.append(JARVIS_FOOTER)

    if full_list_stats:
        ages = full_list_stats.get("ages", [])
        highest_entry = full_list_stats.get("highest_entry")

        if ages:
            age_vals = [a for a, _ in ages]
            avg_age = sum(age_vals) / len(age_vals)
            min_age = min(age_vals)
            max_age = max(age_vals)

            top_rank = _get_rank_label(highest_entry) if highest_entry else "N/A"
            footer_parts.append(
                f"Ages: {min_age}-{max_age} | Avg: {avg_age:.1f} | Top: {top_rank}"
            )

    if footer_parts:
        embed.set_footer(text=" • ".join(footer_parts))

    hero_file = _pick_hero_file(
        entries_list[0],
        nsfw_allowed=nsfw_allowed,
        media_root=media_root,
    )

    if hero_file:
        embed.set_image(url=f"attachment://{hero_file.filename}")

    return embed, hero_file
