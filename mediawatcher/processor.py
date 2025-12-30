"""
MediaWatcher 4.0 - Main Processing Pipeline

Orchestrates the complete file processing workflow.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Optional, List

from .mediawatcher_core import (
    FileType,
    ProcessingSource,
    ProcessingStage,
    FileMetadata,
    ProcessResult,
    validate_file,
    extract_metadata,
    get_file_size_mb
)
from .slug_resolver import SlugResolver, resolve_metadata
from .converter import (
    convert_static_image,
    convert_animated_gif,
    convert_video,
    compress_to_limit,
    generate_thumbnail
)

logger = logging.getLogger(__name__)


# ==============================================================================
# FILE PLACEMENT & ORGANIZATION
# ==============================================================================

def get_target_directory(
    media_root: Path,
    slug: str,
    file_type: FileType,
    nsfw: bool
) -> Path:
    """
    Determine target directory for a file.
    
    Structure:
        {media_root}/{slug}/images/[nsfw/]
        {media_root}/{slug}/gifs/[nsfw/]
        {media_root}/{slug}/videos/[nsfw/]
    
    Args:
        media_root: Root media directory
        slug: Person's slug
        file_type: Type of media file
        nsfw: Whether file is NSFW
    
    Returns:
        Path to target directory
    """
    slug_dir = media_root / slug
    
    if file_type == FileType.IMAGE:
        type_dir = slug_dir / "images"
    elif file_type == FileType.GIF:
        type_dir = slug_dir / "gifs"
    elif file_type == FileType.VIDEO:
        type_dir = slug_dir / "videos"
    else:
        # Unknown type - shouldn't happen, but handle gracefully
        type_dir = slug_dir / "other"
    
    if nsfw:
        type_dir = type_dir / "nsfw"
    
    return type_dir


def get_next_sequence_number(directory: Path, prefix: str, extension: str) -> int:
    """
    Get next available sequence number in directory.
    
    Scans for files matching pattern: {prefix}-####.{ext}
    Returns next number in sequence.
    
    Args:
        directory: Directory to scan
        prefix: Filename prefix (e.g., "anna-faith-nsfw")
        extension: File extension (e.g., ".webp")
    
    Returns:
        Next sequence number (starting at 1)
    """
    if not directory.exists():
        return 1
    
    max_num = 0
    pattern = f"{prefix}-*.{extension.lstrip('.')}"
    
    for file in directory.glob(pattern):
        stem = file.stem
        # Extract number from: prefix-####
        if stem.startswith(prefix + "-"):
            num_part = stem[len(prefix) + 1:]
            if num_part.isdigit():
                num = int(num_part)
                max_num = max(max_num, num)
    
    return max_num + 1


def generate_target_filename(
    slug: str,
    ai: bool,
    nsfw: bool,
    sequence: int,
    extension: str
) -> str:
    """
    Generate target filename following convention.
    
    Format: {slug}-[ai]-[nsfw]-####.{ext}
    
    Examples:
        anna-faith-0001.webp
        anna-faith-nsfw-0023.webp
        anna-faith-ai-nsfw-0005.webp
    
    Args:
        slug: Person's slug
        ai: AI-generated flag
        nsfw: NSFW flag
        sequence: Sequence number
        extension: File extension
    
    Returns:
        Filename string
    """
    parts = [slug]
    
    if ai:
        parts.append("ai")
    
    if nsfw:
        parts.append("nsfw")
    
    prefix = "-".join(parts)
    number = f"{sequence:04d}"
    
    return f"{prefix}-{number}{extension}"


def place_file_atomic(source: Path, destination: Path) -> bool:
    """
    Atomically move file to destination.
    
    Creates destination directory if needed.
    Uses shutil.move for atomic operation.
    
    Args:
        source: Source file path
        destination: Destination file path
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic move
        shutil.move(str(source), str(destination))
        
        logger.info(f"[Place] Moved: {source.name} → {destination}")
        return True
    
    except Exception as e:
        logger.error(f"[Place] Failed to move {source} → {destination}: {e}")
        return False


# ==============================================================================
# REVIEW FOLDER HANDLING
# ==============================================================================

