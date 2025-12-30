"""
utils/mediawatcher/slug_engine.py - Compatibility wrapper for MediaWatcher 4.0

This provides backwards compatibility for code that imports the old slug_engine module.
"""

from .slug_resolver import get_resolver
from config import MEDIAWATCHER_DATA

# Export paths for backwards compatibility
PEOPLE_PATH = MEDIAWATCHER_DATA / "people.json"
ALIASES_PATH = MEDIAWATCHER_DATA / "aliases.json"

# Get global resolver
_resolver = None

def get_engine():
    """Get the slug resolver (old API name)"""
    global _resolver
    if _resolver is None:
        _resolver = get_resolver(PEOPLE_PATH, ALIASES_PATH)
    return _resolver


# For backwards compatibility
class SlugEngine:
    """Old API wrapper"""
    
    def __init__(self):
        """Initialize using global resolver"""
        self.resolver = get_engine()
    
    def resolve(self, slug):
        """Resolve a slug (old API)"""
        # Create minimal metadata object
        from .mediawatcher_core import FileMetadata, ProcessingSource, FileType
        from pathlib import Path
        
        metadata = FileMetadata(
            original_path=Path("temp"),
            filename="temp",
            slug=slug,
            nsfw=False,
            ai=False,
            file_type=FileType.IMAGE,
            source=ProcessingSource.MANUAL
        )
        
        result = self.resolver.resolve(metadata)
        return result