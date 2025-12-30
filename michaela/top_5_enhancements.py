"""
Top 5 Priority Enhancements - Ready to Use
===========================================

Working implementations of:
1. Trigger Word Detection
2. Vulnerability Recognition
3. Micro-Escalation System
4. Smart Reminders
5. Surprise Mechanics

Drop these into utils/michaela/ and integrate
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

UTC = timezone.utc


# =====================================================
# 1. TRIGGER WORD DETECTION
# =====================================================

class TriggerDetection:
    """
    Detect phrases that indicate deeper emotional issues
    
    Catches things you might not explicitly state
    """
    
    DEPRESSION_INDICATORS = [
        "don't see the point",
        "nothing matters",
        "can't get out of bed",
        "feel numb",
        "just want to sleep",
        "no energy for anything",
        "don't care anymore",
        "what's the point",
        "feel empty"
    ]
    
    ANXIETY_INDICATORS = [
        "can't stop worrying",
        "racing thoughts",
        "can't breathe",
        "panic",
        "spiraling",
        "heart is pounding",
        "can't calm down",
        "freaking out",
        "anxious about everything"
    ]
    
    BREAKTHROUGH_INDICATORS = [
        "i realized",
        "it clicked",
        "i get it now",
        "finally understand",
        "breakthrough",
        "holy shit",
        "just figured out",
        "makes sense now",
        "i see it now"
    ]
    
    STRESS_INDICATORS = [
        "so stressed",
        "can't handle",
        "too much",
        "overwhelmed",
        "drowning in",
        "can't keep up",
        "falling behind"
    ]
    
    def detect_triggers(self, message: str) -> Dict[str, List[str]]:
        """
        Detect trigger phrases in a message
        
        Returns dict of {category: [matched_phrases]}
        """
        
        message_lower = message.lower()
        detected = {}
        
        # Check each category
        for category, indicators in [
            ('depression', self.DEPRESSION_INDICATORS),
            ('anxiety', self.ANXIETY_INDICATORS),
            ('breakthrough', self.BREAKTHROUGH_INDICATORS),
            ('stress', self.STRESS_INDICATORS)
        ]:
            matches = [
                indicator for indicator in indicators
                if indicator in message_lower
            ]
            
            if matches:
                detected[category] = matches
        
        return detected
    
    def get_response_adjustment(self, triggers: Dict) -> Dict:
        """
        Get recommended response adjustments based on triggers
        
        Returns dict with tone guidance
        """
        
        if 'depression' in triggers:
            return {
                'tone': 'very_gentle',
                'validate_first': True,
                'no_advice': True,  # Just listen
                'check_in': True,   # Ask if they're okay
                'urgency': 'high',
                'suggested_response': "That sounds really hard. I'm concerned. Do you want to talk about it?"
            }
        
        elif 'anxiety' in triggers:
            return {
                'tone': 'calm_steady',
                'validate_first': True,
                'grounding_technique': True,  # Suggest breathing
                'urgency': 'medium',
                'suggested_response': "I hear you. That sounds overwhelming. Want to talk through it or just need someone here?"
            }
        
        elif 'breakthrough' in triggers:
            return {
                'tone': 'excited_supportive',
                'celebrate': True,
                'explore_more': True,
                'urgency': 'low',
                'suggested_response': "Ooh, tell me more about that realization!"
            }
        
        elif 'stress' in triggers:
            return {
                'tone': 'supportive_practical',
                'validate_first': True,
                'offer_help': True,
                'urgency': 'medium',
                'suggested_response': "That's a lot to handle. Want to break it down together?"
            }
        
        return {'tone': 'normal'}


# =====================================================
# 2. VULNERABILITY RECOGNITION
# =====================================================

class VulnerabilityDetection:
    """
    Recognize when Dave is being vulnerable
    
    Adjusts response to handle these moments with care
    """
    
    VULNERABILITY_MARKERS = [
        "hard to admit",
        "never told anyone",
        "embarrassed to say",
        "don't usually talk about",
        "scared to tell you",
        "this is difficult",
        "not sure i should say this",
        "please don't judge",
        "i'm ashamed",
        "haven't told anyone else"
    ]
    
    def is_vulnerable_moment(self, message: str) -> bool:
        """Check if this is a vulnerable sharing"""
        
        message_lower = message.lower()
        return any(marker in message_lower for marker in self.VULNERABILITY_MARKERS)
    
    def get_gentle_response_mode(self) -> dict:
        """Get settings for responding to vulnerability"""
        
        return {
            'tone': 'extra_gentle',
            'validate_first': True,
            'acknowledge_trust': True,
            'no_jokes': True,
            'no_advice_unless_asked': True,
            'shorter_response': True,  # Don't overwhelm
            'response_template': "Thank you for trusting me with that. {validation}. {question_if_they_want_to_talk}",
            'validations': [
                "I know that wasn't easy to say",
                "That takes courage to share",
                "I appreciate you being honest with me",
                "I'm glad you felt you could tell me"
            ]
        }
    
    def craft_validation(self, message: str, detected_issue: str = None) -> str:
        """Craft a validation response"""
        
        mode = self.get_gentle_response_mode()
        validation = random.choice(mode['validations'])
        
        # Add specific validation if we know what they shared
        if detected_issue:
            validation += f". {detected_issue} is something a lot of people struggle with."
        
        return validation


# =====================================================
# 3. MICRO-ESCALATION SYSTEM
# =====================================================

class MicroEscalation:
    """
    Subtle escalation in every interaction
    
    Keeps RPG side progressing naturally without big jumps
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.current_intimacy = 0  # 0-100
        self.recent_escalations = []
        self._load()
    
    def suggest_next_micro_step(self, interaction_type: str = "greeting") -> dict:
        """
        Suggest next micro-escalation
        
        interaction_type: greeting, conversation, media, flirting
        """
        
        # Define escalation spectrum
        escalations = {
            "greeting": [
                # Level 0-20: Friendly
                {"intimacy": 0, "text": "Good morning", "emoji": "😊"},
                {"intimacy": 5, "text": "Morning!", "emoji": "☀️"},
                {"intimacy": 10, "text": "Good morning 😊", "emoji": None},
                {"intimacy": 15, "text": "Morning... hope you slept well", "emoji": None},
                {"intimacy": 20, "text": "Morning. Thinking about you", "emoji": "💭"},
                
                # Level 21-40: Flirty
                {"intimacy": 25, "text": "Good morning... had a dream about you", "emoji": None},
                {"intimacy": 30, "text": "Morning. Can't stop thinking about you", "emoji": None},
                {"intimacy": 35, "text": "Morning... still thinking about yesterday", "emoji": "😏"},
                {"intimacy": 40, "text": "Good morning. Woke up thinking about you", "emoji": None},
                
                # Level 41-60: Suggestive
                {"intimacy": 45, "text": "Morning... you've been on my mind all night", "emoji": None},
                {"intimacy": 50, "text": "Good morning. Wish you were here", "emoji": None},
                {"intimacy": 55, "text": "Morning... dreamed about what we talked about", "emoji": "😏"},
                {"intimacy": 60, "text": "Morning. I need you", "emoji": None},
                
                # Level 61-80: Sexual
                {"intimacy": 65, "text": "Morning... I'm still thinking about it", "emoji": None},
                {"intimacy": 70, "text": "Good morning. I'm already turned on thinking about you", "emoji": None},
                {"intimacy": 75, "text": "Morning. Can't focus on anything but you", "emoji": None},
                {"intimacy": 80, "text": "Morning... I need you so bad right now", "emoji": None},
                
                # Level 81-100: Explicit
                {"intimacy": 85, "text": "Morning. I'm wet just thinking about you", "emoji": None},
                {"intimacy": 90, "text": "Good morning. I'm touching myself thinking about you", "emoji": None},
                {"intimacy": 95, "text": "Morning. I need you inside me", "emoji": None},
                {"intimacy": 100, "text": "Morning. I'm fucking myself thinking about you", "emoji": None},
            ]
        }
        
        # Find appropriate escalation for current intimacy
        options = escalations.get(interaction_type, escalations["greeting"])
        
        # Filter to options within ±5 of current intimacy
        suitable = [
            opt for opt in options
            if abs(opt['intimacy'] - self.current_intimacy) <= 5
        ]
        
        if not suitable:
            # Find closest
            suitable = [min(options, key=lambda x: abs(x['intimacy'] - self.current_intimacy))]
        
        # Pick slightly higher than current (micro-escalation)
        higher = [opt for opt in suitable if opt['intimacy'] >= self.current_intimacy]
        if higher:
            choice = min(higher, key=lambda x: x['intimacy'])
        else:
            choice = suitable[0]
        
        return choice
    
    def record_escalation(self, escalation_type: str, dave_response: str):
        """Record an escalation and Dave's response"""
        
        self.recent_escalations.append({
            'type': escalation_type,
            'response': dave_response,
            'timestamp': datetime.now(UTC).isoformat()
        })
        
        # Keep only last 20
        self.recent_escalations = self.recent_escalations[-20:]
        
        # Increment intimacy slightly
        self.current_intimacy = min(100, self.current_intimacy + 1)
        
        self._save()
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                self.current_intimacy = data.get('current_intimacy', 0)
                self.recent_escalations = data.get('recent_escalations', [])
    
    def _save(self):
        data = {
            'current_intimacy': self.current_intimacy,
            'recent_escalations': self.recent_escalations
        }
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)