def move_to_review(
    source: Path,
    review_root: Path,
    reason: str,
    metadata: Optional[FileMetadata] = None,
    suggestions: Optional[List[str]] = None
) -> Path:
    """
    Move file to review folder with reason.
    
    Creates metadata.json with details about why file needs review.
    
    Args:
        source: Source file to move
        review_root: Root review directory
        reason: Reason for review (unknown, corrupted, too-large, etc.)
        metadata: Optional file metadata
        suggestions: Optional suggestions for fixing
    
    Returns:
        Path to file in review folder
    """
    # Determine subfolder
    review_folder = review_root / reason
    review_folder.mkdir(parents=True, exist_ok=True)
    
    # Move file
    destination = review_folder / source.name
    
    # Handle duplicate names
    counter = 1
    while destination.exists():
        stem = source.stem
        ext = source.suffix
        destination = review_folder / f"{stem}_{counter}{ext}"
        counter += 1
    
    try:
        shutil.move(str(source), str(destination))
        logger.info(f"[Review] Moved to {reason}/: {source.name}")
    except Exception as e:
        logger.error(f"[Review] Failed to move {source} to review: {e}")
        return source
    
    # Create metadata file
    if metadata:
        metadata_file = destination.parent / f"{destination.stem}_metadata.json"
        try:
            import json
            from dataclasses import asdict
            from datetime import datetime
            
            meta_dict = {
                "original_filename": metadata.filename,
                "original_path": str(metadata.original_path),
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": metadata.source.value,
                "attempted_slug": metadata.slug,
                "handle": metadata.handle,
                "post_url": metadata.post_url,
                "suggestions": suggestions or []
            }
            
            with metadata_file.open("w", encoding="utf-8") as f:
                json.dump(meta_dict, f, indent=2)
        except Exception as e:
            logger.error(f"[Review] Failed to write metadata file: {e}")
    
    return destination


# ==============================================================================
# MAIN PROCESSING PIPELINE
# ==============================================================================

