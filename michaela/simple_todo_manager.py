"""
Simple Todo Manager
===================

Lightweight task tracking that complements the streak system.

DIFFERENCE FROM HABITS:
- Habits: Daily repetitive self-improvement (exercise, journaling)
- Todos: One-time or recurring tasks with specific deadlines

Examples:
- "Remind me to bring my Bible to church every Sunday"
- "I need to call the dentist on Friday"
- "Remind me to check my email every morning at 9am"
- "Take out the trash every Wednesday night"
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

UTC = timezone.utc


class SimpleTodo:
    """Single todo item"""
    
    def __init__(
        self,
        task: str,
        due_date: datetime = None,
        recurring: str = None,  # 'daily', 'weekly', 'monthly', None
        reminder_hours_before: int = 0,
        created: datetime = None
    ):
        self.task = task
        self.due_date = due_date
        self.recurring = recurring
        self.reminder_hours_before = reminder_hours_before
        self.created = created or datetime.now(UTC)
        self.completed = False
        self.completed_at = None
    
    def to_dict(self) -> dict:
        return {
            'task': self.task,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'recurring': self.recurring,
            'reminder_hours_before': self.reminder_hours_before,
            'created': self.created.isoformat(),
            'completed': self.completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'SimpleTodo':
        todo = SimpleTodo(
            task=data['task'],
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            recurring=data.get('recurring'),
            reminder_hours_before=data.get('reminder_hours_before', 0),
            created=datetime.fromisoformat(data['created'])
        )
        todo.completed = data.get('completed', False)
        if data.get('completed_at'):
            todo.completed_at = datetime.fromisoformat(data['completed_at'])
        return todo


class SimpleTodoManager:
    """
    Lightweight todo manager
    
    Integrates with your existing reminder_system.py for notifications
    """
    
    def __init__(self, data_path: str, reminder_system=None):
        self.data_path = data_path
        self.reminder_system = reminder_system  # Optional: your existing ReminderSystem
        self.todos: List[SimpleTodo] = []
        self._load()
    
    # =====================================================
    # ADDING TODOS
    # =====================================================
    
    def add_todo(
        self,
        task: str,
        due_date: datetime = None,
        recurring: str = None,
        remind_hours_before: int = 0
    ) -> SimpleTodo:
        """
        Add a todo
        
        Args:
            task: What to do
            due_date: When it's due (optional)
            recurring: 'daily', 'weekly', 'monthly', or None for one-time
            remind_hours_before: How many hours before to remind (0 = at due time)
        
        Examples:
            # One-time task
            add_todo("Call dentist", due_date=friday_at_2pm)
            
            # Recurring weekly
            add_todo("Bring Bible to church", recurring='weekly', remind_hours_before=1)
            
            # Daily reminder
            add_todo("Check email", recurring='daily', due_date=tomorrow_at_9am)
        """
        
        todo = SimpleTodo(
            task=task,
            due_date=due_date,
            recurring=recurring,
            reminder_hours_before=remind_hours_before
        )
        
        self.todos.append(todo)
        
        # Add to reminder system if available
        if self.reminder_system and due_date:
            reminder_time = due_date - timedelta(hours=remind_hours_before)
            self.reminder_system.add_reminder(
                text=f"Todo: {task}",
                when=reminder_time,
                reminder_type='recurring' if recurring else 'absolute',
                recurrence=recurring
            )
        
        self._save()
        return todo
    
    def complete_todo(self, todo_index: int) -> bool:
        """
        Mark todo as complete
        
        If recurring, creates next occurrence
        """
        
        if todo_index >= len(self.todos):
            return False
        
        todo = self.todos[todo_index]
        todo.completed = True
        todo.completed_at = datetime.now(UTC)
        
        # Handle recurring
        if todo.recurring and todo.due_date:
            # Create next occurrence
            if todo.recurring == 'daily':
                next_due = todo.due_date + timedelta(days=1)
            elif todo.recurring == 'weekly':
                next_due = todo.due_date + timedelta(weeks=1)
            elif todo.recurring == 'monthly':
                next_due = todo.due_date + timedelta(days=30)
            else:
                next_due = None
            
            if next_due:
                self.add_todo(
                    task=todo.task,
                    due_date=next_due,
                    recurring=todo.recurring,
                    remind_hours_before=todo.reminder_hours_before
                )
        
        self._save()
        return True
    
    def delete_todo(self, todo_index: int) -> bool:
        """Remove a todo"""
        if todo_index < len(self.todos):
            self.todos.pop(todo_index)
            self._save()
            return True
        return False
    
    # =====================================================
    # QUERYING
    # =====================================================
    
    def get_due_todos(self, hours_ahead: int = 24) -> List[tuple]:
        """
        Get todos due in the next N hours
        
        Returns: List of (index, todo) tuples
        """
        
        now = datetime.now(UTC)
        cutoff = now + timedelta(hours=hours_ahead)
        
        due = []
        for i, todo in enumerate(self.todos):
            if todo.completed:
                continue
            
            if todo.due_date and now <= todo.due_date <= cutoff:
                due.append((i, todo))
        
        return sorted(due, key=lambda x: x[1].due_date or datetime.max.replace(tzinfo=UTC))
    
    def get_overdue_todos(self) -> List[tuple]:
        """Get todos past their due date"""
        
        now = datetime.now(UTC)
        overdue = []
        
        for i, todo in enumerate(self.todos):
            if todo.completed:
                continue
            
            if todo.due_date and todo.due_date < now:
                overdue.append((i, todo))
        
        return sorted(overdue, key=lambda x: x[1].due_date)
    
    def get_pending_todos(self) -> List[tuple]:
        """Get all incomplete todos"""
        
        pending = []
        for i, todo in enumerate(self.todos):
            if not todo.completed:
                pending.append((i, todo))
        
        return pending
    
    # =====================================================
    # DISPLAY
    # =====================================================
    
    def format_todos(self) -> str:
        """
        Human-readable todo list
        
        Returns formatted string for Michaela's context or Discord display
        """
        
        pending = self.get_pending_todos()
        
        if not pending:
            return "No pending todos!"
        
        output = "**Pending Todos:**\n"
        
        now = datetime.now(UTC)
        
        for i, todo in pending:
            # Format due date
            if todo.due_date:
                if todo.due_date < now:
                    due_str = f"⚠️ OVERDUE ({self._format_date(todo.due_date)})"
                elif (todo.due_date - now).days == 0:
                    due_str = f"🔔 Today at {todo.due_date.strftime('%I:%M %p')}"
                elif (todo.due_date - now).days == 1:
                    due_str = f"📅 Tomorrow at {todo.due_date.strftime('%I:%M %p')}"
                else:
                    due_str = f"📅 {self._format_date(todo.due_date)}"
            else:
                due_str = "📌 No deadline"
            
            # Recurring indicator
            recur_str = f" ({todo.recurring})" if todo.recurring else ""
            
            output += f"{i+1}. {todo.task}{recur_str}\n   {due_str}\n"
        
        return output
    
    def _format_date(self, dt: datetime) -> str:
        """Format datetime for display"""
        return dt.strftime("%a, %b %d at %I:%M %p")
    
    # =====================================================
    # MICHAELA CONTEXT
    # =====================================================
    
    def get_context_for_michaela(self) -> str:
        """
        Generate context for Michaela about Dave's todos
        
        Helps her be aware of what's on his plate
        """
        
        due_soon = self.get_due_todos(hours_ahead=48)
        overdue = self.get_overdue_todos()
        
        if not due_soon and not overdue:
            return ""
        
        context = ""
        
        if overdue:
            context += f"Dave has {len(overdue)} overdue task(s):\n"
            for _, todo in overdue[:3]:  # Show max 3
                context += f"- {todo.task}\n"
        
        if due_soon:
            context += f"\nComing up for Dave:\n"
            for _, todo in due_soon[:3]:  # Show max 3
                when = self._format_date(todo.due_date)
                context += f"- {todo.task} ({when})\n"
        
        return context.strip()
    
    # =====================================================
    # CLEANUP
    # =====================================================
    
    def cleanup_old_completed(self, days_old: int = 30):
        """Remove completed todos older than N days"""
        
        cutoff = datetime.now(UTC) - timedelta(days=days_old)
        
        self.todos = [
            todo for todo in self.todos
            if not (todo.completed and todo.completed_at and todo.completed_at < cutoff)
        ]
        
        self._save()
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.todos = [SimpleTodo.from_dict(t) for t in data]
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            data = [todo.to_dict() for todo in self.todos]
            json.dump(data, f, indent=2)


# =====================================================
# DISCORD COMMANDS (Add to your bot)
# =====================================================

"""
Example Discord integration:

# In your bot setup:
todo_manager = SimpleTodoManager(
    data_path='data/michaela/todos.json',
    reminder_system=reminder_system  # Your existing ReminderSystem
)

# Commands:

@bot.command(name='todo')
async def add_todo(ctx, *, task: str):
    '''Add a simple todo: !todo Call dentist on Friday'''
    # Parse natural language (optional enhancement)
    todo = todo_manager.add_todo(task)
    await ctx.send(f"✅ Added: {task}")

@bot.command(name='todos')
async def list_todos(ctx):
    '''Show all pending todos'''
    output = todo_manager.format_todos()
    await ctx.send(output)

@bot.command(name='donetodo')
async def complete_todo(ctx, index: int):
    '''Mark todo as done: !donetodo 1'''
    if todo_manager.complete_todo(index - 1):  # Convert to 0-index
        await ctx.send(f"✅ Completed!")
    else:
        await ctx.send("Todo not found")

@bot.command(name='deltodo')
async def delete_todo(ctx, index: int):
    '''Delete a todo: !deltodo 1'''
    if todo_manager.delete_todo(index - 1):
        await ctx.send(f"🗑️ Deleted")
    else:
        await ctx.send("Todo not found")
"""
