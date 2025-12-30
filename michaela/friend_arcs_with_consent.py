"""
Complete Friend Story Arcs with Independent Development
========================================================

Friends have their own:
- Personalities and agency
- Story progression
- Desires and boundaries
- Memory and growth

Special focus on Elisha arc with consent/enthusiasm mechanics.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional

UTC = timezone.utc


# =====================================================
# ELISHA ARC - Sister-in-Law Taboo (WITH CONSENT)
# =====================================================

class ElishaStoryArc:
    """
    Elisha (Michaela's sister, Dave's sister-in-law) story arc
    
    CRITICAL: This arc requires enthusiastic consent from all parties
    The story progresses only when Elisha is actively on board
    """
    
    def __init__(self):
        self.current_chapter = "family_normal"
        self.intimacy_with_dave = 0  # 0-100
        self.awareness_of_dynamic = 0  # 0-100 (knows about Dave/Michaela)
        self.her_interest = 0  # 0-100 (her actual desire)
        self.enthusiasm = 0  # 0-100 (how excited she is about possibility)
        self.boundaries_established = False
        
        self.michaela_knows_elisha_interest = False
        self.dave_knows_elisha_interest = False
        
        # Her own agency
        self.elisha_initiated_conversations = []
        self.her_desires: List[str] = []
        self.her_boundaries: List[str] = []
        self.her_fantasies: List[str] = []
    
    def get_chapter_context(self) -> str:
        """Get current chapter context"""
        
        chapters = {
            "family_normal": f"""
ELISHA - FAMILY DYNAMICS

Elisha is Michaela's sister and your sister-in-law.
You see her at family events. Things are normal, appropriate.

Current state:
- Your intimacy with Elisha: {self.intimacy_with_dave}/100 (family baseline)
- Elisha's awareness of you/Michaela: {self.awareness_of_dynamic}/100
- Elisha's interest: {self.her_interest}/100 (currently platonic)

Stay appropriate. She's family.
""",
            
            "subtle_tension": f"""
ELISHA - SUBTLE TENSION

Something's shifted. Small moments at family gatherings.
Eye contact that lasts a beat too long.
Conversations that feel... charged.

Elisha's state:
- Awareness of your dynamic with Michaela: {self.awareness_of_dynamic}/100
- Her interest level: {self.her_interest}/100
- Her enthusiasm: {self.enthusiasm}/100

She hasn't said anything. Neither have you.
But there's something there.

Michaela has noticed the energy between you two.
""",
            
            "michaela_explores": f"""
ELISHA - MICHAELA'S CURIOSITY

Michaela brought up Elisha in conversation.
"I've noticed the way she looks at you..."
"Have you ever thought about her?"

Michaela is... curious. Maybe even turned on by the idea.

Elisha's state:
- Interest level: {self.her_interest}/100
- Awareness that Michaela might know: {self.awareness_of_dynamic}/100
- Enthusiasm: {self.enthusiasm}/100

Michaela is exploring this fantasy with you.
Elisha doesn't know... yet.
""",
            
            "elisha_discovers": f"""
ELISHA - THE DISCOVERY

Elisha found out about you and Michaela.

Her reaction: NOT judgment. Curiosity. Maybe even... jealousy?

"So you and my sister have this... thing?"
"And she's okay with it?"
"That's... actually kind of hot."

She's processing. She's asking questions.
She's more interested than shocked.

Elisha's state:
- Interest: {self.her_interest}/100
- Enthusiasm: {self.enthusiasm}/100
- Her own desires emerging: {', '.join(self.her_desires[:3]) if self.her_desires else 'None yet'}

She's single. She's curious. She's thinking about it.
""",
            
            "elisha_initiates": f"""
ELISHA - SHE MAKES THE FIRST MOVE

Elisha texted you.
Not about family stuff. Not small talk.

She wanted to talk about what she learned.
She asked if it was weird that she found it hot.
She asked if you'd thought about her that way.

She's INITIATING. She has agency here.
She WANTS to explore this.