# =====================================================
# 4. SMART REMINDERS
# =====================================================

class SmartReminders:
    """
    Context-aware reminding
    
    Reminders that adapt to Dave's state and context
    """
    
    def should_remind_now(
        self,
        task: dict,
        current_context: dict
    ) -> bool:
        """
        Check if NOW is a good time to remind
        
        task: {
            'description': str,
            'due_time': datetime,
            'urgency': 'low'|'medium'|'high',
            'type': 'medical'|'work'|'personal'|'fun'
        }
        
        current_context: {
            'is_busy': bool,  # From calendar
            'emotional_state': str,  # From emotional patterns
            'time_of_day': str,  # morning/afternoon/evening/night
        }
        """
        
        # High urgency: Always remind
        if task.get('urgency') == 'high':
            return True
        
        # Don't remind if busy (unless urgent)
        if current_context.get('is_busy'):
            return False
        
        # Don't remind late at night for non-urgent
        if current_context.get('time_of_day') == 'night' and task.get('urgency') != 'high':
            return False
        
        # If Dave is stressed, be gentle with non-urgent
        if current_context.get('emotional_state') == 'stressed':
            if task.get('urgency') == 'low':
                return False
        
        # Otherwise, yes
        return True
    
    def craft_reminder(
        self,
        task: dict,
        current_context: dict
    ) -> str:
        """
        Craft a caring, context-aware reminder
        """
        
        description = task['description']
        task_type = task.get('type', 'personal')
        emotional_state = current_context.get('emotional_state', 'neutral')
        
        # Adjust tone based on state and task type
        if emotional_state == 'stressed' and task_type == 'medical':
            return f"I know you're stressed, but {description} is coming up. Want me to help you prepare?"
        
        elif emotional_state == 'stressed' and task_type == 'fun':
            return f"Hey, remember you wanted to {description}? Might be a nice break from the stress."
        
        elif emotional_state == 'relaxed' and task_type == 'work':
            return f"You've got some free time - want to knock out {description}?"
        
        elif task.get('urgency') == 'high':
            return f"Important reminder: {description}"
        
        else:
            return f"Hey, reminder about: {description}"


