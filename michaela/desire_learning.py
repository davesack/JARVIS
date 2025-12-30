"""
Desire Learning System
======================

Learns exactly what turns Dave on through observation and feedback:
- Tag preferences by context
- Intensity preferences
- Time-of-day patterns
- Mood-based preferences
- Feedback learning
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
from collections import defaultdict

UTC = timezone.utc


class DesireProfile:
    """
    Complete profile of what turns Dave on
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        
        # Tag preferences (what visual elements he likes)
        self.tag_scores: Dict[str, float] = {}  # tag -> score (0-10)
        
        # Context modifiers
        self.context_preferences: Dict[str, Dict] = {
            'stressed': {},      # Prefers when stressed
            'relaxed': {},       # Prefers when relaxed
            'energetic': {},     # Prefers when high energy
            'tired': {},         # Prefers when tired
            'morning': {},       # Morning preferences
            'afternoon': {},     # Afternoon preferences
            'evening': {},       # Evening preferences
            'night': {}          # Late night preferences
        }
        
        # Intensity preferences
        self.intensity_preference = 'moderate'  # 'soft', 'moderate', 'intense', 'varies'
        
        # Angle/pose preferences
        self.pose_scores: Dict[str, float] = {}
        
        # Feedback history
        self.feedback_log: List[dict] = []
        
        # Patterns detected
        self.detected_patterns: List[dict] = []
        
        self._load()
    
    # =====================================================
    # LEARNING
    # =====================================================
    
    def record_reaction(
        self,
        tags: List[str],
        reaction_score: float,  # 1-10 how much he liked it
        context: str = None,
        time_of_day: str = None
    ):
        """
        Record Dave's reaction to content
        
        Args:
            tags: Tags of the content shown
            reaction_score: How much he liked it (1-10)
            context: His emotional state (stressed, relaxed, etc.)
            time_of_day: morning, afternoon, evening, night
        """
        
        # Update global tag scores
        for tag in tags:
            if tag not in self.tag_scores:
                self.tag_scores[tag] = 5.0  # Neutral starting point
            
            # Weighted average (new data weighted more)
            current = self.tag_scores[tag]
            self.tag_scores[tag] = (current * 0.7) + (reaction_score * 0.3)
        
        # Update context-specific preferences
        if context and context in self.context_preferences:
            for tag in tags:
                if tag not in self.context_preferences[context]:
                    self.context_preferences[context][tag] = 5.0
                
                current = self.context_preferences[context][tag]
                self.context_preferences[context][tag] = (current * 0.7) + (reaction_score * 0.3)
        
        # Update time-of-day preferences
        if time_of_day and time_of_day in self.context_preferences:
            for tag in tags:
                if tag not in self.context_preferences[time_of_day]:
                    self.context_preferences[time_of_day][tag] = 5.0
                
                current = self.context_preferences[time_of_day][tag]
                self.context_preferences[time_of_day][tag] = (current * 0.7) + (reaction_score * 0.3)
        
        # Log feedback
        self.feedback_log.append({
            'timestamp': datetime.now(UTC).isoformat(),
            'tags': tags,
            'reaction_score': reaction_score,
            'context': context,
            'time_of_day': time_of_day
        })
        
        # Detect patterns periodically
        if len(self.feedback_log) % 10 == 0:
            self._detect_patterns()
        
        self._save()
    
    def record_explicit_feedback(
        self,
        tags: List[str],
        feedback: str,  # "loved_it", "not_my_thing", "more_of_this"
        context: str = None
    ):
        """
        Record explicit feedback from Dave
        
        Example:
        - "I love shower content" -> record_explicit_feedback(['shower'], 'loved_it')
        - "Not really into that angle" -> record_explicit_feedback(['angle_name'], 'not_my_thing')
        """
        
        score_map = {
            'loved_it': 9.0,
            'really_like': 8.0,
            'more_of_this': 8.5,
            'this_is_hot': 9.5,
            'not_my_thing': 3.0,
            'not_really': 4.0,
            'meh': 5.0,
            'amazing': 10.0,
            'perfect': 10.0
        }
        
        score = score_map.get(feedback, 5.0)
        
        self.record_reaction(tags, score, context)
    
    def _detect_patterns(self):
        """Analyze feedback to detect patterns"""
        
        if len(self.feedback_log) < 10:
            return
        
        recent = self.feedback_log[-50:]  # Last 50 interactions
        
        # Pattern: Context-based preferences
        context_groups = defaultdict(list)
        for entry in recent:
            if entry.get('context'):
                context_groups[entry['context']].append(entry)
        
        for context, entries in context_groups.items():
            if len(entries) < 5:
                continue
            
            # Find consistently high-rated tags in this context
            tag_scores = defaultdict(list)
            for entry in entries:
                for tag in entry['tags']:
                    tag_scores[tag].append(entry['reaction_score'])
            
            # Tags with average > 7.5 in this context
            for tag, scores in tag_scores.items():
                avg = sum(scores) / len(scores)
                if avg > 7.5 and len(scores) >= 3:
                    pattern = {
                        'type': 'context_preference',
                        'context': context,
                        'tag': tag,
                        'strength': avg,
                        'confidence': len(scores)
                    }
                    
                    # Add if not already detected
                    if pattern not in self.detected_patterns:
                        self.detected_patterns.append(pattern)
        
        # Pattern: Time-of-day preferences
        time_groups = defaultdict(list)
        for entry in recent:
            if entry.get('time_of_day'):
                time_groups[entry['time_of_day']].append(entry)
        
        for time_period, entries in time_groups.items():
            if len(entries) < 5:
                continue
            
            tag_scores = defaultdict(list)
            for entry in entries:
                for tag in entry['tags']:
                    tag_scores[tag].append(entry['reaction_score'])
            
            for tag, scores in tag_scores.items():
                avg = sum(scores) / len(scores)
                if avg > 7.5 and len(scores) >= 3:
                    pattern = {
                        'type': 'time_preference',
                        'time': time_period,
                        'tag': tag,
                        'strength': avg,
                        'confidence': len(scores)
                    }
                    
                    if pattern not in self.detected_patterns:
                        self.detected_patterns.append(pattern)
        
        self._save()
    
    # =====================================================
    # RECOMMENDATIONS
    # =====================================================
    
    def recommend_tags(
        self,
        context: str = None,
        time_of_day: str = None,
        count: int = 5
    ) -> List[str]:
        """
        Recommend tags based on current context
        
        Returns: List of tags Dave will likely enjoy right now
        """
        
        # Start with global scores
        candidates = dict(self.tag_scores)
        
        # Adjust for context
        if context and context in self.context_preferences:
            context_prefs = self.context_preferences[context]
            for tag, score in context_prefs.items():
                if tag in candidates:
                    # Boost score if highly rated in this context
                    candidates[tag] = (candidates[tag] + score) / 2
                else:
                    candidates[tag] = score
        
        # Adjust for time of day
        if time_of_day and time_of_day in self.context_preferences:
            time_prefs = self.context_preferences[time_of_day]
            for tag, score in time_prefs.items():
                if tag in candidates:
                    candidates[tag] = (candidates[tag] + score) / 2
                else:
                    candidates[tag] = score
        
        # Sort by score
        sorted_tags = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        
        # Return top N
        return [tag for tag, score in sorted_tags[:count]]
    
    def get_preference_strength(self, tag: str, context: str = None) -> float:
        """
        Get how much Dave likes a specific tag
        
        Returns: Score 0-10
        """
        
        if context and context in self.context_preferences:
            return self.context_preferences[context].get(tag, self.tag_scores.get(tag, 5.0))
        
        return self.tag_scores.get(tag, 5.0)
    
    def should_send_this_content(
        self,
        tags: List[str],
        context: str = None,
        threshold: float = 6.0
    ) -> bool:
        """
        Determine if content with these tags is likely to be well-received
        
        Args:
            tags: Content tags
            context: Current emotional context
            threshold: Minimum score to recommend (default 6.0)
        
        Returns: True if content should be sent
        """
        
        scores = [self.get_preference_strength(tag, context) for tag in tags]
        
        if not scores:
            return False
        
        # Average score
        avg_score = sum(scores) / len(scores)
        
        return avg_score >= threshold
    
    # =====================================================
    # INSIGHTS FOR MICHAELA
    # =====================================================
    
    def get_insights_for_michaela(self) -> str:
        """
        Generate insights about Dave's preferences for Michaela's awareness
        """
        
        if not self.tag_scores and not self.detected_patterns:
            return "Not enough data yet to understand preferences."
        
        insights = []
        
        # Top preferences overall
        if self.tag_scores:
            top_tags = sorted(self.tag_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            top_tags_str = ", ".join([f"{tag} ({score:.1f})" for tag, score in top_tags if score > 6.0])
            
            if top_tags_str:
                insights.append(f"Dave's favorites: {top_tags_str}")
        
        # Context-based insights
        for pattern in self.detected_patterns:
            if pattern['type'] == 'context_preference':
                insights.append(
                    f"When {pattern['context']}, Dave prefers {pattern['tag']} content "
                    f"(strength: {pattern['strength']:.1f})"
                )
            elif pattern['type'] == 'time_preference':
                insights.append(
                    f"In the {pattern['time']}, Dave likes {pattern['tag']} "
                    f"(strength: {pattern['strength']:.1f})"
                )
        
        # Bottom preferences (dislikes)
        if self.tag_scores:
            bottom_tags = sorted(self.tag_scores.items(), key=lambda x: x[1])[:3]
            bottom_tags_str = ", ".join([f"{tag} ({score:.1f})" for tag, score in bottom_tags if score < 5.0])
            
            if bottom_tags_str:
                insights.append(f"Dave is not as into: {bottom_tags_str}")
        
        if not insights:
            return "Building preference profile..."
        
        return "\n".join(insights)
    
    def get_context_for_michaela(self, current_context: str = None) -> str:
        """
        Get preference context for current situation
        """
        
        if not current_context:
            return self.get_insights_for_michaela()
        
        # Get recommendations for current context
        recommended = self.recommend_tags(context=current_context, count=3)
        
        if not recommended:
            return ""
        
        return f"For Dave's current state ({current_context}), best content: {', '.join(recommended)}"
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.tag_scores = data.get('tag_scores', {})
                self.context_preferences = data.get('context_preferences', self.context_preferences)
                self.intensity_preference = data.get('intensity_preference', 'moderate')
                self.pose_scores = data.get('pose_scores', {})
                self.feedback_log = data.get('feedback_log', [])
                self.detected_patterns = data.get('detected_patterns', [])
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'tag_scores': self.tag_scores,
                'context_preferences': self.context_preferences,
                'intensity_preference': self.intensity_preference,
                'pose_scores': self.pose_scores,
                'feedback_log': self.feedback_log[-100:],  # Keep last 100
                'detected_patterns': self.detected_patterns
            }, f, indent=2)


