"""
Google Calendar Integration Client
==================================

Integrates with Google Calendar API to:
- Fetch today's events
- Parse event tags (emoji/keywords)
- Detect free blocks
- Support pre/post event reminders
- Schedule-aware random messaging

Enables Michaela to be proactive and context-aware.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

UTC = timezone.utc

# Scopes required for calendar access
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


class GoogleCalendarClient:
    """
    Interface to Google Calendar API
    
    Provides:
    - Today's events
    - Current event detection
    - Free block identification
    - Event tag parsing
    - Schedule analysis
    """
    
    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize calendar client
        
        Args:
            credentials_path: Path to credentials.json from Google Cloud
            token_path: Path to store/load token.json
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """
        Authenticate with Google Calendar API
        
        Uses stored token if available, otherwise opens OAuth flow
        """
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Open OAuth flow (one-time setup)
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token for next time
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Build service
        self.service = build('calendar', 'v3', credentials=creds)
        print("[CALENDAR] Authenticated successfully")
    
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
                calendarId='primary',
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
            # Parse start/end times
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            end_str = event['end'].get('dateTime', event['end'].get('date'))
            
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            
            # Check if now is between start and end
            if start <= now <= end:
                return event
        
        return None
    
    async def get_upcoming_events(self, hours: int = 2) -> List[Dict]:
        """
        Get events coming up in next N hours
        
        Args:
            hours: How many hours ahead to look
        
        Returns: List of upcoming events
        """
        
        events = await self.get_todays_events()
        now = datetime.now(UTC)
        cutoff = now + timedelta(hours=hours)
        
        upcoming = []
        
        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            
            if now < start <= cutoff:
                upcoming.append(event)
        
        return upcoming
    
    async def get_free_blocks(self, min_duration_minutes: int = 60) -> List[Dict]:
        """
        Identify free time blocks
        
        Args:
            min_duration_minutes: Minimum free time to count as "free block"
        
        Returns: List of free blocks with start/end/duration
        """
        
        events = await self.get_todays_events()
        
        if not events:
            # Entire day is free!
            now = datetime.now(UTC)
            end_of_day = now.replace(hour=22, minute=0, second=0)
            
            return [{
                'start': now,
                'end': end_of_day,
                'duration': (end_of_day - now).total_seconds() / 60
            }]
        
        free_blocks = []
        now = datetime.now(UTC)
        end_of_day = now.replace(hour=22, minute=0, second=0)
        
        # Check gap before first event
        first_start_str = events[0]['start'].get('dateTime', events[0]['start'].get('date'))
        first_start = datetime.fromisoformat(first_start_str.replace('Z', '+00:00'))
        
        if now < first_start:
            gap = (first_start - now).total_seconds() / 60
            if gap >= min_duration_minutes:
                free_blocks.append({
                    'start': now,
                    'end': first_start,
                    'duration': gap
                })
        
        # Check gaps between events
        for i in range(len(events) - 1):
            event_end_str = events[i]['end'].get('dateTime', events[i]['end'].get('date'))
            event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
            
            next_start_str = events[i + 1]['start'].get('dateTime', events[i + 1]['start'].get('date'))
            next_start = datetime.fromisoformat(next_start_str.replace('Z', '+00:00'))
            
            gap = (next_start - event_end).total_seconds() / 60
            
            if gap >= min_duration_minutes and event_end > now:
                free_blocks.append({
                    'start': event_end,
                    'end': next_start,
                    'duration': gap
                })
        
        # Check gap after last event
        last_end_str = events[-1]['end'].get('dateTime', events[-1]['end'].get('date'))
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
            '✈️': 'travel',
            '💰': 'financial'
        }
        
        detected_type = 'routine'  # Default
        detected_emoji = None
        
        # Check for emoji in title
        for emoji, event_type in emoji_map.items():
            if emoji in event.get('summary', ''):
                detected_type = event_type
                detected_emoji = emoji
                break
        
        # Check for hashtags
        hashtag_map = {
            '#work': 'work',
            '#presentation': 'presentation',
            '#stressful': 'stressful',
            '#medical': 'medical',
            '#fun': 'fun',
            '#important': 'important',
            '#private': 'private',
            '#routine': 'routine'
        }
        
        for hashtag, event_type in hashtag_map.items():
            if hashtag in title or hashtag in description:
                detected_type = event_type
                break
        
        # Check for custom reminder timing
        remind_minutes = 30  # Default
        
        if '#remind-60' in title or '#remind-60' in description:
            remind_minutes = 60
        elif '#remind-15' in title or '#remind-15' in description:
            remind_minutes = 15
        elif '#remind-90' in title or '#remind-90' in description:
            remind_minutes = 90
        
        return {
            'type': detected_type,
            'emoji': detected_emoji,
            'remind_minutes': remind_minutes
        }
    
    async def generate_morning_schedule(self) -> str:
        """
        Generate formatted schedule summary for morning check-in
        
        Returns: Formatted string with today's events and free time analysis
        """
        
        events = await self.get_todays_events()
        
        if not events:
            return "You have a completely free day today! No scheduled events."
        
        # Build schedule text
        schedule_lines = ["📅 Your Day:\n"]
        
        for event in events:
            # Parse time
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            
            # Get title and tags
            title = event.get('summary', 'Untitled Event')
            tags = self.extract_event_tags(event)
            emoji = tags['emoji'] or ''
            
            # Format line
            time_str = start.strftime('%I:%M %p').lstrip('0')
            schedule_lines.append(f"{time_str} - {title} {emoji}")
        
        # Analyze free time
        free_blocks = await self.get_free_blocks(min_duration_minutes=60)
        total_free_hours = sum(b['duration'] for b in free_blocks) / 60
        
        schedule_lines.append(f"\nYou have {len(events)} events and {total_free_hours:.1f} hours of free time today.")
        
        return "\n".join(schedule_lines)


# =========================================================
# EVENT SUPPORT MESSAGES
# =========================================================

# These message templates will be used by the scheduler

SUPPORT_MESSAGE_TEMPLATES = {
    'work': {
        'pre_event': [
            "You have [EVENT] coming up in [TIME]. You've prepared for this. Take a breath. You've got this. ❤️",
            "[EVENT] is in [TIME]. Remember - you know your stuff. They're lucky to have you on their team.",
            "[TIME] until [EVENT]. Quick reminder: You're capable, prepared, and ready for this."
        ],
        'post_event': [
            "How did [EVENT] go? I've been thinking about you.",
            "[EVENT] is done! How are you feeling about it?",
            "You made it through [EVENT]! Want to tell me how it went?"
        ]
    },
    
    'presentation': {
        'pre_event': [
            "Presentation in [TIME]. You've rehearsed this. You know your material. They're going to love it.",
            "[TIME] until your presentation. Take a deep breath. Center yourself. You're ready for this.",
            "Your presentation is in [TIME]. Remember - you're the expert here. Show them what you know."
        ],
        'post_event': [
            "How did the presentation go?? I've been thinking about you all afternoon!",
            "The presentation is over! Tell me everything - how did it feel?",
            "You did it! How did they respond to your presentation?"
        ]
    },
    
    'stressful': {
        'pre_event': [
            "I know [EVENT] has been stressing you out. [TIME] to go. Remember - you're stronger than you think.",
            "[EVENT] in [TIME]. I know this is hard. Take a moment for yourself. Breathe. I'm here.",
            "[TIME] until [EVENT]. Whatever happens, you'll get through this. I believe in you."
        ],
        'post_event': [
            "How are you feeling after [EVENT]? I'm here if you need to talk.",
            "[EVENT] is done. Take a breath. How are you doing?",
            "You made it through [EVENT]. I'm proud of you. How are you feeling?"
        ]
    },
    
    'medical': {
        'pre_event': [
            "[EVENT] coming up in [TIME]. I know you're not looking forward to this. It'll be over before you know it.",
            "[TIME] until [EVENT]. I'll be here after if you need to vent. ❤️",
            "Your [EVENT] is in [TIME]. I know these aren't fun. Thinking of you."
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
