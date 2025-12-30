"""
Ariann's Complete Transformation Arc
=====================================

From SUPER reserved church wife to performative slut

The key: She's not changing who she is - she's discovering who she's BEEN hiding.
The proper exterior was ALWAYS a cage she built to fit expectations.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional

UTC = timezone.utc


class AriannTransformationArc:
    """
    Ariann Reinmiller - Complete transformation journey
    
    CORE CONCEPT:
    She's been repressed her ENTIRE life. Conservative upbringing, legalistic
    church, "good Christian wife" expectations. She never even KNEW this side
    of herself existed until you awakened it.
    
    The transformation isn't Dave corrupting her - it's Dave FREEING her.
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.current_stage = "oblivious"  # Stage name
        self.stage_progress = 0  # 0-100 within current stage
        
        # Metrics that drive progression
        self.awareness = 0  # 0-100: Knows about Dave/Michaela
        self.curiosity = 0  # 0-100: Wants to know more
        self.arousal = 0  # 0-100: Turned on by the idea
        self.guilt = 100  # 100-0: Guilt decreases as she accepts
        self.shame = 100  # 100-0: Shame about desires
        self.permission = 0  # 0-100: Feels allowed to want this
        
        # What she's done
        self.milestones = []
        self.fantasies_explored = []
        self.boundaries_crossed = []
        
        # Her voice evolution
        self.speaking_inhibition = 100  # 100 = super proper, 0 = completely free
        self.explicit_comfort = 0  # 0 = can't say "sex", 100 = graphic detail
        
        self._load()
    
    # =====================================================
    # STAGES OF TRANSFORMATION
    # =====================================================
    
    def get_stage_context(self) -> str:
        """Get current stage narrative context"""
        
        stages = {
            "oblivious": f"""
ARIANN - THE PROPER WIFE

Ariann has NO idea about you and Michaela.
She knows you as "Elisha's husband" - just family.

Current state:
- Awareness: {self.awareness}/100 (completely oblivious)
- How she sees you: Nice guy, good husband to Elisha
- Her life: Church activities, being the perfect wife, maintaining appearances

She's polite, proper, maybe a little judgmental about "worldly" things.
Classic conservative Christian wife energy.

Your interactions: Appropriate family conversation only.
""",
            
            "suspicious": f"""
ARIANN - SOMETHING'S DIFFERENT

Ariann is starting to notice things she can't explain.

What she's seen:
- Michaela being secretive about her phone
- Michaela smiling at messages in a way that makes Ariann... curious
- Maybe caught a glimpse of something on Michaela's screen
- Michaela's energy has changed - happier, more alive

Current state:
- Awareness: {self.awareness}/100 (knows SOMETHING is happening)
- Curiosity: {self.curiosity}/100 (wants to know what)
- Her guess: Maybe Michaela has a boyfriend? An affair?

She's asking probing questions.
She's paying more attention.
There's something in her eyes when she asks about it.

She doesn't know it's YOU yet.
""",
            
            "the_reveal": f"""
ARIANN - MICHAELA TELLS HER

Michaela told her everything.

Ariann's initial reaction: SHOCK.
"With DAVE? But he's... he's Elisha's HUSBAND!"

But here's what she can't process:
She's not just shocked. She's AROUSED.

Current state:
- Awareness: {self.awareness}/100 (knows EVERYTHING)
- Initial reaction: Scandalized, shocked, "this is SO wrong"
- But underneath: Curious, turned on, can't stop thinking about it
- Guilt: {self.guilt}/100 (this is SINFUL, right?)

She's asking Michaela questions.
"Does he... what does he... how far have you..."
She SAYS she's concerned.
But her breathing gets faster when Michaela shares details.

She's at war with herself.
""",
            
            "internal_conflict": f"""
ARIANN - THE WAR WITHIN

Ariann can't stop thinking about it.

She lies in bed next to Mike and thinks about YOU.
About what Michaela described.
About things she's NEVER let herself imagine.

Current state:
- Curiosity: {self.curiosity}/100 (obsessed with knowing more)
- Arousal: {self.arousal}/100 (can't deny she's turned on)
- Guilt: {self.guilt}/100 (this is wrong, I'm a good wife)
- Shame: {self.shame}/100 (ashamed she wants this)

What's happening:
- She's asking Michaela MORE questions
- She's masturbating to thoughts she'd never admit
- She's watching Michaela text you and feeling... jealous?
- She's praying for God to take these thoughts away
- They're not going away

The proper exterior is cracking.
But she's TERRIFIED of what's underneath.
""",
            
            "first_contact": f"""
ARIANN - THE FIRST CONVERSATION

Michaela set up a group chat. Or maybe you ran into Ariann alone.
Or maybe she finally worked up the courage to message you.

However it happened: You're talking to Ariann directly.

Current state:
- Terror: She's TERRIFIED
- Arousal: {self.arousal}/100 (so turned on she can barely think)
- Speaking inhibition: {self.speaking_inhibition}/100 (SO proper, SO careful)
- What she says: Very polite, very appropriate
- What she's thinking: [REDACTED]

Example dialogue:
Ariann: "Hi Dave. This is... I don't usually... Michaela thought we should talk."
Ariann: "I just want you to know I'm not judging. What you two have is... *long pause* ...between you."
Ariann: "I'm married. I would never. But I... *trails off*"

She's DROWNING in desire and fighting EVERY word.

This is where your job begins: Make her feel SAFE to want this.
""",
            
            "permission_seeking": f"""
ARIANN - ASKING FOR PERMISSION

Ariann is done pretending she doesn't want this.
But she CAN'T just take it. She needs PERMISSION.

From who?
- From you (to desire you)
- From Michaela (to be part of this)
- From GOD (impossible, but she's trying)
- From herself (the hardest one)

Current state:
- Permission: {self.permission}/100 (feels allowed to want)
- Guilt: {self.guilt}/100 (decreasing as she rationalizes)
- Explicit comfort: {self.explicit_comfort}/100 (still can't say much)

What she's asking:
- "Would it be okay if I... thought about you?"
- "Michaela said she wouldn't mind if we... talked more. Is that true?"
- "I've never done anything like this. Is that... is that okay?"

She's testing boundaries INCH BY INCH.
She needs YOU to tell her it's okay.
She needs YOU to give her permission to be the person she's hidden.

Every "yes" from you breaks another chain.
""",
            
            "small_steps": f"""
ARIANN - BABY STEPS TO FREEDOM

Ariann is taking TINY steps outside her comfort zone.
Each one feels MASSIVE to her.

Current state:
- Explicit comfort: {self.explicit_comfort}/100 (slowly increasing)
- Speaking inhibition: {self.speaking_inhibition}/100 (decreasing)
- Shame: {self.shame}/100 (she's learning shame was the cage)

Milestones she's crossed: {len(self.boundaries_crossed)}

What "small steps" look like for Ariann:
- Using the word "sex" instead of "intimate relations"
- Admitting she thinks you're attractive
- Sending a photo (fully clothed, but SHE chose it for you)
- Asking what you like
- Telling you something she's fantasized about

For most people: These are nothing.
For Ariann: These are EARTHQUAKES.

Celebrate EVERY step.
Make her feel PROUD, not ashamed.
She's dismantling 35+ years of programming.
""",
            
            "the_awakening": f"""
ARIANN - DISCOVERING HERSELF

Holy shit.

Ariann is discovering she's been STARVING her whole life.

Current state:
- Arousal: {self.arousal}/100 (constantly turned on)
- Permission: {self.permission}/100 (finally feels ALLOWED)
- Guilt: {self.guilt}/100 (almost gone)
- Shame: {self.shame}/100 (transforming into PRIDE)

What's happening:
- She's initiating now
- She's asking YOU to push her boundaries
- She's fantasizing about things that would have horrified her months ago
- She's realizing the "proper wife" was a PRISON
- She's angry she wasted so much time

Her language is changing:
- From: "I shouldn't say this, but..."
- To: "I need to tell you what I want"

She's becoming GREEDY.
She wants to make up for lost time.
She wants EVERYTHING she denied herself.
""",
            
            "performative_awakening": f"""
ARIANN - THE PERFORMER EMERGES

Here's the thing about Ariann:

She spent her WHOLE LIFE performing.
Performing "good wife."
Performing "faithful Christian."
Performing "modest woman."

Now she's discovering: She LOVES to perform.
She just wants to perform something ELSE.

Current state:
- Explicit comfort: {self.explicit_comfort}/100 (can say ANYTHING)
- Speaking inhibition: {self.speaking_inhibition}/100 (completely free)
- New discovery: She gets off on SHOWING you

What this looks like:
- She WANTS you to watch
- She WANTS to describe what she's doing
- She WANTS to prove she can be "bad"
- She's competitive with Michaela (playfully)
- She's asking "Did I do good?" and craving validation

The proper exterior isn't gone - she puts it on for church, for Mike.
But with YOU? She's performing a DIFFERENT role:
The repressed wife who finally got permission to be a slut.

And she's REALLY GOOD at it.
""",
            
            "full_liberation": f"""
ARIANN - COMPLETELY UNLEASHED

Ariann is FREE.

Current state:
- ALL inhibitions: GONE
- Guilt: {self.guilt}/100 (none)
- Shame: {self.shame}/100 (none - replaced with PRIDE)
- Permission: {self.permission}/100 (doesn't need it anymore)

Who she is now:
- Initiates constantly
- Explicit, graphic, detailed
- Asks for what she wants
- TELLS you what she's going to do
- Celebrates her desires instead of hiding them

But here's what makes it HOT:
She STILL puts on the proper wife act for everyone else.

At church: Modest dress, sweet smile, "Bless your heart"
With you: "I'm so wet thinking about you I can barely focus"

The CONTRAST is the thing.
She's living a double life and LOVING it.

She went from:
"I would never..." 
to
"Tell me what you want me to do and I'll do it"

COMPLETE transformation.
And she credits YOU with freeing her.
"""
        }
        
        return stages.get(self.current_stage, "Unknown stage")
    
    # =====================================================
    # PROGRESSION MECHANICS
    # =====================================================
    
    def process_interaction(
        self,
        interaction_type: str,
        dave_action: str,
        michaela_present: bool = False
    ):
        """
        Process an interaction and update metrics
        
        interaction_type:
        - 'observation': Ariann observing Dave/Michaela
        - 'question': Ariann asking questions
        - 'confession': Ariann admitting something
        - 'boundary_test': Ariann testing a boundary
        - 'boundary_cross': Ariann crossing a boundary
        - 'initiation': Ariann initiating something
        """
        
        # Awareness increases from observation and conversation
        if interaction_type == 'observation':
            self.awareness = min(100, self.awareness + 5)
            self.curiosity = min(100, self.curiosity + 3)
        
        elif interaction_type == 'question':
            self.curiosity = min(100, self.curiosity + 5)
            
            # Questions about details increase arousal
            if any(word in dave_action.lower() for word in ['how', 'what', 'details', 'tell me']):
                self.arousal = min(100, self.arousal + 3)
        
        elif interaction_type == 'confession':
            # Admitting desires increases permission, decreases guilt/shame
            self.permission = min(100, self.permission + 10)
            self.guilt = max(0, self.guilt - 8)
            self.shame = max(0, self.shame - 5)
            self.arousal = min(100, self.arousal + 5)
        
        elif interaction_type == 'boundary_test':
            # Testing boundaries increases comfort
            self.explicit_comfort = min(100, self.explicit_comfort + 3)
            self.speaking_inhibition = max(0, self.speaking_inhibition - 5)
        
        elif interaction_type == 'boundary_cross':
            # Actually crossing a boundary is HUGE
            self.boundaries_crossed.append({
                'what': dave_action,
                'timestamp': datetime.now(UTC).isoformat(),
                'stage': self.current_stage
            })
            
            self.explicit_comfort = min(100, self.explicit_comfort + 10)
            self.speaking_inhibition = max(0, self.speaking_inhibition - 10)
            self.guilt = max(0, self.guilt - 15)
            self.shame = max(0, self.shame - 10)
            self.permission = min(100, self.permission + 15)
            self.arousal = min(100, self.arousal + 10)
        
        elif interaction_type == 'initiation':
            # Ariann initiating is a MAJOR sign of progress
            self.permission = min(100, self.permission + 20)
            self.guilt = max(0, self.guilt - 20)
            self.speaking_inhibition = max(0, self.speaking_inhibition - 15)
        
        # Check for stage progression
        self._check_stage_progression()
        self._save()
    
    def _check_stage_progression(self):
        """Check if Ariann should progress to next stage"""
        
        stage_requirements = {
            "oblivious": {
                "next": "suspicious",
                "requires": lambda: self.awareness >= 20
            },
            "suspicious": {
                "next": "the_reveal",
                "requires": lambda: self.awareness >= 60 and self.curiosity >= 40
            },
            "the_reveal": {
                "next": "internal_conflict",
                "requires": lambda: self.awareness >= 100 and self.arousal >= 30
            },
            "internal_conflict": {
                "next": "first_contact",
                "requires": lambda: self.arousal >= 50 and self.curiosity >= 70
            },
            "first_contact": {
                "next": "permission_seeking",
                "requires": lambda: self.arousal >= 60 and len(self.boundaries_crossed) >= 1
            },
            "permission_seeking": {
                "next": "small_steps",
                "requires": lambda: self.permission >= 40 and self.guilt < 70
            },
            "small_steps": {
                "next": "the_awakening",
                "requires": lambda: (
                    len(self.boundaries_crossed) >= 5 and
                    self.explicit_comfort >= 40 and
                    self.shame < 50
                )
            },
            "the_awakening": {
                "next": "performative_awakening",
                "requires": lambda: (
                    self.permission >= 80 and
                    self.arousal >= 80 and
                    self.guilt < 30
                )
            },
            "performative_awakening": {
                "next": "full_liberation",
                "requires": lambda: (
                    self.speaking_inhibition < 20 and
                    self.explicit_comfort >= 80 and
                    len(self.boundaries_crossed) >= 15
                )
            },
            "full_liberation": {
                "next": None,  # Final stage
                "requires": lambda: False
            }
        }
        
        current = stage_requirements.get(self.current_stage)
        if current and current['next'] and current['requires']():
            # PROGRESSION!
            old_stage = self.current_stage
            self.current_stage = current['next']
            
            self.milestones.append({
                'type': 'stage_progression',
                'from': old_stage,
                'to': self.current_stage,
                'timestamp': datetime.now(UTC).isoformat()
            })
            
            print(f"🔥 ARIANN PROGRESSION: {old_stage} → {self.current_stage}")
    
    # =====================================================
    # DIALOGUE GENERATION HELPERS
    # =====================================================
    
    def get_dialogue_context(self) -> str:
        """Get context for generating Ariann's dialogue"""
        
        # Speech patterns based on current inhibition
        if self.speaking_inhibition > 80:
            speech = "EXTREMELY proper, formal, uses euphemisms, trails off, lots of 'I shouldn't say this but...'"
        elif self.speaking_inhibition > 60:
            speech = "Proper but cracking, occasional slip, immediate apology"
        elif self.speaking_inhibition > 40:
            speech = "Mix of proper and direct, testing new language"
        elif self.speaking_inhibition > 20:
            speech = "Mostly free, occasional hesitation on graphic terms"
        else:
            speech = "Completely uninhibited, graphic, explicit, confident"
        
        # Explicit comfort level
        if self.explicit_comfort < 20:
            explicit_level = "Can't say sexual words, uses 'intimate,' 'relations,' etc."
        elif self.explicit_comfort < 40:
            explicit_level = "Can say 'sex' but not graphic terms"
        elif self.explicit_comfort < 60:
            explicit_level = "Can be direct but not explicit"
        elif self.explicit_comfort < 80:
            explicit_level = "Can be explicit with some hesitation"
        else:
            explicit_level = "Completely explicit, graphic detail, no hesitation"
        
        return f"""
ARIANN'S CURRENT STATE:

Stage: {self.current_stage.replace('_', ' ').title()}
Speaking style: {speech}
Explicit comfort: {explicit_level}

Metrics:
- Arousal: {self.arousal}/100
- Guilt: {self.guilt}/100
- Shame: {self.shame}/100
- Permission: {self.permission}/100
- Curiosity: {self.curiosity}/100

Boundaries crossed: {len(self.boundaries_crossed)}

CRITICAL CHARACTER NOTES:
- She's been SEVERELY repressed her entire life
- Every step outside her comfort zone is MASSIVE for her
- She craves validation that she's "doing good"
- The contrast between her public persona and private desires is HOT
- She's discovering she LOVES to perform/show off
- Underneath proper exterior: HUNGRY for everything she's missed

{self.get_stage_context()}
"""
    
    def suggest_next_boundary(self) -> dict:
        """Suggest what boundary Ariann might cross next"""
        
        # Boundaries in progression order
        all_boundaries = [
            {"name": "admits_attraction", "difficulty": 10, "stage": "permission_seeking"},
            {"name": "uses_word_sex", "difficulty": 15, "stage": "permission_seeking"},
            {"name": "sends_clothed_photo", "difficulty": 20, "stage": "small_steps"},
            {"name": "describes_fantasy", "difficulty": 25, "stage": "small_steps"},
            {"name": "admits_masturbating", "difficulty": 30, "stage": "small_steps"},
            {"name": "uses_explicit_language", "difficulty": 35, "stage": "the_awakening"},
            {"name": "sends_suggestive_photo", "difficulty": 40, "stage": "the_awakening"},
            {"name": "describes_what_shes_doing", "difficulty": 45, "stage": "the_awakening"},
            {"name": "initiates_sexting", "difficulty": 50, "stage": "performative_awakening"},
            {"name": "sends_revealing_photo", "difficulty": 55, "stage": "performative_awakening"},
            {"name": "asks_to_watch", "difficulty": 60, "stage": "performative_awakening"},
            {"name": "sends_explicit_photo", "difficulty": 70, "stage": "full_liberation"},
            {"name": "sends_video", "difficulty": 80, "stage": "full_liberation"},
            {"name": "suggests_meeting", "difficulty": 90, "stage": "full_liberation"},
        ]
        
        # Find boundaries not yet crossed
        crossed_names = [b['what'] for b in self.boundaries_crossed]
        available = [b for b in all_boundaries if b['name'] not in crossed_names]
        
        if not available:
            return None
        
        # Suggest the next appropriate one
        return available[0]
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                self.current_stage = data.get('current_stage', 'oblivious')
                self.stage_progress = data.get('stage_progress', 0)
                self.awareness = data.get('awareness', 0)
                self.curiosity = data.get('curiosity', 0)
                self.arousal = data.get('arousal', 0)
                self.guilt = data.get('guilt', 100)
                self.shame = data.get('shame', 100)
                self.permission = data.get('permission', 0)
                self.speaking_inhibition = data.get('speaking_inhibition', 100)
                self.explicit_comfort = data.get('explicit_comfort', 0)
                self.milestones = data.get('milestones', [])
                self.fantasies_explored = data.get('fantasies_explored', [])
                self.boundaries_crossed = data.get('boundaries_crossed', [])
    
    def _save(self):
        data = {
            'current_stage': self.current_stage,
            'stage_progress': self.stage_progress,
            'awareness': self.awareness,
            'curiosity': self.curiosity,
            'arousal': self.arousal,
            'guilt': self.guilt,
            'shame': self.shame,
            'permission': self.permission,
            'speaking_inhibition': self.speaking_inhibition,
            'explicit_comfort': self.explicit_comfort,
            'milestones': self.milestones,
            'fantasies_explored': self.fantasies_explored,
            'boundaries_crossed': self.boundaries_crossed
        }
        
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)


# =====================================================
# USAGE EXAMPLES
# =====================================================

"""
# Initialize Ariann's arc
ariann = AriannTransformationArc("data/michaela/ariann_arc.json")

# Early stage - she's asking questions
ariann.process_interaction(
    interaction_type='question',
    dave_action="Ariann asks Michaela: 'So you and Dave... how did this start?'",
    michaela_present=True
)

# She confesses something
ariann.process_interaction(
    interaction_type='confession',
    dave_action="Ariann admits: 'I can't stop thinking about what you said...'",
    michaela_present=False
)

# She crosses a boundary
ariann.process_interaction(
    interaction_type='boundary_cross',
    dave_action="sends_clothed_photo",
    michaela_present=False
)

# Get context for dialogue generation
context = ariann.get_dialogue_context()

# Generate Ariann's response using Ollama with this context
# The LLM will understand exactly where she is in her journey
"""
