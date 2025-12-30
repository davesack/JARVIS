"""
MediaWatcher 4.0 - Main API

High-level interface for media file processing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .mediawatcher_core import ProcessingSource, ProcessResult
from .slug_resolver import SlugResolver, get_resolver
from .processor import MediaProcessor
from .mw_event_logger import EventLogger, get_event_logger

logger = logging.getLogger(__name__)


# ==============================================================================
# MEDIAWATCHER 4.0 - MAIN CLASS
# ==============================================================================

class MediaWatcher:
    """
    MediaWatcher 4.0 - Clean media processing pipeline.
    
    Usage:
        mw = MediaWatcher(
            media_root=Path("media"),
            data_root=Path("data/mediawatcher")
        )
        
        # Process single file
        result = mw.process_file(Path("incoming/anna-faith-001.jpg"))
        
        # Process folder
        results = mw.process_folder(Path("incoming"))
        
        # From Bluesky
        result = mw.ingest_from_bluesky(
            file_path=Path("temp/bluesky-image.jpg"),
            handle="annafaith.bsky.social",
            nsfw=True
        )
    """
    
    def __init__(
        self,
        media_root: Path,
        data_root: Path,
        incoming_dir: Optional[Path] = None,
        dropbox_dir: Optional[Path] = None
    ):
        """
        Initialize MediaWatcher.
        
        Args:
            media_root: Root directory for organized media files
            data_root: Root directory for MediaWatcher data (logs, databases, etc.)
            incoming_dir: Optional incoming folder to watch
            dropbox_dir: Optional Dropbox folder to watch
        """
        self.media_root = media_root
        self.data_root = data_root
        self.incoming_dir = incoming_dir
        self.dropbox_dir = dropbox_dir
        
        # Setup directories
        self.processed_root = media_root / "_processed"
        self.review_root = media_root / "_review"
        self.temp_root = media_root / "_temp"
        
        # Setup data files
        self.people_file = data_root / "people.json"
        self.aliases_file = data_root / "aliases.json"
        self.log_file = data_root / "process_log.jsonl"
        
        # Initialize components
        self.resolver = get_resolver(self.people_file, self.aliases_file)
        self.processor = MediaProcessor(
            media_root=self.media_root,
            processed_root=self.processed_root,
            review_root=self.review_root,
            temp_root=self.temp_root,
            resolver=self.resolver
        )
        self.event_logger = get_event_logger(self.log_file)
        
        logger.info(f"[MediaWatcher] Initialized")
        logger.info(f"[MediaWatcher]   Media root: {self.media_root}")
        logger.info(f"[MediaWatcher]   People: {len(self.resolver.people)}")
        logger.info(f"[MediaWatcher]   Aliases: {len(self.resolver.aliases)}")
    
    # ==========================================================================
    # CORE PROCESSING
    # ==========================================================================
    
    def process_file(
        self,
        file_path: Path,
        source: ProcessingSource = ProcessingSource.INCOMING,
        handle: Optional[str] = None,
        post_url: Optional[str] = None,
        force_slug: Optional[str] = None,
        force_nsfw: Optional[bool] = None
    ) -> ProcessResult:
        """
        Process a single file.
        
        Args:
            file_path: Path to file to process
            source: Where the file came from
            handle: Bluesky handle (if applicable)
            post_url: Bluesky post URL (if applicable)
            force_slug: Override extracted slug
            force_nsfw: Override extracted NSFW flag
        
        Returns:
            ProcessResult with outcome
        """
        result = self.processor.process_file(
            file_path=file_path,
            source=source,
            handle=handle,
            post_url=post_url,
            force_slug=force_slug,
            force_nsfw=force_nsfw
        )
        
        # Log event
        self.event_logger.log_process_complete(result)
        
        return result
    
    def process_folder(
        self,
        folder_path: Path,
        source: ProcessingSource = ProcessingSource.INCOMING,
        recursive: bool = False
    ) -> List[ProcessResult]:
        """
        Process all media files in a folder.
        
        Args:
            folder_path: Path to folder
            source: Where files came from
            recursive: Whether to search subdirectories
        
        Returns:
            List of ProcessResult objects
        """
        # Find all media files
        from .mediawatcher_core import IMAGE_SUFFIXES, GIF_SUFFIXES, VIDEO_SUFFIXES
        
        all_suffixes = IMAGE_SUFFIXES | GIF_SUFFIXES | VIDEO_SUFFIXES
        files = []
        
        if recursive:
            for suffix in all_suffixes:
                files.extend(folder_path.rglob(f"*{suffix}"))
        else:
            for suffix in all_suffixes:
                files.extend(folder_path.glob(f"*{suffix}"))
        
        logger.info(f"[MediaWatcher] Found {len(files)} files in {folder_path}")
        
        # Process batch
        results = self.processor.process_batch(files, source=source)
        
        return results
    
    def process_incoming(self) -> List[ProcessResult]:
        """
        Process all files in incoming and Dropbox folders.
        
        Returns:
            List of ProcessResult objects
        """
        all_results = []
        
        # Process incoming folder
        if self.incoming_dir and self.incoming_dir.exists():
            logger.info(f"[MediaWatcher] Processing incoming: {self.incoming_dir}")
            results = self.process_folder(self.incoming_dir, ProcessingSource.INCOMING)
            all_results.extend(results)
        
        # Process Dropbox folder
        if self.dropbox_dir and self.dropbox_dir.exists():
            logger.info(f"[MediaWatcher] Processing Dropbox: {self.dropbox_dir}")
            results = self.process_folder(self.dropbox_dir, ProcessingSource.DROPBOX)
            all_results.extend(results)
        
        return all_results
    
    # ==========================================================================
    # BLUESKY INTEGRATION
    # ==========================================================================
    
    def ingest_from_bluesky(
        self,
        file_path: Path,
        handle: str,
        post_url: str,
        post_id: str,
        slug: Optional[str] = None,
        nsfw: bool = False
    ) -> ProcessResult:
        """
        Ingest file from Bluesky with handle mapping.
        
        Args:
            file_path: Path to downloaded file
            handle: Bluesky handle (e.g., "annafaith.bsky.social")
            post_url: URL to Bluesky post
            post_id: Bluesky post ID
            slug: Manual slug override (for mapping)
            nsfw: Whether file is NSFW
        
        Returns:
            ProcessResult
        """
        return self.process_file(
            file_path=file_path,
            source=ProcessingSource.BLUESKY,
            handle=handle,
            post_url=post_url,
            force_slug=slug,
            force_nsfw=nsfw
        )
    
    def map_handle_to_slug(self, handle: str, slug: str) -> bool:
        """
        Map a Bluesky handle to a slug.
        
        Args:
            handle: Bluesky handle
            slug: Canonical slug
        
        Returns:
            True if successful, False if slug doesn't exist
        """
        success = self.resolver.add_alias(handle, slug, save=True)
        
        if success:
            logger.info(f"[MediaWatcher] Mapped handle: {handle} → {slug}")
        
        return success
    
    def reprocess_unmapped_handle(self, handle: str) -> List[ProcessResult]:
        """
        Reprocess all files in review with a specific handle.
        
        After mapping a handle, this can reprocess files that were
        previously sent to review.
        
        Args:
            handle: Bluesky handle that was just mapped
        
        Returns:
            List of ProcessResult objects
        """
        unmapped_folder = self.review_root / "unmapped-bluesky"
        if not unmapped_folder.exists():
            return []
        
        # Find files with this handle in filename
        handle_slug = handle.replace(".", "-").replace("@", "")
        files = list(unmapped_folder.glob(f"*{handle_slug}*"))
        
        logger.info(f"[MediaWatcher] Reprocessing {len(files)} files for handle: {handle}")
        
        results = []
        for file_path in files:
            result = self.process_file(
                file_path=file_path,
                source=ProcessingSource.BLUESKY,
                handle=handle
            )
            results.append(result)
        
        return results
    
    # ==========================================================================
    # UTILITIES
    # ==========================================================================
    
    def get_all_slugs(self) -> List[str]:
        """Get sorted list of all known slugs (for autocomplete)"""
        return self.resolver.get_all_slugs()
    
    def reload_database(self):
        """Reload people and aliases from disk"""
        self.resolver.reload()
        logger.info(f"[MediaWatcher] Reloaded database: "
                   f"{len(self.resolver.people)} people, "
                   f"{len(self.resolver.aliases)} aliases")
    
    # ==========================================================================
    # REPAIR
    # ==========================================================================
    
    def scan_for_issues(self, slug_filter: Optional[str] = None):
        """
        Scan media library for issues.
        
        Args:
            slug_filter: Optional slug to scan (if None, scans all)
        
        Returns:
            Tuple of (issues list, summary dict)
        """
        from .repair_api import scan_media_library
        return scan_media_library(self.media_root, self.resolver, slug_filter)
    
    def repair_library(self, issues: List, dry_run: bool = False):
        """
        Apply fixes to media library.
        
        Args:
            issues: List of issues to fix
            dry_run: If True, only simulate
        
        Returns:
            RepairStats with results
        """
        from .repair_api import repair_media_library
        return repair_media_library(self.media_root, issues, dry_run)
    
    def scan_and_repair(
        self,
        slug_filter: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Scan and repair in one operation.
        
        Args:
            slug_filter: Optional slug to process
            dry_run: If True, only simulate
        
        Returns:
            Tuple of (issues found, repair stats)
        """
        from .repair_api import scan_and_repair
        return scan_and_repair(
            self.media_root,
            self.resolver,
            slug_filter,
            dry_run
        )


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def create_mediawatcher(
    media_root: Path,
    data_root: Path,
    incoming_dir: Optional[Path] = None,
    dropbox_dir: Optional[Path] = None
) -> MediaWatcher:
    """
    Create a MediaWatcher instance with standard configuration.
    
    Args:
        media_root: Root directory for media files
        data_root: Root directory for MediaWatcher data
        incoming_dir: Optional incoming folder
        dropbox_dir: Optional Dropbox folder
    
    Returns:
        MediaWatcher instance
    """
    return MediaWatcher(
        media_root=media_root,
        data_root=data_root,
        incoming_dir=incoming_dir,
        dropbox_dir=dropbox_dir
    )
