#!/usr/bin/env python3
"""
JARVIS Arena - Smart Incremental Metadata Enrichment

Only enriches people who are:
1. New (not yet enriched)
2. Missing key data fields
3. Haven't been updated recently

This makes enrichment FAST and suitable for automatic weekly runs.
"""

import sys
import io
from pathlib import Path

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from datetime import datetime, timedelta
from typing import List, Set
import arena_config
from tools.scrapers.metadata_scraper import MetadataScraper
from tools.scrapers.sheets.sheet_client import SheetClient


def get_enrichment_targets() -> List[str]:
    """
    Get list of names that need enrichment.
    
    Targets people who:
    - Don't appear in METADATA_ENRICHED yet, OR
    - Are missing key fields (measurements, height), OR  
    - Haven't been updated in 30+ days
    """
    sheets = SheetClient()
    
    # Read METADATA sheet (your 445 people)
    metadata_cfg = arena_config.METADATA_SHEET
    metadata_rows = sheets.read_rows(
        spreadsheet_id=metadata_cfg["spreadsheet_id"],
        sheet_name=metadata_cfg["sheet_name"],
    )
    
    all_names = set()
    if metadata_rows and len(metadata_rows) > 1:
        # Skip header row
        for row in metadata_rows[1:]:
            if row:  # Row has data
                name = row[0]  # Column A
                if name:
                    all_names.add(name)
    
    print(f"📋 Found {len(all_names)} people in METADATA")
    
    # Read METADATA_ENRICHED sheet
    enriched_cfg = arena_config.GOOGLE_SHEETS["metadata_enriched"]
    try:
        enriched_rows = sheets.read_rows(
            spreadsheet_id=enriched_cfg["spreadsheet_id"],
            sheet_name=enriched_cfg["sheet_name"],
        )
    except:
        enriched_rows = []
    
    enriched_data = {}
    if enriched_rows and len(enriched_rows) > 1:
        for row in enriched_rows[1:]:  # Skip header
            if not row or len(row) < 3:
                continue
            name = row[0]  # Column A
            measurements = row[2] if len(row) > 2 else None  # Column C
            last_updated_str = row[17] if len(row) > 17 else None  # Column R
            
            enriched_data[name] = {
                'has_measurements': bool(measurements),
                'last_updated': last_updated_str,
            }
    
    print(f"📊 Found {len(enriched_data)} enriched people")
    
    # Determine who needs enrichment
    targets = []
    now = datetime.now()
    
    for name in all_names:
        if name not in enriched_data:
            # Never enriched
            targets.append(name)
            continue
        
        entry = enriched_data[name]
        
        # Check if missing key data
        if not entry['has_measurements']:
            targets.append(name)
            continue
        
        # Check if outdated (30+ days)
        last_updated_str = entry.get('last_updated')
        if last_updated_str:
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
                days_old = (now - last_updated).days
                if days_old >= 30:
                    targets.append(name)
            except:
                pass
    
    print(f"🎯 Target: {len(targets)} people need enrichment")
    return targets


def enrich_targets(names: List[str]) -> List[dict]:
    """Scrape metadata for target names."""
    if not names:
        return []
    
    scraper = MetadataScraper(data_dir=str(arena_config.DATA_DIR))
    results = []
    
    print(f"\n🔍 Enriching {len(names)} people...")
    print("=" * 60)
    
    for i, name in enumerate(names, 1):
        print(f"\n[{i}/{len(names)}] {name}")
        
        metadata = {}
        sources = [
            ("Boobpedia", scraper.scrape_boobpedia),
        ]
        
        for source_name, scrape_func in sources:
            try:
                data = scrape_func(name)
                if data and not data.get('error'):
                    metadata[source_name.lower()] = data
                    print(f"  ✅ {source_name}")
            except Exception as e:
                print(f"  ❌ {source_name}: {e}")
        
        if metadata:
            merged = merge_metadata(name, metadata)
            results.append(merged)
        else:
            print(f"  ⚠️  No data found")
        
        # Rate limiting
        time.sleep(arena_config.REQUEST_DELAY)
    
    print("\n" + "=" * 60)
    print(f"✅ Enriched {len(results)}/{len(names)} people")
    return results


def merge_metadata(name: str, sources: dict) -> dict:
    """Merge metadata from multiple sources."""
    merged = {
        "name": name,
        "boobpedia": sources.get("boobpedia"),
    }
    
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
    
    # Collect tags
    tags = set()
    for source_data in sources.values():
        if isinstance(source_data, dict) and source_data.get("tags"):
            tags.update(source_data["tags"])
    
    if tags:
        merged["tags"] = list(tags)
    
    return merged


def write_to_sheet(entries: List[dict]):
    """Write enriched data to METADATA_ENRICHED sheet."""
    if not entries:
        return
    
    sheets = SheetClient()
    cfg = arena_config.GOOGLE_SHEETS["metadata_enriched"]
    timestamp = datetime.now().isoformat()
    
    rows = []
    for entry in entries:
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
    
    sheets.append_rows(
        spreadsheet_id=cfg["spreadsheet_id"],
        sheet_name=cfg["sheet_name"],
        rows=rows,
    )
    
    print(f"📝 Wrote {len(rows)} rows to METADATA_ENRICHED")


def main():
    """Run smart incremental enrichment."""
    print("🎯 JARVIS Smart Incremental Enrichment")
    print("=" * 60)
    
    # Step 1: Identify targets
    targets = get_enrichment_targets()
    
    if not targets:
        print("\n✨ All people are up-to-date! Nothing to enrich.")
        return
    
    # Step 2: Enrich targets
    enriched = enrich_targets(targets)
    
    if not enriched:
        print("\n⚠️  No new data found for any targets")
        return
    
    # Step 3: Write to sheet
    print("\n📝 Writing to METADATA_ENRICHED...")
    write_to_sheet(enriched)
    
    print("\n" + "=" * 60)
    print("🎉 Smart enrichment complete!")
    print(f"   Targets identified: {len(targets)}")
    print(f"   Successfully enriched: {len(enriched)}")


if __name__ == "__main__":
    main()
