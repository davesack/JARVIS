"""
MediaWatcher 4.0 - Repair Script

Scans existing media folder and repairs:
- Old formats (convert to webp/mp4)
- Incorrect filenames (rename to new convention)
- Missing thumbnails (generate for videos/gifs)
- Files over 10MB (compress with quality stepping)
- Incorrect folder placement
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .mediawatcher_core import (
    FileType,
    detect_file_type,
    validate_file,
    parse_filename,
    get_file_size_mb,
    IMAGE_SUFFIXES,
    GIF_SUFFIXES,
    VIDEO_SUFFIXES
)
from .slug_resolver import SlugResolver
from .converter import (
    convert_static_image,
    convert_animated_gif,
    convert_video,
    compress_to_limit,
    generate_thumbnail
)

logger = logging.getLogger(__name__)


# ==============================================================================
# ISSUE TYPES
# ==============================================================================

class IssueType(Enum):
    """Types of issues found in media library"""
    WRONG_FORMAT = "wrong_format"           # JPG/PNG instead of WEBP
    WRONG_FILENAME = "wrong_filename"       # Doesn't match convention
    MISSING_THUMBNAIL = "missing_thumbnail" # Video/GIF without thumbnail
    TOO_LARGE = "too_large"                 # File over 10MB
    WRONG_FOLDER = "wrong_folder"           # In wrong slug/nsfw folder
    DUPLICATE = "duplicate"                 # Duplicate filename in folder


@dataclass
class Issue:
    """A single issue found with a file"""
    issue_type: IssueType
    file_path: Path
    slug: str
    description: str
    suggested_fix: Optional[str] = None


@dataclass
class RepairStats:
    """Statistics from repair operation"""
    total_scanned: int = 0
    issues_found: int = 0
    files_converted: int = 0
    files_renamed: int = 0
    thumbnails_generated: int = 0
    files_compressed: int = 0
    errors: int = 0


# ==============================================================================
# SCANNING
# ==============================================================================

class MediaScanner:
    """Scans media library for issues"""
    
    def __init__(self, media_root: Path, resolver: SlugResolver):
        self.media_root = media_root
        self.resolver = resolver
        self.issues: List[Issue] = []
        self.stats = RepairStats()
    
    def scan_library(self, slug_filter: Optional[str] = None) -> List[Issue]:
        """
        Scan entire media library for issues.
        
        Args:
            slug_filter: If provided, only scan this slug's folder
        
        Returns:
            List of issues found
        """
        logger.info(f"[Repair] Scanning media library: {self.media_root}")
        
        self.issues = []
        self.stats = RepairStats()
        
        # Get all slug folders
        if slug_filter:
            slug_folders = [self.media_root / slug_filter]
        else:
            # All folders except special ones
            slug_folders = [
                d for d in self.media_root.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]
        
        logger.info(f"[Repair] Scanning {len(slug_folders)} slug folders...")
        
        for slug_folder in slug_folders:
            self._scan_slug_folder(slug_folder)
        
        logger.info(f"[Repair] Scan complete: {self.stats.total_scanned} files, "
                   f"{len(self.issues)} issues found")
        
        return self.issues
    
    def _scan_slug_folder(self, slug_folder: Path):
        """Scan a single slug's folder"""
        slug = slug_folder.name
        
        # Scan images, gifs, videos
        for subdir_name in ["images", "gifs", "videos"]:
            subdir = slug_folder / subdir_name
            if subdir.exists():
                self._scan_media_folder(subdir, slug, subdir_name)
            
            # Also scan nsfw subfolder
            nsfw_subdir = subdir / "nsfw"
            if nsfw_subdir.exists():
                self._scan_media_folder(nsfw_subdir, slug, subdir_name, nsfw=True)
    
    def _scan_media_folder(
        self,
        folder: Path,
        slug: str,
        media_type: str,
        nsfw: bool = False
    ):
        """Scan a media folder (images/, gifs/, videos/)"""
        
        # Get all media files
        all_suffixes = IMAGE_SUFFIXES | GIF_SUFFIXES | VIDEO_SUFFIXES
        files = []
        for suffix in all_suffixes:
            files.extend(folder.glob(f"*{suffix}"))
        
        for file_path in files:
            self.stats.total_scanned += 1
            self._check_file(file_path, slug, media_type, nsfw)
    
    def _check_file(
        self,
        file_path: Path,
        slug: str,
        expected_type: str,
        nsfw: bool
    ):
        """Check a single file for issues"""
        
        # Check if this is a thumbnail in the WRONG place (not in /thumbnails/ folder)
        if file_path.stem.endswith("_thumb"):
            # Thumbnails should be in /thumbnails/ subfolder
            if file_path.parent.name != "thumbnails":
                self.issues.append(Issue(
                    issue_type=IssueType.WRONG_FOLDER,
                    file_path=file_path,
                    slug=slug,
                    description=f"Thumbnail in wrong location: {file_path.name}",
                    suggested_fix="Move to thumbnails/ subfolder"
                ))
            return  # Don't check thumbnails for other issues
        
        # Validate file is readable
        validation = validate_file(file_path)
        if not validation:
            self.issues.append(Issue(
                issue_type=IssueType.WRONG_FORMAT,
                file_path=file_path,
                slug=slug,
                description=f"Corrupted or unreadable: {validation.error}"
            ))
            return
        
        # Check format
        file_type = detect_file_type(file_path)
        ext = file_path.suffix.lower()
        
        # Expected extensions
        if expected_type == "images":
            if ext != ".webp":
                self.issues.append(Issue(
                    issue_type=IssueType.WRONG_FORMAT,
                    file_path=file_path,
                    slug=slug,
                    description=f"Image should be .webp, found {ext}",
                    suggested_fix="Convert to .webp"
                ))
        
        elif expected_type == "gifs":
            if ext != ".webp":
                self.issues.append(Issue(
                    issue_type=IssueType.WRONG_FORMAT,
                    file_path=file_path,
                    slug=slug,
                    description=f"GIF should be animated .webp, found {ext}",
                    suggested_fix="Convert to animated .webp"
                ))
        
        elif expected_type == "videos":
            if ext != ".mp4":
                self.issues.append(Issue(
                    issue_type=IssueType.WRONG_FORMAT,
                    file_path=file_path,
                    slug=slug,
                    description=f"Video should be .mp4, found {ext}",
                    suggested_fix="Convert to .mp4"
                ))
        
        # Check filename format
        expected_pattern = self._get_expected_filename_pattern(slug, nsfw)
        if not self._matches_pattern(file_path.name, expected_pattern):
            self.issues.append(Issue(
                issue_type=IssueType.WRONG_FILENAME,
                file_path=file_path,
                slug=slug,
                description=f"Filename doesn't match convention: {file_path.name}",
                suggested_fix=f"Rename to: {expected_pattern}"
            ))
        
        # Check for -ai- in filename but NOT in /ai/ folder
        if "-ai-" in file_path.name.lower() and "/ai/" not in str(file_path).lower():
            self.issues.append(Issue(
                issue_type=IssueType.WRONG_FILENAME,
                file_path=file_path,
                slug=slug,
                description=f"File has -ai- in name but not in ai folder: {file_path.name}",
                suggested_fix=f"Remove -ai- from filename or move to ai folder"
            ))
        
        # Check file size
        size_mb = get_file_size_mb(file_path)
        if size_mb > 10:
            self.issues.append(Issue(
                issue_type=IssueType.TOO_LARGE,
                file_path=file_path,
                slug=slug,
                description=f"File is {size_mb}MB (over 10MB limit)",
                suggested_fix="Compress with quality stepping"
            ))
        
        # Check for thumbnail (videos and gifs)
        if expected_type in ("videos", "gifs"):
            thumb_path = file_path.parent / f"{file_path.stem}_thumb.webp"
            if not thumb_path.exists():
                self.issues.append(Issue(
                    issue_type=IssueType.MISSING_THUMBNAIL,
                    file_path=file_path,
                    slug=slug,
                    description=f"Missing thumbnail: {thumb_path.name}",
                    suggested_fix="Generate thumbnail"
                ))
    
    def _get_expected_filename_pattern(self, slug: str, nsfw: bool) -> str:
        """Get expected filename pattern for this slug/nsfw combo"""
        if nsfw:
            return f"{slug}-nsfw-####.ext"
        else:
            return f"{slug}-####.ext"
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches expected pattern"""
        import re
        
        # Parse actual filename
        slug, nsfw, ai = parse_filename(filename)
        
        # Extract slug from pattern
        pattern_slug = pattern.split("-")[0]
        
        # Basic check: does it start with the right slug?
        if not filename.lower().startswith(pattern_slug.lower()):
            return False
        
        # Check for proper numbering (ends with ####.ext)
        stem = filename.rsplit(".", 1)[0]
        
        # Strip orientation words and (N) patterns BEFORE checking
        stem = re.sub(r'\s*\(\d+\)$', '', stem)  # Remove (1), (2), etc
        stem = re.sub(r'-(square|horizontal|vertical|portrait|landscape)$', '', stem, flags=re.IGNORECASE)
        
        parts = stem.split("-")
        
        # Last part should be a 4-digit number
        if not parts or not parts[-1].isdigit():
            return False
        
        if len(parts[-1]) != 4:
            return False
        
        return True
    
    def get_issues_by_type(self) -> Dict[IssueType, List[Issue]]:
        """Group issues by type"""
        by_type: Dict[IssueType, List[Issue]] = {}
        for issue in self.issues:
            if issue.issue_type not in by_type:
                by_type[issue.issue_type] = []
            by_type[issue.issue_type].append(issue)
        return by_type
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary of issues found"""
        by_type = self.get_issues_by_type()
        return {
            issue_type.value: len(issues)
            for issue_type, issues in by_type.items()
        }
