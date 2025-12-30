from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp

from config import MEDIA_ROOT, BLUESKY_CACHE_RETENTION_DAYS
from .api import BlueskyAPI

log = logging.getLogger("bluesky.media")

# -----------------------------------------------------------------------------
# Filesystem layout
# -----------------------------------------------------------------------------

BSKY_MEDIA_ROOT = MEDIA_ROOT / "bluesky"
BSKY_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Cache management
# -----------------------------------------------------------------------------

def cleanup_bluesky_cache(retention_days: Optional[int] = None) -> int:
    """
    Delete cached Bluesky media files older than retention_days.
    Returns the number of files deleted.
    """
    if not BSKY_MEDIA_ROOT.exists():
        return 0

    days = retention_days if retention_days is not None else BLUESKY_CACHE_RETENTION_DAYS
    cutoff = time.time() - (days * 86400)

    deleted = 0
    for path in BSKY_MEDIA_ROOT.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
        except OSError:
            continue

    return deleted

# -----------------------------------------------------------------------------
# URL helpers
# -----------------------------------------------------------------------------

def _ext_from_url(url: str, default: str = ".jpg") -> str:
    try:
        suffix = Path(urlparse(url).path).suffix
        return suffix if suffix else default
    except Exception:
        return default


def _is_video_url(url: str) -> bool:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix in {".mp4", ".webm", ".mov", ".mkv"}

# -----------------------------------------------------------------------------
# Low-level download helpers
# -----------------------------------------------------------------------------

async def _download_url(
    session: aiohttp.ClientSession,
    url: str,
    dest: Path,
) -> Optional[Path]:
    """Download a URL to disk. Returns the destination path or None on failure."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                log.warning("[BSKY_MEDIA] GET failed %s (%s)", url, resp.status)
                return None
            dest.write_bytes(await resp.read())
        return dest
    except Exception:
        log.exception("[BSKY_MEDIA] Download error: %s", url)
        return None


async def _download_blob(
    api: BlueskyAPI,
    cid: str,
    author_did: str,
    dest: Path,
) -> Optional[Path]:
    """Download a Bluesky blob (used for videos)."""
    await api.ensure_session()
    assert api.session is not None

    url = (
        f"{api.BASE_URL}/com.atproto.sync.getBlob"
        f"?cid={cid}&did={author_did}"
    )

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with api.session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status != 200:
                log.warning("[BSKY_MEDIA] Blob fetch failed %s (%s)", cid, resp.status)
                return None
            dest.write_bytes(await resp.read())
        return dest
    except Exception:
        log.exception("[BSKY_MEDIA] Blob download exception: %s", cid)
        return None

# -----------------------------------------------------------------------------
# Embed parsing
# -----------------------------------------------------------------------------

def _extract_media(embed: dict) -> Tuple[List[str], Optional[str], Optional[str]]:
    """
    Extract media references from a Bluesky embed payload.

    Returns:
        image_urls   -> fullsize image URLs (no thumbnails)
        video_cid    -> CID if a video embed is present
        thumbnail_url-> preferred hero image for embeds
    """
    if not isinstance(embed, dict):
        return [], None, None

    image_urls: List[str] = []
    video_cid: Optional[str] = None
    thumbnail_url: Optional[str] = None

    etype = embed.get("$type")

    # Native video embed
    if etype == "app.bsky.embed.video#view":
        video_cid = embed.get("cid")
        thumbnail_url = embed.get("thumbnail")
        return image_urls, video_cid, thumbnail_url

    # Image embed
    images = embed.get("images")
    if isinstance(images, list):
        for img in images:
            url = img.get("fullsize") or img.get("thumb")
            if url:
                image_urls.append(url)

    # External embed
    external = embed.get("external")
    if isinstance(external, dict):
        thumb = external.get("thumb")
        uri = external.get("uri")

        if thumb and not _is_video_url(thumb):
            image_urls.append(thumb)

        if uri and _is_video_url(uri):
            # External videos are not blobs we can fetch here
            video_cid = None

    # Nested media (quotes / reposts)
    nested = embed.get("media")
    if isinstance(nested, dict):
        nested_images = nested.get("images")
        if isinstance(nested_images, list):
            for img in nested_images:
                url = img.get("fullsize") or img.get("thumb")
                if url:
                    image_urls.append(url)

    return image_urls, video_cid, thumbnail_url

# -----------------------------------------------------------------------------
# Public media API
# -----------------------------------------------------------------------------

async def download_media_for_post(
    api: BlueskyAPI,
    handle: str,
    post_uri: str,
    embed: dict,
    author_did: Optional[str],
) -> Tuple[List[Path], List[Path], Optional[Path]]:
    """
    Download all media associated with a single post.

    Returns:
        image_paths     -> REAL images only (ordered)
        video_paths     -> downloaded video blobs
        thumbnail_path -> hero image for embed
    """
    if not embed:
        return [], [], None

    rkey = post_uri.rsplit("/", 1)[-1] if post_uri else "unknown"
    post_dir = BSKY_MEDIA_ROOT / handle / rkey

    image_urls, video_cid, thumbnail_url = _extract_media(embed)

    await api.ensure_session()
    assert api.session is not None

    # --------------------
    # Images (parallel)
    # --------------------
    image_paths: List[Path] = []

    async def _dl_image(idx: int, url: str) -> Optional[Path]:
        ext = _ext_from_url(url)
        dest = post_dir / f"{handle.replace('.', '-')}-{idx:04d}{ext}"
        return await _download_url(api.session, url, dest)

    tasks = [_dl_image(i, url) for i, url in enumerate(image_urls)]
    for result in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(result, Path):
            image_paths.append(result)

    # --------------------
    # Thumbnail (hero image only)
    # --------------------
    thumbnail_path: Optional[Path] = None
    if thumbnail_url:
        thumb_dest = post_dir / "thumbnail.jpg"
        thumb = await _download_url(api.session, thumbnail_url, thumb_dest)
        if thumb:
            thumbnail_path = thumb

    # --------------------
    # Video blob
    # --------------------
    video_paths: List[Path] = []
    if video_cid and author_did:
        dest = post_dir / f"{handle.replace('.', '-')}-video.mp4"
        blob = await _download_blob(api, video_cid, author_did, dest)
        if blob:
            video_paths.append(blob)

    return image_paths, video_paths, thumbnail_path


async def download_media_for_feed_item(
    api: BlueskyAPI,
    feed_item: dict,
) -> Tuple[List[Path], List[Path], Optional[Path], str, str]:
    """
    Convenience wrapper for feed items.

    Returns:
        image_paths
        video_paths
        thumbnail_path
        handle
        post_uri
    """
    post = feed_item.get("post") or {}
    author = post.get("author") or {}

    handle = author.get("handle", "unknown").lower()
    author_did = author.get("did")
    post_uri = post.get("uri", "")
    embed = post.get("embed") or {}

    images, videos, thumb = await download_media_for_post(
        api=api,
        handle=handle,
        post_uri=post_uri,
        embed=embed,
        author_did=author_did,
    )

    return images, videos, thumb, handle, post_uri
