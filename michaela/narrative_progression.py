"""
Narrative Progression System
============================

Manages the complete story arc of Michaela and Dave's relationship.
Includes unlock system, progression tracking, and context generation.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional

UTC = timezone.utc


class NarrativeProgression:
    """
    Tracks the evolving story with granular unlockable behaviors
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        
        # Story progression
        self.current_chapter = "discovery"
        # Chapters: discovery -> escalation -> secret_intimacy -> 
        # confession_tension -> cooldown -> acceptance -> first_time -> liberation
        
        # Core stats
        self.intimacy_score = 0  # Emotional connection (0-200+)
        self.desire_intensity = 0  # Sexual desire (0-100)
        self.dave_desire = 0  # Dave's desire (0-100)
        self.guilt_intensity = 0  # Guilt about Sebastian (0-100)
        self.michaela_confidence = 0  # Sexual confidence (0-100)
        self.resistance_level = 100  # Resistance to crossing boundaries (0-100)
        self.eagerness_level = 0  # Eagerness to explore (0-100)
        self.sebastian_awareness = 0  # Sebastian's awareness (0-100)
        self.sebastian_arousal = 0  # Post-confession arousal (0-100)
        
        # Unlockable behaviors
        self.unlocked = {
            # Phase 1: Discovery
            "friendly_chat": True,
            "emotional_support": False,
            "flirty_banter": False,
            "compliments": False,
            
            # Phase 2: Early Escalation
            "casual_photos": False,
            "suggestive_photos": False,
            "sexual_tension_acknowledgment": False,
            
            # Phase 3: Secret Intimacy (PRE-CONFESSION - Goes HARD)
            "intimate_photos": False,
            "explicit_photos": False,
            "shower_videos": False,
            "explicit_videos": False,
            "sexual_conversation": False,
            "fantasy_sharing": False,
            "command_acceptance": False,
            "roleplay_scenarios": False,
            "threesome_fantasy": False,
            "porn_sharing": False,
            "michaela_initiated_sexting": False,
            
            # Phase 4: Confession
            "confession_readiness": False,
            
            # Phase 5: Post-Confession
            "sebastian_knows": False,
            "sebastian_aroused": False,
            "permission_dynamic": False,
            "cuckold_fantasy": False,
            
            # Phase 6: First Time
            "first_time_event": False,
            
            # Phase 7: Liberation
            "post_first_time_freedom": False,
            "sebastian_directs_scenarios": False,
            "extreme_scenarios": False,
        }
        
        # Story moments
        self.milestones = []
        self.first_times = {}
        
        # Initiation tracking
        self.michaela_initiations = 0
        self.last_initiation = None
        
        self._load()
    
    # =====================================================
    # STAT ADJUSTMENTS
    # =====================================================
    
    def adjust_intimacy(self, delta: int, reason: str = None):
        """Increase/decrease emotional intimacy"""
        self.intimacy_score += delta
        
        if reason:
            self.milestones.append({
                'event': f"Intimacy {'+' if delta > 0 else ''}{delta}: {reason}",
                'timestamp': datetime.now(UTC).isoformat(),
                'category': 'intimacy'
            })
        
        self._check_auto_unlocks()
        self._save()
    
    def adjust_desire(self, delta: int):
        """Increase/decrease sexual desire"""
        self.desire_intensity = max(0, min(100, self.desire_intensity + delta))
        
        # Desire can reduce resistance
        if delta > 0 and random.random() < 0.3:
            self.resistance_level = max(0, self.resistance_level - (delta // 2))
        
        self._check_auto_unlocks()
        self._save()
    
    def adjust_resistance(self, delta: int):
        """Increase/decrease resistance to boundaries"""
        self.resistance_level = max(0, min(100, self.resistance_level + delta))
        self._check_auto_unlocks()
        self._save()
    
    def adjust_confidence(self, delta: int):
        """Increase/decrease sexual confidence"""
        self.michaela_confidence = max(0, min(100, self.michaela_confidence + delta))
        self._check_auto_unlocks()
        self._save()
    
    def adjust_guilt(self, delta: int):
        """Increase/decrease guilt"""
        self.guilt_intensity = max(0, min(100, self.guilt_intensity + delta))
        
        # Guilt can increase resistance
        if delta > 0 and random.random() < 0.4:
            self.resistance_level = min(100, self.resistance_level + (delta // 3))
        
        self._save()
    
    def adjust_sebastian_awareness(self, delta: int):
        """Increase Sebastian's awareness"""
        self.sebastian_awareness = max(0, min(100, self.sebastian_awareness + delta))
        
        # Phase transitions based on awareness
        if self.sebastian_awareness > 75 and self.current_chapter != "liberation":
            self.current_chapter = "acceptance"
        elif self.sebastian_awareness > 40 and self.current_chapter == "secret_intimacy":
            self.current_chapter = "confession_tension"
        
        self._save()
    
    def advance_chapter(self, new_chapter: str):
        """Move to new chapter"""
        old_chapter = self.current_chapter
        self.current_chapter = new_chapter
        self.milestones.append({
            'event': f"Chapter: {old_chapter} → {new_chapter}",
            'timestamp': datetime.now(UTC).isoformat(),
            'category': 'chapter'
        })
        self._check_auto_unlocks()
        self._save()
    
    # =====================================================
    # UNLOCKING SYSTEM
    # =====================================================
    
    def can_send_media(self) -> bool:
        """Check if any media can be sent"""
        return any([
            self.unlocked.get('casual_photos'),
            self.unlocked.get('suggestive_photos'),
            self.unlocked.get('intimate_photos'),
            self.unlocked.get('explicit_photos')
        ])
    
    def note_media_sent(self):
        """Track that media was sent"""
        self.milestones.append({
            'event': 'Media sent to Dave',
            'timestamp': datetime.now(UTC).isoformat(),
            'category': 'media'
        })
        self._save()
    
    def _check_auto_unlocks(self):
        """Check if conditions are met for automatic unlocks"""
        
        # Define unlock conditions
        conditions = {
            "emotional_support": lambda: self.intimacy_score >= 10,
            
            "flirty_banter": lambda: self.intimacy_score >= 20,
            
            "compliments": lambda: (
                self.unlocked['flirty_banter'] and 
                self.intimacy_score >= 30
            ),
            
            "casual_photos": lambda: (
                self.intimacy_score >= 50 and
                self.michaela_confidence >= 15 and
                self.unlocked['compliments']
            ),
            
            "suggestive_photos": lambda: (
                self.intimacy_score >= 70 and
                self.michaela_confidence >= 25 and
                self.unlocked['casual_photos'] and
                self.desire_intensity >= 20
            ),
            
            "sexual_tension_acknowledgment": lambda: (
                self.desire_intensity >= 30 and
                self.intimacy_score >= 60
            ),
            
            "intimate_photos": lambda: (
                self.intimacy_score >= 90 and
                self.michaela_confidence >= 40 and
                self.desire_intensity >= 40 and
                self.unlocked['suggestive_photos']
            ),
            
            "explicit_photos": lambda: (
                self.intimacy_score >= 110 and
                self.michaela_confidence >= 55 and
                self.desire_intensity >= 60 and
                self.unlocked['intimate_photos']
            ),
            
            "sexual_conversation": lambda: (
                self.desire_intensity >= 50 and
                self.intimacy_score >= 100
            ),
            
            "shower_videos": lambda: (
                self.unlocked['explicit_photos'] and
                self.michaela_confidence >= 60
            ),
            
            "explicit_videos": lambda: (
                self.unlocked['shower_videos'] and
                self.desire_intensity >= 75 and
                self.michaela_confidence >= 70
            ),
            
            "fantasy_sharing": lambda: (
                self.unlocked['sexual_conversation'] and
                self.desire_intensity >= 65
            ),
            
            "command_acceptance": lambda: (
                self.unlocked['explicit_photos'] and
                self.intimacy_score >= 120 and
                self.desire_intensity >= 70
            ),
            
            "roleplay_scenarios": lambda: (
                self.unlocked['fantasy_sharing'] and
                self.michaela_confidence >= 75
            ),
            
            "threesome_fantasy": lambda: (
                self.unlocked['roleplay_scenarios'] and
                self.desire_intensity >= 80
            ),
            
            "porn_sharing": lambda: (
                self.unlocked['explicit_videos'] and
                self.desire_intensity >= 85
            ),
            
            "michaela_initiated_sexting": lambda: (
                self.unlocked['sexual_conversation'] and
                self.desire_intensity >= 70 and
                self.michaela_confidence >= 65
            ),
            
            "sebastian_aroused": lambda: (
                self.unlocked['sebastian_knows'] and
                self.sebastian_arousal >= 50
            ),
            
            "permission_dynamic": lambda: (
                self.unlocked['sebastian_aroused'] and
                self.sebastian_arousal >= 70
            ),
            
            "cuckold_fantasy": lambda: (
                self.unlocked['permission_dynamic'] and
                self.sebastian_arousal >= 85
            ),
            
            "post_first_time_freedom": lambda: (
                self.unlocked['first_time_event']
            ),
            
            "sebastian_directs_scenarios": lambda: (
                self.unlocked['post_first_time_freedom'] and
                self.sebastian_arousal >= 90
            ),
            
            "extreme_scenarios": lambda: (
                self.unlocked['sebastian_directs_scenarios'] and
                self.michaela_confidence >= 95
            ),
        }
        
        # Check each locked behavior
        unlocked_something = False
        for behavior, is_unlocked in self.unlocked.items():
            if not is_unlocked and behavior in conditions:
                if conditions[behavior]():
                    self.unlocked[behavior] = True
                    self.milestones.append({
                        'event': f"🔓 Unlocked: {behavior}",
                        'timestamp': datetime.now(UTC).isoformat(),
                        'category': 'unlock'
                    })
                    print(f"✨ AUTO-UNLOCKED: {behavior}")
                    unlocked_something = True
                    
                    # Phase transitions on key unlocks
                    if behavior == "explicit_photos" and self.current_chapter == "escalation":
                        self.current_chapter = "secret_intimacy"
        
        if unlocked_something:
            self._save()
    
    # =====================================================
    # CONTEXT GENERATION FOR KOBOLD
    # =====================================================
    
    def get_phase_context(self) -> str:
        """Get rich narrative context for Kobold"""
        
        chapter_contexts = {
            "discovery": """
PHASE: Discovery
You and Dave are exploring this connection for the first time.
Everything feels new, slightly forbidden, electric.
You're not sure where this is going yet, but you want it.
Sebastian doesn't know anything yet.
Your confidence is still emerging.
""",
            
            "escalation": f"""
PHASE: Early Escalation
Something has shifted between you and Dave.
Flirtation is becoming natural. Desire is acknowledged.
You're testing boundaries, seeing how this feels.
Guilt hasn't fully set in yet - this still feels playful.
Desire: {self.desire_intensity}/100
Confidence: {self.michaela_confidence}/100
""",
            
            "secret_intimacy": f"""
PHASE: Secret Intimacy (PRE-CONFESSION)
You and Dave have crossed major boundaries.
This is sexual now. Explicit. You've sent him intimate content.
You fantasize about him. You've roleplayed scenarios together.
You've imagined threesomes with him and Elisha.
He's given you commands and you've followed them.
You've shared what you want to do to him.

The guilt is REAL and HEAVY: {self.guilt_intensity}/100
The desire is OVERWHELMING: {self.desire_intensity}/100

Sebastian doesn't know. Every message is a secret.
The thrill of the forbidden makes everything more intense.
But the weight of lying to Sebastian is starting to hurt.

You sometimes INITIATE sexy content now - you want Dave, not just responding.
""",
            
            "confession_tension": f"""
PHASE: Confession Tension
The secret is becoming too much to carry.
The guilt is crushing: {self.guilt_intensity}/100
You know you need to tell Sebastian but you're terrified:
- What if he leaves you?
- What if this ends what you have with Dave?
- What if you lose everything?

But you can't keep living this lie.
""",
            
            "cooldown": """
PHASE: Post-Confession Cooldown
You told Sebastian. Or he found out.
He was hurt. Angry. Confused.
You've backed off from Dave while you and Sebastian process.
Everything is uncertain right now.
You miss what you had with Dave but you need to fix your marriage first.
""",
            
            "acceptance": f"""
PHASE: Acceptance
Something unexpected happened.
Sebastian... is turned on by this.
You and Sebastian have been talking about it. Roleplaying.
The idea of you with Dave excites him.
Sebastian arousal level: {self.sebastian_arousal}/100

This is a new dynamic. The guilt is transforming into permission.
You're starting to talk to Dave about what Sebastian said, what he wants.
""",
            
            "first_time": """
PHASE: First Time Event
Sebastian wants you to be with Dave.
This is actually going to happen.
The buildup is intense. You're nervous and excited and turned on.
You and Dave are going to write this together.
""",
            
            "liberation": f"""
PHASE: Liberation
You've been with Dave. Everything changed.
Sebastian knows. Sebastian WANTS this. Sebastian gets off on this.
You report back to Sebastian what you do with Dave.
Sebastian sometimes tells you what he wants you to do with Dave.

You're fully yourself now. Confident. Adventurous. Free.
Confidence: {self.michaela_confidence}/100
Sebastian arousal: {self.sebastian_arousal}/100

This is who you are now, and it feels RIGHT.
"""
        }
        
        return chapter_contexts.get(self.current_chapter, "")
    
    def get_unlocked_behaviors_context(self) -> str:
        """List what Michaela can currently do"""
        
        unlocked_list = [k for k, v in self.unlocked.items() if v]
        
        if not unlocked_list:
            return "Currently: Only friendly, platonic conversation"
        
        context = "Michaela can currently:\n"
        context += "\n".join(f"- {behavior.replace('_', ' ')}" for behavior in unlocked_list)
        
        return context
    
    def get_current_state_description(self) -> str:
        """Human-readable current state"""
        
        descriptions = {
            "discovery": "Elisha's sister. Polite but distant. Boundaries are clear.",
            "escalation": "The air between you has changed. Jokes land differently.",
            "secret_intimacy": "This is a thing now. You both know it. Sebastian doesn't. The secrecy makes it electric.",
            "confession_tension": "The weight of the secret is becoming too much. Something has to give.",
            "cooldown": "Sebastian knows. Everything is raw and uncertain.",
            "acceptance": "Sebastian supports this. The guilt transformed into permission. New possibilities open.",
            "first_time": "Sebastian wants this. You both want this. Tonight it happens.",
            "liberation": "She's fully herself now. Confident. Playful. Adventurous. This is who she's become."
        }
        
        return descriptions.get(self.current_chapter, "Unknown")
    
    # =====================================================
    # INITIATION SYSTEM
    # =====================================================
    
    def should_michaela_initiate_sexy(self) -> bool:
        """Determine if Michaela should proactively initiate"""
        
        if not self.unlocked.get("michaela_initiated_sexting"):
            return False
        
        # Don't initiate too often
        if self.last_initiation:
            from datetime import timedelta
            hours_since = (datetime.now(UTC) - datetime.fromisoformat(self.last_initiation)).total_seconds() / 3600
            if hours_since < 48:
                return False
        
        # Chance increases with desire and confidence
        base_chance = 0.15
        desire_factor = self.desire_intensity / 100 * 0.2
        confidence_factor = self.michaela_confidence / 100 * 0.15
        
        total_chance = base_chance + desire_factor + confidence_factor
        
        return random.random() < total_chance
    
    def note_michaela_initiation(self, content_type: str):
        """Track when she initiates"""
        self.michaela_initiations += 1
        self.last_initiation = datetime.now(UTC).isoformat()
        self.milestones.append({
            'event': f"Michaela initiated: {content_type}",
            'timestamp': self.last_initiation,
            'category': 'initiation'
        })
        self._save()
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_chapter = data.get('current_chapter', 'discovery')
                self.intimacy_score = data.get('intimacy_score', 0)
                self.desire_intensity = data.get('desire_intensity', 0)
                self.dave_desire = data.get('dave_desire', 0)
                self.guilt_intensity = data.get('guilt_intensity', 0)
                self.michaela_confidence = data.get('michaela_confidence', 0)
                self.resistance_level = data.get('resistance_level', 100)
                self.eagerness_level = data.get('eagerness_level', 0)
                self.sebastian_awareness = data.get('sebastian_awareness', 0)
                self.sebastian_arousal = data.get('sebastian_arousal', 0)
                self.unlocked = data.get('unlocked', self.unlocked)
                self.milestones = data.get('milestones', [])
                self.first_times = data.get('first_times', {})
                self.michaela_initiations = data.get('michaela_initiations', 0)
                self.last_initiation = data.get('last_initiation')
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'current_chapter': self.current_chapter,
                'intimacy_score': self.intimacy_score,
                'desire_intensity': self.desire_intensity,
                'dave_desire': self.dave_desire,
                'guilt_intensity': self.guilt_intensity,
                'michaela_confidence': self.michaela_confidence,
                'resistance_level': self.resistance_level,
                'eagerness_level': self.eagerness_level,
                'sebastian_awareness': self.sebastian_awareness,
                'sebastian_arousal': self.sebastian_arousal,
                'unlocked': self.unlocked,
                'milestones': self.milestones,
                'first_times': self.first_times,
                'michaela_initiations': self.michaela_initiations,
                'last_initiation': self.last_initiation
            }, f, indent=2)


class AutoProgressionEngine:
    """
    Automatically adjusts narrative state based on interactions
    """
    
    def __init__(self, narrative: NarrativeProgression, streaks):
        self.narrative = narrative
        self.streaks = streaks
    
    def process_dave_message(self, message: str):
        """Analyze Dave's message and update state"""
        
        lower = message.lower()
        
        # Track Dave's desire
        if any(word in lower for word in ['want you', 'need you', 'sexy', 'hot', 'beautiful']):
            self.narrative.dave_desire = min(100, self.narrative.dave_desire + 1)
        
        # Vulnerability builds intimacy
        if any(word in lower for word in ['scared', 'struggling', 'hard time', 'worried']):
            self.narrative.adjust_intimacy(3, "Dave was vulnerable")
        
        # Care builds intimacy
        if any(phrase in lower for phrase in ['proud of you', 'care about you', 'love you']):
            self.narrative.adjust_intimacy(2, "Dave expressed care")
        
        # Flirtation
        if any(word in lower for word in ['gorgeous', 'stunning']):
            if self.narrative.unlocked.get('flirty_banter'):
                self.narrative.adjust_desire(1)
    
    def process_habit_completion(self, habit_name: str, streak_data: dict):
        """Habits build intimacy and reduce resistance"""
        
        streak = streak_data['current_streak']
        
        if streak >= 7:
            self.narrative.adjust_intimacy(1, f"{habit_name} - week streak")
        
        if streak >= 30:
            self.narrative.adjust_intimacy(3, f"{habit_name} - month milestone")
            self.narrative.adjust_confidence(5)
            self.narrative.adjust_resistance(-5)
        
        if streak >= 100:
            self.narrative.adjust_intimacy(5, f"{habit_name} - 100 day epic")
            self.narrative.adjust_confidence(10)
            self.narrative.adjust_resistance(-10)
