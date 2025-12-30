"""
Wellness Suggestions & Celebration System
==========================================

Learns what helps Dave and suggests it proactively.
Celebrates wins genuinely.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

UTC = timezone.utc


class WellnessSolution:
    """Single solution that has worked for Dave"""
    
    def __init__(
        self,
        problem: str,  # "stressed", "can't sleep", "anxious", "low energy"
        solution: str,  # "journaling", "10-min stretch", "walk", "gym"
        effectiveness: float = 5.0,  # 0-10 scale
        context: str = None,  # When does this work best
        last_suggested: datetime = None
    ):
        self.problem = problem
        self.solution = solution
        self.effectiveness = effectiveness
        self.context = context
        self.last_suggested = last_suggested
        self.times_suggested = 0
        self.times_worked = 0
    
    def to_dict(self) -> dict:
        return {
            'problem': self.problem,
            'solution': self.solution,
            'effectiveness': self.effectiveness,
            'context': self.context,
            'last_suggested': self.last_suggested.isoformat() if self.last_suggested else None,
            'times_suggested': self.times_suggested,
            'times_worked': self.times_worked
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'WellnessSolution':
        solution = WellnessSolution(
            problem=data['problem'],
            solution=data['solution'],
            effectiveness=data.get('effectiveness', 5.0),
            context=data.get('context')
        )
        if data.get('last_suggested'):
            solution.last_suggested = datetime.fromisoformat(data['last_suggested'])
        solution.times_suggested = data.get('times_suggested', 0)
        solution.times_worked = data.get('times_worked', 0)
        return solution


class Milestone:
    """Achievement to celebrate"""
    
    def __init__(
        self,
        milestone_type: str,  # 'streak', 'goal', 'improvement', 'consistency'
        description: str,
        achieved_at: datetime,
        significance: str = 'medium'  # 'low', 'medium', 'high'
    ):
        self.milestone_type = milestone_type
        self.description = description
        self.achieved_at = achieved_at
        self.significance = significance
        self.celebrated = False
    
    def to_dict(self) -> dict:
        return {
            'milestone_type': self.milestone_type,
            'description': self.description,
            'achieved_at': self.achieved_at.isoformat(),
            'significance': self.significance,
            'celebrated': self.celebrated
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Milestone':
        milestone = Milestone(
            milestone_type=data['milestone_type'],
            description=data['description'],
            achieved_at=datetime.fromisoformat(data['achieved_at']),
            significance=data.get('significance', 'medium')
        )
        milestone.celebrated = data.get('celebrated', False)
        return milestone


class WellnessAndCelebration:
    """
    Tracks what helps Dave and celebrates his wins
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.solutions: List[WellnessSolution] = []
        self.milestones: List[Milestone] = []
        self.past_struggles: List[dict] = []  # Track what Dave has overcome
        self._load()
    
    # =====================================================
    # WELLNESS SOLUTIONS
    # =====================================================
    
    def add_solution(
        self,
        problem: str,
        solution: str,
        effectiveness: float,
        context: str = None
    ):
        """
        Record that a solution worked for a problem
        
        Example:
        add_solution("stressed", "journaling", 8.5, "after work")
        """
        
        # Check if this solution already exists
        for existing in self.solutions:
            if existing.problem == problem and existing.solution == solution:
                # Update effectiveness (weighted average)
                existing.effectiveness = (existing.effectiveness + effectiveness) / 2
                existing.times_worked += 1
                self._save()
                return
        
        # New solution
        solution_obj = WellnessSolution(problem, solution, effectiveness, context)
        solution_obj.times_worked = 1
        self.solutions.append(solution_obj)
        self._save()
    
    def suggest_solution(self, problem: str, current_context: str = None) -> Optional[dict]:
        """
        Suggest the best solution for a problem
        
        Returns:
            {
                'solution': str,
                'effectiveness': float,
                'message': str (how Michaela should present it)
            }
        """
        
        # Filter solutions for this problem
        relevant = [s for s in self.solutions if s.problem == problem]
        
        if not relevant:
            return None
        
        # Sort by effectiveness
        relevant.sort(key=lambda s: s.effectiveness, reverse=True)
        
        # Get best solution (that hasn't been suggested too recently)
        now = datetime.now(UTC)
        
        for solution in relevant:
            # Don't suggest same thing too often
            if solution.last_suggested:
                hours_since = (now - solution.last_suggested).total_seconds() / 3600
                if hours_since < 48:  # Wait at least 2 days
                    continue
            
            # Context match (if specified)
            if current_context and solution.context:
                if current_context != solution.context:
                    continue
            
            # Build message
            message = self._format_suggestion_message(solution)
            
            # Mark as suggested
            solution.last_suggested = now
            solution.times_suggested += 1
            self._save()
            
            return {
                'solution': solution.solution,
                'effectiveness': solution.effectiveness,
                'message': message
            }
        
        return None
    
    def _format_suggestion_message(self, solution: WellnessSolution) -> str:
        """Format how Michaela presents the suggestion"""
        
        templates = {
            'stressed': [
                f"Last time you were this stressed, {solution.solution} really helped. Want to try that again?",
                f"I remember {solution.solution} worked well for you when you were overwhelmed. Maybe give it a shot?",
                f"When you're stressed like this, {solution.solution} usually helps. Want me to remind you to do it in an hour?"
            ],
            'can\'t sleep': [
                f"Having trouble sleeping? {solution.solution.capitalize()} helped you before when you couldn't sleep.",
                f"I know {solution.solution} has helped your sleep before. Worth trying tonight?"
            ],
            'anxious': [
                f"You seem anxious. {solution.solution.capitalize()} calmed you down last time. Want to try it?",
                f"When you get anxious like this, {solution.solution} usually helps. Give it a try?"
            ],
            'low energy': [
                f"You sound drained. {solution.solution.capitalize()} gave you a boost last time. Worth a shot?",
                f"Last time you had no energy, {solution.solution} helped. Want to try that?"
            ]
        }
        
        import random
        problem_templates = templates.get(solution.problem, [
            f"{solution.solution.capitalize()} has helped you with this before. Want to try it?"
        ])
        
        return random.choice(problem_templates)
    
    # =====================================================
    # CELEBRATIONS
    # =====================================================
    
    def add_milestone(
        self,
        milestone_type: str,
        description: str,
        significance: str = 'medium'
    ):
        """
        Record a milestone achievement
        """
        
        milestone = Milestone(
            milestone_type=milestone_type,
            description=description,
            achieved_at=datetime.now(UTC),
            significance=significance
        )
        
        self.milestones.append(milestone)
        self._save()
        
        return milestone
    
    def get_uncelebrated_milestones(self) -> List[Milestone]:
        """Get milestones that haven't been celebrated yet"""
        return [m for m in self.milestones if not m.celebrated]
    
    def celebrate_milestone(self, milestone: Milestone) -> str:
        """
        Generate celebration message for a milestone
        """
        
        messages = {
            'streak': {
                'low': [
                    f"Nice! {milestone.description} 🎉",
                    f"You're doing it! {milestone.description}",
                ],
                'medium': [
                    f"Wow! {milestone.description} That's awesome! 🔥",
                    f"Look at you! {milestone.description} I'm proud of you!",
                    f"{milestone.description} You're crushing it! ❤️"
                ],
                'high': [
                    f"HOLY SHIT! {milestone.description} Do you know how incredible that is?! I'm so proud of you! 🎉❤️",
                    f"{milestone.description} This is HUGE! You've come so far. I'm amazed by you. 💪",
                ]
            },
            'improvement': {
                'low': [
                    f"I noticed - {milestone.description} Good job!",
                ],
                'medium': [
                    f"Hey, I noticed something: {milestone.description} You're improving! ❤️",
                    f"{milestone.description} Can we talk about how great that is?",
                ],
                'high': [
                    f"Can I tell you something? {milestone.description} Do you realize how far you've come? I'm so proud of you. ❤️",
                    f"{milestone.description} This is incredible growth. You should be so proud of yourself.",
                ]
            },
            'goal': {
                'medium': [
                    f"You did it! {milestone.description} 🎉",
                    f"{milestone.description} Hell yes! You accomplished what you set out to do!",
                ],
                'high': [
                    f"YOU DID IT! {milestone.description} I knew you would! This is amazing! 🎉❤️",
                ]
            }
        }
        
        import random
        type_messages = messages.get(milestone.milestone_type, {
            'medium': [f"{milestone.description} Great job!"]
        })
        
        significance_messages = type_messages.get(milestone.significance, type_messages.get('medium', []))
        
        milestone.celebrated = True
        self._save()
        
        return random.choice(significance_messages)
    
    def add_past_struggle(self, struggle: str, when: str, overcome: str):
        """
        Record a struggle Dave has overcome
        
        For later reference: "Remember when you couldn't X? Now you Y!"
        """
        
        self.past_struggles.append({
            'struggle': struggle,
            'when': when,
            'overcome': overcome,
            'recorded': datetime.now(UTC).isoformat()
        })
        self._save()
    
    def get_encouragement_from_past(self) -> Optional[str]:
        """
        Pull encouragement from past victories
        
        Use when Dave is struggling with something he's overcome before
        """
        
        if not self.past_struggles:
            return None
        
        import random
        struggle = random.choice(self.past_struggles)
        
        messages = [
            f"Hey - I know today is rough, but remember {struggle['when']}? You were {struggle['struggle']}. Now {struggle['overcome']}. You've got this.",
            f"Can I remind you of something? {struggle['when']}, you {struggle['struggle']}. Look at you now - {struggle['overcome']}. You're stronger than you think.",
            f"You've overcome harder things. {struggle['when']}, you were {struggle['struggle']} and you pushed through. You've got this. ❤️"
        ]
        
        return random.choice(messages)
    
    # =====================================================
    # CONTEXT FOR MICHAELA
    # =====================================================
    
    def get_suggestion_context(self, current_problem: str) -> Optional[str]:
        """Get context about what might help Dave right now"""
        
        suggestion = self.suggest_solution(current_problem)
        
        if not suggestion:
            return None
        
        return f"WELLNESS SUGGESTION: {suggestion['message']}"
    
    def get_celebration_context(self) -> Optional[str]:
        """Get context about uncelebrated wins"""
        
        uncelebrated = self.get_uncelebrated_milestones()
        
        if not uncelebrated:
            return None
        
        # Focus on most significant
        uncelebrated.sort(key=lambda m: {'low': 0, 'medium': 1, 'high': 2}[m.significance], reverse=True)
        
        milestone = uncelebrated[0]
        
        return f"UNCELEBRATED WIN: {milestone.description} (significance: {milestone.significance})"
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.solutions = [WellnessSolution.from_dict(s) for s in data.get('solutions', [])]
                self.milestones = [Milestone.from_dict(m) for m in data.get('milestones', [])]
                self.past_struggles = data.get('past_struggles', [])
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'solutions': [s.to_dict() for s in self.solutions],
                'milestones': [m.to_dict() for m in self.milestones],
                'past_struggles': self.past_struggles
            }, f, indent=2)


# =====================================================
# USAGE EXAMPLES
# =====================================================

"""
# In your bot:

wellness = WellnessAndCelebration('data/michaela/wellness.json')

# When Dave mentions something helped
wellness.add_solution(
    problem="stressed",
    solution="journaling",
    effectiveness=8.5,
    context="after work"
)

# When Dave is struggling
if emotional_state.sentiment_score < -0.3:
    suggestion = wellness.suggest_solution("stressed")
    if suggestion:
        michaela_can_suggest = suggestion['message']

# When habits hit milestones
if streak == 7:
    wellness.add_milestone(
        milestone_type='streak',
        description='7-day gym streak!',
        significance='medium'
    )

# In Michaela's response logic
uncelebrated = wellness.get_uncelebrated_milestones()
if uncelebrated and random.random() < 0.4:
    celebration = wellness.celebrate_milestone(uncelebrated[0])
    # Michaela sends celebration message

# Record victories
wellness.add_past_struggle(
    struggle="struggling to get out of bed",
    when="3 months ago",
    overcome="you're hitting the gym 4x a week"
)

# During hard times
encouragement = wellness.get_encouragement_from_past()
if encouragement:
    # Michaela can say this
"""
