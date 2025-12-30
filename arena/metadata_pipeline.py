# utils/arena/metadata_pipeline.py

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

import arena_config

from tools.scrapers.sources import (
    BabepediaScraper,
    BoobpediaScraper,
    IAFDScraper,
    Data18Scraper,
    TMDBScraper,
)
from tools.scrapers.mappers import (
    BabepediaMapper,
    BoobpediaMapper,
    IAFDMapper,
    Data18Mapper,
    TMDBMapper,
)
from tools.scrapers.merg_engine import MergeEngine
from tools.scrapers.normalizer import Normalizer
from utils.arena.metadata_enricher import MetadataEnricher
from utils.arena.slugger import slugify
from utils.sheets.google_sheets import GoogleSheetsClient



OUTPUT_FILE = Path(arena_config.DATA_DIR) / "metadata_enriched.json"


class MetadataPipeline:
    def __init__(self):
        self.sheets = GoogleSheetsClient()
        self.merge_engine = MergeEngine()

        self.scrapers = [
            (BabepediaScraper(), BabepediaMapper()),
            (BoobpediaScraper(), BoobpediaMapper()),
            (IAFDScraper(), IAFDMapper()),
            (Data18Scraper(), Data18Mapper()),
            (TMDBScraper(), TMDBMapper()),
            # TMDB goes here later as a normal source
        ]

    # --------------------------------------------------
    # PUBLIC
    # --------------------------------------------------

    async def run(self, names: List[str] | None = None) -> int:
        if not names:
            names = self._collect_names()

        results = []

        for name in sorted(set(names)):
            merged = await self._process_name(name)
            if merged:
                results.append(merged)

        payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "entries": results,
        }

        OUTPUT_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        MetadataEnricher().run()
        return len(results)

    # --------------------------------------------------
    # INTERNALS
    # --------------------------------------------------

    def _collect_names(self) -> List[str]:
        rows = self.sheets.read_column(
            spreadsheet_id=arena_config.METADATA_SHEET["spreadsheet_id"],
            sheet_name=arena_config.METADATA_SHEET["sheet_name"],
            column="A",
        )
        return [r for r in rows if r]

    async def _process_name(self, name: str) -> Dict:
        mapped = []

        for scraper, mapper in self.scrapers:
            raw = await scraper.fetch(name)
            if not raw:
                continue

            normalized = mapper.map(raw)
            if normalized:
                mapped.append(normalized)

        if not mapped:
            return {}

        merged = self.merge_engine.merge(mapped)
        merged["name"] = name
        merged["slug"] = slugify(name)

        return Normalizer.normalize_metadata(merged)
