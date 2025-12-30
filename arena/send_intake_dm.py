#!/usr/bin/env python3
"""
Send DM to owner about new ARENA_INTAKE entries.

This is called as the final step in discovery_runner.
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
import requests
import arena_config
from config import DISCORD_OWNER_ID, TOKEN

# Load discovery notifications
notif_file = Path(arena_config.DATA_DIR) / "discovery_notifications.json"

if not notif_file.exists():
    print("ℹ️  No new candidates to notify about")
    sys.exit(0)

with open(notif_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

candidates = data.get('notifications', [])

if not candidates:
    print("ℹ️  No new candidates found")
    sys.exit(0)

print(f"📬 Sending DM about {len(candidates)} new candidates...")

# Build embed using Discord webhook/DM API
embed = {
    "title": "🔍 New Arena Candidates Discovered",
    "description": f"Found **{len(candidates)}** new candidates for your rankings!",
    "color": 15844367,  # Gold
    "fields": [],
    "footer": {
        "text": "Check ARENA_INTAKE sheet to review and approve"
    }
}

# Add top candidates (limit to 10)
display_count = min(len(candidates), 10)

for i, candidate in enumerate(candidates[:display_count], 1):
    name = candidate.get('name', 'Unknown')
    score = candidate.get('discovery_score', 0)
    sources = candidate.get('source_count', 0)
    archetype = candidate.get('archetype', 'Unknown')
    
    field_value = f"**Score:** {score}/100\n**Sources:** {sources}/4\n**Type:** {archetype}"
    
    reasons = candidate.get('reasons', [])
    if reasons:
        field_value += f"\n• {reasons[0]}"
    
    embed["fields"].append({
        "name": f"{i}. {name}",
        "value": field_value,
        "inline": False
    })

# Add overflow notice
if len(candidates) > display_count:
    remaining = len(candidates) - display_count
    embed["fields"].append({
        "name": "➕ And More...",
        "value": f"Plus **{remaining}** additional candidates",
        "inline": False
    })

# Create DM channel with owner
headers = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Create DM channel
dm_response = requests.post(
    "https://discord.com/api/v10/users/@me/channels",
    headers=headers,
    json={"recipient_id": str(DISCORD_OWNER_ID)}
)

if dm_response.status_code != 200:
    print(f"❌ Failed to create DM channel: {dm_response.status_code}")
    print(dm_response.text)
    sys.exit(1)

dm_channel_id = dm_response.json()["id"]

# Step 2: Send message to DM channel
msg_response = requests.post(
    f"https://discord.com/api/v10/channels/{dm_channel_id}/messages",
    headers=headers,
    json={"embeds": [embed]}
)

if msg_response.status_code == 200:
    print(f"✅ Sent DM about {len(candidates)} new candidates")
else:
    print(f"❌ Failed to send DM: {msg_response.status_code}")
    print(msg_response.text)
    sys.exit(1)
