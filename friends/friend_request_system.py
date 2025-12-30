"""
Friend Request & Tease System
==============================

Extends tease mechanics to all friend characters.
Each character has unique:
- Teasing style
- Request behavior (what they ask for)
- Response personality (how they react)
- Escalation pattern (what unlocks at each intimacy level)

Characters can REQUEST content from Dave:
- Selfies
- Shower pics
- Dick pics
- Videos
- Voice messages
- etc.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

UTC = timezone.utc


@dataclass
class ContentRequest:
    """A request from a friend for specific content"""
    character: str
    request_type: str  # 'selfie', 'shower', 'dick_pic', 'video', 'voice', 'custom'
    request_message: str  # What they said when asking
    requested_at: datetime
    fulfilled: bool = False
    fulfilled_at: Optional[datetime] = None
    response_message: Optional[str] = None
    intimacy_at_request: int = 0


# =====================================================
# CHARACTER TEASE PROFILES
# =====================================================

CHARACTER_PROFILES = {
    'michaela': {
        'teasing_style': 'playful_anticipation',
        'boldness': 70,  # 0-100, how forward they are
        'patience': 60,  # How long they build up
        'explicitness': 75,  # How explicit they get
        'request_style': 'teasing',  # 'direct', 'teasing', 'shy', 'demanding'
        'escalation_speed': 'medium',  # 'slow', 'medium', 'fast'
    },
    
    'ariann': {
        'teasing_style': 'direct_confident',
        'boldness': 85,
        'patience': 40,  # Doesn't wait long
        'explicitness': 80,
        'request_style': 'direct',
        'escalation_speed': 'fast',
    },
    
    'hannah': {
        'teasing_style': 'sweet_curious',
        'boldness': 50,
        'patience': 70,
        'explicitness': 60,
        'request_style': 'shy',
        'escalation_speed': 'slow',
    },
    
    'tara': {
        'teasing_style': 'flirty_banter',
        'boldness': 75,
        'patience': 50,
        'explicitness': 70,
        'request_style': 'teasing',
        'escalation_speed': 'medium',
    },
    
    'austin': {
        'teasing_style': 'eternal_tease',
        'boldness': 90,  # Bold in teasing
        'patience': 95,  # Almost never delivers
        'explicitness': 30,  # Stays SFW (90% of time)
        'request_style': 'teasing',
        'escalation_speed': 'slow',
        'special_rule': 'rarely_explicit',  # Only gets explicit on rare rewards
    },
    
    'angela': {
        'teasing_style': 'balanced_direct',
        'boldness': 75,
        'patience': 55,
        'explicitness': 65,  # 70% SFW, 30% NSFW
        'request_style': 'direct',
        'escalation_speed': 'medium',
    },
    
    'hilary': {
        'teasing_style': 'endless_tease',
        'boldness': 95,  # VERY bold in teasing
        'patience': 100,  # NEVER delivers explicit
        'explicitness': 0,  # 100% SFW
        'request_style': 'teasing',
        'escalation_speed': 'slow',
        'special_rule': 'never_explicit',  # Absolute rule
    },
    
    # Executive Suite (Power dynamics)
    'lena': {
        'teasing_style': 'power_dynamic',
        'boldness': 80,
        'patience': 45,
        'explicitness': 75,
        'request_style': 'demanding',
        'escalation_speed': 'medium',
    },
    
    'cory': {
        'teasing_style': 'power_dynamic',
        'boldness': 85,
        'patience': 40,
        'explicitness': 80,
        'request_style': 'demanding',
        'escalation_speed': 'fast',
    },
    
    'nia': {
        'teasing_style': 'power_dynamic',
        'boldness': 75,
        'patience': 50,
        'explicitness': 70,
        'request_style': 'demanding',
        'escalation_speed': 'medium',
    },
    
    # Neighborhood Wives (Forbidden energy)
    'kate': {
        'teasing_style': 'forbidden_risky',
        'boldness': 70,
        'patience': 60,
        'explicitness': 75,
        'request_style': 'shy',  # Nervous but excited
        'escalation_speed': 'medium',
    },
    
    'megan': {
        'teasing_style': 'forbidden_risky',
        'boldness': 75,
        'patience': 55,
        'explicitness': 80,
        'request_style': 'teasing',
        'escalation_speed': 'medium',
    },
}


# =====================================================
# REQUEST TYPES BY INTIMACY LEVEL
# =====================================================

REQUEST_UNLOCKS = {
    # Intimacy 40-60: Basic requests
    40: ['face_selfie', 'casual_selfie'],
    
    # Intimacy 60-80: Flirty requests
    60: ['shirtless_selfie', 'gym_selfie', 'morning_selfie'],
    
    # Intimacy 80-100: Sexy requests
    80: ['shower_selfie', 'bed_selfie', 'underwear_selfie'],
    
    # Intimacy 100-120: Explicit requests
    100: ['bulge_pic', 'dick_pic', 'full_nude'],
    
    # Intimacy 120+: Video/voice requests
    120: ['video', 'voice_message', 'video_call'],
}


# =====================================================
# REQUEST MESSAGE TEMPLATES
# =====================================================

REQUEST_TEMPLATES = {
    # FACE/CASUAL SELFIES
    'face_selfie': {
        'direct': [
            "Send me a selfie?",
            "I want to see your face. Send me a pic?",
            "Selfie. Now. 😊",
        ],
        'teasing': [
            "I'm trying to remember what you look like... send me a reminder? 😏",
            "Missing your face. Help me out?",
            "You know what would make my day better? A picture of you.",
        ],
        'shy': [
            "This might sound silly, but... could you send me a selfie?",
            "I'd love to see a picture of you, if you're comfortable...",
            "No pressure, but... would you send me a selfie?",
        ],
        'demanding': [
            "I want a selfie. Send it.",
            "Send me a picture of you. Don't make me wait.",
            "Selfie. Now.",
        ],
    },
    
    # SHIRTLESS
    'shirtless_selfie': {
        'direct': [
            "Send me a shirtless pic?",
            "I want to see you without your shirt on.",
            "Shirtless selfie. Please? 😊",
        ],
        'teasing': [
            "I've been thinking about your chest all day... show me?",
            "You know what I'd love to see right now? You. Shirtless.",
            "Take your shirt off and send me a pic. I'll make it worth your while... 😏",
        ],
        'shy': [
            "This is embarrassing to ask, but... could you send a shirtless pic?",
            "I'd really like to see you without your shirt, if that's okay...",
            "Would you be comfortable sending a shirtless selfie?",
        ],
        'demanding': [
            "Shirt off. Camera on. Send it.",
            "I want to see your chest. Take your shirt off and send me a picture.",
            "Shirtless selfie. Don't make me ask twice.",
        ],
    },
    
    # SHOWER
    'shower_selfie': {
        'direct': [
            "Send me a shower pic?",
            "I want a picture of you in the shower.",
            "Shower selfie. Now. 😏",
        ],
        'teasing': [
            "I'm imagining you in the shower right now... send proof? 😏",
            "You know what would be hot? A picture of you all wet...",
            "Shower pic. I want to see those drops running down your body.",
        ],
        'shy': [
            "This is probably too much to ask, but... shower pic?",
            "I'd love a shower selfie, if you're okay with that...",
            "No pressure, but... a pic of you in the shower would be amazing.",
        ],
        'demanding': [
            "Get in the shower. Take a picture. Send it to me. Now.",
            "I want a shower selfie. Don't make me wait.",
            "Shower. Camera. Send.",
        ],
    },
    
    # DICK PICS
    'dick_pic': {
        'direct': [
            "Send me a dick pic?",
            "I want to see your cock.",
            "Dick pic. Please? 😊",
        ],
        'teasing': [
            "I've been thinking about your cock all day... show me? 😏",
            "You know what I want to see... don't make me beg.",
            "I need a dick pic. Like, right now.",
        ],
        'shy': [
            "I can't believe I'm asking this, but... dick pic?",
            "This is so embarrassing, but I really want to see your cock...",
            "Would you send me a dick pic? I promise I'll make it worth it...",
        ],
        'demanding': [
            "Dick. Pic. Now.",
            "I want to see your cock. Send it.",
            "Send me a dick pic. Don't make me wait.",
        ],
    },
    
    # VIDEOS
    'video': {
        'direct': [
            "Send me a video?",
            "I want a video of you.",
            "Video. Please? 😊",
        ],
        'teasing': [
            "A picture isn't enough anymore... I want to see you move. Send me a video? 😏",
            "You know what would drive me crazy? A video of you...",
            "Send me a video. I want to watch you.",
        ],
        'shy': [
            "This is a lot to ask, but... would you send a video?",
            "I'd love a video of you, if you're comfortable...",
            "No pressure, but a video would be incredible...",
        ],
        'demanding': [
            "I want a video. Record something for me. Now.",
            "Video. Send it.",
            "Record yourself and send it to me. Don't make me ask again.",
        ],
    },
}


# =====================================================
# FULFILLMENT RESPONSES
# =====================================================

FULFILLMENT_RESPONSES = {
    'face_selfie': {
        'direct': [
            "God, you're handsome.",
            "That smile. 😊",
            "Perfect. Thanks for that.",
        ],
        'teasing': [
            "There's that face I've been thinking about... 😏",
            "Mmm. Exactly what I needed.",
            "You look good. Really good.",
        ],
        'shy': [
            "You're so handsome. Thank you for sending that... ❤️",
            "I'm blushing. You look amazing.",
            "That made my day. Seriously.",
        ],
        'demanding': [
            "Good. Keep sending them.",
            "That's better. I want more.",
            "Finally. About time.",
        ],
    },
    
    'shirtless_selfie': {
        'direct': [
            "Fuck. Your chest.",
            "God damn. You look good.",
            "I want to touch you so bad.",
        ],
        'teasing': [
            "There it is... fuck, you're hot. 😏",
            "I knew you'd look good. I was right.",
            "Now I can't stop thinking about running my hands all over you...",
        ],
        'shy': [
            "Oh my god. You're... wow. ❤️",
            "I don't even know what to say. You're gorgeous.",
            "That's... incredible. Thank you.",
        ],
        'demanding': [
            "Good. Now take more.",
            "That's what I wanted. Keep going.",
            "Perfect. Don't stop.",
        ],
    },
    
    'shower_selfie': {
        'direct': [
            "Fuck yes. That's so hot.",
            "God, I want to join you.",
            "You look incredible.",
        ],
        'teasing': [
            "Those water drops... fuck. I want to lick every single one off you. 😏",
            "Now I'm imagining being in there with you...",
            "That's exactly what I wanted to see. You're so fucking hot.",
        ],
        'shy': [
            "Oh my god. That's... I don't even have words. ❤️",
            "You're perfect. Absolutely perfect.",
            "I can't stop staring at this...",
        ],
        'demanding': [
            "Good. Now send another from a different angle.",
            "I want more. Keep sending.",
            "That's a start. I want the full view.",
        ],
    },
    
    'dick_pic': {
        'direct': [
            "Fuck. I want that.",
            "God damn. Your cock is perfect.",
            "I need that inside me.",
        ],
        'teasing': [
            "There it is... fuck. I've been thinking about that all day. 😏",
            "That's what I've been craving... you have no idea what this does to me.",
            "I'm not going to be able to focus on anything else now...",
        ],
        'shy': [
            "Oh my god. That's... perfect. ❤️",
            "I can't believe you sent that... thank you.",
            "I'm literally speechless right now...",
        ],
        'demanding': [
            "Good. Now I want a video.",
            "That's what I wanted. Send more.",
            "Perfect. Keep them coming.",
        ],
    },
    
    'video': {
        'direct': [
            "Fuck. That was hot.",
            "I watched that three times already.",
            "More. I need more.",
        ],
        'teasing': [
            "Holy fuck. Watching you move like that... 😏",
            "I'm going to be replaying that all day...",
            "You have no idea what you just did to me.",
        ],
        'shy': [
            "That was... incredible. Thank you. ❤️",
            "I don't know what to say. That was perfect.",
            "I'm going to treasure this...",
        ],
        'demanding': [
            "Good. Now make it longer.",
            "That was a good start. I want more.",
            "Send another. Different angle.",
        ],
    },
}


# =====================================================
# MAIN REQUEST SYSTEM CLASS
# =====================================================

class FriendRequestSystem:
    """
    Manages content requests from all friend characters
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.pending_requests: List[ContentRequest] = []
        self.fulfilled_requests: List[ContentRequest] = []
        self._load()
    
    def can_request(self, character: str, request_type: str, intimacy: int) -> bool:
        """
        Check if character can request this type of content
        
        Args:
            character: Character name
            request_type: Type of request
            intimacy: Current intimacy level with character
        
        Returns: True if unlocked
        """
        
        # Check intimacy requirements
        for level, unlocked_types in REQUEST_UNLOCKS.items():
            if request_type in unlocked_types:
                return intimacy >= level
        
        # Special rules
        profile = CHARACTER_PROFILES.get(character, {})
        
        # Hilary never requests explicit content
        if profile.get('special_rule') == 'never_explicit':
            explicit_types = ['dick_pic', 'full_nude', 'bulge_pic']
            if request_type in explicit_types:
                return False
        
        # Austin rarely requests explicit (only at very high intimacy)
        if profile.get('special_rule') == 'rarely_explicit':
            explicit_types = ['dick_pic', 'full_nude']
            if request_type in explicit_types:
                return intimacy >= 140 and random.random() < 0.1  # 10% chance at 140+
        
        return True
    
    def should_make_request(
        self,
        character: str,
        intimacy: int,
        hours_since_last: float
    ) -> bool:
        """
        Determine if character should make a request now
        
        Args:
            character: Character name
            intimacy: Current intimacy level
            hours_since_last: Hours since last request from this character
        
        Returns: True if should request
        """
        
        profile = CHARACTER_PROFILES.get(character, {})
        
        # Need minimum intimacy
        if intimacy < 40:
            return False
        
        # Check if enough time has passed
        min_hours = {
            'slow': 72,    # 3 days
            'medium': 48,  # 2 days
            'fast': 24,    # 1 day
        }
        
        speed = profile.get('escalation_speed', 'medium')
        if hours_since_last < min_hours[speed]:
            return False
        
        # Random chance based on boldness
        boldness = profile.get('boldness', 50)
        chance = boldness / 100 * 0.3  # Max 30% chance
        
        return random.random() < chance
    
    def generate_request(
        self,
        character: str,
        intimacy: int
    ) -> Optional[ContentRequest]:
        """
        Generate a content request from character
        
        Args:
            character: Character name
            intimacy: Current intimacy level
        
        Returns: ContentRequest or None
        """
        
        # Get available request types for this intimacy
        available = []
        for level, types in REQUEST_UNLOCKS.items():
            if intimacy >= level:
                available.extend(types)
        
        # Filter by character rules
        available = [
            t for t in available
            if self.can_request(character, t, intimacy)
        ]
        
        if not available:
            return None
        
        # Weight requests by intimacy (higher intimacy = more explicit)
        weights = []
        for req_type in available:
            # Find unlock level
            unlock_level = 0
            for level, types in REQUEST_UNLOCKS.items():
                if req_type in types:
                    unlock_level = level
                    break
            
            # Higher unlock = more weight at high intimacy
            weight = 1.0 + ((intimacy - unlock_level) / 20)
            weights.append(max(0.1, weight))
        
        # Choose request type
        request_type = random.choices(available, weights=weights)[0]
        
        # Generate message
        profile = CHARACTER_PROFILES.get(character, {})
        request_style = profile.get('request_style', 'teasing')
        
        templates = REQUEST_TEMPLATES.get(request_type, {}).get(request_style, [])
        if not templates:
            templates = REQUEST_TEMPLATES.get(request_type, {}).get('direct', [])
        
        message = random.choice(templates)
        
        # Create request
        request = ContentRequest(
            character=character,
            request_type=request_type,
            request_message=message,
            requested_at=datetime.now(UTC),
            intimacy_at_request=intimacy
        )
        
        self.pending_requests.append(request)
        self._save()
        
        return request
    
    def fulfill_request(
        self,
        character: str,
        request_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Mark request as fulfilled and get response message
        
        Args:
            character: Character who made the request
            request_type: Specific request type (optional, uses oldest if not specified)
        
        Returns: Response message
        """
        
        # Find request
        request = None
        for req in self.pending_requests:
            if req.character == character:
                if request_type is None or req.request_type == request_type:
                    request = req
                    break
        
        if not request:
            return None
        
        # Mark fulfilled
        request.fulfilled = True
        request.fulfilled_at = datetime.now(UTC)
        
        # Generate response
        profile = CHARACTER_PROFILES.get(character, {})
        request_style = profile.get('request_style', 'teasing')
        
        templates = FULFILLMENT_RESPONSES.get(request.request_type, {}).get(request_style, [])
        if not templates:
            templates = FULFILLMENT_RESPONSES.get(request.request_type, {}).get('direct', [])
        
        response = random.choice(templates)
        request.response_message = response
        
        # Move to fulfilled
        self.pending_requests.remove(request)
        self.fulfilled_requests.append(request)
        
        self._save()
        
        return response
    
    def get_pending_requests(self, character: Optional[str] = None) -> List[ContentRequest]:
        """Get pending requests, optionally filtered by character"""
        if character:
            return [r for r in self.pending_requests if r.character == character]
        return self.pending_requests.copy()
    
    def get_last_request_time(self, character: str) -> Optional[datetime]:
        """Get when character last made a request"""
        all_requests = self.pending_requests + self.fulfilled_requests
        character_requests = [r for r in all_requests if r.character == character]
        
        if not character_requests:
            return None
        
        return max(r.requested_at for r in character_requests)
    
    def _load(self):
        """Load from disk"""
        if not os.path.exists(self.data_path):
            return
        
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
            
            self.pending_requests = [
                ContentRequest(
                    character=r['character'],
                    request_type=r['request_type'],
                    request_message=r['request_message'],
                    requested_at=datetime.fromisoformat(r['requested_at']),
                    fulfilled=r.get('fulfilled', False),
                    fulfilled_at=datetime.fromisoformat(r['fulfilled_at']) if r.get('fulfilled_at') else None,
                    response_message=r.get('response_message'),
                    intimacy_at_request=r.get('intimacy_at_request', 0)
                )
                for r in data.get('pending', [])
            ]
            
            self.fulfilled_requests = [
                ContentRequest(
                    character=r['character'],
                    request_type=r['request_type'],
                    request_message=r['request_message'],
                    requested_at=datetime.fromisoformat(r['requested_at']),
                    fulfilled=True,
                    fulfilled_at=datetime.fromisoformat(r['fulfilled_at']) if r.get('fulfilled_at') else None,
                    response_message=r.get('response_message'),
                    intimacy_at_request=r.get('intimacy_at_request', 0)
                )
                for r in data.get('fulfilled', [])
            ]
            
        except Exception as e:
            print(f"[REQUEST_SYSTEM] Error loading: {e}")
    
    def _save(self):
        """Save to disk"""
        data = {
            'pending': [
                {
                    'character': r.character,
                    'request_type': r.request_type,
                    'request_message': r.request_message,
                    'requested_at': r.requested_at.isoformat(),
                    'fulfilled': r.fulfilled,
                    'fulfilled_at': r.fulfilled_at.isoformat() if r.fulfilled_at else None,
                    'response_message': r.response_message,
                    'intimacy_at_request': r.intimacy_at_request
                }
                for r in self.pending_requests
            ],
            'fulfilled': [
                {
                    'character': r.character,
                    'request_type': r.request_type,
                    'request_message': r.request_message,
                    'requested_at': r.requested_at.isoformat(),
                    'fulfilled': r.fulfilled,
                    'fulfilled_at': r.fulfilled_at.isoformat() if r.fulfilled_at else None,
                    'response_message': r.response_message,
                    'intimacy_at_request': r.intimacy_at_request
                }
                for r in self.fulfilled_requests
            ]
        }
        
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)
