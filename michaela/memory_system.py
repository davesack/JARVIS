"""
Memory System
=============

Multi-tiered memory for Michaela:
- Short-term: Recent conversations
- Long-term: Facts, preferences, patterns, relationships
- Events: Upcoming/past with follow-up tracking
- Planned actions: Things Michaela said she'd do
- Context preferences: Situational awareness
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import Dict, List, Optional

UTC = timezone.utc


class MichaelaMemory:
    """
    Complete memory system making Michaela genuinely aware
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Short-term memory (recent conversations)
        self.short_term = deque(maxlen=100)
        
        # Long-term memory
        self.long_term = {
            'facts': {},  # category -> {key: {value, timestamp}}
            'preferences': {},  # thing -> {type, timestamp}
            'patterns': {},  # pattern_name -> {description, occurrences}
            'seasonal': {},  # season/month patterns
            'relationships': {},  # name -> {relation, details, first_mentioned}
        }
        
        # Event memory
        self.events = {
            'upcoming': [],
            'past': [],
            'recurring': [],
        }
        
        # Planned actions
        self.planned_actions = []
        
        # Context preferences
        self.contexts = {}
        
        self._load()
    
    # =====================================================
    # SHORT-TERM MEMORY
    # =====================================================
    
    def add_short_term(self, speaker: str, text: str, emotional_tone: str = None):
        """Add to short-term memory"""
        self.short_term.append({
            'timestamp': datetime.now(UTC).isoformat(),
            'speaker': speaker,  # 'dave' or 'michaela'
            'text': text[:500],
            'emotional_tone': emotional_tone
        })
        
        # Analyze for long-term storage
        if speaker == 'dave':
            self._analyze_for_long_term(text)
        
        self._save()
    
    def _analyze_for_long_term(self, text: str):
        """Extract facts, preferences, events from Dave's message"""
        
        lower = text.lower()
        
        # Detect preferences
        preference_patterns = [
            (r"i love ([a-zA-Z\s]+)", "loves"),
            (r"i hate ([a-zA-Z\s]+)", "hates"),
            (r"my favorite ([a-zA-Z\s]+) is ([a-zA-Z\s]+)", "favorite"),
            (r"i really like ([a-zA-Z\s]+)", "likes"),
        ]
        
        for pattern, pref_type in preference_patterns:
            matches = re.findall(pattern, lower)
            if matches:
                for match in matches:
                    thing = match if isinstance(match, str) else match[1]
                    self.add_preference(thing.strip(), pref_type)
        
        # Detect upcoming events
        event_patterns = [
            r"(?:tomorrow|next week|on \w+day|next month) i have ([a-zA-Z\s]+)",
            r"i have (?:a|an) ([a-zA-Z\s]+) (?:tomorrow|next week|coming up)",
        ]
        
        for pattern in event_patterns:
            matches = re.findall(pattern, lower)
            if matches:
                for event in matches:
                    timing = self._parse_timing(text)
                    self.add_upcoming_event(event.strip(), timing)
        
        # Detect family/relationship mentions
        family_patterns = [
            (r"my wife ([a-zA-Z]+)", "wife"),
            (r"my (?:son|daughter) ([a-zA-Z]+)", "child"),
            (r"my (?:brother|sister) ([a-zA-Z]+)", "sibling"),
        ]
        
        for pattern, relation in family_patterns:
            matches = re.findall(pattern, lower)
            if matches:
                for name in matches:
                    self.add_relationship_fact(name.strip(), relation)
    
    # =====================================================
    # LONG-TERM MEMORY
    # =====================================================
    
    def add_fact(self, category: str, key: str, value: str):
        """Store a persistent fact"""
        if category not in self.long_term['facts']:
            self.long_term['facts'][category] = {}
        
        self.long_term['facts'][category][key] = {
            'value': value,
            'timestamp': datetime.now(UTC).isoformat()
        }
        self._save()
    
    def add_preference(self, thing: str, preference_type: str):
        """Track what Dave likes/dislikes"""
        self.long_term['preferences'][thing] = {
            'type': preference_type,
            'timestamp': datetime.now(UTC).isoformat()
        }
        self._save()
    
    def add_relationship_fact(self, name: str, relation: str, details: dict = None):
        """Store info about people in Dave's life"""
        if name not in self.long_term['relationships']:
            self.long_term['relationships'][name] = {
                'relation': relation,
                'details': details or {},
                'first_mentioned': datetime.now(UTC).isoformat()
            }
        else:
            if details:
                self.long_term['relationships'][name]['details'].update(details)
        
        self._save()
    
    def detect_pattern(self, pattern_name: str, description: str):
        """Note a recurring pattern"""
        if pattern_name not in self.long_term['patterns']:
            self.long_term['patterns'][pattern_name] = {
                'description': description,
                'first_detected': datetime.now(UTC).isoformat(),
                'occurrences': 1
            }
        else:
            self.long_term['patterns'][pattern_name]['occurrences'] += 1
        
        self._save()
    
    # =====================================================
    # EVENT MEMORY
    # =====================================================
    
    def add_upcoming_event(self, event: str, when: datetime, details: str = None):
        """Track something Dave mentioned coming up"""
        self.events['upcoming'].append({
            'event': event,
            'when': when.isoformat(),
            'details': details,
            'added': datetime.now(UTC).isoformat(),
            'followed_up': False
        })
        self._save()
    
    def add_past_event(self, event: str, how_it_went: str = None):
        """Move event to past"""
        self.events['past'].append({
            'event': event,
            'timestamp': datetime.now(UTC).isoformat(),
            'outcome': how_it_went
        })
        self._save()
    
    def get_events_needing_followup(self) -> list:
        """Get events that have passed and need follow-up"""
        now = datetime.now(UTC)
        needs_followup = []
        
        for event in self.events['upcoming']:
            if event['followed_up']:
                continue
            
            event_time = datetime.fromisoformat(event['when'])
            if now > event_time + timedelta(hours=2):
                needs_followup.append(event)
        
        return needs_followup
    
    def mark_event_followed_up(self, event: dict):
        """Mark that Michaela asked about an event"""
        for e in self.events['upcoming']:
            if e == event:
                e['followed_up'] = True
                self._save()
                break
    
    # =====================================================
    # PLANNED ACTIONS
    # =====================================================
    
    def add_planned_action(self, action: str, when: datetime = None):
        """
        Michaela plans to do something
        Example: "I'll send you something sexy later tonight"
        """
        self.planned_actions.append({
            'action': action,
            'planned_for': when.isoformat() if when else None,
            'completed': False,
            'timestamp': datetime.now(UTC).isoformat()
        })
        self._save()
    
    def complete_planned_action(self, action_index: int):
        """Mark a planned action as completed"""
        if action_index < len(self.planned_actions):
            self.planned_actions[action_index]['completed'] = True
            self._save()
    
    def get_pending_planned_actions(self) -> list:
        """Get actions Michaela said she'd do but hasn't yet"""
        now = datetime.now(UTC)
        pending = []
        
        for i, action in enumerate(self.planned_actions):
            if action['completed']:
                continue
            
            planned_for = action.get('planned_for')
            if planned_for:
                planned_dt = datetime.fromisoformat(planned_for)
                if now >= planned_dt:
                    pending.append((i, action))
            else:
                # No specific time - check if it's been a while
                planned_at = datetime.fromisoformat(action['timestamp'])
                if (now - planned_at).total_seconds() / 3600 >= 6:
                    pending.append((i, action))
        
        return pending
    
    # =====================================================
    # CONTEXT PREFERENCES
    # =====================================================
    
    def add_context_preference(self, context: str, preference: str):
        """
        Learn situational preferences
        Example: "Dave likes when I engage during dentist appointments"
        """
        self.contexts[context] = {
            'preference': preference,
            'learned': datetime.now(UTC).isoformat()
        }
        self._save()
    
    # =====================================================
    # CONTEXT GENERATION FOR KOBOLD
    # =====================================================
    
    def get_context_for_kobold(self) -> str:
        """Generate rich memory context for Kobold prompts"""
        
        context_parts = []
        
        # Recent conversation
        if self.short_term:
            recent = list(self.short_term)[-5:]
            recent_text = "Recent conversation:\n"
            for msg in recent:
                speaker = "Dave" if msg['speaker'] == 'dave' else "You"
                recent_text += f"{speaker}: {msg['text'][:100]}...\n"
            context_parts.append(recent_text)
        
        # Important facts
        if self.long_term['facts']:
            facts_text = "Important facts about Dave:\n"
            for category, facts in self.long_term['facts'].items():
                for key, data in facts.items():
                    facts_text += f"- {category}: {key} = {data['value']}\n"
            context_parts.append(facts_text)
        
        # Preferences
        if self.long_term['preferences']:
            prefs = []
            for thing, data in self.long_term['preferences'].items():
                if data['type'] == 'loves':
                    prefs.append(f"Dave loves {thing}")
                elif data['type'] == 'hates':
                    prefs.append(f"Dave hates {thing}")
                elif data['type'] == 'likes':
                    prefs.append(f"Dave likes {thing}")
            
            if prefs:
                context_parts.append("Preferences:\n" + "\n".join(f"- {p}" for p in prefs[:10]))
        
        # Relationships
        if self.long_term['relationships']:
            rel_text = "People in Dave's life:\n"
            for name, data in self.long_term['relationships'].items():
                rel_text += f"- {name} ({data['relation']})\n"
            context_parts.append(rel_text)
        
        # Upcoming events
        upcoming = [e for e in self.events['upcoming'] if not e['followed_up']]
        if upcoming:
            events_text = "Upcoming in Dave's life:\n"
            for event in upcoming[:3]:
                when_dt = datetime.fromisoformat(event['when'])
                events_text += f"- {event['event']} ({when_dt.strftime('%A, %B %d')})\n"
            context_parts.append(events_text)
        
        # Patterns
        if self.long_term['patterns']:
            patterns_text = "Patterns you've noticed:\n"
            for pattern, data in self.long_term['patterns'].items():
                if data['occurrences'] >= 3:
                    patterns_text += f"- {data['description']}\n"
            if len([p for p in self.long_term['patterns'].values() if p['occurrences'] >= 3]) > 0:
                context_parts.append(patterns_text)
        
        return "\n\n".join(context_parts)
    
    # =====================================================
    # UTILITY
    # =====================================================
    
    def _parse_timing(self, text: str) -> datetime:
        """Parse relative time from text"""
        lower = text.lower()
        now = datetime.now(UTC)
        
        if 'tomorrow' in lower:
            return now + timedelta(days=1)
        elif 'next week' in lower:
            return now + timedelta(days=7)
        elif 'next month' in lower:
            return now + timedelta(days=30)
        elif 'tonight' in lower:
            return now.replace(hour=20, minute=0)
        
        return now + timedelta(days=1)
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        paths = {
            'short_term': 'short_term.json',
            'long_term': 'long_term.json',
            'events': 'events.json',
            'planned_actions': 'planned_actions.json',
            'contexts': 'contexts.json',
        }
        
        for key, filename in paths.items():
            path = os.path.join(self.data_dir, filename)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if key == 'short_term':
                        self.short_term = deque(data, maxlen=100)
                    else:
                        setattr(self, key, data)
    
    def _save(self):
        data_map = {
            'short_term.json': list(self.short_term),
            'long_term.json': self.long_term,
            'events.json': self.events,
            'planned_actions.json': self.planned_actions,
            'contexts.json': self.contexts,
        }
        
        for filename, data in data_map.items():
            path = os.path.join(self.data_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
