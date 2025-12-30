from __future__ import annotations

import json
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import DATA_ROOT

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BSKY_DATA_ROOT = DATA_ROOT / "bsky"
BSKY_DATA_ROOT.mkdir(parents=True, exist_ok=True)

SUBS_FILE = BSKY_DATA_ROOT / "bsky_subscriptions.json"
LAST_SEEN_FILE = BSKY_DATA_ROOT / "bsky_last_seen.json"


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

@dataclass
class Subscription:
    handle: str
    thread_id: Optional[int] = None
    interval_minutes: Optional[int] = None
    next_check_ts: Optional[float] = None


# ------------------------------------------------------------------
# Singleton State
# ------------------------------------------------------------------

_state_lock = threading.Lock()
_shared_state: Optional["BlueskyState"] = None


def get_shared_state() -> "BlueskyState":
    global _shared_state
    if _shared_state is None:
        _shared_state = BlueskyState()
    return _shared_state


# ------------------------------------------------------------------
# State Class
# ------------------------------------------------------------------

class BlueskyState:
    """
    Authoritative persistent state for Bluesky monitoring.

    Guarantees:
      âœ” Atomic writes
      âœ” Single in-memory instance
      âœ” Forward-only watermark movement
      âœ” Safe recovery from corruption
    """

    def __init__(self):
        self.guild_id: Optional[int] = None
        self.parent_channel_id: Optional[int] = None

        self.subscriptions: List[Subscription] = []
        self.slug_map: Dict[str, str] = {}
        self.last_seen: Dict[str, str] = {}

        self._load_subscriptions()
        self._load_last_seen()

    # ------------------------------------------------------------------
    # Atomic helpers
    # ------------------------------------------------------------------

    def _atomic_write(self, path: Path, data: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)

    def _backup_corrupt(self, path: Path):
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_suffix(path.suffix + f".corrupt-{ts}.bak")
        path.rename(backup)

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def _load_subscriptions(self) -> None:
        if not SUBS_FILE.exists():
            return

        try:
            with SUBS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self._backup_corrupt(SUBS_FILE)
            return

        self.guild_id = data.get("guild_id")
        self.parent_channel_id = data.get("parent_channel_id")

        self.subscriptions = [
            Subscription(
                handle=s["handle"].lower(),
                thread_id=s.get("thread_id"),
                interval_minutes=s.get("interval_minutes"),
                next_check_ts=s.get("next_check_ts"),
            )
            for s in data.get("subscriptions", [])
            if "handle" in s
        ]

        self.slug_map = {k.lower(): v for k, v in data.get("slug_map", {}).items()}

    def _save_subscriptions(self) -> None:
        with _state_lock:
            payload = {
                "guild_id": self.guild_id,
                "parent_channel_id": self.parent_channel_id,
                "subscriptions": [asdict(s) for s in self.subscriptions],
                "slug_map": self.slug_map,
            }
            self._atomic_write(SUBS_FILE, payload)

    def _load_last_seen(self) -> None:
        if not LAST_SEEN_FILE.exists():
            self._save_last_seen()
            return

        try:
            with LAST_SEEN_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self._backup_corrupt(LAST_SEEN_FILE)
            self.last_seen = {}
            self._save_last_seen()
            return

        raw = data.get("last_seen", data)
        self.last_seen = {k.lower(): v for k, v in raw.items()}

    def _save_last_seen(self) -> None:
        with _state_lock:
            self._atomic_write(LAST_SEEN_FILE, {"last_seen": self.last_seen})

    # ------------------------------------------------------------------
    # Watermark logic (MOST IMPORTANT)
    # ------------------------------------------------------------------

    def get_last_seen_uri(self, handle: str) -> Optional[str]:
        return self.last_seen.get(handle.lower())

    def set_last_seen_uri(self, handle: str, uri: str) -> None:
        """
        Watermark moves FORWARD ONLY.
        Never regress. Never overwrite newer data.
        """
        handle = handle.lower()
        current = self.last_seen.get(handle)

        if current == uri:
            return

        self.last_seen[handle] = uri
        self._save_last_seen()
        print(f"[BSKY_STATE] Watermark advanced @{handle} â†’ {uri}")

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def get_subscription(self, handle: str) -> Optional[Subscription]:
        handle = handle.lower()
        return next((s for s in self.subscriptions if s.handle == handle), None)

    def list_handles(self) -> List[str]:
        return [s.handle for s in self.subscriptions]

    def add_subscription(
        self, 
        handle: str, 
        thread_id: Optional[int] = None,
        interval_minutes: Optional[int] = None
    ) -> bool:
        handle = handle.lower()
        if self.get_subscription(handle):
            return False
        self.subscriptions.append(Subscription(
            handle=handle,
            thread_id=thread_id,
            interval_minutes=interval_minutes
        ))
        self._save_subscriptions()
        return True

    def remove_subscription(self, handle: str) -> bool:
        handle = handle.lower()
        before = len(self.subscriptions)
        self.subscriptions = [s for s in self.subscriptions if s.handle != handle]

        if len(self.subscriptions) < before:
            self.last_seen.pop(handle, None)
            self._save_subscriptions()
            self._save_last_seen()
            return True
        return False

    # ------------------------------------------------------------------
    # Thread mapping
    # ------------------------------------------------------------------

    def set_thread_id(self, handle: str, thread_id: int) -> None:
        sub = self.get_subscription(handle)
        if not sub:
            sub = Subscription(handle=handle.lower())
            self.subscriptions.append(sub)

        sub.thread_id = thread_id
        self._save_subscriptions()

    def get_thread_id(self, handle: str) -> Optional[int]:
        sub = self.get_subscription(handle)
        return sub.thread_id if sub else None

    def get_subscription_by_thread(self, thread_id: int) -> Optional[Subscription]:
        return next((s for s in self.subscriptions if s.thread_id == thread_id), None)

    # ------------------------------------------------------------------
    # Intervals
    # ------------------------------------------------------------------

    def set_interval(self, handle: str, minutes: Optional[int]) -> None:
        sub = self.get_subscription(handle)
        if sub:
            sub.interval_minutes = minutes
            self._save_subscriptions()

    def get_all_intervals(self) -> Dict[str, int]:
        return {
            s.handle: s.interval_minutes
            for s in self.subscriptions
            if s.interval_minutes is not None
        }

    def initialize_intervals(self, default_minutes: int) -> None:
        import discord
        import random

        now = discord.utils.utcnow().timestamp()
        for sub in self.subscriptions:
            if sub.next_check_ts is None:
                minutes = sub.interval_minutes or default_minutes
                sub.next_check_ts = now + random.uniform(0, minutes * 60)

        self._save_subscriptions()

    def get_due_subscriptions(self, current_ts: float) -> List[Subscription]:
        return [
            s for s in self.subscriptions
            if s.next_check_ts and s.next_check_ts <= current_ts
        ]

    def update_next_check(self, handle: str, current_ts: float, default_minutes: int) -> None:
        sub = self.get_subscription(handle)
        if not sub:
            return

        minutes = sub.interval_minutes or default_minutes
        sub.next_check_ts = current_ts + (minutes * 60)
        self._save_subscriptions()

    # ------------------------------------------------------------------
    # Slug mapping
    # ------------------------------------------------------------------

    def set_slug(self, handle: str, slug: str) -> None:
        self.slug_map[handle.lower()] = slug
        self._save_subscriptions()

    def remove_slug(self, handle: str) -> bool:
        handle = handle.lower()
        if handle in self.slug_map:
            del self.slug_map[handle]
            self._save_subscriptions()
            return True
        return False

    def get_slug_map(self) -> Dict[str, str]:
        return dict(self.slug_map)
