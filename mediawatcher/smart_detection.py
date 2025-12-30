"""
MediaWatcher 4.0 - Smart Detection Module

Advanced media file analysis:
- True media type detection (GIF vs Video, Static vs Animated)
- Quality validation (resolution, bitrate)
- Corruption detection
- Duplicate detection
- Screenshot detection
- Metadata extraction
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from PIL import Image

from config import FFPROBE_PATH

logger = logging.getLogger(__name__)


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

class TrueMediaType(Enum):
    """The ACTUAL type of media, regardless of extension"""
    STATIC_IMAGE = "static_image"
    ANIMATED_IMAGE = "animated_image"  # Animated WebP or GIF
    SHORT_VIDEO_GIF = "short_video_gif"  # MP4 that's actually a GIF
    VIDEO = "video"
    UNKNOWN = "unknown"


@dataclass
class MediaAnalysis:
    """Complete analysis of a media file"""
    true_type: TrueMediaType
    width: int
    height: int
    duration_seconds: Optional[float]
    has_audio: bool
    file_size_mb: float
    
    # Quality indicators
    is_thumbnail: bool  # Too small to be useful
    is_upscaled: bool  # Artificially enlarged
    is_screenshot: bool  # Has UI elements
    is_corrupt: bool
    
    # Hashes for deduplication
    content_hash: str  # SHA256 of file
    
    # Metadata
    metadata: Dict[str, Any]
    
    # Warnings
    warnings: list[str]


# ==============================================================================
# SMART TYPE DETECTION
# ==============================================================================

def detect_true_media_type(path: Path) -> TrueMediaType:
    """
    Detect ACTUAL media type, not just by extension.
    
    Handles:
    - MP4 files that are actually GIFs (no audio, short, looping)
    - WebP files that are static vs animated
    - MOV files that are screen recordings vs videos
    
    Returns:
        TrueMediaType
    """
    ext = path.suffix.lower()
    
    # ===== WebP: Static or Animated? =====
    if ext == ".webp":
        try:
            with Image.open(path) as img:
                try:
                    img.seek(1)  # Try to seek to frame 2
                    return TrueMediaType.ANIMATED_IMAGE
                except EOFError:
                    return TrueMediaType.STATIC_IMAGE
        except Exception as e:
            logger.warning(f"[SmartDetect] Could not analyze WebP {path.name}: {e}")
            return TrueMediaType.UNKNOWN
    
    # ===== GIF: Always animated =====
    if ext == ".gif":
        return TrueMediaType.ANIMATED_IMAGE
    
    # ===== Static Images =====
    if ext in {".jpg", ".jpeg", ".png", ".avif"}:
        return TrueMediaType.STATIC_IMAGE
    
    # ===== Videos/MP4: Check if it's actually a GIF =====
    if ext in {".mp4", ".mov", ".webm", ".mkv", ".avi"}:
        analysis = _analyze_video_file(path)
        
        if not analysis:
            return TrueMediaType.UNKNOWN
        
        has_audio = analysis.get("has_audio", True)
        duration = analysis.get("duration", 999)
        
        # No audio + short duration = probably a GIF saved as MP4
        # (Twitter, Reddit, Imgur all do this)
        if not has_audio and duration < 30:
            return TrueMediaType.SHORT_VIDEO_GIF
        
        return TrueMediaType.VIDEO
    
    return TrueMediaType.UNKNOWN


def _analyze_video_file(path: Path) -> Optional[Dict[str, Any]]:
    """
    Use ffprobe to analyze a video file.
    
    Returns dict with:
    - has_audio: bool
    - duration: float
    - width: int
    - height: int
    - bitrate: int
    - codec: str
    """
    try:
        result = subprocess.run([
            str(FFPROBE_PATH),
            "-v", "error",
            "-show_entries", "stream=codec_type,codec_name,width,height,duration,bit_rate",
            "-show_entries", "format=duration,bit_rate",
            "-of", "json",
            str(path)
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        format_info = data.get("format", {})
        
        # Check for audio stream
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        
        # Get video stream info
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        
        if not video_stream:
            return None
        
        # Get duration (try stream first, then format)
        duration = video_stream.get("duration") or format_info.get("duration")
        duration = float(duration) if duration else None
        
        # Get dimensions
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        
        # Get bitrate
        bitrate = video_stream.get("bit_rate") or format_info.get("bit_rate")
        bitrate = int(bitrate) if bitrate else None
        
        # Get codec
        codec = video_stream.get("codec_name", "unknown")
        
        return {
            "has_audio": has_audio,
            "duration": duration,
            "width": width,
            "height": height,
            "bitrate": bitrate,
            "codec": codec
        }
    
    except FileNotFoundError:
        logger.warning("[SmartDetect] ffprobe not found - skipping video analysis")
        return None
    except Exception as e:
        logger.error(f"[SmartDetect] Error analyzing video {path.name}: {e}")
        return None


# ==============================================================================
# QUALITY DETECTION
# ==============================================================================

def is_thumbnail_size(width: int, height: int, min_size: int = 500) -> bool:
    """
    Check if image is too small to be useful (probably a thumbnail).
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        min_size: Minimum dimension (default 500px)
    
    Returns:
        True if image is too small
    """
    return width < min_size or height < min_size


def is_likely_screenshot(path: Path) -> bool:
    """
    Detect if image is likely a screenshot rather than original content.
    
    Checks for:
    - Letterboxing (black bars)
    - UI elements patterns
    - Aspect ratios common to phones/browsers
    
    Returns:
        True if likely a screenshot
    """
    try:
        with Image.open(path) as img:
            width, height = img.size
            
            # Common phone screenshot aspect ratios
            aspect = width / height if height > 0 else 0
            phone_aspects = [
                (9, 16),   # Most modern phones
                (9, 19.5), # iPhone X series
                (9, 18),   # Galaxy S series
            ]
            
            for w, h in phone_aspects:
                expected_aspect = w / h
                if abs(aspect - expected_aspect) < 0.05:
                    # Might be a phone screenshot
                    # Check for black bars at top/bottom (status bar area)
                    return _has_letterboxing(img)
            
            return False
    
    except Exception:
        return False


def _has_letterboxing(img: Image.Image) -> bool:
    """Check if image has black bars (letterboxing)"""
    width, height = img.size
    
    # Sample top and bottom 5% of image
    top_sample_height = int(height * 0.05)
    
    # Get top strip
    top = img.crop((0, 0, width, top_sample_height))
    top_colors = top.getcolors(maxcolors=10)
    
    # Get bottom strip  
    bottom = img.crop((0, height - top_sample_height, width, height))
    bottom_colors = bottom.getcolors(maxcolors=10)
    
    # Check if predominantly black/dark
    def is_mostly_dark(colors):
        if not colors:
            return False
        # Most common color
        most_common = max(colors, key=lambda x: x[0])
        color = most_common[1]
        # Check if dark (RGB all < 30)
        if isinstance(color, tuple):
            return all(c < 30 for c in color[:3])
        return color < 30
    
    return is_mostly_dark(top_colors) or is_mostly_dark(bottom_colors)


def is_upscaled(path: Path) -> bool:
    """
    Detect if image has been artificially upscaled.
    
    Checks for:
    - Interpolation artifacts
    - Unnatural sharpness patterns
    
    Returns:
        True if likely upscaled
    """
    # TODO: Implement proper upscale detection
    # For now, just return False
    # This would require analyzing frequency domain or edge patterns
    return False


# ==============================================================================
# CORRUPTION DETECTION
# ==============================================================================

def is_corrupt(path: Path) -> Tuple[bool, Optional[str]]:
    """
    Deep corruption check.
    
    Returns:
        (is_corrupt, error_message)
    """
    ext = path.suffix.lower()
    
    # Check file size
    if path.stat().st_size == 0:
        return True, "File is empty (0 bytes)"
    
    # Image files
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
        try:
            with Image.open(path) as img:
                # Try to load the image data
                img.load()
                
                # Check dimensions are reasonable
                width, height = img.size
                if width == 0 or height == 0:
                    return True, "Image has 0 dimensions"
                
                if width > 50000 or height > 50000:
                    return True, "Image dimensions unreasonably large"
                
                # For animated images, try to access all frames
                if ext in {".gif", ".webp"}:
                    try:
                        frame_count = 0
                        while True:
                            img.seek(frame_count)
                            frame_count += 1
                            if frame_count > 10000:  # Safety limit
                                break
                    except EOFError:
                        # Normal end of frames
                        pass
                
                return False, None
        
        except Exception as e:
            return True, f"Image corruption: {str(e)}"
    
    # Video files
    if ext in {".mp4", ".mov", ".webm", ".mkv", ".avi"}:
        analysis = _analyze_video_file(path)
        
        if not analysis:
            return True, "Video file unreadable by ffprobe"
        
        # Check for valid dimensions
        if analysis.get("width", 0) == 0 or analysis.get("height", 0) == 0:
            return True, "Video has 0 dimensions"
        
        # Check for valid duration
        if analysis.get("duration") == 0:
            return True, "Video has 0 duration"
        
        return False, None
    
    return False, None


# ==============================================================================
# DUPLICATE DETECTION
# ==============================================================================

def calculate_content_hash(path: Path) -> str:
    """
    Calculate SHA256 hash of file contents.
    
    Used for exact duplicate detection.
    
    Returns:
        Hex string of hash
    """
    sha256 = hashlib.sha256()
    
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    
    return sha256.hexdigest()


# ==============================================================================
# METADATA EXTRACTION
# ==============================================================================

def extract_metadata(path: Path) -> Dict[str, Any]:
    """
    Extract all useful metadata from a file.
    
    Returns dict with:
    - exif: EXIF data (if image)
    - video_info: Video metadata (if video)
    - file_info: Basic file info
    """
    metadata = {
        "filename": path.name,
        "extension": path.suffix,
        "size_bytes": path.stat().st_size,
        "created": path.stat().st_ctime,
        "modified": path.stat().st_mtime,
    }
    
    ext = path.suffix.lower()
    
    # Extract EXIF from images
    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                if exif:
                    metadata["exif"] = {
                        k: str(v) for k, v in exif.items()
                    }
                
                # Get basic image info
                metadata["image_info"] = {
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                    "format": img.format,
                }
        except Exception as e:
            logger.warning(f"[SmartDetect] Could not extract EXIF from {path.name}: {e}")
    
    # Extract video metadata
    if ext in {".mp4", ".mov", ".webm", ".mkv"}:
        analysis = _analyze_video_file(path)
        if analysis:
            metadata["video_info"] = analysis
    
    return metadata


# ==============================================================================
# COMPLETE ANALYSIS
# ==============================================================================

def analyze_media_file(path: Path, min_resolution: int = 500) -> MediaAnalysis:
    """
    Perform complete analysis of a media file.
    
    Args:
        path: Path to media file
        min_resolution: Minimum width/height for quality check
    
    Returns:
        MediaAnalysis with all detection results
    """
    warnings = []
    
    # Detect true type
    true_type = detect_true_media_type(path)
    
    # Check corruption
    corrupt, corrupt_msg = is_corrupt(path)
    if corrupt:
        warnings.append(f"Corrupted: {corrupt_msg}")
    
    # Get dimensions
    width = 0
    height = 0
    duration = None
    has_audio = False
    
    try:
        if true_type in (TrueMediaType.STATIC_IMAGE, TrueMediaType.ANIMATED_IMAGE):
            with Image.open(path) as img:
                width, height = img.size
        
        elif true_type in (TrueMediaType.SHORT_VIDEO_GIF, TrueMediaType.VIDEO):
            analysis = _analyze_video_file(path)
            if analysis:
                width = analysis.get("width", 0)
                height = analysis.get("height", 0)
                duration = analysis.get("duration")
                has_audio = analysis.get("has_audio", False)
    except Exception as e:
        warnings.append(f"Could not read dimensions: {e}")
    
    # Quality checks
    is_thumb = is_thumbnail_size(width, height, min_resolution)
    if is_thumb:
        warnings.append(f"Image too small ({width}x{height}) - probably a thumbnail")
    
    is_screen = is_likely_screenshot(path)
    if is_screen:
        warnings.append("Appears to be a screenshot, not original content")
    
    is_up = is_upscaled(path)
    if is_up:
        warnings.append("Image appears to be upscaled")
    
    # Calculate hash
    content_hash = calculate_content_hash(path)
    
    # Extract metadata
    metadata = extract_metadata(path)
    
    # File size
    size_mb = round(path.stat().st_size / (1024 * 1024), 2)
    
    return MediaAnalysis(
        true_type=true_type,
        width=width,
        height=height,
        duration_seconds=duration,
        has_audio=has_audio,
        file_size_mb=size_mb,
        is_thumbnail=is_thumb,
        is_upscaled=is_up,
        is_screenshot=is_screen,
        is_corrupt=corrupt,
        content_hash=content_hash,
        metadata=metadata,
        warnings=warnings
    )