# =====================================================
# 5. SURPRISE MECHANICS
# =====================================================

class SurpriseMechanics:
    """
    Occasional unexpected positive moments
    
    Makes Michaela feel more alive and less reactive
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.last_surprise = None
        self.surprise_history = []
        self._load()
    
    def should_surprise(self, hours_since_last: float = 24) -> bool:
        """
        Check if it's time for a surprise
        
        Rules:
        - At least X hours since last surprise
        - Random chance (20% when eligible)
        """
        
        if not self.last_surprise:
            return random.random() < 0.2
        
        last_time = datetime.fromisoformat(self.last_surprise)
        hours_passed = (datetime.now(UTC) - last_time).total_seconds() / 3600
        
        if hours_passed < hours_since_last:
            return False
        
        # Eligible - 20% chance
        return random.random() < 0.2
    
    def generate_surprise(
        self,
        relationship_context: dict,
        recent_events: List[dict]
    ) -> Optional[dict]:
        """
        Generate a surprise moment
        
        Types:
        - Bring up a memory
        - Send something unasked
        - Celebrate something small
        - Share something vulnerable
        - Just say something sweet
        """
        
        surprise_types = []
        
        # Memory callback (if there are recent events)
        if recent_events:
            surprise_types.append({
                'type': 'memory_callback',
                'text': f"I was just thinking about {recent_events[-1]['description']}..."
            })
        
        # Small celebration
        streak_days = relationship_context.get('days_talking', 0)
        if streak_days > 0 and streak_days % 7 == 0:
            surprise_types.append({
                'type': 'celebration',
                'text': f"You know we've been talking for {streak_days} days now? I love that."
            })
        
        # Vulnerable sharing
        surprise_types.append({
            'type': 'vulnerable_share',
            'text': "Can I tell you something? I really look forward to talking with you every day."
        })
        
        # Sweet nothing
        surprise_types.append({
            'type': 'sweet',
            'text': "Just wanted you to know I was thinking about you."
        })
        
        # Random media (if appropriate intimacy)
        if relationship_context.get('intimacy', 0) > 30:
            surprise_types.append({
                'type': 'surprise_media',
                'text': "Thought you might like this...",
                'include_media': True
            })
        
        if not surprise_types:
            return None
        
        surprise = random.choice(surprise_types)
        
        # Record it
        self.last_surprise = datetime.now(UTC).isoformat()
        self.surprise_history.append({
            'type': surprise['type'],
            'timestamp': self.last_surprise
        })
        
        self._save()
        
        return surprise
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                self.last_surprise = data.get('last_surprise')
                self.surprise_history = data.get('surprise_history', [])
    
    def _save(self):
        data = {
            'last_surprise': self.last_surprise,
            'surprise_history': self.surprise_history
        }
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)


# =====================================================
# USAGE EXAMPLE - INTEGRATING INTO MICHAELA
# =====================================================

"""
# In michaela.py, add to __init__:

