"""
utils/mediawatcher/ingest.py - Compatibility wrapper for MediaWatcher 4.0

This provides backwards compatibility for code that imports the old ingest module.
"""

from pathlib import Path
from .mediawatcher import create_mediawatcher
from config import MEDIA_ROOT, MEDIAWATCHER_DATA, DROPBOX_WATCH_ROOT

# Create global MediaWatcher instance
_mw = None

def _get_mediawatcher():
    """Get or create the global MediaWatcher instance"""
    global _mw
    if _mw is None:
        _mw = create_mediawatcher(
            media_root=MEDIA_ROOT,
            data_root=MEDIAWATCHER_DATA,
            incoming_dir=MEDIA_ROOT / "_incoming",
            dropbox_dir=DROPBOX_WATCH_ROOT
        )
    return _mw


def process_all_sources():
    """
    OLD API: Process incoming and Dropbox folders.
    
    Returns dict with old format for backwards compatibility:
    {
        "incoming": {"found": X, "processed": Y, "errors": Z},
        "dropbox": {"found": X, "processed": Y, "errors": Z}
    }
    """
    mw = _get_mediawatcher()
    results = mw.process_incoming()
    
    # Convert to old format
    success_count = sum(1 for r in results if r.success)
    error_count = len(results) - success_count
    
    return {
        "incoming": {
            "found": len(results),
            "processed": success_count,
            "errors": error_count
        },
        "dropbox": {
            "found": 0,
            "processed": 0,
            "errors": 0
        }
    }


def process_incoming_folder():
    """OLD API: Process incoming folder only"""
    mw = _get_mediawatcher()
    
    if mw.incoming_dir and mw.incoming_dir.exists():
        from .mediawatcher_core import ProcessingSource
        results = mw.process_folder(mw.incoming_dir, ProcessingSource.INCOMING)
        
        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count
        
        return len(results), success_count, error_count
    
    return 0, 0, 0
