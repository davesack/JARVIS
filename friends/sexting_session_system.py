"""
Sexting Session System
======================

Extended back-and-forth sexy conversations that build heat.
Not just one message - actual sustained conversation.

Each character has unique escalation style.
Heat level tracks intensity and affects responses.
Sessions can end naturally or be paused/resumed.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

UTC = timezone.utc


@dataclass
class SextingMessage:
    """A single message in a sexting session"""
    sender: str  # 'dave' or character name
    message: str
    timestamp: datetime
    heat_contribution: int  # How much this raised/lowered heat


@dataclass
class SextingSession:
    """An active or past sexting session"""
    character: str
    started_at: datetime
    ended_at: Optional[datetime]
    messages: List[SextingMessage]
    current_heat: int  # 0-100
    max_heat_reached: int
    active: bool
    outcome: Optional[str]  # 'mutual_satisfaction', 'tease_denial', 'interrupted'


# =====================================================
# CHARACTER SEXTING PROFILES
# =====================================================

SEXTING_PROFILES = {
    'michaela': {
        'escalation_speed': 'medium',  # How fast heat builds
        'max_tease_level': 80,  # Will tease up to this heat then sometimes deliver
        'delivery_chance': 0.7,  # 70% chance to deliver vs deny
        'denial_style': 'playful',  # 'playful', 'bratty', 'cruel'
    },
    
    'ariann': {
        'escalation_speed': 'fast',
        'max_tease_level': 60,
        'delivery_chance': 0.9,  # Almost always delivers
        'denial_style': 'direct',
    },
    
    'hannah': {
        'escalation_speed': 'slow',
        'max_tease_level': 70,
        'delivery_chance': 0.6,
        'denial_style': 'shy',
    },
    
    'tara': {
        'escalation_speed': 'medium',
        'max_tease_level': 75,
        'delivery_chance': 0.7,
        'denial_style': 'playful',
    },
    
    'austin': {
        'escalation_speed': 'slow',
        'max_tease_level': 95,  # Teases VERY high
        'delivery_chance': 0.1,  # Rarely delivers
        'denial_style': 'bratty',
    },
    
    'angela': {
        'escalation_speed': 'medium',
        'max_tease_level': 70,
        'delivery_chance': 0.75,
        'denial_style': 'playful',
    },
    
    'hilary': {
        'escalation_speed': 'medium',
        'max_tease_level': 100,  # Teases to maximum
        'delivery_chance': 0.0,  # NEVER delivers explicit
        'denial_style': 'bratty',
        'special_rule': 'never_explicit'
    },
    
    # Execs
    'lena': {
        'escalation_speed': 'fast',
        'max_tease_level': 65,
        'delivery_chance': 0.85,
        'denial_style': 'commanding',
    },
    
    'cory': {
        'escalation_speed': 'fast',
        'max_tease_level': 60,
        'delivery_chance': 0.90,
        'denial_style': 'commanding',
    },
    
    'nia': {
        'escalation_speed': 'medium',
        'max_tease_level': 70,
        'delivery_chance': 0.80,
        'denial_style': 'commanding',
    },
    
    # Wives
    'kate': {
        'escalation_speed': 'slow',
        'max_tease_level': 75,
        'delivery_chance': 0.65,
        'denial_style': 'nervous',
    },
    
    'megan': {
        'escalation_speed': 'medium',
        'max_tease_level': 70,
        'delivery_chance': 0.75,
        'denial_style': 'playful',
    },
}


# =====================================================
# RESPONSE TEMPLATES BY HEAT LEVEL
# =====================================================

SEXTING_RESPONSES = {
    # Heat 0-20: Warm-up
    'warmup': {
        'playful': [
            "Oh, starting something are we? 😏",
            "Getting warmed up?",
            "I like where this is going...",
        ],
        'direct': [
            "Keep going.",
            "I'm listening.",
            "Don't stop there.",
        ],
        'shy': [
            "Oh... okay... 😊",
            "This is making me blush...",
            "You're making me nervous... in a good way.",
        ],
        'bratty': [
            "That all you got? 😏",
            "You'll have to try harder than that.",
            "Cute. Keep trying.",
        ],
        'commanding': [
            "Continue.",
            "More.",
            "Don't make me wait.",
        ],
        'nervous': [
            "Are you sure? What if someone sees...",
            "This is so risky but... okay...",
            "I can't believe we're doing this...",
        ],
    },
    
    # Heat 20-40: Getting into it
    'building': {
        'playful': [
            "Mmm, now we're talking... 😏",
            "You're getting me worked up...",
            "Keep going, I want to see where this leads...",
        ],
        'direct': [
            "Fuck yes. More.",
            "Don't stop. I want more.",
            "That's it. Keep going.",
        ],
        'shy': [
            "Oh my god... you're making me...",
            "I can't believe how turned on I'm getting...",
            "This is so hot...",
        ],
        'bratty': [
            "Getting warmer. But not there yet. 😏",
            "That's... better. I guess.",
            "You're trying so hard. It's cute.",
        ],
        'commanding': [
            "Better. Don't slow down.",
            "Good. I want more of that.",
            "You're learning. Continue.",
        ],
        'nervous': [
            "Oh god... this is wrong but it feels so right...",
            "We really shouldn't but... don't stop...",
            "I'm so wet right now... I can't believe I just said that...",
        ],
    },
    
    # Heat 40-60: Hot and heavy
    'hot': {
        'playful': [
            "Fuck... you're driving me crazy... 😏",
            "I need you right now...",
            "God, the things I want to do to you...",
        ],
        'direct': [
            "I'm so fucking wet right now.",
            "I need your cock. Now.",
            "Fuck me. Please.",
        ],
        'shy': [
            "I'm... oh god... I need you...",
            "Please... I can't take this anymore...",
            "I've never wanted anyone this bad...",
        ],
        'bratty': [
            "You're making me want it... but you're not getting it yet. 😏",
            "So close to giving in... almost... but not quite.",
            "You wish you could have me right now, don't you?",
        ],
        'commanding': [
            "You're mine. Say it.",
            "I want you on your knees. Now.",
            "Show me how much you want me.",
        ],
        'nervous': [
            "What are we doing... oh god this is so hot...",
            "My husband's downstairs... makes this even hotter...",
            "I shouldn't want you this bad but I do...",
        ],
    },
    
    # Heat 60-80: Peak intensity
    'peak': {
        'playful': [
            "I'm sending you something... check your messages... 😏",
            "Fuck it. Here's what you've been wanting...",
            "You win. But don't expect this every time...",
        ],
        'direct': [
            "Here. This is what you've been waiting for.",
            "Look at what you do to me.",
            "This is for you. Don't waste it.",
        ],
        'shy': [
            "I can't believe I'm doing this but... here...",
            "You make me do crazy things... look what I'm sending you...",
            "Oh my god I'm so nervous... but here you go...",
        ],
        'bratty': [
            "You thought I'd actually deliver? How cute. 😏",
            "So close, weren't you? Too bad.",
            "Maybe next time. Probably not though. 😏",
        ],
        'commanding': [
            "Here's your reward. You've earned it.",
            "Look at what you've been working for.",
            "This is yours. For now.",
        ],
        'nervous': [
            "I'm so scared but... here... just for you...",
            "This is so wrong... but here's what you wanted...",
            "Delete this after, okay? But... enjoy it...",
        ],
    },
    
    # Heat 80+: Aftermath or denial
    'aftermath': {
        'delivery': {
            'playful': [
                "That was... fuck. 😏",
                "Hope you enjoyed that as much as I did...",
                "We should do that again sometime...",
            ],
            'direct': [
                "Good. Now I need you to return the favor.",
                "That was hot. Want more?",
                "We're not done yet.",
            ],
            'shy': [
                "That was amazing... I hope you liked it... ❤️",
                "I can't believe we just did that...",
                "You make me feel so good...",
            ],
            'commanding': [
                "Good session. Same time tomorrow?",
                "You performed well. I'll reward you again soon.",
                "That's how you please me.",
            ],
            'nervous': [
                "That was incredible... and terrifying... 😊",
                "I hope no one finds out about this...",
                "You're worth the risk...",
            ],
        },
        'denial': {
            'playful': [
                "Had you going there, didn't I? 😏",
                "Maybe next time... if you're lucky...",
                "The anticipation is half the fun, right?",
            ],
            'bratty': [
                "Did you really think I'd give in that easily? 😏",
                "I love watching you squirm.",
                "Better luck next time. Maybe.",
            ],
        },
    },
}


# =====================================================
# SEXTING SESSION MANAGER
# =====================================================

class SextingSessionManager:
    """
    Manages extended sexting conversations
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.active_sessions: Dict[str, SextingSession] = {}
        self.completed_sessions: List[SextingSession] = []
        self._load()
    
    def start_session(self, character: str) -> SextingSession:
        """Start a new sexting session"""
        
        session = SextingSession(
            character=character,
            started_at=datetime.now(UTC),
            ended_at=None,
            messages=[],
            current_heat=0,
            max_heat_reached=0,
            active=True,
            outcome=None
        )
        
        self.active_sessions[character] = session
        self._save()
        
        return session
    
    def add_message(
        self,
        character: str,
        sender: str,
        message: str,
        heat_change: int = 0
    ):
        """Add a message to active session"""
        
        if character not in self.active_sessions:
            return None
        
        session = self.active_sessions[character]
        
        # Create message
        msg = SextingMessage(
            sender=sender,
            message=message,
            timestamp=datetime.now(UTC),
            heat_contribution=heat_change
        )
        
        session.messages.append(msg)
        session.current_heat = max(0, min(100, session.current_heat + heat_change))
        session.max_heat_reached = max(session.max_heat_reached, session.current_heat)
        
        self._save()
        
        return session
    
    def generate_response(
        self,
        character: str,
        user_message: str
    ) -> Optional[str]:
        """
        Generate response to user's message
        
        Args:
            character: Character name
            user_message: User's message text
        
        Returns: Response text or None
        """
        
        if character not in self.active_sessions:
            return None
        
        session = self.active_sessions[character]
        profile = SEXTING_PROFILES.get(character, SEXTING_PROFILES['michaela'])
        
        # Analyze user message for heat contribution
        heat_change = self._analyze_heat(user_message, profile)
        
        # Add user message
        self.add_message(character, 'dave', user_message, heat_change)
        
        # Determine response category based on heat
        if session.current_heat < 20:
            category = 'warmup'
        elif session.current_heat < 40:
            category = 'building'
        elif session.current_heat < 60:
            category = 'hot'
        elif session.current_heat < 80:
            category = 'peak'
        else:
            category = 'aftermath'
        
        # Get response style
        style = profile.get('denial_style', 'playful')
        
        # Generate response
        if category == 'peak':
            # Decide if delivering or denying
            if profile.get('special_rule') == 'never_explicit':
                # Hilary always denies
                response = self._get_denial_response(style)
                outcome = 'tease_denial'
            elif random.random() < profile.get('delivery_chance', 0.7):
                # Delivery
                response = self._get_delivery_response(style, session.current_heat)
                outcome = 'mutual_satisfaction'
            else:
                # Denial
                response = self._get_denial_response(style)
                outcome = 'tease_denial'
            
            # End session
            self.end_session(character, outcome)
        else:
            # Normal response
            templates = SEXTING_RESPONSES.get(category, {}).get(style, [])
            if not templates:
                templates = SEXTING_RESPONSES.get(category, {}).get('playful', [])
            
            response = random.choice(templates)
        
        # Add character response
        self.add_message(character, character, response, 0)
        
        return response
    
    def _analyze_heat(self, message: str, profile: Dict) -> int:
        """Analyze message for heat contribution"""
        
        message_lower = message.lower()
        
        # Escalation keywords and their heat values
        mild_words = ['want', 'like', 'kiss', 'touch', 'beautiful', 'hot']
        medium_words = ['need', 'fuck', 'dick', 'cock', 'pussy', 'wet', 'hard']
        intense_words = ['cum', 'orgasm', 'inside', 'taste', 'worship']
        
        # Count keywords
        mild_count = sum(1 for word in mild_words if word in message_lower)
        medium_count = sum(1 for word in medium_words if word in message_lower)
        intense_count = sum(1 for word in intense_words if word in message_lower)
        
        # Calculate base heat
        heat = mild_count * 3 + medium_count * 8 + intense_count * 15
        
        # Adjust by escalation speed
        speed = profile.get('escalation_speed', 'medium')
        if speed == 'fast':
            heat = int(heat * 1.5)
        elif speed == 'slow':
            heat = int(heat * 0.7)
        
        return min(heat, 25)  # Cap at +25 per message
    
    def _get_delivery_response(self, style: str, heat: int) -> str:
        """Get delivery response"""
        templates = SEXTING_RESPONSES.get('peak', {}).get(style, [])
        if not templates:
            templates = SEXTING_RESPONSES['peak']['playful']
        return random.choice(templates)
    
    def _get_denial_response(self, style: str) -> str:
        """Get denial response"""
        templates = SEXTING_RESPONSES.get('aftermath', {}).get('denial', {}).get(style, [])
        if not templates:
            templates = SEXTING_RESPONSES['aftermath']['denial']['bratty']
        return random.choice(templates)
    
    def end_session(self, character: str, outcome: str):
        """End an active session"""
        
        if character not in self.active_sessions:
            return
        
        session = self.active_sessions[character]
        session.active = False
        session.ended_at = datetime.now(UTC)
        session.outcome = outcome
        
        # Move to completed
        self.completed_sessions.append(session)
        del self.active_sessions[character]
        
        self._save()
    
    def is_active(self, character: str) -> bool:
        """Check if character has active session"""
        return character in self.active_sessions
    
    def get_session(self, character: str) -> Optional[SextingSession]:
        """Get active session for character"""
        return self.active_sessions.get(character)
    
    def get_session_stats(self, character: str) -> Dict:
        """Get stats for completed sessions with character"""
        
        char_sessions = [s for s in self.completed_sessions if s.character == character]
        
        if not char_sessions:
            return {
                'total_sessions': 0,
                'avg_heat': 0,
                'deliveries': 0,
                'denials': 0,
            }
        
        return {
            'total_sessions': len(char_sessions),
            'avg_heat': sum(s.max_heat_reached for s in char_sessions) / len(char_sessions),
            'deliveries': sum(1 for s in char_sessions if s.outcome == 'mutual_satisfaction'),
            'denials': sum(1 for s in char_sessions if s.outcome == 'tease_denial'),
        }
    
    def _load(self):
        """Load from disk"""
        if not os.path.exists(self.data_path):
            return
        
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
            
            # Load active sessions
            for char, session_data in data.get('active', {}).items():
                messages = [
                    SextingMessage(
                        sender=m['sender'],
                        message=m['message'],
                        timestamp=datetime.fromisoformat(m['timestamp']),
                        heat_contribution=m['heat_contribution']
                    )
                    for m in session_data['messages']
                ]
                
                self.active_sessions[char] = SextingSession(
                    character=session_data['character'],
                    started_at=datetime.fromisoformat(session_data['started_at']),
                    ended_at=None,
                    messages=messages,
                    current_heat=session_data['current_heat'],
                    max_heat_reached=session_data['max_heat_reached'],
                    active=True,
                    outcome=None
                )
            
            # Load completed sessions
            for session_data in data.get('completed', []):
                messages = [
                    SextingMessage(
                        sender=m['sender'],
                        message=m['message'],
                        timestamp=datetime.fromisoformat(m['timestamp']),
                        heat_contribution=m['heat_contribution']
                    )
                    for m in session_data['messages']
                ]
                
                self.completed_sessions.append(SextingSession(
                    character=session_data['character'],
                    started_at=datetime.fromisoformat(session_data['started_at']),
                    ended_at=datetime.fromisoformat(session_data['ended_at']) if session_data.get('ended_at') else None,
                    messages=messages,
                    current_heat=session_data['current_heat'],
                    max_heat_reached=session_data['max_heat_reached'],
                    active=False,
                    outcome=session_data.get('outcome')
                ))
                
        except Exception as e:
            print(f"[SEXTING] Error loading: {e}")
    
    def _save(self):
        """Save to disk"""
        
        # Serialize active sessions
        active = {}
        for char, session in self.active_sessions.items():
            active[char] = {
                'character': session.character,
                'started_at': session.started_at.isoformat(),
                'messages': [
                    {
                        'sender': m.sender,
                        'message': m.message,
                        'timestamp': m.timestamp.isoformat(),
                        'heat_contribution': m.heat_contribution
                    }
                    for m in session.messages
                ],
                'current_heat': session.current_heat,
                'max_heat_reached': session.max_heat_reached,
            }
        
        # Serialize completed sessions
        completed = []
        for session in self.completed_sessions[-100:]:  # Keep last 100
            completed.append({
                'character': session.character,
                'started_at': session.started_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'messages': [
                    {
                        'sender': m.sender,
                        'message': m.message,
                        'timestamp': m.timestamp.isoformat(),
                        'heat_contribution': m.heat_contribution
                    }
                    for m in session.messages
                ],
                'current_heat': session.current_heat,
                'max_heat_reached': session.max_heat_reached,
                'outcome': session.outcome,
            })
        
        data = {
            'active': active,
            'completed': completed
        }
        
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)