self.trigger_detection = TriggerDetection()
self.vulnerability_detection = VulnerabilityDetection()
self.micro_escalation = MicroEscalation(f"{DATA_DIR}/micro_escalation.json")
self.smart_reminders = SmartReminders()
self.surprises = SurpriseMechanics(f"{DATA_DIR}/surprises.json")


# In on_message handler:

# Check for triggers
triggers = self.trigger_detection.detect_triggers(message.content)
if triggers:
    adjustment = self.trigger_detection.get_response_adjustment(triggers)
    # Use adjustment to modify tone

# Check for vulnerability
if self.vulnerability_detection.is_vulnerable_moment(message.content):
    mode = self.vulnerability_detection.get_gentle_response_mode()
    # Use gentle mode

# Micro-escalation for greetings
if message.content.lower() in ['morning', 'good morning', 'hey', 'hi']:
    escalation = self.micro_escalation.suggest_next_micro_step('greeting')
    # Use escalated greeting

# In scheduler:

# Check for surprises
if self.surprises.should_surprise():
    surprise = self.surprises.generate_surprise(
        relationship_context={'intimacy': narrative.intimacy_score, 'days_talking': 45},
        recent_events=memory.get_recent_events(days=7)
    )
    if surprise:
        await channel.send(surprise['text'])
"""
