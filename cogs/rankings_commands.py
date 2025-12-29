# cogs/rankings_commands.py
"""
Complete Rankings command system with:
- Beautiful lists with context colors
- Advanced pagination with jump-to-page
- Age sorting with smart grouping
- Group 1 gating across all commands
- Favorites system with ❥ reactions
- All list and media commands
"""

from __future__ import annotations

import datetime
import random
from pathlib import Path
from typing import Callable, Generic, List, Sequence, Optional, Tuple, TypeVar

import discord
from discord import app_commands, ui
from discord.ext import commands

from config import MEDIA_ROOT, CHANNEL_NO_GROUP1
from utils.rankings.loader import RankingsLoader
from utils.rankings.models import RankingEntry
from utils.rankings.formatting import (
    build_profile_embed, 
    build_list_embed, 
    _age_on, 
    _rank_sort_key,
    _get_rank_label,
    _format_birthdate_for_list,
    JARVIS_FOOTER,
    compute_age_stats,
)
from utils.rankings.pagination import send_paginated
from utils.rankings.fun_facts import generate_fun_facts
from utils.rankings.favorites import get_favorites_for_slug

T = TypeVar("T")

# Month name mappings
MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def _parse_month(text: str) -> Optional[int]:
    """Parse month name or number to month int (1-12)."""
    text = text.lower().strip()
    
    try:
        month = int(text)
        if 1 <= month <= 12:
            return month
    except ValueError:
        pass
    
    return MONTH_NAMES.get(text)

# ================================================================
# NYC Borough Normalization
# ================================================================

def _normalize_city_label(city: str, state: str, country: str) -> str:
    """
    Normalize city labels, especially for NYC boroughs.
    
    Handles full strings like "Manhattan, New York City, New York, USA"
    """
    NYC_BOROUGHS = [
        "manhattan",
        "brooklyn",
        "bronx",
        "queens",
        "staten island",
    ]
    
    # Normalize inputs
    city_lower = (city or "").lower().strip()
    state_lower = (state or "").lower().strip()
    country_lower = (country or "").lower().strip()
    
    # Check if the CITY field contains the full address
    # e.g., "Manhattan, New York City, New York, USA"
    if "," in city_lower:
        # Split and check first part
        city_first_part = city_lower.split(',')[0].strip()
        
        # Check if it starts with a borough
        for borough in NYC_BOROUGHS:
            if city_first_part == borough:
                return "New York City, New York"
        
        # Check if it contains "new york city" anywhere
        if "new york city" in city_lower:
            return "New York City, New York"
    
    # Check if state indicates New York (when columns are properly split)
    if state_lower in ("new york", "ny"):
        city_first_part = city_lower.split(',')[0].strip()
        
        for borough in NYC_BOROUGHS:
            if city_first_part == borough or borough in city_lower:
                return "New York City, New York"
        
        if "new york city" in city_lower or city_lower == "new york" or "nyc" in city_lower:
            return "New York City, New York"
    
    # Standard format
    if state:
        return f"{city}, {state}"
    elif country:
        return f"{city}, {country}"
    else:
        return city

    
def _sort_entries(
    entries: List[RankingEntry],
    sort_by: Optional[str],
    today: datetime.date,
) -> List[RankingEntry]:
    """
    Sort entries based on mode.
    
    - None or "rank": By rank (default)
    - "chronological": By birthdate, oldest → youngest
    - "date": By birthday (month/day), Jan 1 → Dec 31
    - "age": Returns unsorted (caller handles age bucketing)
    """
    if sort_by == "chronological":
        # Sort by full birthdate, oldest first
        # Unknowns go to end
        return sorted(
            entries,
            key=lambda e: e.birth_date if (e.birth_date and e.birth_date.year not in (1, 1000)) else datetime.date.max
        )
    
    elif sort_by == "date":
        # Sort by month/day only, Jan 1 → Dec 31
        # Unknowns grouped at end
        known = []
        unknown = []
        
        for e in entries:
            if e.birth_date and e.birth_date.year not in (1, 1000):
                known.append(e)
            else:
                unknown.append(e)
        
        known.sort(key=lambda e: (e.birth_date.month, e.birth_date.day))
        unknown.sort(key=_rank_sort_key)
        
        return known + unknown
    
    elif sort_by == "age":
        # Don't sort here - caller will handle age bucketing
        return entries
    
    else:
        # Default: rank order
        return sorted(entries, key=lambda e: e.sort_key_rank_only)

# ================================================================
# Autocomplete for sort_by options
# ================================================================

async def autocomplete_sort_by(interaction: discord.Interaction, current: str):
    """
    Autocomplete for sort options:
    - Chronological: Oldest → Youngest (actual age order)
    - By Birthday: Jan 1 → Dec 31 (calendar order)
    - By Age: Age groups, youngest → oldest
    
    Default (no selection) is always RANK ORDER
    """
    choices = [
        app_commands.Choice(name="Chronological (Oldest → Youngest)", value="chronological"),
        app_commands.Choice(name="By Birthday (Jan → Dec)", value="date"),
        app_commands.Choice(name="By Age Groups", value="age"),
    ]
    return [c for c in choices if current.lower() in c.name.lower()]


# ================================================================
# STANDALONE AUTOCOMPLETE FUNCTIONS (for proper decorator usage)
# ================================================================

async def autocomplete_names(interaction: discord.Interaction, current: str):
    """Autocomplete names with Group 1 gating."""
    cog = interaction.client.get_cog("RankingsCog")
    if not cog:
        return []
    
    group1_ok = cog.group1_allowed(interaction)
    cur = current.lower().strip()
    out: List[app_commands.Choice[str]] = []
    
    for e in cog.loader.entries:
        if not group1_ok and e.group == 1:
            continue
        if cur in e.name.lower():
            out.append(app_commands.Choice(name=e.name, value=e.name))
        if len(out) >= 25:
            break
    return out


async def autocomplete_ranks(interaction: discord.Interaction, current: str):
    """Autocomplete ranks with Group 1 gating."""
    cog = interaction.client.get_cog("RankingsCog")
    if not cog:
        return []
    
    group1_ok = cog.group1_allowed(interaction)
    cur = current.lower().strip()
    out: List[app_commands.Choice[str]] = []
    
    seen_ranks = set()
    for e in cog.loader.entries:
        if not group1_ok and e.group == 1:
            continue
        rank_str = e.rank_raw
        if rank_str and rank_str not in seen_ranks:
            if cur in rank_str.lower():
                out.append(app_commands.Choice(name=rank_str, value=rank_str))
                seen_ranks.add(rank_str)
        if len(out) >= 25:
            break
    return out


async def autocomplete_born_mode(
    interaction: discord.Interaction,
    current: str,
):
    modes = ["year", "before", "after"]

    if current:
        modes = [m for m in modes if current.lower() in m]

    return [
        app_commands.Choice(name=m, value=m)
        for m in modes
    ]


async def autocomplete_countries(interaction: discord.Interaction, current: str):
    """Autocomplete countries."""
    cog = interaction.client.get_cog("RankingsCog")
    if not cog:
        return []
    
    cur = current.lower().strip()
    matches = [c for c in cog.loader.by_country.keys() if cur in c.lower()]
    return [app_commands.Choice(name=c, value=c) for c in matches[:25]]


