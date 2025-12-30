from typing import Optional, Dict, Any
from tools.scrapers.base_scraper import BaseScraper
import arena_config
import aiohttp


class TMDBScraper(BaseScraper):
    site_name = "tmdb"

    async def fetch(self, performer_name: str) -> Optional[Dict[str, Any]]:
        api_key = arena_config.TMDB_API_KEY
        if not api_key:
            return None

        url = (
            "https://api.themoviedb.org/3/search/person"
            f"?api_key={api_key}&query={performer_name}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as r:
                if r.status != 200:
                    return None

                data = await r.json()
                if not data.get("results"):
                    return None

                person = data["results"][0]

                return {
                    "name": performer_name,
                    "tmdb_id": person.get("id"),
                    "popularity": person.get("popularity"),
                    "known_for": [
                        k.get("title") or k.get("name")
                        for k in person.get("known_for", [])
                        if k
                    ],
                }
