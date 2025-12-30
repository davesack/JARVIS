"""
Intelligent Streak System
=========================

Smart habit tracking with:
- Grace day bank (earned through milestones)
- Context-aware pausing (medical studies, vacation, etc.)
- Automatic pause calculation
- Manual pause with reasons
"""

from __future__ import annotations

import json
import os
from datetime import datetime, date, timedelta, time, timezone
from typing import Dict, List, Optional

UTC = timezone.utc


class IntelligentStreakSystem:
    """
    Smart streak management that understands life context
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.habits: Dict[str, Dict] = {}
        self.active_contexts: Dict[str, Dict] = {}
        self._load()
    
    # =====================================================
    # HABIT MANAGEMENT
    # =====================================================
    
    def create_habit(
        self,
        name: str,
        description: str = "",
        reminder_time: time = None,
        reminder_days: list = None,
        pausable_contexts: list = None
    ):
        """
        Create a new habit
        
        pausable_contexts: Which life contexts pause this habit
        Examples: ["medical_study", "sick", "vacation"]
        """
        
        self.habits[name] = {
            'name': name,
            'description': description,
            'created': datetime.now(UTC).isoformat(),
            'current_streak': 0,
            'longest_streak': 0,
            'total_completions': 0,
            'last_completion': None,
            
            # Grace system
            'grace_days_banked': 0,
            'grace_days_used': 0,
            
            # Smart pausing
            'pausable_contexts': pausable_contexts or [],
            'currently_paused': False,
            'pause_reason': None,
            'paused_at': None,
            
            # Tracking
            'completions_log': [],
            'reminder_time': reminder_time.isoformat() if reminder_time else None,
            'reminder_days': reminder_days or ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
        }
        self._save()
    
    def log_completion(
        self,
        habit_name: str,
        note: str = None,
        force: bool = False
    ) -> dict:
        """
        Log habit completion with smart streak preservation
        """
        
        if habit_name not in self.habits:
            return {'error': 'Habit not found'}
        
        habit = self.habits[habit_name]
        
        # Check if paused
        if habit['currently_paused'] and not force:
            return {
                'error': f"Habit is paused ({habit['pause_reason']}). Streak is protected."
            }
        
        now = datetime.now(UTC)
        today = now.date()
        
        # Already completed today?
        if habit['last_completion']:
            last_date = datetime.fromisoformat(habit['last_completion']).date()
            if last_date == today:
                return {
                    'already_completed': True,
                    'current_streak': habit['current_streak']
                }
        
        # Calculate streak (accounting for pauses)
        grace_used = False
        if habit['last_completion']:
            last_date = datetime.fromisoformat(habit['last_completion']).date()
            days_since = (today - last_date).days
            
            # Check if we were paused during the gap
            paused_days = self._count_paused_days_between(
                habit_name,
                last_date,
                today
            )
            
            # Adjust for paused days
            actual_gap = days_since - paused_days
            
            if actual_gap <= 1:
                # Streak continues
                habit['current_streak'] += 1
            elif actual_gap == 2 and habit['grace_days_banked'] > 0:
                # Use a grace day
                habit['grace_days_banked'] -= 1
                habit['grace_days_used'] += 1
                habit['current_streak'] += 1
                grace_used = True
            else:
                # Streak broken
                habit['current_streak'] = 1
        else:
            habit['current_streak'] = 1
        
        # Update
        habit['last_completion'] = now.isoformat()
        habit['total_completions'] += 1
        habit['longest_streak'] = max(habit['longest_streak'], habit['current_streak'])
        
        # Log
        habit['completions_log'].append({
            'timestamp': now.isoformat(),
            'note': note,
            'streak': habit['current_streak']
        })
        
        # Earn grace days at milestones
        grace_earned = 0
        streak = habit['current_streak']
        
        if streak == 7:
            grace_earned = 1
        elif streak == 30:
            grace_earned = 2
        elif streak == 100:
            grace_earned = 3
        elif streak % 50 == 0 and streak > 0:
            grace_earned = 2
        
        if grace_earned > 0:
            habit['grace_days_banked'] += grace_earned
        
        self._save()
        
        return {
            'current_streak': streak,
            'longest_streak': habit['longest_streak'],
            'grace_days_banked': habit['grace_days_banked'],
            'grace_earned': grace_earned,
            'grace_used': grace_used,
            'is_milestone': streak in [7, 14, 30, 60, 100] or (streak % 50 == 0 and streak > 0)
        }
    
    # =====================================================
    # CONTEXT MANAGEMENT
    # =====================================================
    
    def activate_context(
        self,
        context_name: str,
        duration: timedelta = None,
        details: dict = None
    ):
        """
        Activate a life context that affects habits
        
        Examples:
        - activate_context("medical_study", duration=timedelta(days=90))
        - activate_context("vacation", duration=timedelta(days=7))
        - activate_context("sick", duration=timedelta(days=3))
        """
        
        end_time = None
        if duration:
            end_time = (datetime.now(UTC) + duration).isoformat()
        
        self.active_contexts[context_name] = {
            'started': datetime.now(UTC).isoformat(),
            'end_time': end_time,
            'details': details or {},
            'active': True
        }
        
        # Auto-pause affected habits
        for habit_name, habit in self.habits.items():
            if context_name in habit['pausable_contexts']:
                habit['currently_paused'] = True
                habit['pause_reason'] = context_name
                habit['paused_at'] = datetime.now(UTC).isoformat()
        
        self._save()
    
    def deactivate_context(self, context_name: str):
        """End a life context and resume affected habits"""
        
        if context_name in self.active_contexts:
            self.active_contexts[context_name]['active'] = False
            self.active_contexts[context_name]['ended'] = datetime.now(UTC).isoformat()
        
        # Resume habits that were paused by this context
        for habit_name, habit in self.habits.items():
            if habit['pause_reason'] == context_name:
                habit['currently_paused'] = False
                habit['pause_reason'] = None
        
        self._save()
    
    def manual_pause_habit(
        self,
        habit_name: str,
        reason: str,
        duration: timedelta = None
    ):
        """Manually pause a specific habit"""
        
        if habit_name not in self.habits:
            return False
        
        habit = self.habits[habit_name]
        habit['currently_paused'] = True
        habit['pause_reason'] = f"manual: {reason}"
        habit['paused_at'] = datetime.now(UTC).isoformat()
        
        if duration:
            habit['pause_until'] = (datetime.now(UTC) + duration).isoformat()
        
        self._save()
        return True
    
    def resume_habit(self, habit_name: str):
        """Resume a paused habit"""
        
        if habit_name not in self.habits:
            return False
        
        habit = self.habits[habit_name]
        habit['currently_paused'] = False
        habit['pause_reason'] = None
        habit.pop('pause_until', None)
        
        self._save()
        return True
    
    def _count_paused_days_between(
        self,
        habit_name: str,
        start_date: date,
        end_date: date
    ) -> int:
        """
        Count how many days between two dates the habit was paused
        This protects streaks during valid pause periods
        """
        
        habit = self.habits.get(habit_name)
        if not habit:
            return 0
        
        paused_days = 0
        current = start_date + timedelta(days=1)
        
        while current < end_date:
            # Check if any active context was pausing this habit on this date
            for context_name, context in self.active_contexts.items():
                if context_name not in habit['pausable_contexts']:
                    continue
                
                context_start = datetime.fromisoformat(context['started']).date()
                context_end = None
                
                if context.get('ended'):
                    context_end = datetime.fromisoformat(context['ended']).date()
                elif context.get('end_time'):
                    context_end = datetime.fromisoformat(context['end_time']).date()
                
                # Was this context active on this day?
                if context_start <= current:
                    if context_end is None or current <= context_end:
                        paused_days += 1
                        break
            
            current += timedelta(days=1)
        
        return paused_days
    
    # =====================================================
    # REMINDERS & ALERTS
    # =====================================================
    
    def get_habits_needing_reminders(self, current_time: datetime) -> list:
        """Get habits that need reminders at this time"""
        
        needs_reminder = []
        current_day = current_time.strftime('%A').lower()
        current_time_obj = current_time.time()
        
        for habit_name, habit in self.habits.items():
            if habit['currently_paused']:
                continue
            
            # Check if today is a reminder day
            if current_day not in habit['reminder_days']:
                continue
            
            # Check if it's reminder time
            if not habit['reminder_time']:
                continue
            
            reminder_time = datetime.fromisoformat(habit['reminder_time']).time()
            
            # Within 15 minutes of reminder time
            time_diff = abs(
                (current_time_obj.hour * 60 + current_time_obj.minute) -
                (reminder_time.hour * 60 + reminder_time.minute)
            )
            
            if time_diff <= 15:
                # Haven't completed today
                if habit['last_completion']:
                    last_date = datetime.fromisoformat(habit['last_completion']).date()
                    if last_date < current_time.date():
                        needs_reminder.append(habit_name)
                else:
                    needs_reminder.append(habit_name)
        
        return needs_reminder
    
    def get_at_risk_habits(self) -> list:
        """Habits that haven't been done and streak is at risk"""
        
        at_risk = []
        now = datetime.now(UTC)
        
        for habit_name, habit in self.habits.items():
            if habit['currently_paused'] or habit['current_streak'] == 0:
                continue
            
            if not habit['last_completion']:
                continue
            
            last_date = datetime.fromisoformat(habit['last_completion']).date()
            today = now.date()
            
            # If we haven't done it today and it's getting late
            if last_date < today and now.hour >= 20:
                at_risk.append({
                    'name': habit_name,
                    'streak': habit['current_streak'],
                    'grace_available': habit['grace_days_banked'] > 0
                })
        
        return at_risk
    
    # =====================================================
    # SUMMARY & CONTEXT
    # =====================================================
    
    def get_summary(self) -> str:
        """Human-readable summary for Michaela"""
        
        if not self.habits:
            return "No habits being tracked yet."
        
        active = [(name, h) for name, h in self.habits.items() 
                  if h['current_streak'] > 0 and not h['currently_paused']]
        
        if not active:
            return "No active streaks right now."
        
        active.sort(key=lambda x: x[1]['current_streak'], reverse=True)
        
        summary = "Current habits:\n"
        for name, habit in active:
            grace = f" (+{habit['grace_days_banked']} grace)" if habit['grace_days_banked'] > 0 else ""
            summary += f"- {name}: {habit['current_streak']} days{grace}\n"
        
        return summary.strip()
    
    def get_active_context_summary(self) -> str:
        """Get current life contexts"""
        
        active = [(name, ctx) for name, ctx in self.active_contexts.items() if ctx['active']]
        
        if not active:
            return ""
        
        summary = "Current life contexts:\n"
        for name, ctx in active:
            details = ctx.get('details', {})
            detail_str = f" ({', '.join(f'{k}: {v}' for k, v in details.items())})" if details else ""
            
            if ctx.get('end_time'):
                end = datetime.fromisoformat(ctx['end_time'])
                days_remaining = (end - datetime.now(UTC)).days
                summary += f"- {name}{detail_str} ({days_remaining} days remaining)\n"
            else:
                summary += f"- {name}{detail_str}\n"
        
        return summary.strip()
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.habits = data.get('habits', {})
                self.active_contexts = data.get('active_contexts', {})
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'habits': self.habits,
                'active_contexts': self.active_contexts
            }, f, indent=2)
