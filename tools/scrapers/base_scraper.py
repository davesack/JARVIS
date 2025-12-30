import abc
from typing import Any, Dict, Optional


class BaseScraper(abc.ABC):
    """
    Abstract scraper interface.
    Each scraper must implement fetch() and return raw site data in dict form.
    """

    site_name: str = "base"

    @abc.abstractmethod
    async def fetch(self, performer_name: str) -> Optional[Dict[str, Any]]:
        """
        Must return raw site-specific data, or None if not found.
        """
        raise NotImplementedError

    async def safe_fetch(self, performer_name: str) -> Optional[Dict[str, Any]]:
        """
        Wrap fetch() with safe exception handling so no scraper explodes the pipeline.
        """
        try:
            return await self.fetch(performer_name)
        except Exception as e:
            return {
                "error": str(e),
                "site": self.site_name,
                "failed": True,
            }
