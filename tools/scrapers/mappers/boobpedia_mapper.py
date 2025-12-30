from typing import Dict, Any, Optional
from tools.scrapers.base_mapper import BaseMapper
from tools.scrapers.normalizer import Normalizer


class BoobpediaMapper(BaseMapper):
    site_name = "boobpedia"

    def map(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not raw or "name" not in raw:
            return None

        return {
            "source": self.site_name,
            "measurements": Normalizer.clean_string(raw.get("measurements")),
            "cup_size": Normalizer.clean_string(raw.get("cup_size")),
            "breast_type": Normalizer.clean_string(raw.get("breast_type")),
            "categories": Normalizer.clean_list(raw.get("categories")),
            "rating": Normalizer.clean_measurement(raw.get("rating")),
            "profile_url": Normalizer.clean_string(raw.get("profile_url")),
        }
