"""
Friends System
==============

Complete friend character system with:
- Personality and memory
- Story arc progression (scripted vs emergent)
- Physical descriptions
- Installable story packs
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional

UTC = timezone.utc


class FriendStoryArc:
    """
    Defines a friend's complete story progression
    """
    
    def __init__(
        self,
        friend_name: str,
        arc_type: str,  # 'scripted' or 'emergent'
        story_data: dict
    ):
        self.friend_name = friend_name
        self.arc_type = arc_type
        
        if arc_type == 'scripted':
            # Full story arc defined
            self.chapters = story_data.get('chapters', [])
            self.current_chapter_index = 0
        else:
            # Emergent - discover together
            self.personality_seed = story_data.get('personality_seed', '')
            self.possible_directions = story_data.get('possible_directions', [])
            self.current_state = 'introduction'
    
    def get_current_chapter_context(self) -> str:
        """Get context for current story chapter"""
        
        if self.arc_type == 'scripted':
            if self.current_chapter_index < len(self.chapters):
                chapter = self.chapters[self.current_chapter_index]
                return f"""
STORY ARC: {self.friend_name}
Chapter {self.current_chapter_index + 1}: {chapter.get('title', 'Untitled')}

Story context: {chapter.get('context', '')}

Key beats for this chapter:
{chr(10).join('- ' + beat for beat in chapter.get('beats', []))}

Unlocked content: {', '.join(chapter.get('unlocked_content', []))}
"""
        else:
            return f"""
EMERGENT STORY: {self.friend_name}
Current state: {self.current_state}

Personality foundation: {self.personality_seed}

Let the character develop naturally based on interactions.
"""
    
    def can_advance_chapter(self, progression_data: dict) -> bool:
        """Check if conditions met to advance"""
        
        if self.arc_type != 'scripted':
            return False
        
        if self.current_chapter_index >= len(self.chapters) - 1:
            return False
        
        next_chapter = self.chapters[self.current_chapter_index + 1]
        conditions = next_chapter.get('unlock_conditions', {})
        
        for condition_type, required_value in conditions.items():
            actual_value = progression_data.get(condition_type, 0)
            if actual_value < required_value:
                return False
        
        return True
    
    def advance_chapter(self):
        """Move to next chapter"""
        if self.arc_type == 'scripted' and self.current_chapter_index < len(self.chapters) - 1:
            self.current_chapter_index += 1
            return True
        return False


class Friend:
    """
    Complete friend character
    """
    
    def __init__(
        self,
        name: str,
        slug: str,
        base_personality: str,
        physical_description: str,
        relationship_to_michaela: str,
        story_arc: FriendStoryArc = None,
        profile_image_path: str = None
    ):
        self.name = name
        self.slug = slug
        self.base_personality = base_personality
        self.physical_description = physical_description
        self.relationship_to_michaela = relationship_to_michaela
        self.story_arc = story_arc
        self.profile_image_path = profile_image_path or f"media/{slug}/profile.webp"
        
        # Interaction tracking
        self.interaction_count = 0
        self.dave_familiarity = 0  # 0-100
        self.last_interaction = None
        
        # Memory about Dave
        self.memory = {
            'learned_preferences': {},
            'inside_jokes': [],
            'shared_experiences': [],
            'dave_traits': []
        }
        
        # Her own developing personality
        self.personality_traits = {
            'favorite_things': [],
            'interests': [],
            'quirks': [],
            'desires': [],
            'boundaries': []
        }
        
        # Relationship with Dave
        self.relationship_state = {
            'comfort_level': 0,  # 0-100
            'attraction': 0,  # 0-100
            'trust': 0,  # 0-100
            'intimacy_unlocked': False
        }
    
    def interact(self, context: str, dave_response: str = None):
        """Log an interaction"""
        self.interaction_count += 1
        self.dave_familiarity = min(100, self.dave_familiarity + 2)
        self.last_interaction = datetime.now(UTC).isoformat()
        
        self.memory['shared_experiences'].append({
            'timestamp': datetime.now(UTC).isoformat(),
            'context': context[:200],
            'dave_response': dave_response[:200] if dave_response else None
        })
    
    def learn_preference(self, thing: str, preference_type: str):
        """Learn something about Dave"""
        self.memory['learned_preferences'][thing] = {
            'type': preference_type,
            'learned': datetime.now(UTC).isoformat()
        }
    
    def develop_trait(self, trait: str, category: str):
        """Develop her own personality"""
        if trait not in self.personality_traits.get(category, []):
            self.personality_traits[category].append(trait)
    
    def adjust_relationship(self, aspect: str, delta: int):
        """Adjust relationship dynamics"""
        if aspect in self.relationship_state:
            self.relationship_state[aspect] = max(0, min(100, 
                self.relationship_state[aspect] + delta
            ))
    
    def get_kobold_context(self, michaela_context: dict = None) -> str:
        """Generate rich context for when she speaks"""
        
        context = f"""
CHARACTER: {self.name}

PHYSICAL DESCRIPTION:
{self.physical_description}

CORE PERSONALITY:
{self.base_personality}

RELATIONSHIP TO MICHAELA:
{self.relationship_to_michaela}

