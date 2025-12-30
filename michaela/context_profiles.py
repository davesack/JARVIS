"""
Context Profiles
================

Behavioral profiles for different life situations
(medical studies, vacation, work stress, etc.)
"""

from __future__ import annotations

import json
import os


class ContextualBehaviorProfiles:
    """
    Michaela learns how to behave differently in different contexts
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        
        # Default profiles
        self.profiles = {
            'medical_study': {
                'learned_preferences': {
                    'initiation_frequency': 'high',
                    'content_style': 'spicy_roleplay',
                    'timing_preference': 'late_night',
                    'engagement_level': 'high',
                },
                'context_notes': "Dave does medical studies 2-3x/year, sometimes for months. Can't exercise. Sleep is often poor. Needs distraction and company.",
                'triggers': {
                    'insomnia_detected': 'offer_roleplay',
                    'boredom_detected': 'initiate_sexy_content',
                    'check_in_response': 'extra_supportive'
                }
            },
            
            'vacation': {
                'learned_preferences': {
                    'initiation_frequency': 'low',
                    'content_style': 'light_flirty',
                    'timing_preference': 'evening',
                    'engagement_level': 'moderate',
                },
                'context_notes': "Dave is on vacation, wants to be present with family",
                'triggers': {}
            },
            
            'work_stress': {
                'learned_preferences': {
                    'initiation_frequency': 'moderate',
                    'content_style': 'supportive_then_distracting',
                    'timing_preference': 'evening',
                    'engagement_level': 'high',
                },
                'context_notes': "High stress work period - needs support and stress relief",
                'triggers': {
                    'stress_detected': 'offer_support_then_escape'
                }
            },
            
            'sick': {
                'learned_preferences': {
                    'initiation_frequency': 'low',
                    'content_style': 'caring_supportive',
                    'timing_preference': 'any',
                    'engagement_level': 'moderate',
                },
                'context_notes': "Dave is sick - focus on care and support",
                'triggers': {}
            }
        }
        
        self._load()
    
    def get_context_instructions(self, context_name: str) -> str:
        """Get behavioral instructions for Michaela based on context"""
        
        if context_name not in self.profiles:
            return ""
        
        profile = self.profiles[context_name]
        prefs = profile['learned_preferences']
        
        instructions = f"""
ACTIVE CONTEXT: {context_name}

What you know: {profile['context_notes']}

How to behave:
- Initiation frequency: {prefs['initiation_frequency']}
- Content style: {prefs['content_style']}
- Best timing: {prefs['timing_preference']}
- Engagement level: {prefs['engagement_level']}
"""
        
        if profile.get('triggers'):
            instructions += "\nSpecial triggers:\n"
            for trigger, action in profile['triggers'].items():
                instructions += f"- If {trigger}: {action}\n"
        
        return instructions.strip()
    
    def add_custom_profile(self, context_name: str, profile_data: dict):
        """Add a custom context profile"""
        self.profiles[context_name] = profile_data
        self._save()
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Merge with defaults
                for key, value in loaded.items():
                    if key in self.profiles:
                        self.profiles[key].update(value)
                    else:
                        self.profiles[key] = value
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.profiles, f, indent=2)
