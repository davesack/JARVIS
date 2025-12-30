"""
MediaWatcher 4.0 - Repair Execution

Applies fixes to issues found by scanner.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from .mediawatcher_core import (
    FileType,
    detect_file_type,
    get_file_size_mb
)
from .converter import (
    convert_static_image,
    convert_animated_gif,
    convert_video,
    compress_to_limit,
    generate_thumbnail
)
from .repair_scanner import Issue, IssueType, RepairStats

logger = logging.getLogger(__name__)


# ==============================================================================
# REPAIR EXECUTION
# ==============================================================================

class MediaRepairer:
    """Executes repairs on media library"""
    
    def __init__(self, media_root: Path, temp_root: Path, backup_root: Path):
        self.media_root = media_root
        self.temp_root = temp_root
        self.backup_root = backup_root
        
        # Ensure directories exist
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)
    
    def repair_issues(
        self,
        issues: List[Issue],
        dry_run: bool = False
    ) -> RepairStats:
        """
        Apply fixes to all issues.
        
        Args:
            issues: List of issues to fix
            dry_run: If True, only simulate (don't actually change files)
        
        Returns:
            RepairStats with results
        """
        stats = RepairStats()
        stats.total_scanned = len(issues)
        
        logger.info(f"[Repair] Processing {len(issues)} issues (dry_run={dry_run})")
        
        # CRITICAL: Process renames FIRST, then thumbnails
        # This prevents trying to generate thumbnails for files that were just renamed
        renames = [i for i in issues if i.issue_type == IssueType.WRONG_FILENAME]
        others = [i for i in issues if i.issue_type != IssueType.WRONG_FILENAME]
        
        # Process renames first
        for issue in renames:
            try:
                self._fix_issue(issue, dry_run, stats)
            except Exception as e:
                logger.error(f"[Repair] Error fixing {issue.file_path}: {e}")
                stats.errors += 1
        
        # Then process everything else
        for issue in others:
            try:
                self._fix_issue(issue, dry_run, stats)
            except Exception as e:
                logger.error(f"[Repair] Error fixing {issue.file_path}: {e}")
                stats.errors += 1
        
        logger.info(f"[Repair] Complete: {stats.files_converted} converted, "
                   f"{stats.files_renamed} renamed, "
                   f"{stats.thumbnails_generated} thumbnails, "
                   f"{stats.errors} errors")
        
        return stats
    
    def _fix_issue(self, issue: Issue, dry_run: bool, stats: RepairStats):
        """Fix a single issue"""
        
        if issue.issue_type == IssueType.WRONG_FORMAT:
            self._fix_wrong_format(issue, dry_run, stats)
        
        elif issue.issue_type == IssueType.WRONG_FILENAME:
            self._fix_wrong_filename(issue, dry_run, stats)
        
        elif issue.issue_type == IssueType.MISSING_THUMBNAIL:
            self._fix_missing_thumbnail(issue, dry_run, stats)
        
        elif issue.issue_type == IssueType.TOO_LARGE:
            self._fix_too_large(issue, dry_run, stats)
        
        elif issue.issue_type == IssueType.WRONG_FOLDER:
            self._fix_wrong_folder(issue, dry_run, stats)
    
    def _fix_wrong_format(self, issue: Issue, dry_run: bool, stats: RepairStats):
        """Convert file to correct format"""
        file_path = issue.file_path
        file_type = detect_file_type(file_path)
        
        # Determine target extension
        if file_type == FileType.IMAGE:
            target_ext = ".webp"
        elif file_type == FileType.GIF:
            target_ext = ".webp"
        elif file_type == FileType.VIDEO:
            target_ext = ".mp4"
        else:
            logger.warning(f"[Repair] Unknown file type for {file_path}")
            return
        
        # Skip if already correct format
        if file_path.suffix.lower() == target_ext:
            return
        
        logger.info(f"[Repair] Converting {file_path.name} → {target_ext}")
        
        if dry_run:
            logger.info(f"[Repair]   DRY RUN: Would convert {file_path.name}")
            return
        
        # Backup original
        backup_path = self.backup_root / file_path.name
        shutil.copy2(file_path, backup_path)
        
        # Convert to temp location
        temp_output = self.temp_root / f"{file_path.stem}{target_ext}"
        
        if file_type == FileType.IMAGE:
            result = convert_static_image(file_path, temp_output, quality=95)
        elif file_type == FileType.GIF:
            result = convert_animated_gif(file_path, temp_output, quality=85)
        elif file_type == FileType.VIDEO:
            result = convert_video(file_path, temp_output, crf=23)
        
        if not result.success:
            logger.error(f"[Repair] Conversion failed: {result.error}")
            stats.errors += 1
            return
        
        # Replace original with converted
        new_path = file_path.parent / f"{file_path.stem}{target_ext}"
        
        # Move converted file to final location
        shutil.move(str(temp_output), str(new_path))
        
        # Only delete original if it has a different extension (conversion happened)
        if file_path.suffix.lower() != target_ext:
            file_path.unlink()
        
        stats.files_converted += 1
        logger.info(f"[Repair]   ✅ Converted: {new_path.name}")
    
    def _fix_wrong_filename(self, issue: Issue, dry_run: bool, stats: RepairStats):
        """Rename file to match convention"""
        file_path = issue.file_path
        folder = file_path.parent
        
        # Get next sequence number
        from .processor import get_next_sequence_number
        
        # Parse current filename
        from .mediawatcher_core import parse_filename
        slug, nsfw, ai = parse_filename(file_path.name)
        
        # Build prefix
        prefix_parts = [slug]
        if ai:
            prefix_parts.append("ai")
        if nsfw:
            prefix_parts.append("nsfw")
        prefix = "-".join(prefix_parts)
        
        # Get next number
        ext = file_path.suffix
        sequence = get_next_sequence_number(folder, prefix, ext)
        
        # Generate new filename
        new_name = f"{prefix}-{sequence:04d}{ext}"
        new_path = folder / new_name
        
        logger.info(f"[Repair] Renaming {file_path.name} → {new_name}")
        
        if dry_run:
            logger.info(f"[Repair]   DRY RUN: Would rename to {new_name}")
            return
        
        # Backup original
        backup_path = self.backup_root / file_path.name
        shutil.copy2(file_path, backup_path)
        
        # Rename
        file_path.rename(new_path)
        
        stats.files_renamed += 1
        logger.info(f"[Repair]   ✅ Renamed: {new_name}")
    
    def _fix_missing_thumbnail(self, issue: Issue, dry_run: bool, stats: RepairStats):
        """Generate missing thumbnail"""
        file_path = issue.file_path
        file_type = detect_file_type(file_path)
        
        # Thumbnails go in /thumbnails/ subfolder
        thumb_dir = file_path.parent / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)
        
        thumb_path = thumb_dir / f"{file_path.stem}_thumb.webp"
        
        logger.info(f"[Repair] Generating thumbnail for {file_path.name}")
        
        if dry_run:
            logger.info(f"[Repair]   DRY RUN: Would generate {thumb_path.name}")
            return
        
        # Generate thumbnail
        result = generate_thumbnail(file_path, file_type, output_path=thumb_path)
        
        if result:
            stats.thumbnails_generated += 1
            logger.info(f"[Repair]   ✅ Generated: {thumb_path.name}")
        else:
            logger.warning(f"[Repair]   ⚠️  Failed to generate thumbnail")
            stats.errors += 1
    
    def _fix_too_large(self, issue: Issue, dry_run: bool, stats: RepairStats):
        """Compress file to under 10MB"""
        file_path = issue.file_path
        file_type = detect_file_type(file_path)
        
        size_mb = get_file_size_mb(file_path)
        logger.info(f"[Repair] Compressing {file_path.name} ({size_mb}MB)")
        
        if dry_run:
            logger.info(f"[Repair]   DRY RUN: Would compress from {size_mb}MB")
            return
        
        # Backup original
        backup_path = self.backup_root / file_path.name
        shutil.copy2(file_path, backup_path)
        
        # Compress
        result = compress_to_limit(file_path, file_type, temp_dir=self.temp_root)
        
        if result.under_limit:
            # Replace original with compressed version
            shutil.move(str(result.output_path), str(file_path))
            stats.files_compressed += 1
            logger.info(f"[Repair]   ✅ Compressed: {size_mb}MB → {result.size_mb}MB "
                       f"(quality {result.quality})")
        else:
            logger.warning(f"[Repair]   ⚠️  Could not compress under 10MB")
            stats.errors += 1
    
    def _fix_wrong_folder(self, issue: Issue, dry_run: bool, stats: RepairStats):
        """Move file to correct folder"""
        file_path = issue.file_path
        
        # Check if this is a thumbnail that needs to move
        if file_path.stem.endswith("_thumb"):
            # Move to thumbnails subfolder
            thumb_dir = file_path.parent / "thumbnails"
            thumb_dir.mkdir(exist_ok=True)
            
            new_path = thumb_dir / file_path.name
            
            logger.info(f"[Repair] Moving thumbnail {file_path.name} → thumbnails/")
            
            if dry_run:
                logger.info(f"[Repair]   DRY RUN: Would move to {new_path}")
                return
            
            # Backup original
            backup_path = self.backup_root / file_path.name
            shutil.copy2(file_path, backup_path)
            
            # Move to thumbnails folder
            shutil.move(str(file_path), str(new_path))
            
            stats.files_renamed += 1  # Count as a move/rename
            logger.info(f"[Repair]   ✅ Moved to: thumbnails/{file_path.name}")
            return
        
        # Other wrong folder cases not yet implemented
        logger.warning(f"[Repair] Wrong folder fixes not yet implemented for: {file_path.name}")
