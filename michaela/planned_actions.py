"""
Planned Actions System
======================

Handles Michaela's promises and delayed gifts:
- "I'll send you something later tonight"
- "I wanted to send you something today, but you'll have to wait"
- Teasing in the morning, delivering in the afternoon
- Delayed responses to requests ("I'll take that shower later")

This is the "queue of promises" that executes over time
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

UTC = timezone.utc


class PlannedAction:
    """Single planned action"""
    
    def __init__(
        self,
        action_type: str,  # 'send_media', 'send_message', 'tease', 'check_in'
        when: datetime,
        data: dict,
        created: datetime = None
    ):
        self.action_type = action_type
        self.when = when
        self.data = data
        self.created = created or datetime.now(UTC)
        self.completed = False
        self.completed_at = None
    
    def to_dict(self) -> dict:
        return {
            'action_type': self.action_type,
            'when': self.when.isoformat(),
            'data': self.data,
            'created': self.created.isoformat(),
            'completed': self.completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'PlannedAction':
        action = PlannedAction(
            action_type=data['action_type'],
            when=datetime.fromisoformat(data['when']),
            data=data['data'],
            created=datetime.fromisoformat(data['created'])
        )
        action.completed = data.get('completed', False)
        if data.get('completed_at'):
            action.completed_at = datetime.fromisoformat(data['completed_at'])
        return action


class PlannedActionsQueue:
    """
    Manages Michaela's queue of planned actions
    
    This is what makes her feel real - she remembers promises and follows through
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.queue: List[PlannedAction] = []
        self._load()
    
    # =====================================================
    # ADDING PLANNED ACTIONS
    # =====================================================
    
    def promise_media_later(
        self,
        media_tags: List[str],
        nsfw: bool,
        delay_hours: int = None,
        specific_time: datetime = None,
        tease_message: str = None
    ):
        """
        Michaela promises to send media later
        
        Args:
            media_tags: Tags for the media to send
            nsfw: NSFW level
            delay_hours: How many hours from now (random 2-8 if not specified)
            specific_time: Send at exact time
            tease_message: Optional tease she said when promising
        
        Example:
            "I'll send you something later tonight when I'm alone."
            "You'll have to wait until I get out of the shower later."
        """
        
        if specific_time:
            when = specific_time
        elif delay_hours:
            when = datetime.now(UTC) + timedelta(hours=delay_hours)
        else:
            # Random delay 2-8 hours
            when = datetime.now(UTC) + timedelta(hours=random.randint(2, 8))
        
        action = PlannedAction(
            action_type='send_media',
            when=when,
            data={
                'tags': media_tags,
                'nsfw': nsfw,
                'tease_message': tease_message,
                'preferred_type': 'images'  # Could be 'gifs', 'videos'
            }
        )
        
        self.queue.append(action)
        self._save()
    
    def promise_message_later(
        self,
        message_prompt: str,
        delay_hours: int = None,
        specific_time: datetime = None
    ):
        """
        Michaela promises to send a message later
        
        Example:
            "I'll check in on you this afternoon to see how that meeting went."
        """
        
        if specific_time:
            when = specific_time
        elif delay_hours:
            when = datetime.now(UTC) + timedelta(hours=delay_hours)
        else:
            when = datetime.now(UTC) + timedelta(hours=random.randint(3, 6))
        
        action = PlannedAction(
            action_type='send_message',
            when=when,
            data={
                'prompt': message_prompt
            }
        )
        
        self.queue.append(action)
        self._save()
    
    def schedule_tease_then_deliver(
        self,
        tease_message: str,
        media_tags: List[str],
        nsfw: bool,
        tease_in_hours: int = 1,
        deliver_in_hours: int = 6
    ):
        """
        Two-part action: tease now-ish, deliver later
        
        Example:
            Morning: "I wanted to send you something today, but you'll have to wait..."
            Afternoon: [sends the thing]
        """
        
        # Schedule tease
        tease_time = datetime.now(UTC) + timedelta(hours=tease_in_hours)
        tease_action = PlannedAction(
            action_type='tease',
            when=tease_time,
            data={'message': tease_message}
        )
        self.queue.append(tease_action)
        
        # Schedule delivery
        deliver_time = datetime.now(UTC) + timedelta(hours=deliver_in_hours)
        deliver_action = PlannedAction(
            action_type='send_media',
            when=deliver_time,
            data={
                'tags': media_tags,
                'nsfw': nsfw,
                'followup_to_tease': True
            }
        )
        self.queue.append(deliver_action)
        
        self._save()
    
    def schedule_delayed_response(
        self,
        request_type: str,  # 'shower_video', 'photo', 'specific_request'
        media_tags: List[str],
        nsfw: bool,
        delay_hours: int = None
    ):
        """
        User asks for something, Michaela says she'll do it later
        
        Example:
            Dave: "Can I see a shower video?"
            Michaela: "I'll hop in the shower later and send you something"
            [6 hours later, sends shower video]
        """
        
        when = datetime.now(UTC) + timedelta(hours=delay_hours or random.randint(4, 8))
        
        action = PlannedAction(
            action_type='send_media',
            when=when,
            data={
                'tags': media_tags,
                'nsfw': nsfw,
                'request_type': request_type,
                'delayed_response': True
            }
        )
        
        self.queue.append(action)
        self._save()
    
    # =====================================================
    # RETRIEVING DUE ACTIONS
    # =====================================================
    
    def get_due_actions(self) -> List[PlannedAction]:
        """Get all actions that are due now"""
        
        now = datetime.now(UTC)
        due = []
        
        for action in self.queue:
            if not action.completed and action.when <= now:
                due.append(action)
        
        return due
    
    def get_upcoming_actions(self, hours_ahead: int = 24) -> List[PlannedAction]:
        """Get actions scheduled in the next N hours"""
        
        now = datetime.now(UTC)
        cutoff = now + timedelta(hours=hours_ahead)
        
        upcoming = []
        for action in self.queue:
            if not action.completed and now < action.when <= cutoff:
                upcoming.append(action)
        
        return sorted(upcoming, key=lambda a: a.when)
    
    def complete_action(self, action: PlannedAction):
        """Mark action as completed"""
        
        action.completed = True
        action.completed_at = datetime.now(UTC)
        self._save()
    
    def cancel_action(self, action: PlannedAction):
        """Remove action from queue"""
        
        if action in self.queue:
            self.queue.remove(action)
            self._save()
    
    # =====================================================
    # QUEUE MANAGEMENT
    # =====================================================
    
    def cleanup_old_completed(self, days_old: int = 7):
        """Remove completed actions older than N days"""
        
        cutoff = datetime.now(UTC) - timedelta(days=days_old)
        
        self.queue = [
            action for action in self.queue
            if not (action.completed and action.completed_at and action.completed_at < cutoff)
        ]
        
        self._save()
    
    def get_queue_summary(self) -> Dict:
        """Get summary of queue status"""
        
        pending = [a for a in self.queue if not a.completed]
        completed = [a for a in self.queue if a.completed]
        
        return {
            'total_pending': len(pending),
            'total_completed': len(completed),
            'next_action': pending[0].when if pending else None,
            'pending_by_type': self._count_by_type(pending),
            'completed_by_type': self._count_by_type(completed)
        }
    
    def _count_by_type(self, actions: List[PlannedAction]) -> Dict[str, int]:
        """Count actions by type"""
        
        counts = {}
        for action in actions:
            counts[action.action_type] = counts.get(action.action_type, 0) + 1
        return counts
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        """Load queue from disk"""
        
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.queue = [PlannedAction.from_dict(a) for a in data]
    
    def _save(self):
        """Save queue to disk"""
        
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            data = [action.to_dict() for action in self.queue]
            json.dump(data, f, indent=2)
