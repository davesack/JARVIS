import abc
from typing import Any, Dict, Optional


class BaseMapper(abc.ABC):
    """
    Normalizes and maps raw scraper output into the unified metadata schema.
    """

    site_name: str = "base"

    @abc.abstractmethod
    def map(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert raw site-specific structure into normalized fields.
        Return None if raw data is invalid.
        """
        raise NotImplementedError

    def safe_map(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Protect against unexpected site format failures.
        """
        if not raw or raw.get("failed"):
            return None
        try:
            return self.map(raw)
        except Exception:
            return None
