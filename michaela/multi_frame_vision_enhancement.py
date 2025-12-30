"""
Multi-Frame Video/GIF Analysis - ADD THESE METHODS TO YOUR EXISTING llama_vision.py
===================================================================================

These methods enhance your existing LlamaVisionSystem class with:
- Multi-frame extraction from videos/GIFs
- OCR text detection across frames
- Motion analysis
- Comprehensive video descriptions

Installation requirements:
pip install opencv-python pytesseract pillow --break-system-packages

Also install Tesseract OCR:
Ubuntu: sudo apt-get install tesseract-ocr
"""

import cv2
import pytesseract
import base64
import numpy as np
from io import BytesIO
from PIL import Image
from typing import List, Dict, Optional
import aiohttp


# ============================================================================
# ADD THESE METHODS TO YOUR LlamaVisionSystem CLASS
# ============================================================================

async def extract_frames_from_video(
    self,
    video_url: str,
    num_frames: int = 5,
    method: str = 'evenly_spaced'
) -> List[bytes]:
    """
    Extract frames from a video or GIF
    
    Args:
        video_url: URL of the video/GIF
        num_frames: How many frames to extract (default 5)
        method: 'evenly_spaced', 'key_frames', or 'motion_peaks'
    
    Returns:
        List of frame images as bytes
    """
    
    # Download video
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url) as resp:
                if resp.status != 200:
                    print(f"[VISION] Failed to download video: {resp.status}")
                    return []
                
                video_bytes = await resp.read()
    except Exception as e:
        print(f"[VISION] Error downloading video: {e}")
        return []
    
    # Save temporarily
    temp_path = "/tmp/temp_video.mp4"
    with open(temp_path, 'wb') as f:
        f.write(video_bytes)
    
    # Open with OpenCV
    cap = cv2.VideoCapture(temp_path)
    
    if not cap.isOpened():
        print("[VISION] Failed to open video")
        return []
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    frames = []
    
    if method == 'evenly_spaced':
        # Extract frames at even intervals
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Convert to bytes
                pil_img = Image.fromarray(frame_rgb)
                buf = BytesIO()
                pil_img.save(buf, format='JPEG', quality=85)
                frames.append(buf.getvalue())
    
    elif method == 'motion_peaks':
        # Find frames with most motion (scene changes)
        prev_frame = None
        motion_scores = []
        
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_frame is not None:
                # Calculate frame difference
                diff = cv2.absdiff(gray, prev_frame)
                motion_score = np.mean(diff)
                motion_scores.append((i, motion_score, frame))
            
            prev_frame = gray
        
        # Get frames with highest motion
        motion_scores.sort(key=lambda x: x[1], reverse=True)
        top_frames = motion_scores[:num_frames]
        top_frames.sort(key=lambda x: x[0])  # Sort by time
        
        for _, _, frame in top_frames:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            buf = BytesIO()
            pil_img.save(buf, format='JPEG', quality=85)
            frames.append(buf.getvalue())
    
    cap.release()
    
    return frames


async def extract_text_from_frame(self, frame_bytes: bytes) -> Dict:
    """
    Extract text from a frame using OCR
    
    Returns:
        {
            'text': str,
            'confidence': float,
            'found': bool
        }
    """
    
    try:
        # Convert bytes to PIL Image
        img = Image.open(BytesIO(frame_bytes))
        
        # Use Tesseract OCR
        ocr_data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT
        )
        
        # Filter by confidence
        texts = []
        confidences = []
        
        for i, conf in enumerate(ocr_data['conf']):
            if conf > 30:  # Confidence threshold
                text = ocr_data['text'][i].strip()
                if text:
                    texts.append(text)
                    confidences.append(conf)
        
        if texts:
            combined_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences)
            
            return {
                'text': combined_text,
                'confidence': avg_confidence,
                'found': True
            }
        else:
            return {
                'text': '',
                'confidence': 0,
                'found': False
            }
    
    except Exception as e:
        print(f"[VISION] OCR error: {e}")
        return {
            'text': '',
            'confidence': 0,
            'found': False
        }


