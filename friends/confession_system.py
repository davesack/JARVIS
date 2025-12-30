"""
Confession & Secret Sharing System
===================================

Characters share secrets and confessions at different intimacy levels.
Builds trust and emotional connection through vulnerability.

Each character has unique confessions that unlock progressively.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

UTC = timezone.utc


@dataclass
class Confession:
    """A confession/secret from a character"""
    character: str
    confession_id: str
    intimacy_required: int
    confession_text: str
    revealed_at: Optional[datetime] = None
    revealed: bool = False


# =====================================================
# CONFESSION DATABASE BY CHARACTER
# =====================================================

CONFESSIONS = {
    'michaela': [
        {
            'id': 'thinking_about_you',
            'intimacy': 50,
            'text': "Can I tell you something? I think about you more than I probably should."
        },
        {
            'id': 'touch_myself',
            'intimacy': 70,
            'text': "This is embarrassing but... I touch myself thinking about you."
        },
        {
            'id': 'sebastian_comparison',
            'intimacy': 90,
            'text': "I have a confession. When I'm with Sebastian, sometimes I close my eyes and imagine it's you."
        },
        {
            'id': 'falling_for_you',
            'intimacy': 110,
            'text': "I can't keep this to myself anymore. I'm falling for you, Dave. I know it's complicated, but it's true."
        },
        {
            'id': 'need_you',
            'intimacy': 130,
            'text': "I need to be honest with you. I don't just want you. I need you. This isn't just physical anymore."
        },
    ],
    
    'ariann': [
        {
            'id': 'fantasizing',
            'intimacy': 50,
            'text': "I have to tell you something. I've been fantasizing about you for months."
        },
        {
            'id': 'direct_want',
            'intimacy': 70,
            'text': "You want honesty? I want you. Like, really want you. No games."
        },
        {
            'id': 'confidence',
            'intimacy': 90,
            'text': "Confession: I'm confident about most things. But you? You make me nervous in the best way."
        },
        {
            'id': 'no_regrets',
            'intimacy': 110,
            'text': "I don't regret any of this. Whatever happens, I wanted you to know that."
        },
    ],
    
    'hannah': [
        {
            'id': 'think_about_you',
            'intimacy': 50,
            'text': "I need to tell you something... I think about you way more than I should."
        },
        {
            'id': 'boyfriend_comparison',
            'intimacy': 70,
            'text': "This is so embarrassing but... when I'm with my boyfriend, I sometimes pretend it's you."
        },
        {
            'id': 'feel_guilty',
            'intimacy': 90,
            'text': "I feel guilty about this. But I can't stop. I don't want to stop."
        },
        {
            'id': 'never_felt_this',
            'intimacy': 110,
            'text': "I've never felt this way about anyone. It scares me how much I want you."
        },
    ],
    
    'tara': [
        {
            'id': 'flirting_serious',
            'intimacy': 50,
            'text': "You know all that flirting? It's not just fun for me anymore. I mean it."
        },
        {
            'id': 'dream_about_you',
            'intimacy': 70,
            'text': "Confession: I dream about you. Like, detailed dreams. Should I be embarrassed?"
        },
        {
            'id': 'cant_focus',
            'intimacy': 90,
            'text': "I can't focus when you're around. Or when you're not around. You're just... always there."
        },
    ],
    
    'austin': [
        {
            'id': 'enjoy_teasing',
            'intimacy': 50,
            'text': "Want to know a secret? I love teasing you. Seeing you want me is... intoxicating."
        },
        {
            'id': 'tempted',
            'intimacy': 80,
            'text': "I'll admit something. Sometimes I'm tempted to give you what you want. But where's the fun in that? 😏"
        },
        {
            'id': 'actually_want',
            'intimacy': 120,
            'text': "Okay, real talk. I do want you. I just like making you work for it."
        },
    ],
    
    'angela': [
        {
            'id': 'australia_lonely',
            'intimacy': 50,
            'text': "You want honesty? Australia's beautiful, but I get lonely. You make it better."
        },
        {
            'id': 'think_about_visit',
            'intimacy': 70,
            'text': "I think about you visiting. What we'd do. Gets me through the distance."
        },
        {
            'id': 'not_casual',
            'intimacy': 100,
            'text': "This isn't casual for me anymore. Just so you know."
        },
    ],
    
    'hilary': [
        {
            'id': 'power_feeling',
            'intimacy': 60,
            'text': "Want to know a secret? I love having this power over you. Makes me feel... alive. 😏"
        },
        {
            'id': 'close_to_breaking',
            'intimacy': 90,
            'text': "Confession: Sometimes I get really close to sending you something explicit. Then I remember how fun it is to keep you waiting. 😏"
        },
        {
            'id': 'want_you_bad',
            'intimacy': 120,
            'text': "I have to admit something. I want you. Really bad. Like, aching for it. But you're still not getting anything from me. 😏"
        },
        {
            'id': 'never_give_in',
            'intimacy': 150,
            'text': "Final confession: I'll never give you what you want. And watching you want it anyway? That's what I love most. 😏"
        },
    ],
    
    # Executive Suite
    'lena': [
        {
            'id': 'power_dynamic',
            'intimacy': 60,
            'text': "I like having power over you. In the office, in private. Don't pretend you don't like it too."
        },
        {
            'id': 'think_about_office',
            'intimacy': 80,
            'text': "I think about you in my office. After hours. Just us."
        },
        {
            'id': 'want_you_now',
            'intimacy': 110,
            'text': "I'm done being subtle. I want you. In my office. Soon."
        },
    ],
    
    'cory': [
        {
            'id': 'noticed_you',
            'intimacy': 60,
            'text': "I noticed you before you noticed me. Been waiting for you to catch up."
        },
        {
            'id': 'not_patient',
            'intimacy': 80,
            'text': "I'm not a patient woman. But for you? I'll make an exception. For now."
        },
        {
            'id': 'mine',
            'intimacy': 110,
            'text': "You're mine. We both know it. Stop pretending otherwise."
        },
    ],
    
    'nia': [
        {
            'id': 'watching_you',
            'intimacy': 60,
            'text': "I've been watching you. The way you move, the way you talk. Impressive."
        },
        {
            'id': 'rare_approval',
            'intimacy': 80,
            'text': "I don't give approval easily. But you? You've earned it."
        },
    ],
    
    # Neighborhood Wives
    'kate': [
        {
            'id': 'notice_you',
            'intimacy': 50,
            'text': "This is so wrong but... I notice you. More than I should."
        },
        {
            'id': 'husband_doesnt_know',
            'intimacy': 70,
            'text': "My husband doesn't know I think about you. It's risky but... I can't help it."
        },
        {
            'id': 'want_this',
            'intimacy': 100,
            'text': "I shouldn't want this. But I do. God help me, I really do."
        },
    ],
    
    'megan': [
        {
            'id': 'saw_you_looking',
            'intimacy': 50,
            'text': "I saw you looking at me. Don't pretend you weren't. It's okay. I liked it."
        },
        {
            'id': 'forbidden_exciting',
            'intimacy': 70,
            'text': "The forbidden part? That makes it more exciting. Doesn't it?"
        },
        {
            'id': 'no_backing_out',
            'intimacy': 100,
            'text': "We've come this far. No backing out now. I don't want to anyway."
        },
    ],
}


# =====================================================
# CONFESSION SYSTEM CLASS
# =====================================================

class ConfessionSystem:
    """
    Manages confession/secret sharing for all characters
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.revealed_confessions: Dict[str, List[Confession]] = {}
        self._load()
    
    def get_available_confession(
        self,
        character: str,
        intimacy: int
    ) -> Optional[Dict]:
        """
        Get next available confession for character at this intimacy level
        
        Args:
            character: Character name
            intimacy: Current intimacy level
        
        Returns: Confession dict or None
        """
        
        if character not in CONFESSIONS:
            return None
        
        # Get character's confessions
        char_confessions = CONFESSIONS[character]
        
        # Get already revealed IDs
        revealed_ids = set()
        if character in self.revealed_confessions:
            revealed_ids = {c.confession_id for c in self.revealed_confessions[character]}
        
        # Find next unlocked but unrevealed confession
        for confession in char_confessions:
            if confession['id'] not in revealed_ids and intimacy >= confession['intimacy']:
                return confession
        
        return None
    
    def should_confess(
        self,
        character: str,
        intimacy: int,
        hours_since_last_confession: float = 0
    ) -> bool:
        """
        Determine if character should confess now
        
        Args:
            character: Character name
            intimacy: Current intimacy level
            hours_since_last_confession: Hours since last confession
        
        Returns: True if should confess
        """
        
        # Check if there's an available confession
        confession = self.get_available_confession(character, intimacy)
        if not confession:
            return False
        
        # Must wait at least 48 hours between confessions
        if hours_since_last_confession < 48:
            return False
        
        # 20% chance when eligible
        return random.random() < 0.20
    
    def reveal_confession(
        self,
        character: str,
        intimacy: int
    ) -> Optional[str]:
        """
        Reveal next confession for character
        
        Args:
            character: Character name
            intimacy: Current intimacy level
        
        Returns: Confession text or None
        """
        
        confession_data = self.get_available_confession(character, intimacy)
        if not confession_data:
            return None
        
        # Create confession object
        confession = Confession(
            character=character,
            confession_id=confession_data['id'],
            intimacy_required=confession_data['intimacy'],
            confession_text=confession_data['text'],
            revealed_at=datetime.now(UTC),
            revealed=True
        )
        
        # Store as revealed
        if character not in self.revealed_confessions:
            self.revealed_confessions[character] = []
        
        self.revealed_confessions[character].append(confession)
        self._save()
        
        return confession.confession_text
    
    def get_last_confession_time(self, character: str) -> Optional[datetime]:
        """Get when character last made a confession"""
        if character not in self.revealed_confessions:
            return None
        
        if not self.revealed_confessions[character]:
            return None
        
        return max(c.revealed_at for c in self.revealed_confessions[character])
    
    def get_revealed_count(self, character: str) -> int:
        """Get how many confessions character has revealed"""
        if character not in self.revealed_confessions:
            return 0
        return len(self.revealed_confessions[character])
    
    def get_total_confessions(self, character: str) -> int:
        """Get total confessions available for character"""
        return len(CONFESSIONS.get(character, []))
    
    def _load(self):
        """Load from disk"""
        if not os.path.exists(self.data_path):
            return
        
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
            
            for character, confessions in data.items():
                self.revealed_confessions[character] = [
                    Confession(
                        character=c['character'],
                        confession_id=c['confession_id'],
                        intimacy_required=c['intimacy_required'],
                        confession_text=c['confession_text'],
                        revealed_at=datetime.fromisoformat(c['revealed_at']),
                        revealed=c['revealed']
                    )
                    for c in confessions
                ]
        except Exception as e:
            print(f"[CONFESSIONS] Error loading: {e}")
    
    def _save(self):
        """Save to disk"""
        data = {}
        
        for character, confessions in self.revealed_confessions.items():
            data[character] = [
                {
                    'character': c.character,
                    'confession_id': c.confession_id,
                    'intimacy_required': c.intimacy_required,
                    'confession_text': c.confession_text,
                    'revealed_at': c.revealed_at.isoformat(),
                    'revealed': c.revealed
                }
                for c in confessions
            ]
        
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)