async def autocomplete_states(interaction: discord.Interaction, current: str):
    """Autocomplete states - US states and Canadian provinces only."""
    cog = interaction.client.get_cog("RankingsCog")
    if not cog:
        return []
    
    # Whitelist of US states and Canadian provinces
    allowed_states = {
        # US States
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", 
        "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", 
        "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", 
        "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", 
        "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", 
        "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", 
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", 
        "Wisconsin", "Wyoming",
        # Canadian Provinces
        "Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador",
        "Northwest Territories", "Nova Scotia", "Nunavut", "Ontario", "Prince Edward Island",
        "Quebec", "Saskatchewan", "Yukon"
    }
    
    cur = current.lower().strip()
    # Only show states/provinces from the whitelist
    all_states = [s for s in cog.loader.by_state.keys() if s in allowed_states]
    matches = [s for s in all_states if cur in s.lower()]
    return [app_commands.Choice(name=s, value=s) for s in sorted(matches)[:25]]


async def autocomplete_search_mode(interaction: discord.Interaction, current: str):
    """Autocomplete for search mode."""
    modes = ["name", "rank", "random"]
    return [
        app_commands.Choice(name=mode.capitalize(), value=mode)
        for mode in modes
        if current.lower() in mode.lower()
    ]


# ================================================================
# Media helpers
# ================================================================

def _iter_media_files(
    slug: str,
    media_type: str,
    *,
    nsfw_allowed: bool,
) -> List[Path]:
    """Get all media files for a slug and type."""
    base = Path(MEDIA_ROOT) / slug / media_type
    paths: List[Path] = []

    if base.exists():
        for p in base.iterdir():
            if p.is_file():
                paths.append(p)

    nsfw_dir = base / "nsfw"
    if nsfw_allowed and nsfw_dir.exists():
        for p in nsfw_dir.iterdir():
            if p.is_file():
                paths.append(p)

    return sorted(paths)


# ================================================================
# Media carousel with ❥ reaction
# ================================================================

class MediaCarouselView(ui.View):
    """Simple carousel that auto-adds ❥ for favoriting."""
    
    def __init__(self, title: str, paths: List[Path]):
        super().__init__(timeout=300)
        self.title = title
        self.paths = paths
        self.index = 0
        self.message: Optional[discord.Message] = None

    async def _update(self, interaction: discord.Interaction, *, initial: bool = False):
        if not self.paths:
            text = "No media found."
            if initial:
                await interaction.response.send_message(text, ephemeral=True)
            else:
                await interaction.response.edit_message(content=text, attachments=[], view=None)
            return

        path = self.paths[self.index]
        file = discord.File(str(path))
        msg = f"{self.title} — {self.index + 1}/{len(self.paths)}"

        if initial:
            await interaction.response.send_message(content=msg, file=file, view=self)
            self.message = await interaction.original_response()
            await self.message.add_reaction("❤️")
        else:
            await interaction.response.edit_message(content=msg, attachments=[file], view=self)
            # Clear old reactions and add new ❥
            if self.message:
                await self.message.clear_reactions()
                await self.message.add_reaction("❤️")

    @ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        if not self.paths:
            return
        self.index = (self.index - 1) % len(self.paths)
        await self._update(interaction)

    @ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if not self.paths:
            return
        self.index = (self.index + 1) % len(self.paths)
        await self._update(interaction)


# ================================================================
# Rankings Cog
# ================================================================

class RankingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Use RankingsCache to avoid hitting Google Sheets API every restart
        from utils.rankings.cache import RankingsCache
        cache = RankingsCache()
        self.loader = cache.load()

    # ---------------- Permission Helpers ----------------

    def nsfw_allowed(self, interaction: discord.Interaction) -> bool:
        """Check if NSFW content is allowed."""
        ch = interaction.channel
        if isinstance(ch, discord.DMChannel):
            return True
        return getattr(ch, "nsfw", False) is True

    def group1_allowed(self, interaction: discord.Interaction) -> bool:
        """Check if Group 1 entries are allowed."""
        ch = interaction.channel
        if isinstance(ch, discord.DMChannel):
            return True
        channel_id = getattr(ch, "id", None)
        return channel_id not in CHANNEL_NO_GROUP1

    def filter_group1(self, entries: List[RankingEntry], interaction: discord.Interaction) -> List[RankingEntry]:
        """Filter out Group 1 if not allowed."""
        if self.group1_allowed(interaction):
            return entries
        return [e for e in entries if e.group != 1]

    # ---------------- Lookup Helpers ----------------

    def _find_entry(self, name: str) -> Optional[RankingEntry]:
        """Find entry by name or slug."""
        key = name.lower().strip()
        if key in self.loader.by_slug:
            return self.loader.by_slug[key]
        return self.loader.by_name_lower.get(key)

    def _find_by_rank(self, rank: str) -> Optional[RankingEntry]:
        """Find entry by rank string."""
        rank = rank.strip().upper().lstrip("#")
        return self.loader.by_rank.get(rank)
        
    # ---------- Stats Calculation Helper ------------

    def _calculate_full_list_stats(
        self,
        entries: List[RankingEntry],
        context: str = "default",
    ) -> dict:
        """Calculate comprehensive stats from entry list."""
        today = datetime.date.today()

        ages: list[tuple[int, RankingEntry]] = []
        birth_years = []
        birth_months = []
        cities = []
        states = []
        countries = []

        for e in entries:
            bd = getattr(e, "birth_date", None)

            # Collect geographic data
            city = getattr(e, "birth_city", None)
            state = getattr(e, "birth_state", None)
            country = getattr(e, "birth_country", None)
            
            if city:
                cities.append(city)
            if state:
                states.append(state)
            if country:
                countries.append(country)

            # Must be a real date object
            if not isinstance(bd, datetime.date):
                continue

            # Skip placeholder sentinel
            if bd.year in (1, 1000):
                continue

            age = _age_on(e, today)
            if age is None:
                continue

            ages.append((age, e))
            birth_years.append(bd.year)
            birth_months.append(bd.month)

        # Use the fixed compute_age_stats from formatting.py
        stats = compute_age_stats(entries, on_date=today)
        
        # Add birth data to stats dict
        stats["birth_years"] = birth_years
        stats["birth_months"] = birth_months
        stats["cities"] = cities
        stats["states"] = states
        stats["countries"] = countries
        stats["total_people"] = len(entries)
        
        # Add GLOBAL totals (from full loader dataset)
        stats["total_countries_global"] = len(self.loader.by_country)
        stats["total_states_global"] = len(self.loader.by_state)
        
        # Add highest entry
        stats["highest_entry"] = min(
            entries,
            key=lambda e: e.sort_key_rank_only,
            default=None,
        )

        # ✅ Create counters for month/year FIRST
        from collections import Counter
        month_counts = Counter(birth_months) if birth_months else Counter()
        year_counts = Counter(birth_years) if birth_years else Counter()
        
        # ✅ THEN add them to stats
        stats["month_counts"] = month_counts
        stats["year_counts"] = year_counts
        
        # ✅ Return the stats dict (already has youngest/oldest from compute_age_stats)
        return stats

    # ---------------- Pagination Helper ----------------

    async def _paginate(
            self,
            interaction: discord.Interaction,
            entries: List[RankingEntry],
            title: str,
            context: str = "default",
            sort_by: str = "rank",
        ) -> None:
            """Show paginated list using build_list_embed."""
            entries = self.filter_group1(entries, interaction)
            
            if not entries:
                await interaction.response.send_message(
                    "No matches found.", ephemeral=True
                )
                return

            nsfw = self.nsfw_allowed(interaction)
            
            # Calculate stats ONCE from the FULL list
            full_list_stats = self._calculate_full_list_stats(entries, context)
            print(
                "[DEBUG] ages count:",
                len(full_list_stats.get("ages", []))
            )
            # Create render function that adapts build_list_embed for pagination
            async def render_page(page_entries: List[RankingEntry], page_num: int, total_pages: int):
                page_title = f"{title} (Page {page_num}/{total_pages})"
                embed, file = await build_list_embed(
                    page_entries,
                    title=page_title,
                    nsfw_allowed=nsfw,
                    media_root=MEDIA_ROOT,
                    context=context,
                    full_list_stats=full_list_stats,  # ADD THIS LINE
                )
                files = [file] if file else []
                return embed, files
            
            await send_paginated(
                interaction,
                items=entries,
                render_page=render_page,
                page_size=25,
            )

    # -------------- Pagination Age Buckets --------------

    async def _paginate_age_buckets(
        self,
        interaction: discord.Interaction,
        pages: List[List[Tuple[int, List[RankingEntry]]]],
        title: str,
        context: str = "default",
    ):
        """
        Paginate age-bucketed results.
        Each page shows multiple age groups.
        """
        if not pages:
            await interaction.followup.send("No results found.", ephemeral=True)
            return

        nsfw = self.nsfw_allowed(interaction)
        today = datetime.date.today()
        
        # Calculate stats from ALL entries across ALL pages
        all_entries = [e for page in pages for _, bucket in page for e in bucket]
        full_list_stats = self._calculate_full_list_stats(all_entries, context)

        async def render_page(page_entries: List[RankingEntry], page_num: int, total_pages: int):
            """Render one page of age-bucketed results."""
            page_title = f"{title} (Page {page_num}/{total_pages})"
            
            # Group THIS page's entries by age
            page_buckets = {}
            for e in page_entries:
                age = _age_on(e, today)
                if age is not None:
                    page_buckets.setdefault(age, []).append(e)
            
            # Build description with age headers
            lines = []
            header_lines = []
            
            # Add overall stats to first page only
            if page_num == 1:
                youngest = full_list_stats.get("youngest")
                oldest = full_list_stats.get("oldest")
                
                if youngest and oldest:
                    young_age, young_entry = youngest
                    old_age, old_entry = oldest
                    header_lines.append(f"🌟 **Youngest:** {young_entry.name} ({young_age})")
                    header_lines.append(f"🌙 **Oldest:** {old_entry.name} ({old_age})\n")
            
            if header_lines:
                lines.extend(header_lines)
            
            # Sort ages youngest to oldest for display
            for age in sorted(page_buckets.keys()):
                bucket = page_buckets[age]
                bucket.sort(key=lambda e: e.sort_key_rank_only)
                
                # Age header
                birth_year = today.year - age
                lines.append(f"\n**Age {age}** (Born {birth_year})")
                
                # Entries in this age group
                for e in bucket:
                    rank_label = _get_rank_label(e)
                    if not rank_label.startswith("#"):
                        rank_label = f"#{rank_label}"
                    
                    name = e.name
                    if len(name) > 24:
                        name = name[:23] + "…"
                    
                    date_str = _format_birthdate_for_list(e.birth_date)
                    lines.append(f"`{rank_label:<5} {name:<24} {date_str}`")
            
            embed = discord.Embed(
                title=page_title,
                description="\n".join(lines),
                color=discord.Color.blue(),
            )
            
            # Footer
            footer_parts = []
            if JARVIS_FOOTER:
                footer_parts.append(JARVIS_FOOTER)
            
            ages = full_list_stats.get("ages", [])
            if ages:
                age_vals = [a for a, _ in ages]
                avg_age = sum(age_vals) / len(age_vals)
                min_age = min(age_vals)
                max_age = max(age_vals)
                
                highest_entry = full_list_stats.get("highest_entry")
                top_rank = _get_rank_label(highest_entry) if highest_entry else "N/A"
                
                footer_parts.append(
                    f"Ages: {min_age}-{max_age} | Avg: {avg_age:.1f} | Top: {top_rank}"
                )
            
            if footer_parts:
                embed.set_footer(text=" • ".join(footer_parts))
            
            # Hero image from first person on this page
            hero_file = None
            if page_entries:
                from utils.rankings.formatting import _pick_hero_file
                hero_file = _pick_hero_file(
                    page_entries[0],
                    nsfw_allowed=nsfw,
                    media_root=MEDIA_ROOT,
                )
                if hero_file:
                    embed.set_image(url=f"attachment://{hero_file.filename}")
            
            files = [hero_file] if hero_file else []
            return embed, files
        
        # Flatten pages into a single list for pagination
        flat_entries = [e for page in pages for _, bucket in page for e in bucket]
        
        await send_paginated(
            interaction,
            items=flat_entries,
            render_page=render_page,
            page_size=25,
        )
        
    
