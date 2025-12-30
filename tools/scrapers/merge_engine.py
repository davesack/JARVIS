from typing import Dict, Any, List, Optional


class MergeEngine:
    """
    Combines normalized metadata from multiple sources into final unified metadata.
    SL = “light source”, lowest priority.
    """

    PRIORITY = {
        "tmdb": 6,          # highest authority for mainstream metadata 
        "babepedia": 5,
        "boobpedia": 5,
        "iafd": 4,
        "data18": 4,
    }

    def merge(self, mapped_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Take multiple normalized dicts and merge into a final performer object.
        """
        final: Dict[str, Any] = {}

        for entry in sorted(mapped_list, key=lambda x: self.PRIORITY.get(x["source"], 0), reverse=True):
            for k, v in entry.items():
                if k == "source":
                    continue

                # Only overwrite blank or missing
                if k not in final or final[k] in (None, "", [], {}):
                    final[k] = v

        return final
