from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import List, Optional, Dict, Any

from config import EVENTS_DB as EVENTS_DB_PATH

EVENTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Event:
    id: str
    guild_id: int
    name: str
    type: str
    date: str           # MM-DD
    start_year: int
    channel_id: int
    created_by: int
    notes: Optional[str] = None
    show_age: bool = True


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data["id"],
            guild_id=int(data["guild_id"]),
            name=data["name"],
            type=data["type"],
            date=data["date"],
            start_year=int(data["start_year"]),
            channel_id=int(data["channel_id"]),
            created_by=int(data["created_by"]),
            notes=data.get("notes"),
            show_age=data.get("show_age", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------
# Raw DB helpers
# --------------------------------------------------

def _load_raw_db() -> Dict[str, Any]:
    if not EVENTS_DB_PATH.exists():
        return {"events": []}
    try:
        with EVENTS_DB_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"events": []}


def _save_raw_db(data: Dict[str, Any]) -> None:
    tmp = EVENTS_DB_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(EVENTS_DB_PATH)


# --------------------------------------------------
# Public API
# --------------------------------------------------

def load_events() -> List[Event]:
    raw = _load_raw_db()
    events = []
    for e in raw.get("events", []):
        try:
            events.append(Event.from_dict(e))
        except Exception:
            continue
    return events


def save_events(events: List[Event]) -> None:
    _save_raw_db({"events": [e.to_dict() for e in events]})


def add_event(
    *,
    guild_id: int,
    name: str,
    event_type: str,
    month: int,
    day: int,
    start_year: int,
    channel_id: int,
    created_by: int,
    notes: Optional[str] = None,
    show_age: bool = True,
) -> Event:
    events = load_events()
    mm_dd = f"{month:02d}-{day:02d}"

    # Duplicate protection
    for e in events:
        if (
            e.guild_id == guild_id
            and e.name.lower() == name.lower()
            and e.type == event_type.lower()
            and e.date == mm_dd
        ):
            raise ValueError("Duplicate event already exists.")

    event = Event(
        id=str(uuid.uuid4()),
        guild_id=guild_id,
        name=name.strip(),
        type=event_type.strip().lower(),
        date=mm_dd,
        start_year=start_year,
        channel_id=channel_id,
        created_by=created_by,
        notes=notes.strip() if notes else None,
        show_age=show_age,
    )

    events.append(event)
    save_events(events)
    return event


def update_event(event_id: str, **updates) -> Optional[Event]:
    events = load_events()
    for e in events:
        if e.id == event_id:
            for key, value in updates.items():
                if hasattr(e, key) and value is not None:
                    setattr(e, key, value)
            save_events(events)
            return e
    return None


def delete_event(event_id: str, guild_id: Optional[int] = None) -> bool:
    events = load_events()
    new_events = []
    deleted = False

    for e in events:
        if e.id == event_id and (guild_id is None or e.guild_id == guild_id):
            deleted = True
            continue
        new_events.append(e)

    if deleted:
        save_events(new_events)
    return deleted


def list_events(guild_id: Optional[int] = None) -> List[Event]:
    events = load_events()
    return [e for e in events if guild_id is None or e.guild_id == guild_id]


def get_events_for_date(target_date: date) -> List[Event]:
    mm_dd = f"{target_date.month:02d}-{target_date.day:02d}"
    return [e for e in load_events() if e.date == mm_dd]
