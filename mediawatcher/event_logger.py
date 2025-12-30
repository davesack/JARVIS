"""
utils/mediawatcher/event_logger.py - Compatibility wrapper for MediaWatcher 4.0

This provides backwards compatibility for code that imports the old event_logger module.
"""

from .mw_event_logger import get_event_logger
from config import MEDIAWATCHER_DATA


def log_event(event_type, data):
    """Log an event (old API)"""
    log_file = MEDIAWATCHER_DATA / "process_log.jsonl"
    logger = get_event_logger(log_file)
    logger.log_event(event_type, data)


def read_events_since(timestamp):
    """
    Compatibility stub for old API.
    Returns empty list as the new system doesn't track offsets this way.
    """
    return []


def get_current_offset():
    """
    Compatibility stub for old API.
    Returns 0 as the new system doesn't use offsets.
    """
    return 0
