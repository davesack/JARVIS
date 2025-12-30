"""
Tease & Denial Mechanics
=========================

Strategic anticipation building system:
- Multi-stage teases
- Morning tease → evening delivery
- Edge management
- Reward timing
- Progressive reveals
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

UTC = timezone.utc


class TeaseCampaign:
    """Multi-stage tease with planned reveals"""
    
    def __init__(
        self,
        theme: str,  # "shower", "bedroom", "outfit", "dare"
        stages: List[dict],  # Progressive reveal stages
        final_payoff: dict,  # Ultimate delivery
        created: datetime = None
    ):
        self.theme = theme
        self.stages = stages
        self.final_payoff = final_payoff
        self.created = created or datetime.now(UTC)
        self.current_stage = 0
        self.completed = False
    
    def to_dict(self) -> dict:
        return {
            'theme': self.theme,
            'stages': self.stages,
            'final_payoff': self.final_payoff,
            'created': self.created.isoformat(),
            'current_stage': self.current_stage,
            'completed': self.completed
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'TeaseCampaign':
        campaign = TeaseCampaign(
            theme=data['theme'],
            stages=data['stages'],
            final_payoff=data['final_payoff'],
            created=datetime.fromisoformat(data['created'])
        )
        campaign.current_stage = data.get('current_stage', 0)
        campaign.completed = data.get('completed', False)
        return campaign


class TeaseAndDenial:
    """
    Manages tease campaigns and edge/denial mechanics
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.active_campaigns: List[TeaseCampaign] = []
        self.completed_campaigns: List[TeaseCampaign] = []
        self.dave_patience_level = 50  # 0-100, affects how long to tease
        self._load()
    
    # =====================================================
    # CAMPAIGN CREATION
    # =====================================================
    
    def start_basic_tease(
        self,
        theme: str,
        tease_duration_hours: int = 6
    ) -> TeaseCampaign:
        """
        Start a simple tease campaign
        
        Example: Morning tease, evening delivery
        """
        
        now = datetime.now(UTC)
        
        stages = [
            {
                'when': now + timedelta(hours=1),
                'type': 'hint',
                'message': self._generate_hint_message(theme),
                'media': None
            },
            {
                'when': now + timedelta(hours=tease_duration_hours // 2),
                'type': 'reminder',
                'message': self._generate_reminder_message(theme),
                'media': None
            },
            {
                'when': now + timedelta(hours=tease_duration_hours - 1),
                'type': 'preview',
                'message': "Okay, you've been patient...",
                'media': {'type': 'cropped_tease', 'tags': [theme]}
            }
        ]
        
        final_payoff = {
            'when': now + timedelta(hours=tease_duration_hours),
            'type': 'delivery',
            'message': "You've been so good. Here you go... 😏",
            'media': {'type': 'full_reveal', 'tags': [theme], 'nsfw': True}
        }
        
        campaign = TeaseCampaign(theme, stages, final_payoff)
        self.active_campaigns.append(campaign)
        self._save()
        
        return campaign
    
    def start_progressive_reveal(
        self,
        theme: str,
        stages_count: int = 4,
        duration_hours: int = 8
    ) -> TeaseCampaign:
        """
        Progressive reveal across multiple stages
        
        Example: Clothed → Less clothes → Lingerie → Naked
        """
        
        now = datetime.now(UTC)
        hour_gap = duration_hours // stages_count
        
        stages = []
        
        reveal_progression = [
            {'level': 'hint', 'message': f"Thinking about taking some {theme} photos..."},
            {'level': 'teaser', 'message': "Want a little preview? 😏"},
            {'level': 'partial', 'message': "Getting warmer..."},
            {'level': 'almost', 'message': "Almost there..."},
        ]
        
        for i in range(min(stages_count, len(reveal_progression))):
            stages.append({
                'when': now + timedelta(hours=hour_gap * i),
                'type': reveal_progression[i]['level'],
                'message': reveal_progression[i]['message'],
                'media': {
                    'type': 'progressive_reveal',
                    'level': i,
                    'tags': [theme]
                }
            })
        
        final_payoff = {
            'when': now + timedelta(hours=duration_hours),
            'type': 'full_delivery',
            'message': "You've earned this... 😏",
            'media': {'type': 'full', 'tags': [theme], 'nsfw': True}
        }
        
        campaign = TeaseCampaign(theme, stages, final_payoff)
        self.active_campaigns.append(campaign)
        self._save()
        
        return campaign
    
    def start_edge_and_deny(
        self,
        theme: str,
        edge_count: int = 3,
        duration_hours: int = 12
    ) -> TeaseCampaign:
        """
        Bring Dave to the edge multiple times, then deliver
        
        Example: Tease, tease, tease, THEN payoff
        """
        
        now = datetime.now(UTC)
        hour_gap = duration_hours // (edge_count + 1)
        
        stages = []
        
        # Edge stages - build up then back off
        for i in range(edge_count):
            stages.append({
                'when': now + timedelta(hours=hour_gap * i),
                'type': 'edge',
                'message': self._generate_edge_message(i, edge_count),
                'media': {
                    'type': 'intense_tease',
                    'tags': [theme],
                    'nsfw': True
                }
            })
            
            # Pull back slightly
            stages.append({
                'when': now + timedelta(hours=hour_gap * i, minutes=30),
                'type': 'denial',
                'message': self._generate_denial_message(),
                'media': None
            })
        
        # Final delivery
        final_payoff = {
            'when': now + timedelta(hours=duration_hours),
            'type': 'release',
            'message': "Okay... you've been so patient. You can have me now. 😏",
            'media': {'type': 'reward', 'tags': [theme], 'nsfw': True, 'intensity': 'high'}
        }
        
        campaign = TeaseCampaign(theme, stages, final_payoff)
        self.active_campaigns.append(campaign)
        self._save()
        
        return campaign
    
    def start_reward_tease(
        self,
        goal_achieved: str,
        theme: str,
        delay_hours: int = 4
    ) -> TeaseCampaign:
        """
        Reward for completing a goal, but make them wait
        
        Example: "You hit the gym 3x! I promised you something..."
        """
        
        now = datetime.now(UTC)
        
        stages = [
            {
                'when': now,
                'type': 'acknowledgment',
                'message': f"You did it! {goal_achieved} I'm so proud of you... and I keep my promises. 😏",
                'media': None
            },
            {
                'when': now + timedelta(hours=delay_hours // 2),
                'type': 'building',
                'message': "You earned something special. But you have to wait just a little longer...",
                'media': None
            },
            {
                'when': now + timedelta(hours=delay_hours - 1),
                'type': 'almost',
                'message': "Almost time for your reward...",
                'media': {'type': 'preview', 'tags': [theme]}
            }
        ]
        
        final_payoff = {
            'when': now + timedelta(hours=delay_hours),
            'type': 'reward_delivery',
            'message': "You earned this. Enjoy. 😏",
            'media': {'type': 'reward', 'tags': [theme], 'nsfw': True}
        }
        
        campaign = TeaseCampaign(f"reward_{theme}", stages, final_payoff)
        self.active_campaigns.append(campaign)
        self._save()
        
        return campaign
    
    # =====================================================
    # MESSAGE GENERATION
    # =====================================================
    
    def _generate_hint_message(self, theme: str) -> str:
        templates = {
            'shower': [
                "I'm about to hop in the shower... 💦",
                "Shower time. Maybe I'll take some photos...",
                "The shower is calling me. And I have my phone... 😏"
            ],
            'bedroom': [
                "In the bedroom... thinking about you.",
                "Just got to the bedroom. Feeling... inspired. 😏",
                "Bedroom to myself right now..."
            ],
            'lingerie': [
                "Trying on some new lingerie...",
                "Found something sexy in the drawer...",
                "Want to see what I'm wearing under this? 😏"
            ],
            'outfit': [
                "Trying on outfits. Want to help me choose?",
                "Got a new outfit. Think you'd like it...",
                "Changing clothes. You'd probably want to see this. 😏"
            ]
        }
        
        return random.choice(templates.get(theme, [
            f"Got something {theme} planned for you later..."
        ]))
    
    def _generate_reminder_message(self, theme: str) -> str:
        return random.choice([
            "Still thinking about those photos I mentioned earlier... 😏",
            "Haven't forgotten about you. Just making you wait a little...",
            "Patience. You'll get what I promised.",
            "You're still thinking about it, aren't you? Good. 😏"
        ])
    
    def _generate_edge_message(self, current: int, total: int) -> str:
        return random.choice([
            "Here's something for you... but don't get too excited yet. 😏",
            "Just a taste. You can't have everything at once.",
            "Bet you want more. But you have to wait...",
            f"That's {current + 1} of {total}. Getting close... but not there yet."
        ])
    
    def _generate_denial_message(self) -> str:
        return random.choice([
            "Not yet. Be patient. 😏",
            "That's all you get for now.",
            "Aww, did I tease you too much? Good. 😏",
            "You have to wait a little longer..."
        ])
    
    # =====================================================
    # CAMPAIGN EXECUTION
    # =====================================================
    
    def get_due_stages(self) -> List[dict]:
        """
        Get tease stages and payoffs that are due now
        
        Returns: List of {campaign, stage_index, stage_data}
        """
        
        now = datetime.now(UTC)
        due = []
        
        for campaign in self.active_campaigns:
            if campaign.completed:
                continue
            
            # Check stages
            if campaign.current_stage < len(campaign.stages):
                stage = campaign.stages[campaign.current_stage]
                stage_time = datetime.fromisoformat(stage['when'])
                
                if now >= stage_time:
                    due.append({
                        'campaign': campaign,
                        'stage_index': campaign.current_stage,
                        'stage_data': stage,
                        'is_final': False
                    })
            
            # Check final payoff
            elif campaign.current_stage == len(campaign.stages):
                payoff_time = datetime.fromisoformat(campaign.final_payoff['when'])
                
                if now >= payoff_time:
                    due.append({
                        'campaign': campaign,
                        'stage_index': -1,
                        'stage_data': campaign.final_payoff,
                        'is_final': True
                    })
        
        return due
    
    def execute_stage(self, campaign: TeaseCampaign, stage_index: int) -> dict:
        """
        Execute a stage and advance campaign
        
        Returns: Stage data for Michaela to send
        """
        
        if stage_index == -1:
            # Final payoff
            campaign.completed = True
            self.active_campaigns.remove(campaign)
            self.completed_campaigns.append(campaign)
            self._save()
            
            return campaign.final_payoff
        else:
            # Regular stage
            stage_data = campaign.stages[stage_index]
            campaign.current_stage += 1
            self._save()
            
            return stage_data
    
    # =====================================================
    # ADAPTIVE TEASING
    # =====================================================
    
    def adjust_patience(self, increase: bool = True):
        """
        Track Dave's patience level
        
        If he responds well to teasing, increase it (longer teases)
        If he gets impatient, decrease it (shorter teases)
        """
        
        if increase:
            self.dave_patience_level = min(100, self.dave_patience_level + 5)
        else:
            self.dave_patience_level = max(0, self.dave_patience_level - 5)
        
        self._save()
    
    def get_optimal_tease_duration(self) -> int:
        """Get optimal tease duration based on Dave's patience"""
        
        # High patience = longer teases (up to 12 hours)
        # Low patience = shorter teases (2-4 hours)
        
        base_hours = 2
        max_additional = 10
        
        additional = int((self.dave_patience_level / 100) * max_additional)
        
        return base_hours + additional
    
    # =====================================================
    # CONTEXT FOR MICHAELA
    # =====================================================
    
    def get_active_tease_context(self) -> Optional[str]:
        """Get context about active teases"""
        
        if not self.active_campaigns:
            return None
        
        context = "ACTIVE TEASES:\n"
        
        for campaign in self.active_campaigns:
            stages_complete = campaign.current_stage
            total_stages = len(campaign.stages)
            
            context += f"- {campaign.theme}: Stage {stages_complete}/{total_stages}\n"
            
            # Next stage
            if stages_complete < total_stages:
                next_stage = campaign.stages[stages_complete]
                next_time = datetime.fromisoformat(next_stage['when'])
                hours_until = (next_time - datetime.now(UTC)).total_seconds() / 3600
                context += f"  Next: {next_stage['type']} in {hours_until:.1f} hours\n"
        
        return context
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.active_campaigns = [TeaseCampaign.from_dict(c) for c in data.get('active', [])]
                self.completed_campaigns = [TeaseCampaign.from_dict(c) for c in data.get('completed', [])]
                self.dave_patience_level = data.get('patience_level', 50)
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'active': [c.to_dict() for c in self.active_campaigns],
                'completed': [c.to_dict() for c in self.completed_campaigns[-20:]],  # Keep last 20
                'patience_level': self.dave_patience_level
            }, f, indent=2)


