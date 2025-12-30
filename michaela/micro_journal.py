"""
Micro Journal
=============

Daily micro-journaling that feeds emotional trend analysis
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


class MicroJournal:
    """
    Daily micro-journaling with trend detection
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.entries = []
        self._load()
    
    def add_entry(
        self,
        text: str,
        mood: str = None,
        energy: int = None
    ):
        """
        Add a journal entry
        energy: 1-10 scale
        mood: detected or self-reported
        """
        
        self.entries.append({
            'timestamp': datetime.now(UTC).isoformat(),
            'date': datetime.now(UTC).date().isoformat(),
            'text': text,
            'mood': mood,
            'energy': energy,
            'word_count': len(text.split())
        })
        
        self._save()
    
    def get_recent_entries(self, days: int = 7) -> list:
        """Get journal entries from last N days"""
        
        cutoff = (datetime.now(UTC) - timedelta(days=days)).date()
        
        return [
            e for e in self.entries
            if datetime.fromisoformat(e['timestamp']).date() >= cutoff
        ]
    
    def analyze_trends(self) -> dict:
        """Analyze recent journal entries for patterns"""
        
        recent = self.get_recent_entries(days=14)
        
        if not recent:
            return {'trend': 'insufficient_data'}
        
        # Mood frequency
        mood_counts = {}
        for entry in recent:
            if entry.get('mood'):
                mood_counts[entry['mood']] = mood_counts.get(entry['mood'], 0) + 1
        
        # Energy trend
        energy_values = [e['energy'] for e in recent if e.get('energy')]
        avg_energy = sum(energy_values) / len(energy_values) if energy_values else None
        
        # Common themes (simple keyword extraction)
        all_text = ' '.join(e['text'].lower() for e in recent)
        
        stress_keywords = ['stress', 'anxious', 'worried', 'overwhelmed', 'pressure']
        positive_keywords = ['good', 'happy', 'proud', 'accomplished', 'excited']
        
        stress_count = sum(all_text.count(word) for word in stress_keywords)
        positive_count = sum(all_text.count(word) for word in positive_keywords)
        
        return {
            'entries_count': len(recent),
            'dominant_mood': max(mood_counts, key=mood_counts.get) if mood_counts else None,
            'average_energy': avg_energy,
            'stress_indicators': stress_count,
            'positive_indicators': positive_count,
            'emotional_tone': 'positive' if positive_count > stress_count else 'stressed' if stress_count > positive_count else 'neutral'
        }
    
    def get_journal_context(self) -> str:
        """Summary for Michaela's awareness"""
        
        trends = self.analyze_trends()
        
        if trends.get('trend') == 'insufficient_data':
            return ""
        
        context = f"Recent journaling patterns ({trends['entries_count']} entries):\n"
        
        if trends.get('dominant_mood'):
            context += f"- Predominant mood: {trends['dominant_mood']}\n"
        
        if trends.get('average_energy'):
            context += f"- Average energy: {trends['average_energy']:.1f}/10\n"
        
        context += f"- Emotional tone: {trends['emotional_tone']}"
        
        return context
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.entries = json.load(f)
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.entries, f, indent=2)
