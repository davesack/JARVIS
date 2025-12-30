# utils/rankings/kobold_client.py

from __future__ import annotations

import aiohttp
from typing import List, Optional

from utils.rankings.models import RankingEntry


class KoboldClient:
    """
    Lightweight async client for generating AI-enhanced fun insights
    ("Kobold Insights") for RankingEntry profiles.

    IMPORTANT:
    - This client is SAFE BY DEFAULT.
    - If api_url is not provided, all calls return None.
    - No command depends on this being enabled.

    To enable:
    - Provide api_url
    - Optionally provide api_key
    - Ensure your Kobold endpoint matches the expected JSON format
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------

    def is_enabled(self) -> bool:
        """Return True if Kobold integration is configured."""
        return bool(self.api_url)

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    async def generate_insights(
        self,
        entry: RankingEntry,
        *,
        count: int = 3,
    ) -> Optional[List[str]]:
        """
        Generate up to `count` short, fun insights for a RankingEntry.

        Returns:
            - List[str] if successful
            - None if disabled or on any error

        This method MUST NEVER raise.
        """
        if not self.api_url:
            return None

        prompt = _build_kobold_prompt(entry, count)

        payload = {
            "prompt": prompt,
            "max_tokens": 180,
        }

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
        except Exception:
            # Absolute silence on failure by design
            return None

        # Expected response shape:
        # { "insights": ["...", "..."] }
        insights = data.get("insights")

        if not isinstance(insights, list):
            return None

        cleaned: List[str] = [
            str(text).strip()
            for text in insights
            if isinstance(text, str) and text.strip()
        ]

        if not cleaned:
            return None

        return cleaned[:count]


# ------------------------------------------------------------
# Prompt builder (internal)
# ------------------------------------------------------------

def _build_kobold_prompt(entry: RankingEntry, count: int) -> str:
    """
    Build a structured, entertainment-style prompt designed to produce
    fun, human-sounding insights — NOT biographies.
    """

    name = entry.name
    birthplace = entry.birthplace_display or "Unknown"
    gender = entry.gender or "Unknown"
    rank = entry.display_rank_for_title
    group = entry.group

    dob = "Unknown"
    if entry.birth_date:
        if entry.birth_date.year == 1000:
            dob = f"{entry.birth_date.month}/{entry.birth_date.day} (year unknown)"
        else:
            dob = entry.birth_date.isoformat()

    details = entry.known_for or ""

    return f"""
You are an AI entertainment analyst who generates fun, lively, human-sounding insights
about public figures.

Person:
- Name: {name}
- Gender: {gender}
- Rank: {rank} (Group {group})
- Birthplace: {birthplace}
- Birthday: {dob}
- Known For / Details: {details}

Task:
Generate {count} distinct, interesting insights.

Style guidelines:
- Sound confident and natural
- Think entertainment trivia, patterns, or pop-culture notes
- Avoid generic praise
- Avoid disclaimers
- No NSFW content

Rules:
- Each insight should be 1–3 sentences
- Each insight should feel meaningfully different
- No repeated structure

Return ONLY valid JSON:
{{ "insights": ["text1", "text2", "text3"] }}
""".strip()


# ------------------------------------------------------------
# Shared global instance
# ------------------------------------------------------------

kobold_client = KoboldClient()