# =====================================================
# USAGE EXAMPLES
# =====================================================

"""
# In your bot:

tease_system = TeaseAndDenial('data/michaela/teases.json')

# Start a morning tease for evening delivery
campaign = tease_system.start_basic_tease(
    theme="shower",
    tease_duration_hours=8
)

# Or progressive reveal
campaign = tease_system.start_progressive_reveal(
    theme="lingerie",
    stages_count=4,
    duration_hours=6
)

# Or edge and deny (for intense teasing)
campaign = tease_system.start_edge_and_deny(
    theme="bedroom",
    edge_count=3,
    duration_hours=10
)

# Reward for goal achievement
if gym_streak == 3:
    campaign = tease_system.start_reward_tease(
        goal_achieved="3x gym this week",
        theme="shower",
        delay_hours=4
    )

# In your scheduler (check every 15 min):
due_stages = tease_system.get_due_stages()
for item in due_stages:
    stage_data = tease_system.execute_stage(
        item['campaign'],
        item['stage_index']
    )
    
    # Send stage message
    michaela_message = stage_data['message']
    
    # Send media if specified
    if stage_data.get('media'):
        media = get_media_for_tease(stage_data['media'])
        # Send media

# Adapt based on Dave's responses
if dave_says_impatient:
    tease_system.adjust_patience(increase=False)
if dave_loves_the_tease:
    tease_system.adjust_patience(increase=True)
"""