# =====================================================
# USAGE EXAMPLES
# =====================================================

"""
# In your bot:

desire = DesireProfile('data/michaela/desire_profile.json')

# After sending content, track reaction
# Implicit feedback (from conversation tone)
if dave_seems_excited:
    desire.record_reaction(
        tags=['shower', 'mirror', 'wet'],
        reaction_score=8.5,
        context='stressed',  # He was stressed today
        time_of_day='evening'
    )

# Explicit feedback
if dave_says "I love shower content":
    desire.record_explicit_feedback(
        tags=['shower'],
        feedback='loved_it',
        context='stressed'
    )

# Before sending content, check if it's a good idea
tags_to_send = ['shower', 'mirror']
current_context = 'stressed'  # From emotional_pattern_recognition

if desire.should_send_this_content(tags_to_send, current_context):
    # Send it!
    pass
else:
    # Maybe choose different tags
    better_tags = desire.recommend_tags(context=current_context, count=3)

# Get insights for Michaela's awareness
insights = desire.get_context_for_michaela(current_context='relaxed')
# Add to her prompt

# Michaela can reference this in conversation:
"I've noticed something... when you're stressed from work, you prefer 
softer content - just me, nothing too intense. But when you're relaxed 
on weekends? That's when you like the really dirty stuff. Am I reading 
that right? 😏"
"""
