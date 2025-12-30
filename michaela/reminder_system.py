"""
Reminder System
===============

Flexible reminder system for:
- Absolute time reminders
- Before-event reminders
- Recurring reminders
- Future messages
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


class ReminderSystem:
    """
    General-purpose reminder system
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.reminders = []
        self._load()
    
    def add_reminder(
        self,
        text: str,
        when: datetime,
        reminder_type: str = "absolute",
        event_reference: str = None,
        recurrence: str = None
    ):
        """
        Add a reminder
        
        reminder_type: 'absolute', 'before_event', 'recurring', 'future_message'
        recurrence: 'daily', 'weekly', 'monthly'
        """
        
        self.reminders.append({
            'id': str(uuid.uuid4()),
            'text': text,
            'when': when.isoformat(),
            'type': reminder_type,
            'event_reference': event_reference,
            'recurrence': recurrence,
            'completed': False,
            'created': datetime.now(UTC).isoformat()
        })
        self._save()
    
    def get_due_reminders(self) -> list:
        """Get reminders that are due now"""
        
        now = datetime.now(UTC)
        due = []
        
        for reminder in self.reminders:
            if reminder['completed']:
                continue
            
            reminder_time = datetime.fromisoformat(reminder['when'])
            
            if now >= reminder_time:
                due.append(reminder)
        
        return due
    
    def complete_reminder(self, reminder_id: str):
        """Mark reminder as complete"""
        
        for reminder in self.reminders:
            if reminder['id'] == reminder_id:
                reminder['completed'] = True
                
                # Handle recurring
                if reminder['recurrence']:
                    self._schedule_next_occurrence(reminder)
                
                self._save()
                break
    
    def _schedule_next_occurrence(self, reminder: dict):
        """Schedule next occurrence of recurring reminder"""
        
        current_time = datetime.fromisoformat(reminder['when'])
        
        if reminder['recurrence'] == 'daily':
            next_time = current_time + timedelta(days=1)
        elif reminder['recurrence'] == 'weekly':
            next_time = current_time + timedelta(weeks=1)
        elif reminder['recurrence'] == 'monthly':
            next_time = current_time + timedelta(days=30)
        else:
            return
        
        self.add_reminder(
            text=reminder['text'],
            when=next_time,
            reminder_type='recurring',
            recurrence=reminder['recurrence']
        )
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.reminders = json.load(f)
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, indent=2)