async def analyze_video_motion(self, video_url: str) -> Dict:
    """
    Analyze motion level in a video
    
    Returns:
        {
            'level': str,  # 'static', 'low', 'moderate', 'high'
            'score': float,
            'scene_changes': int
        }
    """
    
    # Download video
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url) as resp:
                if resp.status != 200:
                    return {'level': 'unknown', 'score': 0, 'scene_changes': 0}
                video_bytes = await resp.read()
    except:
        return {'level': 'unknown', 'score': 0, 'scene_changes': 0}
    
    temp_path = "/tmp/temp_video_motion.mp4"
    with open(temp_path, 'wb') as f:
        f.write(video_bytes)
    
    cap = cv2.VideoCapture(temp_path)
    
    prev_frame = None
    motion_scores = []
    scene_changes = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            motion_score = np.mean(diff)
            motion_scores.append(motion_score)
            
            # Detect scene changes (large differences)
            if motion_score > 50:  # Threshold
                scene_changes += 1
        
        prev_frame = gray
    
    cap.release()
    
    if not motion_scores:
        return {'level': 'unknown', 'score': 0, 'scene_changes': 0}
    
    avg_motion = sum(motion_scores) / len(motion_scores)
    
    # Categorize
    if avg_motion < 5:
        level = 'static'
    elif avg_motion < 15:
        level = 'low'
    elif avg_motion < 30:
        level = 'moderate'
    else:
        level = 'high'
    
    return {
        'level': level,
        'score': avg_motion,
        'scene_changes': scene_changes
    }


async def michaela_comment_on_video(
    self,
    video_url: str,
    user_message: str,
    michaela_personality: str,
    narrative_context: str,
    num_frames: int = 3
) -> str:
    """
    Generate Michaela's comment on a video/GIF using multi-frame analysis
    
    This is BETTER than single-frame because:
    - Understands motion and progression
    - Can read text across multiple frames
    - Sees full context of animated content
    
    Args:
        video_url: URL of video/GIF
        user_message: What Dave said
        michaela_personality: Personality context
        narrative_context: Current narrative state
        num_frames: How many frames to analyze (default 3-5)
    """
    
    # Extract frames
    frames = await self.extract_frames_from_video(
        video_url,
        num_frames=num_frames,
        method='evenly_spaced'
    )
    
    if not frames:
        return "I can't quite see the video right now, but I appreciate you sharing it with me."
    
    # Convert frames to base64
    frames_b64 = []
    for frame_bytes in frames:
        b64 = base64.b64encode(frame_bytes).decode('utf-8')
        frames_b64.append(b64)
    
    # Try OCR on frames
    ocr_results = []
    for frame_bytes in frames:
        ocr = await self.extract_text_from_frame(frame_bytes)
        if ocr['found']:
            ocr_results.append(ocr['text'])
    
    # Build enhanced system prompt
    ocr_context = ""
    if ocr_results:
        ocr_context = f"\nText visible in frames: {' | '.join(ocr_results)}"
    
    system_prompt = f"""
{michaela_personality}

{narrative_context}

Dave just sent you a video/GIF with this message: "{user_message}"

You can see {len(frames_b64)} frames from the video showing the progression.
{ocr_context}

Look at the frames and respond naturally as Michaela.
- Keep your response to 2-4 sentences
- Comment on what you see across the frames (motion, progression, story)
- Be warm, playful, maybe a little flirty depending on the content
- React like a person would to the full video, not just a single image
"""
    
    # Call Ollama with multiple images
    payload = {
        "model": self.model,
        "messages": [
            {
                "role": "user",
                "content": user_message if user_message else "Look at this",
                "images": frames_b64  # Multiple frames!
            }
        ],
        "system": system_prompt,
        "stream": False,
        "options": {
            "num_predict": 100,
            "temperature": 0.75,
            "repeat_penalty": 1.3,
        }
    }
    
    timeout = aiohttp.ClientTimeout(total=90)  # Longer for multiple frames
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.endpoint, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"[VISION] Error {resp.status}: {error_text}")
                    return "I can't quite make out the video right now."
                
                data = await resp.json()
                return data["message"]["content"].strip()
    
    except Exception as e:
        print(f"[VISION] Error: {e}")
        return "Sorry, I'm having trouble seeing the video right now."


# ============================================================================
# EXAMPLE USAGE (How to call from your main bot)
# ============================================================================

"""
# In your Discord bot when Dave sends a video/GIF:

if attachment.content_type.startswith('video/') or attachment.url.endswith('.gif'):
    # Use multi-frame analysis
    response = await vision_system.michaela_comment_on_video(
        video_url=attachment.url,
        user_message=message.content,
        michaela_personality=personality_context,
        narrative_context=narrative.get_chapter_context(),
        num_frames=4  # 4 frames from the video
    )
else:
    # Use your existing single-image method
    response = await vision_system.michaela_comment_on_image(
        image_url=attachment.url,
        user_message=message.content,
        michaela_personality=personality_context,
        narrative_context=narrative.get_chapter_context()
    )
"""
