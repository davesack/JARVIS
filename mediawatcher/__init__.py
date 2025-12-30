# utils/mediawatcher/__init__.py

"""
MediaWatcher 4.0 - Clean media processing pipeline

Main API: MediaWatcher class from mediawatcher.py
See example_usage.py for usage examples.
"""

from .mediawatcher import MediaWatcher, create_mediawatcher

__all__ = ["MediaWatcher", "create_mediawatcher"]
