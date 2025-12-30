#!/usr/bin/env python3
"""
JARVIS Arena - Metadata Enrichment Workflow

This workflow:
1. Reads your existing 445 people from METADATA sheet
2. Scrapes Babepedia, Boobpedia, IAFD, Data18 for each person
3. Extracts measurements, physical attributes
4. Updates METADATA sheet with the enriched data

Run manually:
    python tools/scrapers/enrich_metadata_workflow.py

Or add to discovery_runner for periodic updates.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from typing import Dict, List
import arena_config
from metadata_scraper import MetadataScraper  # Relative import
from sheets.sheet_client import SheetClient  # Relative import

# Output file
OUTPUT_FILE = Path(arena_config.DATA_DIR) / "metadata_enriched.json"


def read_existing_names() -> List[str]:
    """Read names from METADATA sheet."""
    from tools.scrapers.sheets.sheet_client import SheetClient
    
    sheets = SheetClient()
    cfg = arena_config.METADATA_SHEET
    
    # Read column A (names) starting from row 2
    names = sheets.read_column(
        spreadsheet_id=cfg["spreadsheet_id"],
        sheet_name=cfg["sheet_name"],
        column="A",
    )
    
    # Filter out header and empty rows
    return [name for name in names[1:] if name]  # Skip header row


def scrape_metadata_for_names(names: List[str]) -> Dict:
    """Scrape metadata for a list of names."""
    scraper = MetadataScraper(data_dir=str(arena_config.DATA_DIR))
    results = []
    
    print(f"\n🔍 Starting metadata scraping for {len(names)} people...")
    print("=" * 60)
    
    for i, name in enumerate(names, 1):
        print(f"\n[{i}/{len(names)}] Processing: {name}")
        
        metadata = {}
        
        # Scrape physical/biographical data only
        # CelebBattles competitive stats are scraped separately for Arena
        sources = [
            ("Boobpedia", scraper.scrape_boobpedia),
        ]
        
        for source_name, scrape_func in sources:
            try:
                data = scrape_func(name)
                if data and not data.get('error'):
                    metadata[source_name.lower()] = data
                    print(f"  ✅ {source_name}: Found data")
                else:
                    print(f"  ⚠️  {source_name}: No data")
            except Exception as e:
                print(f"  ❌ {source_name}: Error - {e}")
        
        if metadata:
            # Merge data from all sources
            merged = merge_metadata(name, metadata)
            results.append(merged)
        else:
            print(f"  ℹ️  No data found (likely Group 1 personal contact)")
        
        # Rate limiting
        time.sleep(arena_config.REQUEST_DELAY)
    
    print("\n" + "=" * 60)
    print(f"✅ Scraped metadata for {len(results)} people")
    
    return {"entries": results, "total": len(results)}


def merge_metadata(name: str, sources: Dict) -> Dict:
    """Merge metadata from multiple sources into single entry."""
    merged = {
        "name": name,
        "boobpedia": sources.get("boobpedia"),
    }
    
    # Only one source now
    priority = ["boobpedia"]
    
    fields = [
        "height", "measurements", "bust", "waist", "hips",
        "bra_size", "cup_size", "weight",
        "ethnicity", "nationality", "hair_color", "eye_color",
        "birthdate", "birthplace", "biography", "born",
        "years_active", "body_type", "boobs", "shown",
        "rating", "rank", "battles", "win_rate",
        "professions", "sexuality"
    ]
    
    for field in fields:
        for source in priority:
            if source in sources and sources[source].get(field):
                merged[field] = sources[source][field]
                break
    
    # Collect tags from all sources
    tags = set()
    for source_data in sources.values():
        if isinstance(source_data, dict) and source_data.get("tags"):
            tags.update(source_data["tags"])
    
    if tags:
        merged["tags"] = list(tags)
    
    return merged


def main():
    """Run the complete metadata enrichment workflow."""
    print("🎯 JARVIS Metadata Enrichment Workflow")
    print("=" * 60)
    
    # Step 1: Read existing names
    print("\n📋 Step 1: Reading names from METADATA sheet...")
    names = read_existing_names()
    print(f"   Found {len(names)} people in METADATA")
    
    # Step 2: Scrape metadata
    print("\n🔍 Step 2: Scraping metadata from external sources...")
    print("   Sources: Babepedia, Boobpedia, IAFD, Data18")
    enriched_data = scrape_metadata_for_names(names)
    
    # Step 3: Save results to JSON (backup)
    print("\n💾 Step 3: Saving enriched metadata...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(enriched_data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"   Saved to: {OUTPUT_FILE}")
    
    # Step 4: Write to METADATA_ENRICHED sheet
    print("\n📝 Step 4: Writing to METADATA_ENRICHED sheet...")
    from tools.scrapers.sheets.sheet_client import SheetClient
    from datetime import datetime
    
    sheets = SheetClient()
    cfg = arena_config.GOOGLE_SHEETS["metadata_enriched"]
    
    # Build rows for sheet
    rows = []
    timestamp = datetime.now().isoformat()
    
    for entry in enriched_data["entries"]:
        # Track which sources had data
        sources = []
        if entry.get("boobpedia"):
            sources.append("Boobpedia")
        
        row = [
            entry.get("name"),
            entry.get("height"),
            entry.get("measurements"),
            entry.get("bust"),
            entry.get("waist"),
            entry.get("hips"),
            entry.get("bra_size"),
            entry.get("cup_size"),
            entry.get("weight"),
            entry.get("ethnicity"),
            entry.get("nationality"),
            entry.get("hair_color"),
            entry.get("eye_color"),
            entry.get("birthdate"),
            entry.get("birthplace"),
            ", ".join(entry.get("tags", [])),
            ", ".join(sources),
            timestamp,
            entry.get("biography", ""),
            entry.get("years_active", ""),
            entry.get("body_type", ""),
            entry.get("boobs", ""),
            entry.get("shown", ""),
            entry.get("special", ""),
        ]
        rows.append(row)
    
    if rows:
        sheets.append_rows(
            spreadsheet_id=cfg["spreadsheet_id"],
            sheet_name=cfg["sheet_name"],
            rows=rows,
        )
        print(f"   Wrote {len(rows)} rows to METADATA_ENRICHED")
    
    print("\n" + "=" * 60)
    print("🎉 Metadata enrichment complete!")
    print(f"   Total people processed: {enriched_data['total']}")
    print(f"   Rows written to METADATA_ENRICHED: {len(rows)}")
    print("\n💡 Next steps:")
    print("   1. Review data in METADATA_ENRICHED sheet")
    print("   2. Manually copy/paste desired columns to METADATA")
    print("   3. Or run again to update specific people")


if __name__ == "__main__":
    main()
