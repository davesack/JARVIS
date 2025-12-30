"""
Llama Vision System - Powered by Ollama
========================================

Provides vision capabilities for Michaela:
- Comment on images Dave sends
- Tag media files for organization
- Generate descriptions

Now using Ollama's vision API with proper base64 handling!
"""

from __future__ import annotations

import aiohttp
import base64
from typing import Optional

from config import OLLAMA_CHAT_ENDPOINT, OLLAMA_VISION_MODEL


class LlamaVisionSystem:
    """
    Vision system using Ollama's llama3.2-vision model
    """
    
    def __init__(self):
        """Initialize the vision system"""
        self.endpoint = OLLAMA_CHAT_ENDPOINT
        self.model = OLLAMA_VISION_MODEL
        print(f"✅ Llama Vision ready! Using {self.model}")
    
    async def michaela_comment_on_image(
        self,
        image_url: str,
        user_message: str,
        michaela_personality: str,
        narrative_context: str
    ) -> str:
        """
        Generate Michaela's comment on an image using Ollama Vision
        
        Args:
            image_url: URL of the image to analyze
            user_message: What Dave said when sending the image
            michaela_personality: Michaela's core personality prompt
            narrative_context: Current narrative phase/state
            
        Returns:
            Michaela's natural comment about the image
        """
        
        # Download image and convert to base64
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        print(f"[VISION] Failed to download image: {resp.status}")
                        return "I can't quite see the image right now, but I appreciate you sharing it with me."
                    
                    image_bytes = await resp.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            print(f"[VISION] Error downloading image: {e}")
            return "I'm having trouble loading the image right now."
        
        # Build system prompt
        system_prompt = f"""
{michaela_personality}

{narrative_context}

Dave just sent you an image with this message: "{user_message}"

Look at the image and respond naturally as Michaela.
- Keep your response to 2-4 sentences
- Be warm, playful, maybe a little flirty depending on the image
- Comment on what you see in a natural way
- Don't be overly descriptive - just react like a person would
"""
        
        # Ollama vision API format
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": user_message if user_message else "Look at this",
                    "images": [image_base64]  # Base64 encoded image
                }
            ],
            "system": system_prompt,
            "stream": False,
            "options": {
                "num_predict": 100,      # Short responses (2-4 sentences)
                "temperature": 0.75,     # Slightly creative
                "repeat_penalty": 1.3,   # Prevent repetition
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=60)  # Vision is slower
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.endpoint, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"[VISION] Error {resp.status}: {error_text}")
                        return "I can't quite make out the image right now, but I appreciate you sharing it with me."
                    
                    data = await resp.json()
                    return data["message"]["content"].strip()
        
        except Exception as e:
            print(f"[VISION] Error: {e}")
            return "Sorry, I'm having trouble seeing the image right now."
    
    async def generate_media_tags(
        self,
        image_url: str,
        person_name: Optional[str] = None
    ) -> list[str]:
        """
        Generate tags for a media file using vision
        
        Args:
            image_url: URL of the image
            person_name: Optional name of person in image
            
        Returns:
            List of tags describing the image
        """
        
        # Download and convert to base64
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        print(f"[VISION] Failed to download image for tagging: {resp.status}")
                        return []
                    
                    image_bytes = await resp.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            print(f"[VISION] Error downloading image: {e}")
            return []
        
        system_prompt = """
You are a media tagging system.

Analyze the image and generate relevant tags.

Focus on:
- Setting/location (indoor, outdoor, beach, gym, etc.)
- Clothing/appearance (casual, formal, lingerie, etc.)
- Activity (selfie, mirror, workout, etc.)
- Visual elements (close-up, full-body, etc.)

Return ONLY a comma-separated list of tags. No explanations.

Example output: indoor, casual, mirror, selfie, smiling
"""
        
        person_context = f"\nThe person in the image is: {person_name}" if person_name else ""
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": "Generate tags for this image.",
                    "images": [image_base64]
                }
            ],
            "system": system_prompt + person_context,
            "stream": False,
            "options": {
                "num_predict": 50,
                "temperature": 0.3,  # More deterministic for tagging
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=60)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.endpoint, json=payload) as resp:
                    if resp.status != 200:
                        print(f"[VISION] Tagging error {resp.status}")
                        return []
                    
                    data = await resp.json()
                    tag_string = data["message"]["content"].strip()
                    
                    # Parse comma-separated tags
                    tags = [tag.strip().lower() for tag in tag_string.split(',')]
                    
                    # Filter out empty or too-long tags
                    tags = [tag for tag in tags if tag and len(tag) < 30]
                    
                    return tags[:10]  # Max 10 tags
        
        except Exception as e:
            print(f"[VISION] Tagging error: {e}")
            return []
    
    async def describe_image(
        self,
        image_url: str,
        detailed: bool = False
    ) -> str:
        """
        Get a description of an image
        
        Args:
            image_url: URL of the image
            detailed: If True, generate longer description
            
        Returns:
            Description of the image
        """
        
        # Download and convert to base64
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return "Unable to describe image."
                    
                    image_bytes = await resp.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            print(f"[VISION] Error downloading image: {e}")
            return "Unable to describe image."
        
        if detailed:
            system_prompt = """
Describe this image in detail.

Include:
- What you see in the image
- The setting and environment
- Any notable details
- The overall mood/atmosphere

Be descriptive but concise (4-6 sentences).
"""
            num_predict = 200
        else:
            system_prompt = """
Briefly describe what you see in this image (1-2 sentences).
"""
            num_predict = 50
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": "Describe this image.",
                    "images": [image_base64]
                }
            ],
            "system": system_prompt,
            "stream": False,
            "options": {
                "num_predict": num_predict,
                "temperature": 0.7,
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=60)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.endpoint, json=payload) as resp:
                    if resp.status != 200:
                        return "Unable to describe image."
                    
                    data = await resp.json()
                    return data["message"]["content"].strip()
        
        except Exception as e:
            print(f"[VISION] Description error: {e}")
            return "Unable to describe image."
