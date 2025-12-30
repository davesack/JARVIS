from typing import Dict, Any, Optional
from tools.scrapers.base_mapper import BaseMapper
from tools.scrapers.normalizer import Normalizer


class TMDBMapper(BaseMapper):
    site_name = "tmdb"

    def map(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not raw or "name" not in raw:
            return None

        return {
            "source": self.site_name,
            "tmdb_id": raw.get("tmdb_id"),
            "tmdb_popularity": Normalizer.clean_measurement(raw.get("popularity")),
            "known_for": Normalizer.clean_list(raw.get("known_for")),
        }
