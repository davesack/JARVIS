"""
MediaWatcher 4.0 - Conversion & Compression Engine

Handles format conversion and size optimization with quality stepping.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional, List

from PIL import Image

from config import FFMPEG_PATH, FFPROBE_PATH
from .mediawatcher_core import (
    FileType,
    ConversionResult,
    CompressionResult,
    get_file_size_mb,
    STATIC_IMAGE_TARGET,
    ANIMATED_TARGET,
    VIDEO_TARGET,
    DISCORD_SIZE_LIMIT_MB,
    IMAGE_QUALITY_STEPS,
    ANIMATED_QUALITY_STEPS,
    VIDEO_CRF_STEPS
)

logger = logging.getLogger(__name__)


# ==============================================================================
# FORMAT CONVERSION
# ==============================================================================

def convert_static_image(input_path: Path, output_path: Path, quality: int = 95) -> ConversionResult:
    """
    Convert static image to webp format.
    
    Args:
        input_path: Source image file
        output_path: Destination webp file
        quality: WebP quality (1-100)
    
    Returns:
        ConversionResult with success status and file info
    """
    try:
        original_size = get_file_size_mb(input_path)
        
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            # Save as WebP
            img.save(
                output_path,
                "WEBP",
                quality=quality,
                method=6  # Slowest but best compression
            )
        
        converted_size = get_file_size_mb(output_path)
        
        logger.info(f"[Convert] Static image: {input_path.name} → {output_path.name} "
                   f"({original_size}MB → {converted_size}MB)")
        
        return ConversionResult(
            success=True,
            output_path=output_path,
            original_size_mb=original_size,
            converted_size_mb=converted_size,
            format="webp"
        )
    
    except Exception as e:
        logger.error(f"[Convert] Failed to convert {input_path}: {e}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_size_mb=get_file_size_mb(input_path),
            converted_size_mb=0,
            format="webp",
            error=str(e)
        )


def convert_animated_gif(input_path: Path, output_path: Path, quality: int = 85) -> ConversionResult:
    """
    Convert animated GIF to animated WebP format.
    
    For large GIFs (>5MB), uses ffmpeg for better compression.
    For small GIFs, uses PIL.
    
    Args:
        input_path: Source GIF file
        output_path: Destination animated webp file
        quality: WebP quality (1-100)
    
    Returns:
        ConversionResult
    """
    try:
        original_size = get_file_size_mb(input_path)
        
        # For large GIFs, use ffmpeg (better compression)
        if original_size > 5.0:
            logger.info(f"[Convert] Large GIF ({original_size}MB), using ffmpeg")
            
            cmd = [
                str(FFMPEG_PATH),
                "-i", str(input_path),
                "-c:v", "libwebp",
                "-lossless", "0",
                "-quality", str(quality),
                "-preset", "default",
                "-loop", "0",
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise Exception(f"ffmpeg failed: {result.stderr}")
        
        else:
            # Small GIF, use PIL
            with Image.open(input_path) as img:
                img.save(
                    output_path,
                    "WEBP",
                    save_all=True,
                    quality=quality,
                    method=6,
                    minimize_size=True
                )
        
        converted_size = get_file_size_mb(output_path)
        
        logger.info(f"[Convert] Animated GIF: {input_path.name} → {output_path.name} "
                   f"({original_size}MB → {converted_size}MB)")
        
        return ConversionResult(
            success=True,
            output_path=output_path,
            original_size_mb=original_size,
            converted_size_mb=converted_size,
            format="animated-webp"
        )
    
    except Exception as e:
        logger.error(f"[Convert] Failed to convert animated GIF {input_path}: {e}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_size_mb=get_file_size_mb(input_path),
            converted_size_mb=0,
            format="animated-webp",
            error=str(e)
        )


def convert_video(input_path: Path, output_path: Path, crf: int = 23) -> ConversionResult:
    """
    Convert video to MP4 h264 format OR animated WebP.
    
    Automatically detects output format based on file extension:
    - .mp4 → h264 MP4
    - .webp → animated WebP
    
    Args:
        input_path: Source video file
        output_path: Destination file (.mp4 or .webp)
        crf: Constant Rate Factor (18-28, lower = better quality)
    
    Returns:
        ConversionResult
    """
    try:
        original_size = get_file_size_mb(input_path)
        output_ext = output_path.suffix.lower()
        
        if output_ext == '.webp':
            # Convert to animated WebP
            cmd = [
                str(FFMPEG_PATH),
                "-i", str(input_path),
                "-c:v", "libwebp",
                "-lossless", "0",
                "-quality", str(100 - crf),  # Convert CRF to WebP quality
                "-preset", "default",
                "-loop", "0",
                "-y",
                str(output_path)
            ]
            output_format = "animated-webp"
        
        else:
            # Convert to MP4 h264
            cmd = [
                str(FFMPEG_PATH),
                "-i", str(input_path),
                "-c:v", "libx264",
                "-crf", str(crf),
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                "-y",
                str(output_path)
            ]
            output_format = "mp4"
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg failed: {result.stderr}")
        
        converted_size = get_file_size_mb(output_path)
        
        logger.info(f"[Convert] Video: {input_path.name} → {output_path.name} "
                   f"({original_size}MB → {converted_size}MB, format={output_format})")
        
        return ConversionResult(
            success=True,
            output_path=output_path,
            original_size_mb=original_size,
            converted_size_mb=converted_size,
            format=output_format
        )
    
    except FileNotFoundError:
        error = "ffmpeg not installed or not in PATH"
        logger.error(f"[Convert] {error}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_size_mb=get_file_size_mb(input_path),
            converted_size_mb=0,
            format="mp4",
            error=error
        )
    except subprocess.TimeoutExpired:
        error = "Video conversion timeout (file too large or complex)"
        logger.error(f"[Convert] {error}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_size_mb=get_file_size_mb(input_path),
            converted_size_mb=0,
            format="mp4",
            error=error
        )
    except Exception as e:
        logger.error(f"[Convert] Failed to convert video {input_path}: {e}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_size_mb=get_file_size_mb(input_path),
            converted_size_mb=0,
            format="mp4",
            error=str(e)
        )


# ==============================================================================
# COMPRESSION WITH QUALITY STEPPING
# ==============================================================================

def compress_to_limit(
    input_path: Path,
    file_type: FileType,
    limit_mb: float = DISCORD_SIZE_LIMIT_MB,
    temp_dir: Optional[Path] = None
) -> CompressionResult:
    """
    Compress file to be under size limit using quality stepping.
    
    Tries progressively lower quality settings until file is under limit.
    Stops at minimum quality threshold (75% for images, CRF 28 for videos).
    
    Args:
        input_path: File to compress
        file_type: Type of media file
        limit_mb: Target size limit in MB
        temp_dir: Directory for temporary files
    
    Returns:
        CompressionResult with final file and quality info
    """
    if temp_dir is None:
        temp_dir = input_path.parent
    
    current_size = get_file_size_mb(input_path)
    
    # Already under limit
    if current_size <= limit_mb:
        return CompressionResult(
            success=True,
            output_path=input_path,
            size_mb=current_size,
            quality=100,  # Original quality
            under_limit=True
        )
    
    # Determine quality steps based on file type
    if file_type == FileType.IMAGE:
        quality_steps = IMAGE_QUALITY_STEPS
    elif file_type == FileType.GIF:
        quality_steps = ANIMATED_QUALITY_STEPS
    elif file_type == FileType.VIDEO:
        quality_steps = VIDEO_CRF_STEPS
    else:
        return CompressionResult(
            success=False,
            output_path=input_path,
            size_mb=current_size,
            quality=0,
            under_limit=False,
            error="Unknown file type"
        )
    
    # Try each quality step
    for quality in quality_steps:
        temp_output = temp_dir / f"{input_path.stem}_q{quality}{input_path.suffix}"
        
        logger.info(f"[Compress] Trying quality {quality} for {input_path.name}...")
        
        # Apply compression
        if file_type == FileType.IMAGE:
            result = convert_static_image(input_path, temp_output, quality)
        elif file_type == FileType.GIF:
            result = convert_animated_gif(input_path, temp_output, quality)
        elif file_type == FileType.VIDEO:
            result = convert_video(input_path, temp_output, quality)
        
        if not result.success:
            continue
        
        # Check size
        size_mb = get_file_size_mb(temp_output)
        
        if size_mb <= limit_mb:
            # Success!
            logger.info(f"[Compress] Success at quality {quality}: {size_mb}MB <= {limit_mb}MB")
            return CompressionResult(
                success=True,
                output_path=temp_output,
                size_mb=size_mb,
                quality=quality,
                under_limit=True
            )
        else:
            # Still too large, try next quality
            logger.info(f"[Compress] Still too large at quality {quality}: {size_mb}MB > {limit_mb}MB")
            # Clean up temp file
            try:
                temp_output.unlink()
            except:
                pass
    
    # Failed to compress under limit
    logger.warning(f"[Compress] Could not compress {input_path.name} under {limit_mb}MB "
                  f"(final size: {current_size}MB at minimum quality {quality_steps[-1]})")
    
    return CompressionResult(
        success=False,
        output_path=input_path,
        size_mb=current_size,
        quality=quality_steps[-1],
        under_limit=False,
        error=f"File too large ({current_size}MB) - cannot compress below {limit_mb}MB at minimum quality"
    )


# ==============================================================================
# THUMBNAIL GENERATION
# ==============================================================================

def generate_thumbnail(input_path: Path, file_type: FileType, output_path: Optional[Path] = None) -> Optional[Path]:
    """
    Generate thumbnail for video or animated file.
    
    For images: No thumbnail needed (return None)
    For GIFs: Extract first frame
    For Videos: Extract frame at 10% mark
    
    Args:
        input_path: Source media file
        file_type: Type of media
        output_path: Where to save thumbnail (if None, uses input_path stem + _thumb.webp)
    
    Returns:
        Path to thumbnail, or None if not applicable/failed
    """
    if file_type == FileType.IMAGE:
        # Static images don't need thumbnails
        return None
    
    if output_path is None:
        # Thumbnails go in /thumbnails/ subfolder
        thumb_dir = input_path.parent / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)
        output_path = thumb_dir / f"{input_path.stem}_thumb.webp"
    
    try:
        if file_type == FileType.GIF:
            # Extract first frame from animated file
            with Image.open(input_path) as img:
                img.seek(0)
                frame = img.copy()
                frame.save(output_path, "WEBP", quality=85)
            
            logger.info(f"[Thumbnail] Generated for GIF: {output_path.name}")
            return output_path
        
        elif file_type == FileType.VIDEO:
            # Extract frame at 10% mark using ffmpeg
            # First get video duration
            probe_cmd = [
                str(FFPROBE_PATH),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(input_path)
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception("Could not probe video duration")
            
            duration = float(result.stdout.strip())
            timestamp = duration * 0.1  # 10% mark
            
            # Extract frame
            extract_cmd = [
                str(FFMPEG_PATH),
                "-ss", str(timestamp),
                "-i", str(input_path),
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(extract_cmd, capture_output=True, timeout=30)
            if result.returncode != 0:
                raise Exception("Could not extract video frame")
            
            logger.info(f"[Thumbnail] Generated for video: {output_path.name}")
            return output_path
    
    except Exception as e:
        logger.error(f"[Thumbnail] Failed to generate thumbnail for {input_path}: {e}")
        return None
