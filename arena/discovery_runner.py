from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

DISCOVERY_STEPS = [
    ("External Rankings", "tools/scrapers/external_scraper.py"),
    ("Data Processor", "tools/scrapers/data_processor.py"),
    ("Auto Add to Sheet", "tools/scrapers/sheets/auto_adder.py"),
    ("Discord Notification", "utils/arena/send_intake_dm.py"),
    ("Smart Enrichment", "tools/scrapers/smart_enrichment.py"), 
]


def run_arena_discovery() -> list[str]:
    """
    Runs the full Arena discovery process.

    This discovers new candidates, enriches metadata,
    and optionally inserts results into the rankings sheet.

    Safe to call from:
    - scheduler
    - /admin run_discovery
    """
    logs = ["🔎 **Arena Discovery Started**"]

    for label, script in DISCOVERY_STEPS:
        logs.append(f"🚀 Running **{label}**")

        result = subprocess.run(
            [sys.executable, script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',  # Force UTF-8 for emoji support on Windows
            errors='replace',  # Replace invalid chars instead of crashing
        )

        if result.returncode != 0:
            logs.append(f"❌ **{label} failed**")
            logs.append(f"```{result.stderr}```")
            raise RuntimeError("\n".join(logs))

        logs.append(f"✅ **{label} completed**")

    logs.append("🎉 **Arena Discovery Finished Successfully**")
    return logs