Elisha's state:
- Interest: {self.her_interest}/100 (HIGH)
- Enthusiasm: {self.enthusiasm}/100
- Her desires: {', '.join(self.her_desires[:5])}
- Her boundaries: {', '.join(self.her_boundaries)}

She's setting the pace. She's choosing this.
Michaela knows. Michaela is excited about it.

This only happens because SHE wants it.
""",
            
            "three_way_dynamic": f"""
ELISHA - THE NEW DYNAMIC

This is actually happening.

Elisha is part of this now. By HER choice.
She talks to you. She talks to Michaela.
Sometimes all three of you talk together.

The dynamic:
- You + Michaela: {100}/100 (established)
- You + Elisha: {self.intimacy_with_dave}/100 (developing)
- Michaela + Elisha: Sisters who share... unconventionally

Elisha's agency:
- SHE decides when to engage
- SHE sets boundaries
- SHE initiates when she wants
- SHE can pull back anytime

Her current state:
- Enthusiasm: {self.enthusiasm}/100
- Active participation: {len(self.elisha_initiated_conversations)} times
- Her desires: {', '.join(self.her_desires)}

This works because everyone wants it.
Especially Elisha.
""",
            
            "family_gatherings_charged": f"""
ELISHA - FAMILY EVENTS WITH CONTEXT

Family gatherings are... different now.

You all know. Sebastian knows.
But everyone else at the table doesn't.

Elisha across the table, catching your eye.
Michaela noticing, smiling to herself.
The shared secret.

After everyone leaves:
Sometimes Elisha stays. Sometimes you all talk.
Sometimes it's more than talk.

But always: She's enthusiastic. She's choosing this.

Boundaries are clear:
{chr(10).join('- ' + b for b in self.her_boundaries) if self.her_boundaries else '- Still being established'}

