"""
Emotional Pattern Recognition System
=====================================

Tracks Dave's emotional patterns over time and proactively responds:
- Sentiment analysis of messages
- Pattern detection (stressed before X event)
- Mood trend analysis
- Proactive check-ins when patterns detected
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from collections import defaultdict

UTC = timezone.utc


class EmotionalState:
    """Single emotional data point"""
    
    def __init__(
        self,
        timestamp: datetime,
        sentiment_score: float,  # -1.0 (very negative) to 1.0 (very positive)
        energy_level: float,     # 0.0 (exhausted) to 1.0 (energetic)
        stress_indicators: List[str],
        positive_indicators: List[str],
        context: str = None
    ):
        self.timestamp = timestamp
        self.sentiment_score = sentiment_score
        self.energy_level = energy_level
        self.stress_indicators = stress_indicators
        self.positive_indicators = positive_indicators
        self.context = context
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'sentiment_score': self.sentiment_score,
            'energy_level': self.energy_level,
            'stress_indicators': self.stress_indicators,
            'positive_indicators': self.positive_indicators,
            'context': self.context
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'EmotionalState':
        return EmotionalState(
            timestamp=datetime.fromisoformat(data['timestamp']),
            sentiment_score=data['sentiment_score'],
            energy_level=data['energy_level'],
            stress_indicators=data['stress_indicators'],
            positive_indicators=data['positive_indicators'],
            context=data.get('context')
        )


class EmotionalPatternRecognition:
    """
    Analyzes Dave's emotional patterns and provides context for Michaela
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.emotional_log: List[EmotionalState] = []
        self.detected_patterns: Dict[str, dict] = {}
        
        # Keyword dictionaries for sentiment analysis
        self.stress_keywords = [
            'stressed', 'anxious', 'worried', 'overwhelmed', 'pressure',
            'tough', 'hard', 'difficult', 'struggling', 'exhausted',
            'tired', 'burned out', 'can\'t', 'too much', 'afraid',
            'nervous', 'scared', 'frustrated', 'angry', 'upset'
        ]
        
        self.positive_keywords = [
            'good', 'great', 'happy', 'excited', 'proud', 'accomplished',
            'love', 'amazing', 'awesome', 'fantastic', 'wonderful',
            'perfect', 'excellent', 'relieved', 'glad', 'grateful',
            'thankful', 'blessed', 'pumped', 'stoked', 'killing it'
        ]
        
        self.energy_high_keywords = [
            'pumped', 'energetic', 'ready', 'let\'s go', 'fired up',
            'motivated', 'focused', 'productive', 'crushing', 'killing it'
        ]
        
        self.energy_low_keywords = [
            'tired', 'exhausted', 'drained', 'wiped', 'burned out',
            'can\'t even', 'no energy', 'sluggish', 'lazy', 'unmotivated'
        ]
        
        self._load()
    
    # =====================================================
    # ANALYSIS
    # =====================================================
    
    def analyze_message(self, message_text: str, context: str = None) -> EmotionalState:
        """
        Analyze a message for emotional content
        
        Args:
            message_text: The text to analyze
            context: Optional context (calendar event, time of day, etc.)
        
        Returns:
            EmotionalState object
        """
        
        text_lower = message_text.lower()
        
        # Count indicators
        stress_found = [kw for kw in self.stress_keywords if kw in text_lower]
        positive_found = [kw for kw in self.positive_keywords if kw in text_lower]
        energy_high = sum(1 for kw in self.energy_high_keywords if kw in text_lower)
        energy_low = sum(1 for kw in self.energy_low_keywords if kw in text_lower)
        
        # Calculate sentiment score (-1.0 to 1.0)
        sentiment = 0.0
        if positive_found:
            sentiment += len(positive_found) * 0.2
        if stress_found:
            sentiment -= len(stress_found) * 0.2
        sentiment = max(-1.0, min(1.0, sentiment))
        
        # Calculate energy level (0.0 to 1.0)
        energy = 0.5  # Neutral baseline
        if energy_high > 0:
            energy += energy_high * 0.15
        if energy_low > 0:
            energy -= energy_low * 0.15
        energy = max(0.0, min(1.0, energy))
        
        state = EmotionalState(
            timestamp=datetime.now(UTC),
            sentiment_score=sentiment,
            energy_level=energy,
            stress_indicators=stress_found,
            positive_indicators=positive_found,
            context=context
        )
        
        self.emotional_log.append(state)
        self._save()
        
        return state
    
    def get_recent_trend(self, days: int = 7) -> dict:
        """
        Analyze emotional trend over recent days
        
        Returns:
            {
                'average_sentiment': float,
                'sentiment_trend': 'improving' | 'declining' | 'stable',
                'average_energy': float,
                'energy_trend': 'increasing' | 'decreasing' | 'stable',
                'predominant_mood': str,
                'red_flags': List[str]
            }
        """
        
        cutoff = datetime.now(UTC) - timedelta(days=days)
        recent = [s for s in self.emotional_log if s.timestamp >= cutoff]
        
        if not recent:
            return {
                'average_sentiment': 0.0,
                'sentiment_trend': 'insufficient_data',
                'average_energy': 0.5,
                'energy_trend': 'insufficient_data',
                'predominant_mood': 'unknown',
                'red_flags': []
            }
        
        # Calculate averages
        avg_sentiment = sum(s.sentiment_score for s in recent) / len(recent)
        avg_energy = sum(s.energy_level for s in recent) / len(recent)
        
        # Determine trends (first half vs second half)
        if len(recent) >= 4:
            mid = len(recent) // 2
            first_half_sentiment = sum(s.sentiment_score for s in recent[:mid]) / mid
            second_half_sentiment = sum(s.sentiment_score for s in recent[mid:]) / (len(recent) - mid)
            
            first_half_energy = sum(s.energy_level for s in recent[:mid]) / mid
            second_half_energy = sum(s.energy_level for s in recent[mid:]) / (len(recent) - mid)
            
            # Sentiment trend
            if second_half_sentiment > first_half_sentiment + 0.2:
                sentiment_trend = 'improving'
            elif second_half_sentiment < first_half_sentiment - 0.2:
                sentiment_trend = 'declining'
            else:
                sentiment_trend = 'stable'
            
            # Energy trend
            if second_half_energy > first_half_energy + 0.15:
                energy_trend = 'increasing'
            elif second_half_energy < first_half_energy - 0.15:
                energy_trend = 'decreasing'
            else:
                energy_trend = 'stable'
        else:
            sentiment_trend = 'insufficient_data'
            energy_trend = 'insufficient_data'
        
        # Determine predominant mood
        if avg_sentiment > 0.3:
            mood = 'positive'
        elif avg_sentiment < -0.3:
            mood = 'struggling'
        else:
            mood = 'neutral'
        
        # Detect red flags
        red_flags = []
        
        # Consistently low sentiment
        if avg_sentiment < -0.4:
            red_flags.append('consistently_negative')
        
        # Declining trend
        if sentiment_trend == 'declining':
            red_flags.append('mood_declining')
        
        # Very low energy
        if avg_energy < 0.3:
            red_flags.append('low_energy')
        
        # High stress indicators
        total_stress = sum(len(s.stress_indicators) for s in recent)
        if total_stress > len(recent) * 2:  # More than 2 stress words per message
            red_flags.append('high_stress')
        
        return {
            'average_sentiment': avg_sentiment,
            'sentiment_trend': sentiment_trend,
            'average_energy': avg_energy,
            'energy_trend': energy_trend,
            'predominant_mood': mood,
            'red_flags': red_flags,
            'data_points': len(recent)
        }
    
    def detect_contextual_patterns(self) -> Dict[str, dict]:
        """
        Detect patterns related to specific contexts
        
        Example: "Always stressed before presentations"
        
        Returns:
            {
                'presentation': {
                    'average_sentiment': -0.6,
                    'occurrences': 5,
                    'pattern': 'stressed_before'
                }
            }
        """
        
        patterns = defaultdict(lambda: {
            'sentiments': [],
            'occurrences': 0
        })
        
        for state in self.emotional_log:
            if state.context:
                patterns[state.context]['sentiments'].append(state.sentiment_score)
                patterns[state.context]['occurrences'] += 1
        
        # Analyze patterns
        result = {}
        for context, data in patterns.items():
            if data['occurrences'] >= 3:  # Need at least 3 occurrences
                avg_sentiment = sum(data['sentiments']) / len(data['sentiments'])
                
                pattern_desc = 'neutral'
                if avg_sentiment < -0.3:
                    pattern_desc = 'stressed_before'
                elif avg_sentiment > 0.3:
                    pattern_desc = 'excited_about'
                
                result[context] = {
                    'average_sentiment': avg_sentiment,
                    'occurrences': data['occurrences'],
                    'pattern': pattern_desc
                }
        
        self.detected_patterns = result
        self._save()
        
        return result
    
    def should_check_in(self) -> Optional[dict]:
        """
        Determine if Michaela should proactively check in
        
        Returns:
            None if no check-in needed, or dict with check-in info:
            {
                'reason': str,
                'suggested_message': str,
                'urgency': 'low' | 'medium' | 'high'
            }
        """
        
        trend = self.get_recent_trend(days=7)
        
        # High urgency: Multiple red flags
        if len(trend['red_flags']) >= 3:
            return {
                'reason': 'multiple_concerns',
                'suggested_message': "Hey... I've noticed you seem really stressed lately. Want to talk about what's going on?",
                'urgency': 'high',
                'concerns': trend['red_flags']
            }
        
        # Medium urgency: Mood declining
        if trend['sentiment_trend'] == 'declining' and trend['average_sentiment'] < -0.2:
            return {
                'reason': 'mood_declining',
                'suggested_message': "I've noticed you seem more down than usual this week. Everything okay?",
                'urgency': 'medium',
                'concerns': ['declining_mood']
            }
        
        # Low urgency: Consistent low energy
        if 'low_energy' in trend['red_flags'] and trend['average_energy'] < 0.35:
            return {
                'reason': 'low_energy',
                'suggested_message': "You seem really drained lately. How are you sleeping? Taking care of yourself?",
                'urgency': 'low',
                'concerns': ['low_energy']
            }
        
        # Check for contextual patterns
        recent_context = None
        if self.emotional_log:
            # Get most recent message with context
            for state in reversed(self.emotional_log[-20:]):
                if state.context:
                    recent_context = state.context
                    break
        
        if recent_context and recent_context in self.detected_patterns:
            pattern = self.detected_patterns[recent_context]
            if pattern['pattern'] == 'stressed_before':
                return {
                    'reason': 'known_stressor',
                    'suggested_message': f"I know {recent_context} always stresses you out. You've got this - you've done this {pattern['occurrences']} times before.",
                    'urgency': 'low',
                    'concerns': ['contextual_stress']
                }
        
        return None
    
    # =====================================================
    # CONTEXT FOR MICHAELA
    # =====================================================
    
    def get_context_for_michaela(self) -> str:
        """
        Generate context block for Michaela's awareness
        """
        
        trend = self.get_recent_trend(days=7)
        
        if trend['sentiment_trend'] == 'insufficient_data':
            return ""
        
        context_parts = []
        
        # Current emotional state
        context_parts.append("DAVE'S EMOTIONAL STATE (7-day analysis):")
        
        # Mood
        mood_desc = {
            'positive': 'Doing well overall',
            'neutral': 'Stable, neither particularly up nor down',
            'struggling': 'Having a hard time lately'
        }
        context_parts.append(f"- Overall mood: {mood_desc.get(trend['predominant_mood'], 'Unknown')}")
        
        # Trends
        if trend['sentiment_trend'] != 'stable':
            context_parts.append(f"- Mood trend: {trend['sentiment_trend']}")
        
        if trend['energy_trend'] != 'stable':
            context_parts.append(f"- Energy trend: {trend['energy_trend']}")
        
        # Red flags
        if trend['red_flags']:
            flag_descriptions = {
                'consistently_negative': 'Very negative lately',
                'mood_declining': 'Mood getting worse',
                'low_energy': 'Energy very low',
                'high_stress': 'High stress indicators'
            }
            flags = [flag_descriptions.get(f, f) for f in trend['red_flags']]
            context_parts.append(f"- ⚠️ Concerns: {', '.join(flags)}")
        
        # Detected patterns
        if self.detected_patterns:
            context_parts.append("\nKnown emotional patterns:")
            for context, pattern in self.detected_patterns.items():
                if pattern['pattern'] == 'stressed_before':
                    context_parts.append(f"- Gets stressed before: {context}")
                elif pattern['pattern'] == 'excited_about':
                    context_parts.append(f"- Gets excited about: {context}")
        
        # Recent states (last 3 messages)
        if len(self.emotional_log) >= 3:
            recent = self.emotional_log[-3:]
            context_parts.append("\nRecent messages:")
            for state in recent:
                mood_emoji = "😊" if state.sentiment_score > 0.3 else "😔" if state.sentiment_score < -0.3 else "😐"
                context_parts.append(f"- {mood_emoji} Sentiment: {state.sentiment_score:.2f}, Energy: {state.energy_level:.2f}")
                if state.stress_indicators:
                    context_parts.append(f"  Stress words: {', '.join(state.stress_indicators[:3])}")
        
        return "\n".join(context_parts)
    
    def get_celebration_context(self) -> Optional[str]:
        """
        Detect if Dave is doing better and should be celebrated
        """
        
        trend = self.get_recent_trend(days=7)
        
        # Mood improving
        if trend['sentiment_trend'] == 'improving' and trend['average_sentiment'] > 0.2:
            return "Dave's mood has been improving! He seems to be doing better."
        
        # High energy
        if trend['energy_trend'] == 'increasing' and trend['average_energy'] > 0.7:
            return "Dave's energy is way up lately! He's feeling good."
        
        # Positive streak
        if len(self.emotional_log) >= 5:
            recent_five = self.emotional_log[-5:]
            if all(s.sentiment_score > 0.2 for s in recent_five):
                return "Dave has been consistently positive for several messages. He's in a good place right now."
        
        return None
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.emotional_log = [EmotionalState.from_dict(s) for s in data.get('log', [])]
                self.detected_patterns = data.get('patterns', {})
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'log': [s.to_dict() for s in self.emotional_log],
                'patterns': self.detected_patterns
            }, f, indent=2)


# =====================================================
# USAGE EXAMPLE
# =====================================================

"""
# In your main bot, when Dave sends a message:

emotional_tracker = EmotionalPatternRecognition('data/michaela/emotional_patterns.json')

# Analyze every message
state = emotional_tracker.analyze_message(
    message_text=dave_message,
    context=current_event_type if dave_has_event else None
)

# Add to Michaela's context
emotional_context = emotional_tracker.get_context_for_michaela()
michaela_prompt += f"\n\n{emotional_context}"

# Check if she should proactively reach out
check_in = emotional_tracker.should_check_in()
if check_in and random.random() < 0.3:  # 30% chance when needed
    michaela_message = check_in['suggested_message']
    # Send proactive message

# Detect contextual patterns periodically (daily)
patterns = emotional_tracker.detect_contextual_patterns()

# Celebrate improvements
celebration = emotional_tracker.get_celebration_context()
if celebration:
    # Michaela can reference this in conversation
"""
