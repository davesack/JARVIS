#!/usr/bin/env python3
"""
JARVIS Arena — Discovery Notifier (Phase 3)

Consumes processed external signals + metadata pipeline output and
produces structured discovery recommendations.

This module is READ-ONLY with respect to scrapers.
No scraping occurs here.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import arena_config


class DiscoveryNotifier:
    """
    Evaluates processed external signals and emits discovery notifications
    for performers not yet present in the main rankings dataset.
    """

    def __init__(self):
        self.data_dir = Path(arena_config.DATA_DIR)
        self.db_path = self.data_dir / "external_signals.db"

        # Thresholds (single source of truth)
        self.min_sources = arena_config.MIN_SOURCE_COUNT
        self.min_discovery_score = arena_config.MIN_DISCOVERY_SCORE
        self.high_confidence_score = arena_config.HIGH_CONFIDENCE_THRESHOLD

        self.output_path = self.data_dir / "discovery_notifications.json"

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def generate(self, existing_names: Optional[List[str]] = None) -> List[Dict]:
        """
        Generate discovery notifications.

        Args:
            existing_names: Names already present in Google Sheet / rankings

        Returns:
            List of notification dictionaries
        """

        if existing_names is None:
            existing_names = []

        candidates = self._fetch_candidates()
        notifications: List[Dict] = []

        for row in candidates:
            name = row["name"]

            if name in existing_names:
                continue

            notif = self._build_notification(row)
            notifications.append(notif)

        self._save(notifications)
        self._print(notifications)

        return notifications

    # ------------------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------------------

    def _fetch_candidates(self) -> List[Dict]:
        """Pull qualifying candidates from SQLite."""

        query = """
            SELECT
                name,
                discovery_score,
                source_count,
                competitive_score,
                momentum_score,
                resume_score,
                appeal_score,
                cb_rank,
                ce_tier,
                bl_tier,
                bp_top100_rank,
                bp_most_viewed_rank
            FROM external_signals
            WHERE discovery_score >= ?
              AND source_count >= ?
            ORDER BY discovery_score DESC
        """

        rows: List[Dict] = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                query,
                (self.min_discovery_score, self.min_sources),
            )
            for row in cursor.fetchall():
                rows.append(dict(row))

        return rows

    def _build_notification(self, row: Dict) -> Dict:
        """Create a structured notification payload."""

        disc = row["discovery_score"]
        sources = row["source_count"]

        if disc >= self.high_confidence_score:
            level = "HIGH_CONFIDENCE"
            emoji = "🏆"
        elif sources >= 4:
            level = "CONSENSUS"
            emoji = "✨"
        else:
            level = "STANDARD"
            emoji = "🔍"

        reasons = self._build_reasons(row)
        archetype = self._determine_archetype(
            row["competitive_score"],
            row["momentum_score"],
            row["resume_score"],
            row["appeal_score"],
        )

        return {
            "name": row["name"],
            "level": level,
            "emoji": emoji,
            "discovery_score": round(disc, 1),
            "source_count": sources,
            "scores": {
                "competitive": round(row["competitive_score"], 1),
                "momentum": round(row["momentum_score"], 1),
                "resume": round(row["resume_score"], 1),
                "appeal": round(row["appeal_score"], 1),
            },
            "archetype": archetype,
            "reasons": reasons,
            "external_snapshot": {
                "celebbattles_rank": row["cb_rank"],
                "economy_tier": row["ce_tier"],
                "battleleague_tier": row["bl_tier"],
                "babepedia_top100": row["bp_top100_rank"],
                "babepedia_views": row["bp_most_viewed_rank"],
            },
            "generated_at": datetime.now().isoformat(),
        }

    def _build_reasons(self, row: Dict) -> List[str]:
        """Human-readable justification list."""

        reasons: List[str] = []

        if row.get("cb_rank") and row["cb_rank"] <= 10:
            reasons.append(f"Top {row['cb_rank']} in CelebBattles")

        if row.get("ce_tier") in {"A", "B"}:
            reasons.append(f"Tier {row['ce_tier']} market momentum")

        if row.get("bl_tier"):
            reasons.append(f"BattleLeague tier: {row['bl_tier']}")

        if row.get("bp_top100_rank") and row["bp_top100_rank"] <= 50:
            reasons.append("Babepedia Top 50 appearance")

        if row.get("bp_most_viewed_rank") and row["bp_most_viewed_rank"] <= 50:
            reasons.append("High Babepedia view activity")

        return reasons

    # ------------------------------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------------------------------

    def _determine_archetype(
        self, comp: float, mom: float, res: float, app: float
    ) -> str:
        """Classify discovery archetype."""

        if all(v >= 70 for v in (comp, mom, res, app)):
            return "Consensus Monster"

        if comp >= 70 and app < 60:
            return "Technical Fighter"

        if app >= 70 and comp < 60:
            return "Visual Darling"

        if mom >= 75:
            return "Hype Surge"

        if comp >= 65 and res >= 65:
            return "Battle-Tested"

        if mom >= 65 and app >= 65:
            return "Rising Star"

        return "Well-Rounded Candidate"

    # ------------------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------------------

    def _save(self, notifications: List[Dict]) -> None:
        payload = {
            "generated_at": datetime.now().isoformat(),
            "count": len(notifications),
            "criteria": {
                "min_sources": self.min_sources,
                "min_discovery_score": self.min_discovery_score,
                "high_confidence_score": self.high_confidence_score,
            },
            "notifications": notifications,
        }

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _print(self, notifications: List[Dict]) -> None:
        print("=" * 80)
        print("🔔 DISCOVERY NOTIFICATIONS")
        print("=" * 80)

        if not notifications:
            print("No new discovery candidates found.")
            return

        for n in notifications:
            print(f"{n['emoji']} {n['name']} — {n['level']}")
            print(f"  Score: {n['discovery_score']} | Sources: {n['source_count']}")
            print(f"  Archetype: {n['archetype']}")
            if n["reasons"]:
                for r in n["reasons"]:
                    print(f"   • {r}")
            print()


if __name__ == "__main__":
    notifier = DiscoveryNotifier()

    # Example stub — in production, load from Google Sheet sync
    existing = ["Salma Hayek", "Eva Mendes", "Hayley Atwell"]

    notifier.generate(existing)