# ================================================================
# /rank command group
# ================================================================

rank = app_commands.Group(name="rank", description="Rankings commands")

# ================================================================
# /rank today
# ================================================================

@rank.command(name="today", description="Show birthdays today or for a given date.")
async def rank_today(interaction: discord.Interaction, date: Optional[str] = None):
    # Defer immediately to prevent timeout
    await interaction.response.defer()
    
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")

    today = datetime.date.today()
    target = today
    
    # Parse date_text if provided (e.g., "nov 28", "november 28", "11 28", "11/28")
    if date:
        parts = date.lower().strip().replace("/", " ").replace("-", " ").split()
        if len(parts) >= 2:
            # Try to parse month
            month_num = _parse_month(parts[0])
            if month_num:
                try:
                    day_num = int(parts[1])
                    if 1 <= day_num <= 31:
                        # Use current year for the date
                        target = datetime.date(today.year, month_num, day_num)
                except (ValueError, TypeError):
                    pass

    entries = [
        e for e in cog.loader.entries
        if getattr(e, "birth_date", None)
        and e.birth_date.month == target.month
        and e.birth_date.day == target.day
    ]
    
    entries = cog.filter_group1(entries, interaction)

    if not entries:
        return await interaction.followup.send("🎂 No birthdays on that date.", ephemeral=True)

    nsfw = cog.nsfw_allowed(interaction)
    used_categories: set[str] = set()

    for idx, e in enumerate(entries):
        facts = generate_fun_facts(
            e, 
            cog.loader.entries,  
            today=target, 
            used_categories=used_categories,
            exclude_categories={"birth_day"},  # Exclude birth_day from birthday embeds since we show all birthdays
            max_facts=2,
        )
        
        embed, hero_file, thumbnail_file = await build_profile_embed(
            e, 
            nsfw_allowed=nsfw, 
            media_root=MEDIA_ROOT, 
            fun_facts=facts, 
            on_date=target,
            all_entries=cog.loader.entries,
        )

        # Send both files if they exist
        files = [f for f in [hero_file, thumbnail_file] if f is not None]
        if files:
            await interaction.followup.send(embed=embed, files=files)
        else:
            await interaction.followup.send(embed=embed)


# ================================================================
# /rank search (by NAME)
# ================================================================

# NEW CONSOLIDATED RANK COMMANDS
# These will replace the old search, view, random, born, before_year, after_year commands

# ================================================================
# /rank search mode:name|rank|random
# ================================================================

