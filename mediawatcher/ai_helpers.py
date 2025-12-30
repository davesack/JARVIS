# utils/mediawatcher/ai_helpers.py

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
import json
import base64

logger = logging.getLogger(__name__)

# Ollama configuration - update these in your config.py
try:
    from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_ENABLED
except ImportError:
    OLLAMA_URL = "http://localhost:11434"
    OLLAMA_MODEL = "llama3.2-vision:latest"
    OLLAMA_ENABLED = False


async def ai_tag_media(path: Path) -> Dict[str, List[str]]:
    """
    Use Ollama to generate tags for media files.
    
    Returns structure like:
        {
            "suggested_tags": ["bikini", "beach", "outdoor"],
            "warnings": []
        }
    """
    if not OLLAMA_ENABLED:
        return {"suggested_tags": [], "warnings": []}
    
    try:
        # Only process images for now (Ollama vision models work best with images)
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            return {"suggested_tags": [], "warnings": []}
        
        # Read and encode image
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Build prompt
        prompt = """Analyze this image and provide tags for categorization.

Focus on:
- Clothing/attire (e.g., bikini, dress, casual, lingerie)
- Setting (e.g., beach, indoor, studio, outdoor)
- Activity (e.g., posing, candid, action)
- Style (e.g., professional, casual, artistic)
- Content rating (sfw, nsfw)

Return ONLY a JSON array of tags, nothing else. Example:
["bikini", "beach", "outdoor", "professional", "sfw"]

Tags:"""

        # Call Ollama API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 100,
                    }
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.error(f"Ollama API error: {response.status}")
                    return {"suggested_tags": [], "warnings": []}
                
                result = await response.json()
                response_text = result.get("response", "")
                
                # Try to parse JSON from response
                tags = _parse_tags_from_response(response_text)
                
                return {
                    "suggested_tags": tags,
                    "warnings": []
                }
    
    except asyncio.TimeoutError:
        logger.warning(f"Ollama timeout for {path.name}")
        return {"suggested_tags": [], "warnings": ["AI tagging timeout"]}
    except Exception as e:
        logger.exception(f"Error in AI tagging for {path.name}: {e}")
        return {"suggested_tags": [], "warnings": [f"AI error: {str(e)}"]}


def _parse_tags_from_response(text: str) -> List[str]:
    """
    Extract tags from Ollama response.
    
    Handles various response formats:
    - Pure JSON array: ["tag1", "tag2"]
    - Markdown code blocks: ```json ["tag1", "tag2"] ```
    - Plain text lists: "tag1, tag2, tag3"
    """
    # Clean up markdown code blocks
    text = text.strip()
    
    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
        text = text.replace("```json", "").replace("```", "").strip()
    
    # Try to parse as JSON
    try:
        tags = json.loads(text)
        if isinstance(tags, list):
            return [str(t).lower().strip() for t in tags if t]
    except json.JSONDecodeError:
        pass
    
    # Fallback: try comma-separated
    if "," in text:
        tags = [t.strip().lower() for t in text.split(",") if t.strip()]
        return tags
    
    # Fallback: try space-separated
    tags = text.split()
    return [t.lower().strip("[]\"',") for t in tags if t]


# Sync wrapper for compatibility
def ai_tag_media_sync(path: Path) -> Dict[str, List[str]]:
    """Synchronous wrapper for ai_tag_media"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(ai_tag_media(path))


# Convenience function for batch processing
async def ai_tag_media_batch(paths: List[Path]) -> Dict[Path, Dict[str, List[str]]]:
    """
    Tag multiple media files concurrently.
    
    Returns:
        Dictionary mapping paths to their tag results
    """
    tasks = [ai_tag_media(path) for path in paths]
    results = await asyncio.gather(*tasks)
    
    return {
        path: result
        for path, result in zip(paths, results)
    }
