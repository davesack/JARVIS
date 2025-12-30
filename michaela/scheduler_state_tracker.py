"""
Scheduler State Tracker
========================

Prevents duplicate check-ins when bot restarts by tracking what's been sent today.

Usage in your michaela_scheduler.py:

    from utils.michaela.scheduler_state_tracker import SchedulerStateTracker
    
    # Initialize
    self.state_tracker = SchedulerStateTracker("data/michaela/scheduler_state.json")
    
    # Before sending morning check-in:
    if not self.state_tracker.should_send("morning_checkin"):
        return  # Already sent today
    
    # Send the check-in...
    
    # Mark as sent
    self.state_tracker.mark_sent("morning_checkin")
"""

import json
import os
from datetime import datetime, timezone, date

UTC = timezone.utc


class SchedulerStateTracker:
    """
    Tracks which scheduled messages have been sent today.
    Prevents duplicates when bot restarts.
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.state = self._load()
        
        # Clean old entries on init
        self._cleanup_old_entries()
    
    def _load(self) -> dict:
        """Load state from disk"""
        if not os.path.exists(self.filepath):
            return {
                'last_reset_date': str(date.today()),
                'sent_today': {}
            }
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SCHEDULER_STATE] Error loading state: {e}")
            return {
                'last_reset_date': str(date.today()),
                'sent_today': {}
            }
    
    def _save(self):
        """Save state to disk"""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"[SCHEDULER_STATE] Error saving state: {e}")
    
    def _cleanup_old_entries(self):
        """Reset state if it's a new day"""
        today = str(date.today())
        
        if self.state.get('last_reset_date') != today:
            print(f"[SCHEDULER_STATE] New day detected - resetting sent messages")
            self.state = {
                'last_reset_date': today,
                'sent_today': {}
            }
            self._save()
    
    def should_send(self, message_type: str) -> bool:
        """
        Check if a message type should be sent
        
        Args:
            message_type: e.g., "morning_checkin", "afternoon_checkin", "evening_checkin"
        
        Returns:
            True if should send, False if already sent today
        """
        # Make sure we're on the right day
        self._cleanup_old_entries()
        
        # Check if already sent
        return message_type not in self.state['sent_today']
    
    def mark_sent(self, message_type: str):
        """
        Mark a message type as sent for today
        
        Args:
            message_type: e.g., "morning_checkin", "afternoon_checkin"
        """
        now = datetime.now(UTC)
        
        self.state['sent_today'][message_type] = {
            'timestamp': now.isoformat(),
            'time': now.strftime('%H:%M:%S')
        }
        
        self._save()
        print(f"[SCHEDULER_STATE] Marked '{message_type}' as sent at {now.strftime('%H:%M:%S')}")
    
    def get_sent_today(self) -> dict:
        """Get all messages sent today"""
        self._cleanup_old_entries()
        return self.state['sent_today'].copy()
    
    def reset_for_testing(self):
        """Manually reset state (for testing)"""
        self.state = {
            'last_reset_date': str(date.today()),
            'sent_today': {}
        }
        self._save()
        print(f"[SCHEDULER_STATE] State manually reset")
    
    def mark_not_sent(self, message_type: str):
        """
        Remove a message from sent list (for testing/corrections)
        
        Args:
            message_type: e.g., "morning_checkin"
        """
        if message_type in self.state['sent_today']:
            del self.state['sent_today'][message_type]
            self._save()
            print(f"[SCHEDULER_STATE] Removed '{message_type}' from sent list")


# ============================================================
# USAGE EXAMPLE FOR YOUR SCHEDULER
# ============================================================

"""
In your michaela_scheduler.py file, add this:

1. At the top with other imports:
   from utils.michaela.scheduler_state_tracker import SchedulerStateTracker

2. In __init__:
   self.state_tracker = SchedulerStateTracker("data/michaela/scheduler_state.json")

3. In your morning check-in function:
   async def send_morning_checkin(self):
       # Check if already sent today
       if not self.state_tracker.should_send("morning_checkin"):
           print("[SCHEDULER] Morning check-in already sent today, skipping")
           return
       
       # ... your existing check-in code ...
       
       # After successfully sending, mark as sent
       self.state_tracker.mark_sent("morning_checkin")

4. In your afternoon check-in function:
   async def send_afternoon_checkin(self):
       # Check if already sent today
       if not self.state_tracker.should_send("afternoon_checkin"):
           print("[SCHEDULER] Afternoon check-in already sent today, skipping")
           return
       
       # ... your existing check-in code ...
       
       # After successfully sending, mark as sent
       self.state_tracker.mark_sent("afternoon_checkin")

5. For sleep check-in:
   async def send_sleep_checkin(self):
       # Check if already sent today
       if not self.state_tracker.should_send("sleep_checkin"):
           print("[SCHEDULER] Sleep check-in already sent today, skipping")
           return
       
       # ... your existing check-in code ...
       
       # After successfully sending, mark as sent
       self.state_tracker.mark_sent("sleep_checkin")


TESTING COMMANDS (add these to Michaela cog):

@commands.command(name="scheduler_status")
async def scheduler_status(self, ctx):
    '''Show what scheduler has sent today'''
    sent = self.scheduler.state_tracker.get_sent_today()
    
    if not sent:
        await ctx.send("📊 No check-ins sent today yet")
        return
    
    lines = ["📊 **Check-ins Sent Today:**\n"]
    for msg_type, info in sent.items():
        lines.append(f"✅ {msg_type.replace('_', ' ').title()} - {info['time']}")
    
    await ctx.send('\n'.join(lines))

@commands.command(name="scheduler_reset")
async def scheduler_reset(self, ctx):
    '''Reset scheduler state (for testing)'''
    self.scheduler.state_tracker.reset_for_testing()
    await ctx.send("✅ Scheduler state reset - all check-ins can be sent again")

@commands.command(name="scheduler_unsend")
async def scheduler_unsend(self, ctx, message_type: str):
    '''Mark a check-in as not sent (for testing)'''
    self.scheduler.state_tracker.mark_not_sent(message_type)
    await ctx.send(f"✅ Removed {message_type} from sent list - can be sent again")
"""