@rank.command(name="search", description="Search for a person by name, rank, or get a random person.")
@app_commands.autocomplete(mode=autocomplete_search_mode, query=autocomplete_names)
async def rank_search(
    interaction: discord.Interaction, 
    mode: str,
    query: Optional[str] = None
):
    """
    Unified search command with three modes:
    - name: Search by person's name (autocomplete shows names)
    - rank: Search by rank (user types rank, autocomplete ignored)
    - random: Get a random person (query not needed)
    
    Note: Autocomplete always shows names, but users can ignore it for rank mode.
    """
    await interaction.response.defer()
    
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    
    # MODE: RANDOM
    if mode == "random":
        choices = cog.filter_group1(cog.loader.entries, interaction)
        
        if not choices:
            return await interaction.followup.send("No entries available.", ephemeral=True)
        
        entry = random.choice(choices)
    
    # MODE: NAME
    elif mode == "name":
        if not query:
            return await interaction.followup.send(
                "Please provide a name to search for.", ephemeral=True
            )
        
        entry = cog._find_entry(query)
        if not entry:
            return await interaction.followup.send(
                "I couldn't find that name.", ephemeral=True
            )
    
    # MODE: RANK
    elif mode == "rank":
        if not query:
            return await interaction.followup.send(
                "Please provide a rank to search for (e.g., 'A', '1', '250')", ephemeral=True
            )
        
        entry = cog._find_by_rank(query)
        if not entry:
            return await interaction.followup.send(
                f"I couldn't find rank '{query}'.", ephemeral=True
            )
    
    else:
        return await interaction.followup.send(
            "Invalid mode. Please choose: name, rank, or random", ephemeral=True
        )
    
    # Check group1 permissions
    if entry.group == 1 and not cog.group1_allowed(interaction):
        return await interaction.followup.send(
            "That person is not available in this channel.", ephemeral=True
        )
    
    # Generate embed
    nsfw = cog.nsfw_allowed(interaction)
    facts = generate_fun_facts(
        entry, 
        cog.loader.entries, 
        today=datetime.date.today(),
        max_facts=2,
    )
    
    embed, hero_file, thumbnail_file = await build_profile_embed(
        entry, 
        nsfw_allowed=nsfw, 
        media_root=MEDIA_ROOT,
        fun_facts=facts, 
        kobold_insights=None, 
        on_date=None,
        all_entries=cog.loader.entries,
    )
    
    # Send
    files = [f for f in [hero_file, thumbnail_file] if f is not None]
    if files:
        await interaction.followup.send(embed=embed, files=files)
    else:
        await interaction.followup.send(embed=embed)


# ================================================================
# /rank top
# ================================================================

@rank.command(name="top", description="Show the top ranked people.")
@app_commands.autocomplete(sort_by=autocomplete_sort_by)
async def rank_top(
    interaction: discord.Interaction,
    count: Optional[int] = 25,
    sort_by: Optional[str] = None,
):
    await interaction.response.defer()
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")

    # --------------------------------------------------
    # Base dataset: numeric ranks only (Groups 2+)
    # --------------------------------------------------

    entries = [
        e for e in cog.loader.entries
        if e.group != 1 and e.numeric_rank is not None
    ]

    today = datetime.date.today()

    # --------------------------------------------------
    # AGE SORT (bucketed, non-splitting)
    # --------------------------------------------------

    if sort_by == "age":
        from utils.rankings.formatting import _paginate_age_buckets

        # Limit to top N *by rank first*
        entries.sort(key=lambda e: e.sort_key_rank_only)
        entries = entries[:count]

        pages = _paginate_age_buckets(
            entries,
            on_date=today,
            page_size=25,
        )

        await cog._paginate_age_buckets(
            interaction,
            pages,
            title=f"Top {count} Rankings",
            context="top",
        )
        return

    # --------------------------------------------------
    # DATE SORT (chronological birthdate)
    # --------------------------------------------------

    if sort_by == "date":
        entries = sorted(
            entries,
            key=lambda e: e.birth_date or datetime.date.max
        )

    # --------------------------------------------------
    # DEFAULT: TRUE RANK
    # --------------------------------------------------

    else:
        entries = sorted(entries, key=lambda e: e.sort_key_rank_only)

    top_entries = entries[:count]

    await cog._paginate(
        interaction,
        top_entries,
        f"Top {count} Rankings",
        context="top",
        sort_by=sort_by or "rank",
    )


# ================================================================
# /rank group
# ================================================================

@rank.command(name="group", description="List all rankings in a given group.")
@app_commands.autocomplete(sort_by=autocomplete_sort_by)
async def rank_group(
    interaction: discord.Interaction,
    group: int,
    sort_by: Optional[str] = None,
):
    await interaction.response.defer()
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    today = datetime.date.today()

    entries = [e for e in cog.loader.entries if e.group == group]

    # AGE SORT - Use bucketed pagination
    if sort_by == "age":
        from utils.rankings.formatting import _paginate_age_buckets

        entries.sort(key=lambda e: e.sort_key_rank_only)
        pages = _paginate_age_buckets(entries, on_date=today, page_size=25)
        
        await cog._paginate_age_buckets(
            interaction,
            pages,
            f"Group {group} Rankings",
            context="group",
        )
        return

    # Apply other sorting using helper
    entries = _sort_entries(entries, sort_by, today)

    await cog._paginate(
        interaction,
        entries,
        f"Group {group} Rankings",
        context="group",
        sort_by=sort_by or "rank",
    )


# ================================================================
# /rank born mode:year|before|after
# ================================================================

@rank.command(name="born", description="Show people born in/before/after a given year (sorted by rank by default).")
@app_commands.autocomplete(mode=autocomplete_born_mode, sort_by=autocomplete_sort_by)
async def rank_born(
    interaction: discord.Interaction,
    mode: str,
    year: int,
    sort_by: Optional[str] = None,
):
    """
    Modes: year, before, after
    Sort options: None (rank), "chronological", "date", "age"
    
    NOTE: For "year" mode, youngest/oldest are calculated from ALL entries,
    not just this year (since everyone born in 1985 is the same age).
    """
    await interaction.response.defer()
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    today = datetime.date.today()

    # Filter by mode
    if mode == "year":
        entries = [
            e for e in cog.loader.by_birth_year.get(year, [])
            if e.birth_date
        ]
        title = f"Born in {year}"
        
        # For single-year queries, calculate youngest/oldest from FULL dataset
        # (otherwise everyone is the same age!)
        stats_entries = cog.loader.entries

    elif mode == "before":
        entries = [
            e for e in cog.loader.entries
            if e.birth_date
            and e.birth_date.year not in (1, 1000)
            and e.birth_date.year < year
        ]
        title = f"Born Before {year}"
        stats_entries = entries  # Use filtered list for before/after

    elif mode == "after":
        entries = [
            e for e in cog.loader.entries
            if e.birth_date
            and e.birth_date.year not in (1, 1000)
            and e.birth_date.year > year
        ]
        title = f"Born After {year}"
        stats_entries = entries  # Use filtered list for before/after

    else:
        await interaction.followup.send(
            "Invalid mode. Choose: year, before, or after.",
            ephemeral=True,
        )
        return

    # AGE SORT - Use bucketed pagination
    if sort_by == "age":
        from utils.rankings.formatting import _paginate_age_buckets

        entries.sort(key=lambda e: e.sort_key_rank_only)
        pages = _paginate_age_buckets(entries, on_date=today, page_size=25)
        
        await cog._paginate_age_buckets(
            interaction,
            pages,
            title,
            context="year",
        )
        return
    
    # Apply other sorting
    entries = _sort_entries(entries, sort_by, today)

    # Calculate stats from appropriate dataset
    entries = cog.filter_group1(entries, interaction)
    
    if not entries:
        await interaction.followup.send("No matches found.", ephemeral=True)
        return

    nsfw = cog.nsfw_allowed(interaction)
    
    # Calculate stats from stats_entries (full for year, filtered for before/after)
    full_list_stats = cog._calculate_full_list_stats(stats_entries, context="year")

    # Create render function
    async def render_page(page_entries: List[RankingEntry], page_num: int, total_pages: int):
        page_title = f"{title} (Page {page_num}/{total_pages})"
        embed, file = await build_list_embed(
            page_entries,
            title=page_title,
            nsfw_allowed=nsfw,
            media_root=MEDIA_ROOT,
            context="year",
            full_list_stats=full_list_stats,
        )
        files = [file] if file else []
        return embed, files
    
    await send_paginated(
        interaction,
        items=entries,
        render_page=render_page,
        page_size=25,
    )