This is wild. This is hot. This is consensual.
"""
        }
        
        return chapters.get(self.current_chapter, "")
    
    def elisha_expresses_interest(self, interest_type: str):
        """
        Elisha actively expresses interest - HER agency
        
        Examples:
        - "curious_about_you_michaela"
        - "wants_to_talk"
        - "finds_it_hot"
        - "wants_to_explore"
        - "has_her_own_desires"
        """
        
        self.her_interest = min(100, self.her_interest + 15)
        self.enthusiasm = min(100, self.enthusiasm + 10)
        
        # Record that SHE initiated
        self.elisha_initiated_conversations.append({
            'timestamp': datetime.now(UTC).isoformat(),
            'type': interest_type
        })
    
    def elisha_sets_boundary(self, boundary: str):
        """Elisha establishes a boundary - HER control"""
        
        if boundary not in self.her_boundaries:
            self.her_boundaries.append(boundary)
            self.boundaries_established = True
    
    def elisha_shares_desire(self, desire: str):
        """Elisha shares what SHE wants"""
        
        if desire not in self.her_desires:
            self.her_desires.append(desire)
    
    def can_progress_to_next_chapter(self) -> bool:
        """
        Can only progress when Elisha is enthusiastic
        
        This ensures consent at every stage
        """
        
        progression = {
            "family_normal": self.her_interest >= 20,
            "subtle_tension": self.awareness_of_dynamic >= 40,
            "michaela_explores": self.her_interest >= 50,
            "elisha_discovers": self.enthusiasm >= 60,
            "elisha_initiates": (
                self.enthusiasm >= 75 and
                len(self.elisha_initiated_conversations) >= 3 and
                self.boundaries_established
            ),
            "three_way_dynamic": (
                self.enthusiasm >= 85 and
                len(self.her_desires) >= 3
            )
        }
        
        return progression.get(self.current_chapter, False)


# =====================================================
# ARIANN ARC - The Curious Best Friend
# =====================================================

class AriannStoryArc:
    """
    Ariann (Michaela's best friend) discovers the secret and gets curious
    """
    
    def __init__(self):
        self.current_chapter = "oblivious"
        self.suspicion_level = 0  # 0-100
        self.comfort_with_dynamic = 0  # 0-100
        self.her_interest = 0  # 0-100
        self.dave_familiarity = 0  # 0-100
        
        self.knows_about_dynamic = False
        self.michaela_told_her = False
        
        # Her personality
        self.personality_traits = [
            "open-minded",
            "curious",
            "non-judgmental",
            "playful"
        ]
    
    def get_chapter_context(self) -> str:
        """Get current chapter context"""
        
        chapters = {
            "oblivious": """
ARIANN - MICHAELA'S BEST FRIEND

Ariann has no idea what's going on between you and Michaela.
She knows you as "Elisha's husband" - family connection.

Your interactions with Ariann: Polite, appropriate.
Her awareness: Zero.

Keep it normal.
""",
            
            "suspicious": f"""
ARIANN - SOMETHING'S UP

Ariann is starting to notice things.

She saw a text notification on Michaela's phone.
She noticed Michaela being cagey about who she's texting.
At girls' night: "You've been different lately. Happy. What's going on?"

Her suspicion: {self.suspicion_level}/100
She doesn't know yet. But she's curious.

Michaela is deciding whether to tell her.
""",
            
            "the_reveal": f"""
ARIANN - MICHAELA TELLS HER

Michaela told Ariann about you two.

Ariann's reaction: Shock → Curiosity → Acceptance

"Wait, WHAT?"
"And Sebastian knows?"
"Holy shit, Michaela..."
"Okay but like... tell me everything."

Her comfort: {self.comfort_with_dynamic}/100
She's processing. Asking questions. Not judging.

She's actually kind of impressed.
""",
            
            "curiosity_grows": f"""
ARIANN - GETTING CURIOUS

Ariann keeps bringing it up.

"So what's he like?"
"Do you have pictures?" (playful, testing boundaries)
"I can't believe you're doing this. It's actually kind of hot."

Her interest: {self.her_interest}/100
Your familiarity: {self.dave_familiarity}/100

She's asking about YOU now, not just the dynamic.
Michaela notices. Michaela is... okay with it?
""",
            
            "first_interactions": f"""
ARIANN - TALKING TO YOU

Ariann started talking to you directly.

Started as curiosity. "Michaela's told me about you..."
But now she's flirting. Tentatively. Testing.

Her interest: {self.her_interest}/100
Your familiarity: {self.dave_familiarity}/100

She's single. She's intrigued.
She wants to understand the appeal.

Michaela gave her permission to explore.
""",
            
            "part_of_it": f"""
ARIANN - IN THE MIX

Ariann is part of this now.

Group chats sometimes. Just the three of you.
She sends photos "for feedback".
The energy is playful, sexy, fun.

She has her own dynamic with you:
- Playful teasing
- Genuine curiosity
- Exploration (with Michaela's blessing)

This works because:
- Michaela approves
- Ariann is upfront about her interest
- Everyone communicates

The best friend is in on the secret. And loving it.
"""
        }
        
        return chapters.get(self.current_chapter, "")


# =====================================================
# HANNAH ARC - The Flirty Colleague
# =====================================================

class HannahStoryArc:
    """
    Hannah (Dave's colleague) starts flirting, Michaela gets competitive
    """
    
    def __init__(self):
        self.current_chapter = "professional"
        self.flirtation_level = 0  # 0-100
        self.michaela_jealousy = 0  # 0-100
        self.competition_active = False
        
        # Hannah's personality
        self.hannah_traits = [
            "confident",
            "flirty",
            "ambitious",
            "attractive"
        ]
    
    def get_chapter_context(self) -> str:
        """Get current chapter context"""
        
        chapters = {
            "professional": """
HANNAH - WORK COLLEAGUE

Hannah is a colleague. Professional relationship.
Friendly but appropriate.

Nothing's happening. Just work.
""",
            
            "flirtation_starts": f"""
HANNAH - SHE'S FLIRTING

Hannah's been more... friendly lately.

Compliments that feel personal.
Finding excuses to talk to you.
Lingering touches (hand on arm, etc.)

Her flirtation: {self.flirtation_level}/100

You mention it to Michaela.
Michaela's reaction: Curious. Maybe a little jealous?
""",
            
            "michaela_competitive": f"""
HANNAH - MICHAELA'S COMPETITION MODE

Michaela heard about Hannah flirting.

Her response? Not upset. COMPETITIVE.

"What does she look like?"
"Bet I can send you better content than she could ever give you."
"Tell me when she flirts. I'll remind you who you really want."

Michaela's jealousy: {self.michaela_jealousy}/100 (aroused jealousy)

The competition is ON.
When Hannah flirts → Michaela escalates.
""",
            
            "playing_both": f"""
HANNAH - PLAYING WITH TENSION

You're in an interesting position.

Hannah flirts at work.
You tell Michaela about it.
Michaela sends you something FILTHY in response.

Hannah doesn't know she's competing with Michaela.
But Michaela knows. And she's winning.

You're enjoying both dynamics:
- Hannah's attention at work
- Michaela's competitive fire

Michaela gets off on "beating" Hannah.
"""
        }
        
        return chapters.get(self.current_chapter, "")


# =====================================================
# FRIEND MANAGER - Independent Development
# =====================================================

class IndependentFriendSystem:
    """
    Manages friends as independent characters with agency
    
    Friends can:
    - Initiate conversations
    - Have their own desires
    - Set boundaries
    - Grow independently
    - Interact with Dave OR Michaela separately
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        
        self.elisha = ElishaStoryArc()
        self.ariann = AriannStoryArc()
        self.hannah = HannahStoryArc()
        
        # Track who's active
        self.active_friends: List[str] = []
        
        self._load()
    
    def friend_initiates_contact(
        self,
        friend_name: str,
        message_type: str,
        context: str = None
    ):
        """
        A friend reaches out on THEIR initiative
        
        This preserves their agency - they're not just responding
        """
        
        if friend_name == "elisha":
            self.elisha.elisha_expresses_interest(message_type)
        
        # Record initiative
        print(f"[FRIEND] {friend_name} initiated: {message_type}")
    
    def get_friend_context(self, friend_name: str) -> str:
        """Get current story context for a friend"""
        
        if friend_name == "elisha":
            return self.elisha.get_chapter_context()
        elif friend_name == "ariann":
            return self.ariann.get_chapter_context()
        elif friend_name == "hannah":
            return self.hannah.get_chapter_context()
        
        return ""
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Load friend states
                # (Implementation for loading each friend's state)
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'elisha': {
                    'chapter': self.elisha.current_chapter,
                    'intimacy': self.elisha.intimacy_with_dave,
                    'interest': self.elisha.her_interest,
                    'enthusiasm': self.elisha.enthusiasm,
                    'desires': self.elisha.her_desires,
                    'boundaries': self.elisha.her_boundaries
                },
                'ariann': {
                    'chapter': self.ariann.current_chapter,
                    'suspicion': self.ariann.suspicion_level,
                    'comfort': self.ariann.comfort_with_dynamic
                },
                'hannah': {
                    'chapter': self.hannah.current_chapter,
                    'flirtation': self.hannah.flirtation_level,
                    'michaela_jealousy': self.hannah.michaela_jealousy
                }
            }, f, indent=2)


# =====================================================
# USAGE EXAMPLES
# =====================================================

"""
# In your bot:

friends = IndependentFriendSystem('data/michaela/friends_v2.json')

# Elisha expresses interest (HER agency)
friends.friend_initiates_contact(
    friend_name="elisha",
    message_type="curious_about_you_michaela",
    context="After family dinner"
)

# Elisha sets boundaries
friends.elisha.elisha_sets_boundary("Nothing physical without Michaela present")
friends.elisha.elisha_shares_desire("Wants to see photos")

# Check if can progress
if friends.elisha.can_progress_to_next_chapter():
    friends.elisha.current_chapter = "three_way_dynamic"

# Get context for conversation
elisha_context = friends.get_friend_context("elisha")
# Add to prompt when Elisha is in scene

# Key principle: THEY initiate, THEY set pace, THEY establish boundaries
"""
