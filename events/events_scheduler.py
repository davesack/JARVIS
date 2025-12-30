from __future__ import annotations

import json
import random
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import aiohttp
import discord

from config import EVENTS_MEDIA_ROOT, GIPHY_API_KEY
from .events_db import get_events_for_date, Event


# --------------------------------------------------
# Media repetition tracking
# --------------------------------------------------

MEDIA_HISTORY_FILE = EVENTS_MEDIA_ROOT / "_recent_media.json"
EVENTS_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _load_media_history() -> dict:
    if not MEDIA_HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(MEDIA_HISTORY_FILE.read_text())
    except Exception:
        return {}


def _save_media_history(data: dict) -> None:
    MEDIA_HISTORY_FILE.write_text(json.dumps(data, indent=2))


def _pick_random_gif(event_type: str) -> Optional[Path]:
    """
    Picks a random GIF from:
      media/events/<event_type>/
    while avoiding recent repeats.
    """
    folder = EVENTS_MEDIA_ROOT / event_type.lower()
    if not folder.exists() or not folder.is_dir():
        return None

    gifs = [p for p in folder.iterdir() if p.suffix.lower() == ".gif"]
    if not gifs:
        return None

    history = _load_media_history()
    recent = set(history.get(event_type, [])[-5:])

    available = [g for g in gifs if g.name not in recent] or gifs
    chosen = random.choice(available)

    history.setdefault(event_type, []).append(chosen.name)
    history[event_type] = history[event_type][-10:]
    _save_media_history(history)

    return chosen


async def _get_giphy_url(event_type: str) -> Optional[str]:
    if not GIPHY_API_KEY:
        return None

    params = {
        "api_key": GIPHY_API_KEY,
        "q": event_type,
        "limit": 10,
        "rating": "pg",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.giphy.com/v1/gifs/search",
                params=params,
                timeout=5,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        return None

    results = data.get("data", [])
    if not results:
        return None

    return random.choice(results)["images"]["original"]["url"]


# --------------------------------------------------
# Event wording
# --------------------------------------------------

EVENT_COPY = {
    "birthday": {
        "emoji": "🎂",
        "title": "Birthday",
        "lines": [
            "Today we celebrate **{name}**! 🎉",
            "It's **{name}**'s special day! 🥳",
            "Everyone wish **{name}** a very happy birthday! 🎈",
        ],
        "years_label": "Turning",
        "years_suffix": "birthday",
    },
    "anniversary": {
        "emoji": "💍",
        "title": "Anniversary",
        "lines": [
            "Today we celebrate **{name}**'s anniversary! 💖",
            "Cheers to **{name}** on this special anniversary! 🥂",
            "Another year, another milestone for **{name}**! ✨",
        ],
        "years_label": "Celebrating",
        "years_suffix": "anniversary",
    },
    "memorial": {
        "emoji": "🕊️",
        "title": "In Memoriam",
        "lines": [
            "Today we remember **{name}**. 🤍",
            "Remembering **{name}** on this day. 🕯️",
            "Honoring the memory of **{name}** today. 🌹",
        ],
        "years_label": "Years Since",
        "years_suffix": None,
    },
}


# --------------------------------------------------
# Embed builder
# --------------------------------------------------

def build_event_embed(event: Event, today: date) -> discord.Embed:
    cfg = EVENT_COPY.get(event.type, EVENT_COPY["birthday"])

    years = max(1, today.year - event.start_year)
    ordinal_year = _ordinal(years)

    embed = discord.Embed(
        title=f"{cfg['emoji']} {cfg['title']}: {event.name}",
        description=random.choice(cfg["lines"]).format(name=event.name),
        timestamp=datetime.utcnow(),
        color=discord.Color.blurple(),
    )

    if event.show_age:
        if cfg["years_suffix"]:
            value = f"{ordinal_year} {cfg['years_suffix']}"
        else:
            value = f"{years}"

        embed.add_field(
            name=cfg["years_label"],
            value=value,
            inline=True,
        )

    embed.add_field(name="Date", value=event.date, inline=True)

    if event.notes:
        embed.add_field(name="Notes", value=event.notes, inline=False)

    embed.set_footer(text="JARVIS Celebration System")
    return embed


# --------------------------------------------------
# Posting logic
# --------------------------------------------------

async def post_events_for_date(
    bot: discord.Client,
    target_date: Optional[date] = None,
) -> int:
    target_date = target_date or date.today()
    events = get_events_for_date(target_date)
    count = 0

    for event in events:
        channel = bot.get_channel(event.channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(event.channel_id)
            except Exception:
                continue

        if not isinstance(channel, discord.abc.Messageable):
            continue

        embed = build_event_embed(event, target_date)

        gif = _pick_random_gif(event.type)
        if gif:
            file = discord.File(gif, filename=gif.name)
            embed.set_image(url=f"attachment://{gif.name}")
            await channel.send(embed=embed, file=file)
        else:
            giphy = await _get_giphy_url(event.type)
            if giphy:
                embed.set_image(url=giphy)
            await channel.send(embed=embed)

        count += 1

    return count