# ================================================================
# /rank decade
# ================================================================

@rank.command(name="decade", description="Show people born in a decade (e.g., 1980).")
@app_commands.autocomplete(sort_by=autocomplete_sort_by)
async def rank_decade(
    interaction: discord.Interaction,
    decade: int,
    sort_by: Optional[str] = None,
):
    await interaction.response.defer()
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    today = datetime.date.today()

    start_year = decade
    end_year = decade + 9

    entries = [
        e for e in cog.loader.entries
        if e.birth_date
        and e.birth_date.year != 1000
        and start_year <= e.birth_date.year <= end_year
    ]

    title = f"Born in the {decade}s"

    # AGE SORT - Use bucketed pagination
    if sort_by == "age":
        from utils.rankings.formatting import _paginate_age_buckets

        entries.sort(key=lambda e: e.sort_key_rank_only)
        pages = _paginate_age_buckets(entries, on_date=today, page_size=25)
        
        await cog._paginate_age_buckets(
            interaction,
            pages,
            title=title,
            context="decade",
        )
        return

    # Apply other sorting using helper
    entries = _sort_entries(entries, sort_by, today)

    await cog._paginate(
        interaction,
        entries,
        title,
        context="decade",
        sort_by=sort_by or "rank",
    )


# ================================================================
# /rank month
# ================================================================

@rank.command(name="month", description="Show people born in a given month.")
@app_commands.autocomplete(sort_by=autocomplete_sort_by)
async def rank_month(
    interaction: discord.Interaction,
    month: str,
    sort_by: Optional[str] = None,
):
    await interaction.response.defer()
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    today = datetime.date.today()

    month_num = _parse_month(month)
    if not month_num:
        return await interaction.followup.send(
            "Invalid month. Try: `nov`, `November`, or `11`.",
            ephemeral=True,
        )

    entries = [
        e for e in cog.loader.entries
        if e.birth_date
        and e.birth_date.year != 1000
        and e.birth_date.month == month_num
    ]

    month_name = datetime.date(2000, month_num, 1).strftime("%B")
    title = f"Born in {month_name}"

    # AGE SORT - Use bucketed pagination
    if sort_by == "age":
        from utils.rankings.formatting import _paginate_age_buckets

        entries.sort(key=lambda e: e.sort_key_rank_only)
        pages = _paginate_age_buckets(entries, on_date=today, page_size=25)
        
        await cog._paginate_age_buckets(
            interaction,
            pages,
            title=title,
            context="month",
        )
        return

    # Apply sorting - special handling for date mode (month/day only)
    if sort_by == "date":
        # For month view, date mode just sorts by day within month
        entries = sorted(entries, key=lambda e: e.birth_date.day if e.birth_date else 99)
    else:
        # Use helper for chronological and rank
        entries = _sort_entries(entries, sort_by, today)

    await cog._paginate(
        interaction,
        entries,
        title,
        context="month",
        sort_by=sort_by or "rank",
    )


# /rank birthplace - Rulebreaker Command
# Shows top 10 cities OR people from a specific city

# ================================================================
# AUTOCOMPLETE for Cities (City, State / City, Country)
# ================================================================

async def autocomplete_cities(interaction: discord.Interaction, current: str):
    """
    Autocomplete for birthplace cities with NYC normalization.
    """
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")

    suggestions = {}

    for entry in cog.loader.entries:
        city = getattr(entry, "birth_city", None)
        if not city or city == "-":
            continue

        state = getattr(entry, "birth_state", None)
        country = getattr(entry, "birth_country", None)

        # Use normalization function
        label = _normalize_city_label(city, state, country)

        suggestions.setdefault(label, []).append(entry)

    # Filter by input
    if current:
        suggestions = {
            k: v for k, v in suggestions.items()
            if current.lower() in k.lower()
        }

    # Sort by population
    sorted_labels = sorted(
        suggestions.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )

    return [
        app_commands.Choice(
            name=f"{label} ({len(entries)} people)",
            value=label,
        )
        for label, entries in sorted_labels[:25]
    ]


# ================================================================
# /rank birthplace
# ================================================================

