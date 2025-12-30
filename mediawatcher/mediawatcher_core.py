"""
MediaWatcher 4.0 - Core Processing Engine

Clean, atomic, idempotent media file processing with proper error handling.
Author: Claude (Anthropic)
Date: 2025-12-12
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum

from PIL import Image

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# File type categories
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
GIF_SUFFIXES = {".gif"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m4v", ".webm"}

# Target formats
STATIC_IMAGE_TARGET = ".webp"
ANIMATED_TARGET = ".webp"
VIDEO_TARGET = ".mp4"

# Compression settings
DISCORD_SIZE_LIMIT_MB = 10
IMAGE_QUALITY_STEPS = [95, 85, 75]
ANIMATED_QUALITY_STEPS = [85, 75]
VIDEO_CRF_STEPS = [23, 26, 28]

# Quality thresholds
MIN_RESOLUTION = 500  # Reject images smaller than this
MAX_FILE_SIZE_MB = 100  # Reject files larger than this (before processing)


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

class FileType(Enum):
    """Type of media file"""
    IMAGE = "image"
    GIF = "gif"
    VIDEO = "video"
    UNKNOWN = "unknown"


class ProcessingSource(Enum):
    """Where the file came from"""
    INCOMING = "incoming"
    DROPBOX = "dropbox"
    BLUESKY = "bluesky"
    MANUAL = "manual"


class ProcessingStage(Enum):
    """Current stage in the pipeline"""
    VALIDATE = "validate"
    EXTRACT = "extract"
    RESOLVE = "resolve"
    CONVERT = "convert"
    COMPRESS = "compress"
    THUMBNAIL = "thumbnail"
    DEDUPE = "dedupe"
    PLACE = "place"
    COMPLETE = "complete"


@dataclass
class ValidationResult:
    """Result of file validation"""
    success: bool
    error: Optional[str] = None
    
    def __bool__(self):
        return self.success


@dataclass
class FileMetadata:
    """Extracted metadata from file"""
    original_path: Path
    filename: str
    slug: Optional[str]
    nsfw: bool
    ai: bool
    file_type: FileType
    source: ProcessingSource
    
    # Bluesky-specific
    handle: Optional[str] = None
    post_url: Optional[str] = None
    post_id: Optional[str] = None


@dataclass
class ResolutionResult:
    """Result of slug resolution"""
    success: bool
    slug: Optional[str]
    method: str  # "direct", "alias", "handle", "manual", "failed"
    confidence: float = 1.0
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
    
    def __bool__(self):
        return self.success


@dataclass
class ConversionResult:
    """Result of format conversion"""
    success: bool
    output_path: Optional[Path]
    original_size_mb: float
    converted_size_mb: float
    format: str
    error: Optional[str] = None


@dataclass
class CompressionResult:
    """Result of compression to size limit"""
    success: bool
    output_path: Path
    size_mb: float
    quality: int
    under_limit: bool
    error: Optional[str] = None


@dataclass
class ProcessResult:
    """Final result of processing a file"""
    success: bool
    original_path: Path
    final_path: Optional[Path] = None
    slug: Optional[str] = None
    stage_reached: ProcessingStage = ProcessingStage.VALIDATE
    error: Optional[str] = None
    
    # Statistics
    size_mb: Optional[float] = None
    quality: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    
    # Review info if failed
    review_folder: Optional[str] = None
    review_reason: Optional[str] = None


# ==============================================================================
# FILE VALIDATION
# ==============================================================================

def validate_file(path: Path) -> ValidationResult:
    """
    Validate that file exists, is readable, and not corrupted.
    
    Returns ValidationResult with success=True if file is good to process.
    """
    # Check exists
    if not path.exists():
        return ValidationResult(False, "File not found")
    
    # Check is file (not directory)
    if not path.is_file():
        return ValidationResult(False, "Not a file")
    
    # Check readable
    try:
        path.stat()
    except PermissionError:
        return ValidationResult(False, "Permission denied")
    except Exception as e:
        return ValidationResult(False, f"Cannot access file: {e}")
    
    # Check not empty
    size = path.stat().st_size
    if size == 0:
        return ValidationResult(False, "Empty file (0 bytes)")
    
    # Check extension
    ext = path.suffix.lower()
    all_supported = IMAGE_SUFFIXES | GIF_SUFFIXES | VIDEO_SUFFIXES
    if ext not in all_supported:
        return ValidationResult(False, f"Unsupported format: {ext}")
    
    # Check not corrupted (try to open/probe)
    try:
        if ext in IMAGE_SUFFIXES or ext in GIF_SUFFIXES:
            # Try to open with PIL
            with Image.open(path) as img:
                img.verify()
        elif ext in VIDEO_SUFFIXES:
            # Try to probe with ffprobe from config
            try:
                from config import FFPROBE_PATH
                result = subprocess.run(
                    [str(FFPROBE_PATH), "-v", "error", str(path)],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode != 0:
                    return ValidationResult(False, f"Video corrupted or unreadable")
            except ImportError:
                logger.warning("ffprobe not found - skipping video validation")
            except FileNotFoundError:
                # ffprobe not installed - skip video validation
                logger.warning("ffprobe not found - skipping video validation")
    except subprocess.TimeoutExpired:
        return ValidationResult(False, "Video probe timeout (file may be corrupted)")
    except Exception as e:
        return ValidationResult(False, f"File corrupted: {e}")
    
    return ValidationResult(True)


def detect_file_type(path: Path) -> FileType:
    """
    Detect what type of media file this is.
    
    Uses smart detection if available to handle:
    - MP4 files that are actually GIFs
    - Static vs animated WebP
    """
    try:
        from .smart_detection import detect_true_media_type, TrueMediaType
        
        true_type = detect_true_media_type(path)
        
        # Map to FileType
        if true_type == TrueMediaType.STATIC_IMAGE:
            return FileType.IMAGE
        elif true_type == TrueMediaType.ANIMATED_IMAGE:
            return FileType.GIF
        elif true_type == TrueMediaType.SHORT_VIDEO_GIF:
            return FileType.GIF  # Treat as GIF!
        elif true_type == TrueMediaType.VIDEO:
            return FileType.VIDEO
        else:
            return FileType.UNKNOWN
    
    except ImportError:
        # Fallback to basic extension-based detection
        pass
    except Exception as e:
        logger.warning(f"Smart detection failed for {path.name}: {e}")
    
    # Fallback: Basic extension-based detection
    ext = path.suffix.lower()
    
    if ext in IMAGE_SUFFIXES:
        return FileType.IMAGE
    
    if ext in GIF_SUFFIXES:
        return FileType.GIF
    
    # Check if webp is animated (basic check)
    if ext == ".webp":
        try:
            with Image.open(path) as img:
                img.seek(1)  # Try to seek to second frame
                return FileType.GIF  # It's animated
        except EOFError:
            return FileType.IMAGE  # Static webp
        except Exception:
            return FileType.IMAGE  # Assume static on error
    
    if ext in VIDEO_SUFFIXES:
        return FileType.VIDEO
    
    return FileType.UNKNOWN


# ==============================================================================
# FILENAME PARSING
# ==============================================================================

def parse_filename(filename: str) -> Tuple[str, bool, bool]:
    """
    Parse filename to extract slug, nsfw flag, and ai flag.
    
    Handles patterns like:
        jennifer-connelly-nsfw-001.jpg → ("jennifer-connelly", True, False)
        anna-faith (2).gif → ("anna-faith", False, False)
        tessa-fowler-ai-nsfw-003.webp → ("tessa-fowler", True, True)
    
    Returns:
        (slug, nsfw, ai)
    """
    import re
    
    lower = filename.lower()
    
    # Remove extension
    stem = lower.rsplit(".", 1)[0] if "." in lower else lower
    
    # Strip (N) patterns like " (1)", " (2)", etc.
    stem = re.sub(r'\s*\(\d+\)$', '', stem)
    
    # Split into parts
    parts = stem.split("-")
    
    # Check for flags and numbers at the end
    nsfw = False
    ai = False
    
    # Remove orientation suffixes first
    if parts and parts[-1] in {"square", "horizontal", "vertical", "portrait", "landscape"}:
        parts.pop()
    
    # Remove trailing number if present (e.g., "001", "0023")
    if parts and parts[-1].isdigit():
        parts.pop()
    
    # Check for "nsfw" flag
    if parts and parts[-1] == "nsfw":
        parts.pop()
        nsfw = True
    
    # Check for "ai" flag
    if parts and parts[-1] == "ai":
        parts.pop()
        ai = True
    
    # What's left is the slug
    if not parts:
        slug = "unknown"
    else:
        slug = "-".join(parts)
    
    return slug, nsfw, ai


def extract_metadata(
    path: Path,
    source: ProcessingSource,
    handle: Optional[str] = None,
    post_url: Optional[str] = None,
    post_id: Optional[str] = None
) -> FileMetadata:
    """
    Extract all metadata from a file.
    
    Args:
        path: Path to the file
        source: Where the file came from
        handle: Bluesky handle if from Bluesky
        post_url: Bluesky post URL if from Bluesky
        post_id: Bluesky post ID if from Bluesky
    
    Returns:
        FileMetadata with all extracted information
    """
    filename = path.name
    slug, nsfw, ai = parse_filename(filename)
    file_type = detect_file_type(path)
    
    return FileMetadata(
        original_path=path,
        filename=filename,
        slug=slug,
        nsfw=nsfw,
        ai=ai,
        file_type=file_type,
        source=source,
        handle=handle,
        post_url=post_url,
        post_id=post_id
    )


# ==============================================================================
# UTILITIES
# ==============================================================================

def format_size_mb(size_bytes: int) -> float:
    """Convert bytes to MB rounded to 2 decimal places"""
    return round(size_bytes / (1024 * 1024), 2)


def get_file_size_mb(path: Path) -> float:
    """Get file size in MB"""
    return format_size_mb(path.stat().st_size)


def sanitize_slug(slug: str) -> str:
    """
    Ensure slug is safe for filesystem use.
    
    Converts to lowercase, replaces spaces with hyphens, removes special chars.
    """
    import unicodedata
    import re
    
    # Normalize unicode
    slug = unicodedata.normalize("NFKD", slug)
    slug = "".join(c for c in slug if not unicodedata.combining(c))
    
    # Convert to lowercase
    slug = slug.lower()
    
    # Replace spaces and underscores with hyphens
    slug = slug.replace(" ", "-").replace("_", "-")
    
    # Keep only alphanumeric and hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    
    return slug or "unknown"
