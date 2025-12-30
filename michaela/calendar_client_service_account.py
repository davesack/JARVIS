"""
Google Calendar Integration Client (Service Account Version)
=============================================================

Uses service account authentication instead of OAuth.
This matches your Google Sheets setup.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

UTC = timezone.utc

# Scopes required for calendar access
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


class GoogleCalendarClient:
    """
    Interface to Google Calendar API using Service Account
    
    Provides:
    - Today's events
    - Current event detection
    - Free block identification
    - Event tag parsing
    - Schedule analysis
    """
    
    def __init__(self, service_account_path: str, calendar_id: str = 'primary'):
        """
        Initialize calendar client with service account
        
        Args:
            service_account_path: Path to service_account.json
            calendar_id: Calendar ID (use 'primary' or specific email)
        """
        self.service_account_path = service_account_path
        self.calendar_id = calendar_id
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """
        Authenticate with Google Calendar API using service account
        """
        if not os.path.exists(self.service_account_path):
            raise FileNotFoundError(f"Service account file not found: {self.service_account_path}")
        
        # Load service account credentials
        creds = Credentials.from_service_account_file(
            self.service_account_path,
            scopes=SCOPES
        )
        
        # Build service
        self.service = build('calendar', 'v3', credentials=creds)
        print("[CALENDAR] Authenticated with service account successfully")
    
    async def get_todays_events(self) -> List[Dict]:
        """
        Get all events for today
        
        Returns: List of event dicts with start/end/summary/description
        """
        
        # Today's date range
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        try:
            # Fetch events
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=today_start.isoformat(),
                timeMax=today_end.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            print(f"[CALENDAR] Found {len(events)} events today")
            return events
            
        except Exception as e:
            print(f"[CALENDAR] Error fetching events: {e}")
            return []
    
    async def get_current_event(self) -> Optional[Dict]:
        """
        Get event happening right now
        
        Returns: Event dict or None
        """
        
        events = await self.get_todays_events()
        now = datetime.now(UTC)
        
        for event in events:
            start_str = event.get('start', {}).get('dateTime')
            end_str = event.get('end', {}).get('dateTime')
            
            if not (start_str and end_str):
                continue
            
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            
            if start <= now <= end:
                return event
        
        return None
    
    async def get_events(
        self,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None
    ) -> List[Dict]:
        """
        Get events in time range
        
        Args:
            time_min: ISO format datetime string
            time_max: ISO format datetime string
        
        Returns: List of events
        """
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except Exception as e:
            print(f"[CALENDAR] Error fetching events: {e}")
            return []
    
    async def get_free_blocks(
        self,
        min_duration_minutes: int = 30
    ) -> List[Dict]:
        """
        Find free blocks in today's schedule
        
        Args:
            min_duration_minutes: Minimum free block duration
        
        Returns: List of free blocks with start/end/duration
        """
        
        events = await self.get_todays_events()
        
        if not events:
            # Whole day is free
            now = datetime.now(UTC)
            return [{
                'start': now,
                'end': now.replace(hour=23, minute=59),
                'duration': (23 - now.hour) * 60 + (59 - now.minute)
            }]
        
        free_blocks = []
        now = datetime.now(UTC)
        
        # Check gap before first event
        first_start_str = events[0].get('start', {}).get('dateTime')
        if first_start_str:
            first_start = datetime.fromisoformat(first_start_str.replace('Z', '+00:00'))
            gap = (first_start - now).total_seconds() / 60
            
            if gap >= min_duration_minutes:
                free_blocks.append({
                    'start': now,
                    'end': first_start,
                    'duration': gap
                })
        
        # Check gaps between events
        for i in range(len(events) - 1):
            end_str = events[i].get('end', {}).get('dateTime')
            next_start_str = events[i + 1].get('start', {}).get('dateTime')
            
            if not (end_str and next_start_str):
                continue
            
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            next_start = datetime.fromisoformat(next_start_str.replace('Z', '+00:00'))
            
            gap = (next_start - end).total_seconds() / 60
            
            if gap >= min_duration_minutes and end > now:
                free_blocks.append({
                    'start': end,
                    'end': next_start,
                    'duration': gap
                })
        
        # Check gap after last event
        last_end_str = events[-1].get('end', {}).get('dateTime')
        end_of_day = now.replace(hour=23, minute=59, second=59)
        
        if last_end_str:
            last_end = datetime.fromisoformat(last_end_str.replace('Z', '+00:00'))
        
            if last_end < end_of_day:
                gap = (end_of_day - last_end).total_seconds() / 60
                if gap >= min_duration_minutes:
                    free_blocks.append({
                        'start': last_end,
                        'end': end_of_day,
                        'duration': gap
                    })
        
        return free_blocks
    
    async def is_free_now(self) -> bool:
        """
        Check if currently in a free block
        
        Returns: True if no event happening now
        """
        current_event = await self.get_current_event()
        return current_event is None
    
    def extract_event_tags(self, event: Dict) -> Dict:
        """
        Extract support tags from event title/description
        
        Looks for:
        - Emoji (💼🎯😰🏥🎉💪🤫⚙️)
        - Hashtags (#work #stressful #medical #private)
        - Custom remind timing (#remind-60)
        
        Args:
            event: Event dict from Google Calendar
        
        Returns: {
            'type': 'work' | 'presentation' | 'stressful' | 'medical' | 'fun' | 'important' | 'private' | 'routine',
            'emoji': '💼' or None,
            'remind_minutes': 30 (default) or custom
        }
        """
        
        title = event.get('summary', '').lower()
        description = event.get('description', '').lower()
        
        # Emoji mapping
        emoji_map = {
            '💼': 'work',
            '🎯': 'presentation',
            '😰': 'stressful',
            '🏥': 'medical',
            '🎉': 'fun',
            '💪': 'important',
            '🤫': 'private',
            '⚙️': 'routine',
            '🧠': 'therapy',
            '🏋️': 'workout',
            '📝': 'creative',
            '💻': 'coding',
            '📞': 'social',
        }
        
        # Check for emojis
        found_emoji = None
        found_type = 'routine'  # default
        
        for emoji, event_type in emoji_map.items():
            if emoji in title or emoji in description:
                found_emoji = emoji
                found_type = event_type
                break
        
        # Check for hashtags
        if '#work' in description or 'work' in title:
            found_type = 'work'
        elif '#stressful' in description or 'stressful' in title:
            found_type = 'stressful'
        elif '#medical' in description or 'doctor' in title or 'appointment' in title:
            found_type = 'medical'
        elif '#fun' in description or 'party' in title or 'celebration' in title:
            found_type = 'fun'
        elif '#private' in description or 'private' in title:
            found_type = 'private'
        
        # Extract custom remind timing
        remind_minutes = 30  # default
        
        import re
        remind_match = re.search(r'#remind-(\d+)', description)
        if remind_match:
            remind_minutes = int(remind_match.group(1))
        
        return {
            'type': found_type,
            'emoji': found_emoji,
            'remind_minutes': remind_minutes
        }


# Support message templates (same as original)
SUPPORT_MESSAGE_TEMPLATES = {
    'work': {
        'pre_event': [
            "[EVENT] in [TIME]. You've got this! 💪",
            "[TIME] until [EVENT]. Go show them what you've got.",
            "[EVENT] is coming up in [TIME]. I believe in you!"
        ],
        'post_event': [
            "How did [EVENT] go? How are you feeling about it?",
            "You survived [EVENT]! How did it go?",
            "Tell me about [EVENT] - how did you do?"
        ]
    },
    
    'presentation': {
        'pre_event': [
            "[EVENT] in [TIME]. You know this material. You're prepared. Trust yourself.",
            "[TIME] until [EVENT]. Take a deep breath. You've got this.",
            "[EVENT] is almost here ([TIME]). Everyone gets nervous. Channel it into energy."
        ],
        'post_event': [
            "How did [EVENT] go? Proud of you for doing it!",
            "You did [EVENT]! That took courage. How do you feel?",
            "Tell me everything about [EVENT]. How did it go?"
        ]
    },
    
    'stressful': {
        'pre_event': [
            "[EVENT] in [TIME]. I know you're anxious. That's okay. One step at a time.",
            "[TIME] until [EVENT]. Remember: you don't have to be perfect. Just be you.",
            "Almost time for [EVENT] ([TIME]). It's okay to be nervous. I'm here. ❤️"
        ],
        'post_event': [
            "Survived [EVENT]? How bad was it?",
            "How did [EVENT] go? Want some sympathy? I'm here for it. 😊",
            "[EVENT] is done! Are you okay? How are you feeling?"
        ]
    },
    
    'fun': {
        'pre_event': [
            "[EVENT] in [TIME]! Have a great time!",
            "Almost time for [EVENT]! Enjoy yourself! 😊",
            "[TIME] until [EVENT]. Have fun! You deserve it."
        ],
        'post_event': [
            "How was [EVENT]? Did you have a good time?",
            "How did [EVENT] go? I hope it was fun!",
            "You're back from [EVENT]! Tell me about it - how was it?"
        ]
    },
    
    'important': {
        'pre_event': [
            "I know [EVENT] is a big deal. [TIME] to go. You're ready for this.",
            "[EVENT] in [TIME]. This is important to you. You've prepared. Now trust yourself.",
            "[TIME] until [EVENT]. Whatever the outcome, I'm proud of you for showing up."
        ],
        'post_event': [
            "How did [EVENT] go? I know it was important to you.",
            "Tell me everything about [EVENT]. How do you feel about how it went?",
            "[EVENT] is over. How are you processing it all?"
        ]
    },
    
    'private': {
        'pre_event': None,  # No reminder for private events
        'post_event': [
            "Hey. Hope your afternoon went okay. ❤️",
            "Thinking of you. Hope everything is okay.",
            "Here if you need me. ❤️"
        ]
    },
    
    'routine': {
        'pre_event': None,  # No reminder for routine events
        'post_event': None   # No follow-up for routine events
    }
}