class MediaProcessor:
    """
    Main processing pipeline for media files.
    
    Orchestrates validation, resolution, conversion, compression, and placement.
    """
    
    def __init__(
        self,
        media_root: Path,
        processed_root: Path,
        review_root: Path,
        temp_root: Path,
        resolver: SlugResolver
    ):
        self.media_root = media_root
        self.processed_root = processed_root
        self.review_root = review_root
        self.temp_root = temp_root
        self.resolver = resolver
        
        # Ensure directories exist
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.processed_root.mkdir(parents=True, exist_ok=True)
        self.review_root.mkdir(parents=True, exist_ok=True)
        self.temp_root.mkdir(parents=True, exist_ok=True)
    
    def process_file(
        self,
        file_path: Path,
        source: ProcessingSource = ProcessingSource.INCOMING,
        handle: Optional[str] = None,
        post_url: Optional[str] = None,
        post_id: Optional[str] = None,
        force_slug: Optional[str] = None,
        force_nsfw: Optional[bool] = None
    ) -> ProcessResult:
        """
        Process a single file through the complete pipeline.
        
        Args:
            file_path: Path to file to process
            source: Where the file came from
            handle: Bluesky handle (if from Bluesky)
            post_url: Bluesky post URL (if from Bluesky)
            post_id: Bluesky post ID (if from Bluesky)
            force_slug: Override extracted slug (for manual mapping)
            force_nsfw: Override extracted NSFW flag (for manual classification)
        
        Returns:
            ProcessResult with outcome and details
        """
        start_time = time.time()
        result = ProcessResult(
            success=False,
            original_path=file_path,
            stage_reached=ProcessingStage.VALIDATE
        )
        
        logger.info(f"[Pipeline] Processing: {file_path.name}")
        
        # ============================================================
        # STAGE 1: VALIDATE
        # ============================================================
        validation = validate_file(file_path)
        if not validation:
            result.error = f"Validation failed: {validation.error}"
            result.review_folder = "corrupted"
            result.review_reason = validation.error
            move_to_review(file_path, self.review_root, "corrupted")
            return result
        
        # ============================================================
        # STAGE 1.5: SMART DETECTION & QUALITY CHECKS
        # ============================================================
        try:
            from .smart_detection import analyze_media_file
            
            analysis = analyze_media_file(file_path)
            
            # Check for corruption
            if analysis.is_corrupt:
                result.error = "File is corrupted"
                result.review_folder = "corrupted"
                result.review_reason = "Deep corruption check failed"
                move_to_review(file_path, self.review_root, "corrupted", metadata=metadata)
                return result
            
            # Check for thumbnail size
            if analysis.is_thumbnail:
                result.error = f"Image too small ({analysis.width}x{analysis.height})"
                result.review_folder = "thumbnail"
                result.review_reason = f"Below minimum resolution (500px)"
                move_to_review(file_path, self.review_root, "thumbnail", metadata=metadata)
                return result
            
            # Warn about screenshots (but don't reject)
            if analysis.is_screenshot:
                logger.warning(f"[Pipeline] {file_path.name} appears to be a screenshot")
            
            # Log warnings
            for warning in analysis.warnings:
                logger.warning(f"[Pipeline] {file_path.name}: {warning}")
        
        except ImportError:
            # Smart detection not available - skip
            logger.warning("[Pipeline] Smart detection not available")
        except Exception as e:
            # Don't fail the whole pipeline if analysis fails
            logger.warning(f"[Pipeline] Smart detection failed for {file_path.name}: {e}")
        
        # ============================================================
        # STAGE 2: EXTRACT METADATA
        # ============================================================
        result.stage_reached = ProcessingStage.EXTRACT
        
        metadata = extract_metadata(
            file_path,
            source,
            handle=handle,
            post_url=post_url,
            post_id=post_id
        )
        
        # Apply overrides if provided
        if force_slug:
            metadata.slug = force_slug
        if force_nsfw is not None:
            metadata.nsfw = force_nsfw
        
        logger.info(f"[Pipeline] Extracted: slug={metadata.slug}, nsfw={metadata.nsfw}, "
                   f"ai={metadata.ai}, type={metadata.file_type.value}")
        
        # ============================================================
        # STAGE 3: RESOLVE SLUG
        # ============================================================
        result.stage_reached = ProcessingStage.RESOLVE
        
        resolution = resolve_metadata(metadata, self.resolver)
        
        if not resolution:
            # Resolution failed
            reason = "unmapped-bluesky" if metadata.handle else "unknown"
            result.error = f"Could not resolve slug: {metadata.slug}"
            result.review_folder = reason
            result.review_reason = result.error
            
            move_to_review(
                file_path,
                self.review_root,
                reason,
                metadata=metadata,
                suggestions=resolution.suggestions
            )
            return result
        
        # Use resolved slug
        slug = resolution.slug
        result.slug = slug
        
        logger.info(f"[Pipeline] Resolved: {metadata.slug} → {slug} (method: {resolution.method})")
        
        # ============================================================
        # STAGE 4: CONVERT TO TARGET FORMAT
        # ============================================================
        result.stage_reached = ProcessingStage.CONVERT
        
        # Determine target extension
        if metadata.file_type == FileType.IMAGE:
            target_ext = ".webp"
        elif metadata.file_type == FileType.GIF:
            target_ext = ".webp"
        elif metadata.file_type == FileType.VIDEO:
            target_ext = ".mp4"
        else:
            result.error = f"Unknown file type: {metadata.file_type}"
            move_to_review(file_path, self.review_root, "unknown-type", metadata)
            return result
        
        # Create temp file for conversion
        temp_converted = self.temp_root / f"{file_path.stem}_converted{target_ext}"
        
        # Convert based on type
        # CRITICAL: If source is MP4, always use video converter (ffmpeg)
        # even if detected as GIF type (short videos)
        source_is_mp4 = file_path.suffix.lower() in {'.mp4', '.mov', '.mkv', '.avi', '.webm'}
        
        if metadata.file_type == FileType.IMAGE:
            conversion = convert_static_image(file_path, temp_converted, quality=95)
        elif metadata.file_type == FileType.GIF:
            if source_is_mp4:
                # MP4 detected as GIF (short video) - use ffmpeg to convert to animated webp
                conversion = convert_video(file_path, temp_converted, crf=23)
            else:
                # Actual GIF file - use PIL
                conversion = convert_animated_gif(file_path, temp_converted, quality=85)
        elif metadata.file_type == FileType.VIDEO:
            conversion = convert_video(file_path, temp_converted, crf=23)
        
        if not conversion.success:
            result.error = f"Conversion failed: {conversion.error}"
            move_to_review(file_path, self.review_root, "conversion-failed", metadata)
            return result
        
        converted_file = conversion.output_path
        
        # ============================================================
        # STAGE 5: COMPRESS TO SIZE LIMIT
        # ============================================================
        result.stage_reached = ProcessingStage.COMPRESS
        
        compression = compress_to_limit(
            converted_file,
            metadata.file_type,
            temp_dir=self.temp_root
        )
        
        if not compression.under_limit:
            # File too large even at minimum quality
            result.error = compression.error
            result.review_folder = "too-large"
            result.review_reason = compression.error
            result.size_mb = compression.size_mb
            result.quality = compression.quality
            
            # Move original (not converted) to review
            move_to_review(file_path, self.review_root, "too-large", metadata)
            
            # Clean up temp files
            try:
                converted_file.unlink(missing_ok=True)
                compression.output_path.unlink(missing_ok=True)
            except:
                pass
            
            return result
        
        final_file = compression.output_path
        result.size_mb = compression.size_mb
        result.quality = compression.quality
        
        logger.info(f"[Pipeline] Compressed: {compression.size_mb}MB at quality {compression.quality}")
        
        # ============================================================
        # STAGE 6: GENERATE THUMBNAIL (if needed)
        # ============================================================
        result.stage_reached = ProcessingStage.THUMBNAIL
        
        thumbnail_path = None
        if metadata.file_type in (FileType.GIF, FileType.VIDEO):
            thumbnail_path = generate_thumbnail(
                final_file,
                metadata.file_type,
                output_path=self.temp_root / f"{final_file.stem}_thumb.webp"
            )
        
        # ============================================================
        # STAGE 7: CHECK FOR DUPLICATES
        # ============================================================
        result.stage_reached = ProcessingStage.DEDUPE
        
        # Get target directory and filename
        target_dir = get_target_directory(
            self.media_root,
            slug,
            metadata.file_type,
            metadata.nsfw
        )
        
        # Build filename prefix for sequence number
        prefix_parts = [slug]
        if metadata.ai:
            prefix_parts.append("ai")
        if metadata.nsfw:
            prefix_parts.append("nsfw")
        prefix = "-".join(prefix_parts)
        
        # Get next sequence number
        sequence = get_next_sequence_number(target_dir, prefix, target_ext)
        
        # Generate final filename
        final_filename = generate_target_filename(
            slug,
            metadata.ai,
            metadata.nsfw,
            sequence,
            target_ext
        )
        
        final_destination = target_dir / final_filename
        
        # Generate thumbnail filename if applicable
        if thumbnail_path:
            thumb_filename = f"{final_filename.rsplit('.', 1)[0]}_thumb.webp"
            thumb_destination = target_dir / thumb_filename
        else:
            thumb_destination = None
        
        # ============================================================
        # STAGE 8: PLACE FILES
        # ============================================================
        result.stage_reached = ProcessingStage.PLACE
        
        # Place main file
        if not place_file_atomic(final_file, final_destination):
            result.error = "Failed to place file in final location"
            return result
        
        result.final_path = final_destination
        
        # Place thumbnail if exists
        if thumbnail_path and thumb_destination:
            place_file_atomic(thumbnail_path, thumb_destination)
        
        # Move original to processed folder (backup for 30 days)
        processed_backup = self.processed_root / file_path.name
        try:
            shutil.move(str(file_path), str(processed_backup))
            logger.info(f"[Pipeline] Backed up original to: {processed_backup}")
        except Exception as e:
            logger.warning(f"[Pipeline] Could not backup original: {e}")
            # Not fatal - file is already placed
        
        # ============================================================
        # STAGE 9: COMPLETE
        # ============================================================
        result.stage_reached = ProcessingStage.COMPLETE
        result.success = True
        result.processing_time_seconds = round(time.time() - start_time, 2)
        
        logger.info(f"[Pipeline] ✅ SUCCESS: {file_path.name} → {final_destination} "
                   f"({result.size_mb}MB, quality {result.quality}, {result.processing_time_seconds}s)")
        
        return result
    
    def process_batch(
        self,
        files: List[Path],
        source: ProcessingSource = ProcessingSource.INCOMING,
        dry_run: bool = False
    ) -> List[ProcessResult]:
        """
        Process multiple files in batch.
        
        Args:
            files: List of files to process
            source: Where files came from
            dry_run: If True, only simulate processing
        
        Returns:
            List of ProcessResult objects
        """
        results = []
        total = len(files)
        
        logger.info(f"[Batch] Processing {total} files (dry_run={dry_run})...")
        
        for idx, file_path in enumerate(files, 1):
            logger.info(f"[Batch] [{idx}/{total}] {file_path.name}")
            
            if dry_run:
                # TODO: Implement dry run simulation
                logger.info(f"[Batch] DRY RUN: Would process {file_path.name}")
                continue
            
            result = self.process_file(file_path, source=source)
            results.append(result)
        
        # Summary
        success_count = sum(1 for r in results if r.success)
        error_count = total - success_count
        
        logger.info(f"[Batch] Complete: {success_count} succeeded, {error_count} failed")
        
        return results