@rank.command(
    name="birthplace",
    description="Show top 10 cities or people from a specific city.",
)
@app_commands.autocomplete(
    city=autocomplete_cities,
    sort_by=autocomplete_sort_by,
)
async def rank_birthplace(
    interaction: discord.Interaction,
    city: Optional[str] = None,
    sort_by: Optional[str] = None,
):
    """
    Rulebreaker command:

    - Without city:
        Page 1 = Top 10 cities summary
        Pages 2+ = Top 10 people from each city (rank order)

    - With city:
        Standard list embed
        Supports sort_by = rank (default), date, age
    """
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")

    # ============================================================
    # NYC DEBUG - DELETE AFTER FIXING
    # ============================================================
    if not city:  # Only when showing top 10 cities
        print("\n" + "="*70)
        print("NYC DIAGNOSTIC")
        print("="*70)
        
        nyc_count = 0
        for e in cog.loader.entries:
            # YOUR SHEET HAS "place_of_birth" not separate columns!
            birthplace = getattr(e, "place_of_birth", None)
            
            # Check if it mentions New York
            if birthplace and "york" in birthplace.lower():
                nyc_count += 1
                
                # Also check what the loader puts in birth_city
                city_val = getattr(e, "birth_city", None)
                state_val = getattr(e, "birth_state", None)
                country_val = getattr(e, "birth_country", None)
                
                normalized = _normalize_city_label(
                    city_val or "", 
                    state_val or "", 
                    country_val or ""
                )
                
                print(f"\n[{nyc_count}] {e.name}")
                print(f"  place_of_birth: '{birthplace}'")
                print(f"  birth_city:     '{city_val}'")
                print(f"  birth_state:    '{state_val}'")
                print(f"  birth_country:  '{country_val}'")
                print(f"  → normalized:   '{normalized}'")
                
                if nyc_count >= 20:  # Show first 20
                    break
        
        print(f"\n{'='*70}")
        print(f"TOTAL: {nyc_count} NYC entries")
        print("="*70 + "\n")
    # ============================================================
    # END DEBUG
    # ============================================================

    # ------------------------------------------------------------
    # CASE 1: Specific city requested (WITH sort_by)
    # ------------------------------------------------------------
    if city:
        # Normalize lookup using the same function
        entries = []
        for e in cog.loader.entries:
            city_name = getattr(e, "birth_city", None)
            state = getattr(e, "birth_state", None)
            country = getattr(e, "birth_country", None)

            if city_name:
                label = _normalize_city_label(city_name, state, country)
                if label == city:
                    entries.append(e)

        if not entries:
            return await interaction.response.send_message(
                f"No one in the rankings was born in {city}.",
                ephemeral=True,
            )

        entries = cog.filter_group1(entries, interaction)

        if not entries:
            return await interaction.response.send_message(
                f"No one available in {city} for this channel.",
                ephemeral=True,
            )

        today = datetime.date.today()

        # AGE SORT - Use bucketed pagination
        if sort_by == "age":
            from utils.rankings.formatting import _paginate_age_buckets

            entries.sort(key=lambda e: e.sort_key_rank_only)
            pages = _paginate_age_buckets(entries, on_date=today, page_size=25)
            
            await cog._paginate_age_buckets(
                interaction,
                pages,
                f"Born in {city}",
                context="city",
            )
            return

        # Apply other sorting using centralized function
        entries = _sort_entries(entries, sort_by, today)

        await cog._paginate(
            interaction,
            entries,
            f"Born in {city}",
            context="city",
            sort_by=sort_by,
        )
        return
		

    # ------------------------------------------------------------
    # CASE 2: Top 10 cities (RULEBREAKER MODE with NYC normalization)
    # ------------------------------------------------------------
    city_counts: dict[str, int] = {}
    city_entries_map: dict[str, list] = {}

    for e in cog.loader.entries:
        city_name = getattr(e, "birth_city", None)
        if not city_name or city_name == "-":
            continue

        state = getattr(e, "birth_state", None)
        country = getattr(e, "birth_country", None)

        # Use normalization function
        label = _normalize_city_label(city_name, state, country)

        city_entries_map.setdefault(label, []).append(e)

    for label, entries in city_entries_map.items():
        filtered = cog.filter_group1(entries, interaction)
        if filtered:
            city_counts[label] = len(filtered)

    if not city_counts:
        return await interaction.response.send_message(
            "No city data available.",
            ephemeral=True,
        )

    top_cities = sorted(
        city_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    await _send_birthplace_top_cities(
        interaction,
        cog,
        top_cities,
        city_entries_map,
    )


# ================================================================
# RULEBREAKER PAGINATION
# ================================================================

async def _send_birthplace_top_cities(
    interaction: discord.Interaction,
    cog: RankingsCog,
    top_cities: List[Tuple[str, int]],
    city_entries_map: dict[str, list],
):
    """
    Page 1:
      Top 10 Cities by Birth
      Header stats + medals + monospace list

    Pages 2+:
      Top 10 people from each city (rank order)
    """
    nsfw = cog.nsfw_allowed(interaction)
    total_pages = 1 + len(top_cities)

    total_people = sum(count for _, count in top_cities)
    total_cities = len(city_entries_map)

    async def render_page(page_num: int):
        # ---------------- PAGE 1 ----------------
        if page_num == 1:
            lines = []

            medals = ["🥇", "🥈", "🥉"]

            for i, (city, count) in enumerate(top_cities[:3]):
                lines.append(
                    f"{medals[i]} **#{i+1} {city}** — {count} people"
                )

            lines.append("")

            for i, (city, count) in enumerate(top_cities[3:], start=4):
                lines.append(
                    f"`#{i:<2} {city:<30} {count:>3} people`"
                )

            embed = discord.Embed(
                title="Top 10 Cities by Birth",
                description="\n".join(lines),
                color=discord.Color.blue(),
            )
            embed.set_footer(
                text="Use the buttons to view top people from each city"
            )
            return embed, []

        # ---------------- PAGES 2+ ----------------
        city_index = page_num - 2
        city_name, _ = top_cities[city_index]

        entries = cog.filter_group1(
            city_entries_map[city_name],
            interaction,
        )

        top_10 = sorted(
            entries,
            key=lambda e: e.sort_key_rank_only,
        )[:10]

        embed, hero = await build_list_embed(
            top_10,
            title=f"{city_name} ({len(entries)} total)",
            nsfw_allowed=nsfw,
            media_root=MEDIA_ROOT,
        )

        return embed, [hero] if hero else []

    # ---------------- VIEW ----------------
    class BirthplacePaginationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
            self.page = 1

        @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
        async def prev(self, interaction: discord.Interaction, _):
            if self.page > 1:
                self.page -= 1
                await self.update(interaction)

        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
        async def next(self, interaction: discord.Interaction, _):
            if self.page < total_pages:
                self.page += 1
                await self.update(interaction)

        async def update(self, interaction: discord.Interaction):
            embed, files = await render_page(self.page)
            self.prev.disabled = self.page == 1
            self.next.disabled = self.page == total_pages
            await interaction.response.edit_message(
                embed=embed,
                attachments=files,
                view=self,
            )

    view = BirthplacePaginationView()
    embed, files = await render_page(1)
    view.prev.disabled = True
    view.next.disabled = total_pages == 1

    await interaction.response.send_message(
        embed=embed,
        files=files,
        view=view if total_pages > 1 else None,
    )


# ================================================================
# /rank country
# ================================================================

@rank.command(name="country", description="List people by birth country.")
@app_commands.autocomplete(country=autocomplete_countries, sort_by=autocomplete_sort_by)
async def rank_country(
    interaction: discord.Interaction,
    country: str,
    sort_by: Optional[str] = None,
):
    await interaction.response.defer()

    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    today = datetime.date.today()
    
    key = country.strip().lower()
    matched_entries: List[RankingEntry] = []
    
    for c_name, group in cog.loader.by_country.items():
        if key in c_name.lower():
            matched_entries.extend(group)

    # AGE SORT - Use bucketed pagination
    if sort_by == "age":
        from utils.rankings.formatting import _paginate_age_buckets

        matched_entries.sort(key=lambda e: e.sort_key_rank_only)
        pages = _paginate_age_buckets(matched_entries, on_date=today, page_size=25)
        
        await cog._paginate_age_buckets(
            interaction,
            pages,
            f"Born in {country}",
            context="country",
        )
        return

    # Apply other sorting
    matched_entries = _sort_entries(matched_entries, sort_by, today)

    await cog._paginate(
        interaction,
        matched_entries,
        f"Born in {country}",
        context="country",
        sort_by=sort_by or "rank",
    )


# ================================================================
# /rank state
# ================================================================

@rank.command(name="state", description="List people by birth state/province.")
@app_commands.autocomplete(state=autocomplete_states, sort_by=autocomplete_sort_by)
async def rank_state(
    interaction: discord.Interaction,
    state: str,
    sort_by: Optional[str] = None,
):
    await interaction.response.defer()

    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    today = datetime.date.today()
    
    key = state.strip().lower()
    matched_entries: List[RankingEntry] = []
    
    for s_name, group in cog.loader.by_state.items():
        if key in s_name.lower():
            matched_entries.extend(group)

    # AGE SORT - Use bucketed pagination
    if sort_by == "age":
        from utils.rankings.formatting import _paginate_age_buckets

        matched_entries.sort(key=lambda e: e.sort_key_rank_only)
        pages = _paginate_age_buckets(matched_entries, on_date=today, page_size=25)
        
        await cog._paginate_age_buckets(
            interaction,
            pages,
            f"Born in {state}",
            context="state",
        )
        return

    # Apply other sorting
    matched_entries = _sort_entries(matched_entries, sort_by, today)

    await cog._paginate(
        interaction,
        matched_entries,
        f"Born in {state}",
        context="state",
        sort_by=sort_by or "rank",
    )


# ================================================================
# /rank images / gifs / videos
# ================================================================

async def _send_media_command(
    interaction: discord.Interaction,
    *,
    name: str,
    media_type: str,
    max_count: int,
):
    """Shared logic for media commands."""
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    entry = cog._find_entry(name)
    
    if not entry:
        return await interaction.followup.send("I couldn't find that name.", ephemeral=True)
    
    if entry.group == 1 and not cog.group1_allowed(interaction):
        return await interaction.followup.send(
            "That person is not available in this channel.", ephemeral=True
        )

    nsfw = cog.nsfw_allowed(interaction)
    all_files = _iter_media_files(entry.slug, media_type, nsfw_allowed=nsfw)
    
    if not all_files:
        return await interaction.response.send_message(
            f"No {media_type} found for {entry.name}.", ephemeral=True
        )

    count = min(max_count, len(all_files))
    selected = random.sample(all_files, count)

    if len(selected) == 1:
        file = discord.File(str(selected[0]))
        await interaction.response.send_message(
            content=f"{entry.name} — {media_type[:-1].capitalize()}",
            file=file,
        )
        # Add fire reaction - get the message
        # We need to use webhook followup to get the message after response.send_message
        # Actually, we can't add reactions after response.send_message without followup
        # So let's just skip the reaction for now
        # Reaction removed - can't add after response.send_message
    else:
        view = MediaCarouselView(f"{entry.name} — {media_type.capitalize()}", selected)
        await view._update(interaction, initial=True)


@rank.command(name="images", description="Show random images for a person.")
@app_commands.autocomplete(name=autocomplete_names)
async def rank_images(interaction: discord.Interaction, name: str, count: int = 3):
    if count < 1 or count > 10:
        count = 3
    await _send_media_command(interaction, name=name, media_type="images", max_count=count)


@rank.command(name="gifs", description="Show random GIFs for a person.")
@app_commands.autocomplete(name=autocomplete_names)
async def rank_gifs(interaction: discord.Interaction, name: str, count: int = 3):
    if count < 1 or count > 5:
        count = 3
    await _send_media_command(interaction, name=name, media_type="gifs", max_count=count)


@rank.command(name="videos", description="Show random videos for a person.")
@app_commands.autocomplete(name=autocomplete_names)
async def rank_videos(interaction: discord.Interaction, name: str, count: int = 1):
    if count < 1 or count > 3:
        count = 1
    await _send_media_command(interaction, name=name, media_type="videos", max_count=count)


# ================================================================
# /rank favorites
# ================================================================

# NEW /rank favorites - Better Design
# /rank favorites [person] [type:all|images|gifs|videos] [count:1-10]

# ================================================================
# AUTOCOMPLETE
# ================================================================

async def autocomplete_favorite_type(interaction: discord.Interaction, current: str):
    """Autocomplete for favorite media types."""
    types = ["all", "images", "gifs", "videos"]
    return [
        app_commands.Choice(name=t.capitalize(), value=t)
        for t in types
        if current.lower() in t.lower()
    ]


# ================================================================
# /rank favorites - RULEBREAKER COMMAND
# ================================================================

@rank.command(name="favorites", description="Show favorite media - overall stats or for a specific person.")
@app_commands.autocomplete(person=autocomplete_names, media_type=autocomplete_favorite_type)
async def rank_favorites(
    interaction: discord.Interaction,
    person: Optional[str] = None,
    media_type: Optional[str] = "all",
    count: Optional[int] = 10
):
    """
    Flexible favorites command:
    - No params: 5-page overview (top people, files, image, gif, video)
    - Person only: Show their favorites (all types)
    - Person + type: Show their favorites filtered by type
    - Type only: Show top 10 of that type globally
    """
    cog: RankingsCog = interaction.client.get_cog("RankingsCog")
    
    # Validate and clamp count
    if media_type == "images":
        count = min(max(1, count), 10)
    elif media_type == "gifs":
        count = min(max(1, count), 5)
    elif media_type == "videos":
        count = min(max(1, count), 3)
    else:
        count = min(max(1, count), 10)
    
    # CASE 1: No person, no type (or type=all) → 5-PAGE OVERVIEW
    if not person and (not media_type or media_type == "all"):
        await _send_favorites_overview(interaction, cog)
        return
    
    # CASE 2: Type only (no person) → TOP 10 OF THAT TYPE GLOBALLY
    if not person and media_type and media_type != "all":
        await _send_favorites_global_type(interaction, cog, media_type, count)
        return
    
    # CASE 3 & 4: Person specified
    if person:
        entry = cog._find_entry(person)
        
        if not entry:
            return await interaction.response.send_message(
                "I couldn't find that name.", ephemeral=True
            )
        
        if entry.group == 1 and not cog.group1_allowed(interaction):
            return await interaction.response.send_message(
                "That person is not available in this channel.", ephemeral=True
            )
        
        # Get their favorites
        from utils.rankings.favorites import get_favorites_for_slug
        all_favorites = get_favorites_for_slug(entry.slug)
        
        if not all_favorites:
            return await interaction.response.send_message(
                f"No favorites found for {entry.name}.", ephemeral=True
            )
        
        # Filter by type if specified
        if media_type and media_type != "all":
            filtered = []
            for path, fav_count in all_favorites:
                path_str = str(path).lower()
                
                if media_type == "images":
                    if "/images/" in path_str and not path_str.endswith(".gif"):
                        filtered.append((path, fav_count))
                elif media_type == "gifs":
                    if "/gifs/" in path_str or path_str.endswith(".gif"):
                        filtered.append((path, fav_count))
                elif media_type == "videos":
                    if "/videos/" in path_str:
                        filtered.append((path, fav_count))
            
            favorites = filtered[:count]
        else:
            favorites = all_favorites[:count]
        
        if not favorites:
            return await interaction.response.send_message(
                f"No {media_type} favorites found for {entry.name}.", ephemeral=True
            )
        
        # Filter NSFW
        nsfw = cog.nsfw_allowed(interaction)
        filtered_favs = []
        for path, fav_count in favorites:
            if not nsfw and ("/nsfw/" in str(path) or "\\nsfw\\" in str(path)):
                continue
            if path.exists():
                filtered_favs.append((path, fav_count))
        
        if not filtered_favs:
            return await interaction.response.send_message(
                f"No favorites for {entry.name} are allowed in this channel.",
                ephemeral=True,
            )
        
        paths = [p for p, _ in filtered_favs]
        
        # Single file
        if len(paths) == 1:
            file = discord.File(str(paths[0]))
            type_str = f" ({media_type})" if media_type != "all" else ""
            await interaction.response.send_message(
                content=f"{entry.name} — Favorite{type_str} (❤️ {filtered_favs[0][1]})",
                file=file,
            )
        # Multiple files - carousel
        else:
            type_str = f" {media_type.capitalize()}" if media_type != "all" else ""
            view = MediaCarouselView(f"{entry.name} —{type_str} Favorites", paths)
            await view._update(interaction, initial=True)


# ================================================================
# HELPER: 5-Page Overview
# ================================================================

async def _send_favorites_overview(interaction: discord.Interaction, cog: RankingsCog):
    """
    5-page overview:
    Page 1: Top 10 people
    Page 2: Top 10 files
    Page 3: Most favorited image
    Page 4: Most favorited gif
    Page 5: Most favorited video
    """
    from utils.rankings.favorites import (
        get_top_favorited_people,
        get_top_favorited_media,
        get_top_favorited_by_type,
        get_favorites_for_slug
    )
    
    nsfw = cog.nsfw_allowed(interaction)
    
    # Prepare data
    top_people = get_top_favorited_people(10)
    top_files = get_top_favorited_media(10)
    top_images = get_top_favorited_by_type("images", 1)
    top_gifs = get_top_favorited_by_type("gifs", 1)
    top_videos = get_top_favorited_by_type("videos", 1)
    
    total_pages = 5
    
    async def render_page(page_num: int):
        """Render each page of the overview."""
        
        # PAGE 1: Top 10 People
        if page_num == 1:
            lines = ["**Top 10 Most Favorited People**\n"]
            for i, (slug, total_favs) in enumerate(top_people, 1):
                # Get person name
                entry = cog.loader.by_slug.get(slug)
                name = entry.name if entry else slug
                
                # Get file count
                person_favs = get_favorites_for_slug(slug)
                file_count = len(person_favs)
                
                lines.append(f"**#{i}** {name} — 🔥 {total_favs} favorites ({file_count} files)")
            
            embed = discord.Embed(
                title="❤️ Favorites Overview",
                description="\n".join(lines),
                color=discord.Color.red()
            )
            embed.set_footer(text="Page 1/5 — Top People • Use buttons to see more")
            
            # Get hero image from #1 person
            hero_file = None
            if top_people:
                top_slug = top_people[0][0]
                top_entry = cog.loader.by_slug.get(top_slug)
                if top_entry:
                    from utils.rankings.formatting import _pick_hero_file
                    hero_file = _pick_hero_file(top_entry, nsfw_allowed=nsfw, media_root=MEDIA_ROOT)
                    if hero_file:
                        embed.set_image(url=f"attachment://{hero_file.filename}")
            
            files = [hero_file] if hero_file else []
            return embed, files
        
        # PAGE 2: Top 10 Files
        elif page_num == 2:
            lines = ["**Top 10 Most Favorited Files**\n"]
            for i, (path, fav_count) in enumerate(top_files, 1):
                # Get slug from path
                path_parts = str(path).split("\\") if "\\" in str(path) else str(path).split("/")
                slug = path_parts[-4] if len(path_parts) >= 4 else "unknown"
                
                entry = cog.loader.by_slug.get(slug)
                name = entry.name if entry else slug
                
                filename = path.name
                lines.append(f"**#{i}** {name} — `{filename}` (❤️ {fav_count})")
            
            embed = discord.Embed(
                title="❤️ Favorites Overview",
                description="\n".join(lines),
                color=discord.Color.red()
            )
            embed.set_footer(text="Page 2/5 — Top Files")
            
            # Show the #1 file
            hero_file = None
            if top_files and top_files[0][0].exists():
                hero_file = discord.File(str(top_files[0][0]))
                embed.set_image(url=f"attachment://{hero_file.filename}")
            
            files = [hero_file] if hero_file else []
            return embed, files
        
        # PAGE 3: Most favorited image
        elif page_num == 3:
            return await _render_top_media_page(
                "Image", top_images, cog, nsfw, page_num
            )
        
        # PAGE 4: Most favorited gif
        elif page_num == 4:
            return await _render_top_media_page(
                "GIF", top_gifs, cog, nsfw, page_num
            )
        
        # PAGE 5: Most favorited video
        elif page_num == 5:
            return await _render_top_media_page(
                "Video", top_videos, cog, nsfw, page_num
            )
    
    # Create pagination view
    class FavoritesOverviewView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
            self.current_page = 1
            self.total_pages = total_pages
        
        @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
        async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 1:
                self.current_page -= 1
                await self._update(interaction)
        
        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < self.total_pages:
                self.current_page += 1
                await self._update(interaction)
        
        async def _update(self, interaction: discord.Interaction):
            embed, files = await render_page(self.current_page)
            
            # Update button states
            self.prev_button.disabled = (self.current_page == 1)
            self.next_button.disabled = (self.current_page == self.total_pages)
            
            await interaction.response.edit_message(embed=embed, attachments=files, view=self)
    
    view = FavoritesOverviewView()
    view.prev_button.disabled = True
    
    # Render first page
    embed, files = await render_page(1)
    
    await interaction.response.send_message(
        embed=embed,
        files=files,
        view=view,
    )


async def _render_top_media_page(
    media_label: str,
    top_items: List[Tuple[Path, int]],
    cog: RankingsCog,
    nsfw: bool,
    page_num: int
):
    """Render a page showing the top media of a specific type."""
    if not top_items:
        embed = discord.Embed(
            title="❤️ Favorites Overview",
            description=f"No {media_label.lower()} favorites found.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Page {page_num}/5 — Top {media_label}")
        return embed, []
    
    path, fav_count = top_items[0]
    
    # Get slug and person info
    path_parts = str(path).split("\\") if "\\" in str(path) else str(path).split("/")
    slug = path_parts[-4] if len(path_parts) >= 4 else "unknown"
    
    entry = cog.loader.by_slug.get(slug)
    name = entry.name if entry else slug
    
    # Get person's total favorites
    from utils.rankings.favorites import get_favorites_for_slug, get_person_favorite_totals
    person_favs = get_favorites_for_slug(slug)
    person_totals = get_person_favorite_totals()
    total_favs = person_totals.get(slug, 0)
    
    filename = path.name
    
    description = (
        f"**{name}**\n"
        f"File: `{filename}`\n"
        f"❤️ {fav_count} favorites\n\n"
        f"**Overall:** {total_favs} total favorites ({len(person_favs)} files)\n\n"
        f"_Use `/rank favorites type:{media_label.lower()}s` to see top 10 {media_label.lower()}s_"
    )
    
    embed = discord.Embed(
        title=f"❤️ Most Favorited {media_label}",
        description=description,
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Page {page_num}/5 — Top {media_label}")
    
    # Attach the file
    hero_file = None
    if path.exists():
        hero_file = discord.File(str(path))
        embed.set_image(url=f"attachment://{hero_file.filename}")
    
    files = [hero_file] if hero_file else []
    return embed, files


# ================================================================
# HELPER: Global Top 10 by Type
# ================================================================

async def _send_favorites_global_type(
    interaction: discord.Interaction,
    cog: RankingsCog,
    media_type: str,
    count: int
):
    """
    Show top N favorites of a specific type globally.
    One per page with details.
    """
    from utils.rankings.favorites import get_top_favorited_by_type, get_person_favorite_totals, get_favorites_for_slug
    
    nsfw = cog.nsfw_allowed(interaction)
    
    # Get top items
    top_items = get_top_favorited_by_type(media_type, count)
    
    if not top_items:
        return await interaction.response.send_message(
            f"No {media_type} favorites found.", ephemeral=True
        )
    
    total_pages = len(top_items)
    person_totals = get_person_favorite_totals()
    
    async def render_page(page_num: int):
        """Render one favorite per page."""
        idx = page_num - 1
        path, fav_count = top_items[idx]
        
        # Get slug and person info
        path_parts = str(path).split("\\") if "\\" in str(path) else str(path).split("/")
        slug = path_parts[-4] if len(path_parts) >= 4 else "unknown"
        
        entry = cog.loader.by_slug.get(slug)
        name = entry.name if entry else slug
        
        # Get person's favorites
        person_favs = get_favorites_for_slug(slug)
        total_favs = person_totals.get(slug, 0)
        
        filename = path.name
        
        description = (
            f"**#{page_num}** {name}\n"
            f"File: `{filename}`\n"
            f"❤️ {fav_count} favorites\n\n"
            f"**{name}'s Stats:**\n"
            f"• {total_favs} total favorites\n"
            f"• {len(person_favs)} favorited files"
        )
        
        embed = discord.Embed(
            title=f"Top {media_type.capitalize()}",
            description=description,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Page {page_num}/{total_pages}")
        
        # Attach file
        hero_file = None
        if path.exists():
            hero_file = discord.File(str(path))
            embed.set_image(url=f"attachment://{hero_file.filename}")
        
        files = [hero_file] if hero_file else []
        return embed, files
    
    # Single item
    if total_pages == 1:
        embed, files = await render_page(1)
        return await interaction.response.send_message(embed=embed, files=files)
    
    # Multiple items - pagination
    class GlobalTypePaginationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
            self.current_page = 1
            self.total_pages = total_pages
        
        @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
        async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 1:
                self.current_page -= 1
                await self._update(interaction)
        
        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < self.total_pages:
                self.current_page += 1
                await self._update(interaction)
        
        async def _update(self, interaction: discord.Interaction):
            embed, files = await render_page(self.current_page)
            
            # Update button states
            self.prev_button.disabled = (self.current_page == 1)
            self.next_button.disabled = (self.current_page == self.total_pages)
            
            await interaction.response.edit_message(embed=embed, attachments=files, view=self)
    
    view = GlobalTypePaginationView()
    view.prev_button.disabled = True
    
    embed, files = await render_page(1)
    
    await interaction.response.send_message(embed=embed, files=files, view=view)


# ================================================================
# Register the Cog + Commands
# ================================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(RankingsCog(bot))
    bot.tree.add_command(rank)
