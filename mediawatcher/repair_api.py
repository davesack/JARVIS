"""
MediaWatcher 4.0 - Repair API

High-level API for scanning and repairing media library.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, List, Dict

from .repair_scanner import MediaScanner, Issue, IssueType, RepairStats
from .repair_executor import MediaRepairer
from .slug_resolver import SlugResolver

logger = logging.getLogger(__name__)


# ==============================================================================
# MAIN REPAIR API
# ==============================================================================

def scan_media_library(
    media_root: Path,
    resolver: SlugResolver,
    slug_filter: Optional[str] = None
) -> tuple[List[Issue], Dict[str, int]]:
    """
    Scan media library for issues.
    
    Args:
        media_root: Root media directory
        resolver: Slug resolver for validation
        slug_filter: Optional slug to scan (if None, scans all)
    
    Returns:
        Tuple of (issues list, summary dict)
    """
    scanner = MediaScanner(media_root, resolver)
    issues = scanner.scan_library(slug_filter=slug_filter)
    summary = scanner.get_summary()
    
    return issues, summary


def repair_media_library(
    media_root: Path,
    issues: List[Issue],
    dry_run: bool = False
) -> RepairStats:
    """
    Apply fixes to media library.
    
    Args:
        media_root: Root media directory
        issues: List of issues to fix
        dry_run: If True, only simulate (don't actually change files)
    
    Returns:
        RepairStats with results
    """
    temp_root = media_root / "_temp"
    backup_root = media_root / "_repair_backup"
    
    repairer = MediaRepairer(media_root, temp_root, backup_root)
    stats = repairer.repair_issues(issues, dry_run=dry_run)
    
    return stats


def scan_and_repair(
    media_root: Path,
    resolver: SlugResolver,
    slug_filter: Optional[str] = None,
    dry_run: bool = False
) -> tuple[List[Issue], RepairStats]:
    """
    Convenience function: scan and repair in one go.
    
    Args:
        media_root: Root media directory
        resolver: Slug resolver
        slug_filter: Optional slug to process
        dry_run: If True, only simulate
    
    Returns:
        Tuple of (issues found, repair stats)
    """
    # Scan
    issues, summary = scan_media_library(media_root, resolver, slug_filter)
    
    logger.info(f"[Repair] Found {len(issues)} issues")
    for issue_type, count in summary.items():
        logger.info(f"[Repair]   {issue_type}: {count}")
    
    if not issues:
        logger.info("[Repair] No issues found - library is clean!")
        return issues, RepairStats()
    
    # Repair
    stats = repair_media_library(media_root, issues, dry_run=dry_run)
    
    return issues, stats
