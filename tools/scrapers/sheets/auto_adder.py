#!/usr/bin/env python3
"""
JARVIS Arena – Auto Adder (ARENA_INTAKE)
...
"""

from __future__ import annotations
import sys
import io
from pathlib import Path

# Force UTF-8 encoding for stdout/stderr on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parents[3]))

import json
from datetime import datetime
from typing import Dict, List

from tools.scrapers.sheets.sheet_client import SheetClient
import arena_config


DATA_FILE = Path(arena_config.DATA_DIR) / "arena_candidates.json"


class ArenaAutoAdder:
    def __init__(self):
        self.sheets = SheetClient()
        self.sheet_cfg = arena_config.ARENA_INTAKE_SHEET

    # ------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------

    def run(self) -> int:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        candidates = data.get("candidates", [])

        if not candidates:
            return 0

        existing = self._existing_names()
        rows = []

        now = datetime.utcnow().isoformat()

        for c in candidates:
            if not c.get("auto_add"):
                continue

            name = c["name"]
            if name in existing:
                continue

            rows.append(self._build_row(c, now))

        if rows:
            self.sheets.append_rows(
                spreadsheet_id=self.sheet_cfg["spreadsheet_id"],
                sheet_name=self.sheet_cfg["sheet_name"],
                rows=rows,
            )

        return len(rows)

    # ------------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------------

    def _existing_names(self) -> set[str]:
        rows = self.sheets.read_column(
            spreadsheet_id=self.sheet_cfg["spreadsheet_id"],
            sheet_name=self.sheet_cfg["sheet_name"],
            column="A",
        )
        return {r for r in rows if r}

    def _build_row(self, c: Dict, timestamp: str) -> List:
        metadata = c.get("metadata", {})

        return [
            c.get("name"),
            round(c.get("discovery_score", 0), 2),
            c.get("source_count", 0),
            metadata.get("height"),
            metadata.get("measurements"),
            metadata.get("ethnicity"),
            metadata.get("nationality"),
            metadata.get("hair_color"),
            metadata.get("eye_color"),
            ", ".join(metadata.get("tags", [])),
            timestamp,
            "PENDING",
        ]


if __name__ == "__main__":
    added = ArenaAutoAdder().run()
    print(f"Added {added} rows to ARENA_INTAKE")
