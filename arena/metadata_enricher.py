#!/usr/bin/env python3
"""
JARVIS Arena — Metadata Enricher

Purpose:
- Fill missing metadata fields for existing METADATA rows
- Never overwrite curated values
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from utils.sheets.google_sheets import GoogleSheetsClient
import arena_config


METADATA_FILE = Path(arena_config.DATA_DIR) / "metadata_enriched.json"


SAFE_FIELDS = [
    "height",
    "measurements",
    "ethnicity",
    "nationality",
    "hair_color",
    "eye_color",
]


class MetadataEnricher:
    def __init__(self):
        self.sheets = GoogleSheetsClient()
        self.sheet_cfg = arena_config.METADATA_SHEET

    # ------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------

    def run(self) -> int:
        scraped = self._load_scraped_metadata()
        rows = self.sheets.read_rows(
            spreadsheet_id=self.sheet_cfg["spreadsheet_id"],
            sheet_name=self.sheet_cfg["sheet_name"],
        )

        if not rows:
            return 0

        header = rows[0]
        updated = 0

        name_idx = header.index("name")
        col_map = {col: i for i, col in enumerate(header)}

        for i, row in enumerate(rows[1:], start=2):
            name = row[name_idx]
            if not name or name not in scraped:
                continue

            updated_row = list(row)
            changed = False
            src = scraped[name]

            for field in SAFE_FIELDS:
                idx = col_map.get(field)
                if idx is None:
                    continue

                if not updated_row[idx] and src.get(field):
                    updated_row[idx] = src[field]
                    changed = True

            # tags (merge)
            if "tags" in col_map and src.get("tags"):
                idx = col_map["tags"]
                existing = set(str(updated_row[idx]).split(",")) if updated_row[idx] else set()
                merged = existing | set(src["tags"])
                updated_row[idx] = ", ".join(sorted(t.strip() for t in merged if t.strip()))
                if merged != existing:
                    changed = True

            if changed:
                self.sheets.update_row(
                    spreadsheet_id=self.sheet_cfg["spreadsheet_id"],
                    sheet_name=self.sheet_cfg["sheet_name"],
                    row_number=i,
                    values=updated_row,
                )
                updated += 1

        return updated

    # ------------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------------

    def _load_scraped_metadata(self) -> Dict[str, Dict[str, Any]]:
        data = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
        return {e["name"]: e for e in data.get("entries", [])}


if __name__ == "__main__":
    count = MetadataEnricher().run()
    print(f"Enriched {count} METADATA rows")