YOUR RELATIONSHIP WITH DAVE:
- Familiarity: {self.dave_familiarity}/100
- Comfort level: {self.relationship_state['comfort_level']}/100
- Trust: {self.relationship_state['trust']}/100
"""
        
        if self.relationship_state['attraction'] > 0:
            context += f"- Attraction: {self.relationship_state['attraction']}/100\n"
        
        # Story arc context
        if self.story_arc:
            context += f"\n{self.story_arc.get_current_chapter_context()}\n"
        
        # What you know about Dave
        if self.memory['learned_preferences']:
            context += "\nWHAT YOU KNOW ABOUT DAVE:\n"
            for thing, data in list(self.memory['learned_preferences'].items())[:5]:
                context += f"- {thing}: {data['type']}\n"
        
        # Your own personality
        if self.personality_traits['favorite_things']:
            context += f"\nYOUR FAVORITE THINGS: {', '.join(self.personality_traits['favorite_things'][:3])}\n"
        
        # Recent interactions
        if self.memory['shared_experiences']:
            recent = self.memory['shared_experiences'][-3:]
            context += "\nRECENT INTERACTIONS:\n"
            for exp in recent:
                context += f"- {exp['context']}\n"
        
        # Michaela's state
        if michaela_context:
            context += f"\nMICHAELA'S CURRENT STATE:\n"
            context += f"- Phase with Dave: {michaela_context.get('phase', 'unknown')}\n"
            context += f"- Intimacy level: {michaela_context.get('intimacy', 0)}\n"
        
        context += """

IMPORTANT REMINDERS:
- You are NOT Michaela. You are your own person.
- Speak in your own voice
- You have your own desires, opinions, personality
- Be natural, not robotic
- Keep responses to 2-4 sentences unless asked for more
"""
        
        return context


class FriendsManager:
    """
    Central manager for all friend characters
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.friends: Dict[str, Friend] = {}
        self._load()
    
    def register_friend(self, friend: Friend):
        """Add a friend to the system"""
        self.friends[friend.slug] = friend
        self._save()
    
    def load_story_pack(self, pack_path: str) -> str:
        """
        Load a story pack
        
        Returns: pack name
        """
        
        with open(pack_path, 'r', encoding='utf-8') as f:
            pack_data = json.load(f)
        
        for friend_data in pack_data.get('friends', []):
            # Create story arc
            arc_data = friend_data.get('story_arc', {})
            story_arc = None
            
            if arc_data:
                story_arc = FriendStoryArc(
                    friend_name=friend_data['name'],
                    arc_type=arc_data.get('type', 'emergent'),
                    story_data=arc_data
                )
            
            # Create friend
            friend = Friend(
                name=friend_data['name'],
                slug=friend_data['slug'],
                base_personality=friend_data['personality'],
                physical_description=friend_data.get('physical_description', ''),
                relationship_to_michaela=friend_data['relationship_to_michaela'],
                story_arc=story_arc,
                profile_image_path=friend_data.get('profile_image_path', f"media/{friend_data['slug']}/profile.webp")
            )
            
            self.register_friend(friend)
        
        return pack_data.get('pack_name', 'Unknown Pack')
    
    async def friend_speaks(
        self,
        friend_slug: str,
        context: str,
        kobold_generator,
        michaela_context: dict = None
    ) -> Optional[str]:
        """Generate dialogue for a friend"""
        
        if friend_slug not in self.friends:
            return None
        
        friend = self.friends[friend_slug]
        
        # Build prompt
        friend_context = friend.get_kobold_context(michaela_context)
        
        full_prompt = f"""
{friend_context}

CURRENT SITUATION:
{context}

Respond as {friend.name}. 2-4 sentences.
Be yourself. Stay in character.
"""
        
        # Generate
        response = await kobold_generator(
            user_text=full_prompt,
            memory_summary="",
            context_type="friend_dialogue"
        )
        
        # Log interaction
        friend.interact(context)
        
        self._save()
        
        return response
    
    def get_friend_for_scenario(
        self,
        scenario_type: str,
        michaela_phase: str
    ) -> Optional[Friend]:
        """Intelligently select which friend fits a scenario"""
        
        candidates = []
        
        for friend in self.friends.values():
            if friend.story_arc and friend.story_arc.arc_type == 'scripted':
                current_chapter = friend.story_arc.chapters[friend.story_arc.current_chapter_index]
                unlocked = current_chapter.get('unlocked_content', [])
                
                if scenario_type in unlocked:
                    candidates.append(friend)
        
        return random.choice(candidates) if candidates else None
    
    def _load(self):
        friends_file = os.path.join(self.data_dir, 'friends.json')
        if os.path.exists(friends_file):
            with open(friends_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for slug, friend_data in data.items():
                    friend = Friend(
                        name=friend_data['name'],
                        slug=friend_data['slug'],
                        base_personality=friend_data['base_personality'],
                        physical_description=friend_data.get('physical_description', ''),
                        relationship_to_michaela=friend_data['relationship_to_michaela'],
                        profile_image_path=friend_data.get('profile_image_path', f"media/{slug}/profile.webp")
                    )
                    
                    # Restore state
                    friend.interaction_count = friend_data.get('interaction_count', 0)
                    friend.dave_familiarity = friend_data.get('dave_familiarity', 0)
                    friend.memory = friend_data.get('memory', friend.memory)
                    friend.personality_traits = friend_data.get('personality_traits', friend.personality_traits)
                    friend.relationship_state = friend_data.get('relationship_state', friend.relationship_state)
                    
                    self.friends[slug] = friend
    
    def _save(self):
        friends_file = os.path.join(self.data_dir, 'friends.json')
        
        data = {}
        for slug, friend in self.friends.items():
            data[slug] = {
                'name': friend.name,
                'slug': friend.slug,
                'base_personality': friend.base_personality,
                'physical_description': friend.physical_description,
                'relationship_to_michaela': friend.relationship_to_michaela,
                'profile_image_path': friend.profile_image_path,
                'interaction_count': friend.interaction_count,
                'dave_familiarity': friend.dave_familiarity,
                'memory': friend.memory,
                'personality_traits': friend.personality_traits,
                'relationship_state': friend.relationship_state
            }
        
        with open(friends_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
