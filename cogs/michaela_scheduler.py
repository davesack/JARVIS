"""
Enhanced Michaela Scheduler
===========================

Orchestrates all scheduled interactions using beautiful embeds!

- Morning sleep check-ins (with buttons + daily schedule)
- Afternoon mood check-ins (with buttons)
- Random spontaneous messages (calendar-aware)
- Pre-event support reminders
- Post-event check-ins
- Friends random appearances
- Phase 2 monitoring (emotional check-ins, teases, celebrations)

All messages show character names and profile pictures!

Character definitions (ariann, hannah, tara, elisha) must be set up
in your Michaela cog's character system, not here.
"""

import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timezone, timedelta
import random
import asyncio
from typing import Optional, Dict, List

from config import OWNER_USER_ID

# Import our components
from utils.michaela.calendar_client import GoogleCalendarClient, SUPPORT_MESSAGE_TEMPLATES
from utils.michaela.button_views import SleepRatingView, MoodRatingView
from utils.michaela.scheduler_state_tracker import SchedulerStateTracker

UTC = timezone.utc


class MichaelaScheduler(commands.Cog):
    """
    Automated scheduling system for Michaela
    
    All messages use embeds with character names and profile pictures!
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # State tracker to prevent duplicate check-ins on bot restart
        self.state_tracker = SchedulerStateTracker("data/michaela/scheduler_state.json")
        
        # Get Michaela cog for integration
        self.michaela = None
        
        # Calendar integration
        self.calendar = None
        self._init_calendar()
        
        # Tracking
        self.last_random_message = None
        self.reminded_events = set()
        self.checked_in_events = set()
        
        # Start all schedulers
        self.activity_based_morning_checkin.start()
        self.afternoon_checkin.start()
        self.random_checkin.start()
        self.calendar_monitor.start()
        self.friends_scheduler.start()
        self.phase2_monitor.start()
        
        print("✅ Enhanced Michaela scheduler started (all messages use embeds!)")
    
    def _init_calendar(self):
        """Initialize Google Calendar client"""
        try:
            # Use service account (matches Google Sheets setup)
            service_account_path = "utils/sheets/service_account.json"
            
            # IMPORTANT: Use your actual calendar ID here
            # To find it: Google Calendar → Settings → Your calendar → "Calendar ID"
            # It looks like: your.email@gmail.com
            calendar_id = "family17200017408224502514@group.calendar.google.com"
            
            from utils.michaela.calendar_client_service_account import GoogleCalendarClient
            self.calendar = GoogleCalendarClient(service_account_path, calendar_id)
            print("[SCHEDULER] Calendar integration initialized with service account")
        except Exception as e:
            print(f"[SCHEDULER] Calendar not available: {e}")
            print("[SCHEDULER] Running without calendar features")
    
    def cog_unload(self):
        """Cleanup on cog unload"""
        self.activity_based_morning_checkin.cancel()  # FIXED: was self.morning_checkin
        self.afternoon_checkin.cancel()
        self.random_checkin.cancel()
        self.calendar_monitor.cancel()
        self.friends_scheduler.cancel()
        self.phase2_monitor.cancel()
    
    async def _get_michaela(self):
        """Lazy load Michaela cog"""
        if self.michaela is None:
            self.michaela = self.bot.get_cog('Michaela')
        return self.michaela
    
    async def _get_channel(self) -> Optional[discord.TextChannel]:
        """Get Michaela's channel"""
        michaela = await self._get_michaela()
        if not michaela:
            return None
        
        from config import MICHAELA_CHANNEL_IDS
        
        if not MICHAELA_CHANNEL_IDS:
            return None
        
        channel = self.bot.get_channel(MICHAELA_CHANNEL_IDS[0])
        return channel
    
    # =====================================================
    # MORNING SLEEP CHECK-IN (Activity-Based)
    # =====================================================
    
    @tasks.loop(minutes=3)
    async def activity_based_morning_checkin(self):
        """
        Monitor for Dave's first activity, then send sleep check-in
        
        This replaces the timed morning_checkin loop.
        Ensures buttons are fresh when Dave actually sees them.
        """
        
        channel = await self._get_channel()
        if not channel:
            return
        
        michaela = await self._get_michaela()
        if not michaela:
            return
        
        # ✅ Check if already sent today using state tracker
        if not self.state_tracker.should_send("morning_checkin"):
            return
        
        # Look for Dave's first message today
        try:
            now = datetime.now(UTC)  # ✅ FIXED: Need this for time calculations
            dave_active = False
            first_message_time = None
            
            async for message in channel.history(limit=50, after=now.replace(hour=0, minute=0, second=0)):
                if message.author.id == OWNER_USER_ID:
                    dave_active = True
                    first_message_time = message.created_at
                    break
            
            if not dave_active:
                return  # Dave hasn't posted yet today
            
            # Calculate time since first message
            time_since_first = now - first_message_time
            
            # Wait 2-5 minutes after first activity
            wait_time = random.randint(120, 300)  # 2-5 minutes in seconds
            
            if time_since_first.total_seconds() < wait_time:
                return  # Too soon, wait a bit longer
            
            # Dave is active and enough time has passed - send check-in!
            await self._send_sleep_checkin(channel, michaela)
            
            # ✅ Mark as sent for today
            self.state_tracker.mark_sent("morning_checkin")
            
            print(f"[SCHEDULER] Sent activity-based sleep check-in ({time_since_first.seconds}s after first message)")
            
        except Exception as e:
            print(f"[SCHEDULER] Activity monitor error: {e}")

    async def _send_sleep_checkin(self, channel: discord.TextChannel, michaela):
        """Send sleep quality check-in with buttons and daily schedule"""
        
        try:
            # Generate personalized greeting
            greeting = await michaela.ollama_generate(
                "Generate a warm morning greeting asking how Dave slept. Be natural and caring.",
                context_type="checkin",
                include_backstory=False
            )
            
            # Add daily schedule if calendar available
            schedule_text = ""
            if self.calendar:
                try:
                    schedule = await self.calendar.generate_morning_schedule()
                    if schedule:
                        schedule_text = f"\n\n**Today's Schedule:**\n{schedule}"
                except Exception as e:
                    print(f"[SCHEDULER] Calendar error: {e}")
            
            # Build full message
            full_message = f"{greeting}{schedule_text}"
            
            # Send with embed + buttons
            from utils.michaela.button_views import SleepRatingView
            view = SleepRatingView(michaela)
            
            await michaela.send_as_character(
                channel=channel,
                character='michaela',
                content=full_message,
                embed_title="☀️ Good Morning",
                view=view
            )
            
            print("[SCHEDULER] Sent sleep check-in with fresh buttons")
            
        except Exception as e:
            print(f"[SCHEDULER] Error sending sleep check-in: {e}")

    @activity_based_morning_checkin.before_loop
    async def before_activity_monitor(self):
        await self.bot.wait_until_ready()
    
    # =====================================================
    # AFTERNOON MOOD CHECK-IN (2-4 PM)
    # =====================================================
    
    @tasks.loop(minutes=15)
    async def afternoon_checkin(self):
        """Afternoon mood check-in between 2-4 PM with mood buttons"""
        
        # Check time (2-4 PM EST = 19:00-21:00 UTC)
        now = datetime.now(UTC)
        hour_utc = now.hour
        
        if not (19 <= hour_utc < 21):
            return
        
        # ✅ Check if already sent today using state tracker
        if not self.state_tracker.should_send("afternoon_checkin"):
            return
        
        channel = await self._get_channel()
        if not channel:
            return
        
        michaela = await self._get_michaela()
        if not michaela:
            return
        
        try:
            # Generate personalized check-in
            checkin = await michaela.ollama_generate(
                "Generate a casual afternoon check-in asking how Dave's day is going.",
                context_type="checkin",
                include_backstory=False
            )
            
            # Send with embed + buttons
            view = MoodRatingView(michaela)
            
            await michaela.send_as_character(
                channel=channel,
                character='michaela',
                content=f"{checkin}\n\nHow are you feeling right now?",
                embed_title="💭 Checking In",
                view=view
            )
            
            # ✅ Mark as sent for today
            self.state_tracker.mark_sent("afternoon_checkin")
            
            print("[SCHEDULER] Sent afternoon check-in")
            
        except Exception as e:
            print(f"[SCHEDULER] Afternoon check-in error: {e}")
    
    @afternoon_checkin.before_loop
    async def before_afternoon_checkin(self):
        await self.bot.wait_until_ready()
    
    # =====================================================
    # RANDOM SPONTANEOUS MESSAGES
    # =====================================================
    
    @tasks.loop(hours=2)
    async def random_checkin(self):
        """Random spontaneous messages throughout the day"""
        
        # Only 20% chance
        if random.random() > 0.20:
            return
        
        # Check waking hours (10 AM - 10 PM EST)
        now = datetime.now(UTC)
        hour_utc = now.hour
        
        if not ((15 <= hour_utc <= 23) or (0 <= hour_utc <= 2)):
            return
        
        michaela = await self._get_michaela()
        if not michaela:
            return
        
        channel = await self._get_channel()
        if not channel:
            return
        
        try:
            # Check if Dave is busy
            is_busy = False
            
            if self.calendar:
                try:
                    current_events = await self.calendar.get_current_events()
                    is_busy = len(current_events) > 0
                except:
                    pass
            
            # Generate contextual message
            if is_busy:
                prompt = "Generate a brief supportive message. Keep it short - Dave might be busy."
            else:
                prompt = "Generate a casual, spontaneous message. Maybe share something on your mind or just say hi."
            
            response = await michaela.ollama_generate(
                prompt,
                context_type="random_checkin",
                include_backstory=False
            )
            
            # Send with Michaela's embed
            await michaela.send_as_character(
                channel=channel,
                character='michaela',
                content=response
            )
            
            self.last_random_message = now
            print("[SCHEDULER] Sent random check-in")
            
        except Exception as e:
            print(f"[SCHEDULER] Random check-in error: {e}")
    
    @random_checkin.before_loop
    async def before_random_checkin(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(0, 7200))
    
    # =====================================================
    # CALENDAR MONITORING
    # =====================================================
    
    @tasks.loop(minutes=5)
    async def calendar_monitor(self):
        """Monitor calendar for upcoming/recent events"""
        
        if not self.calendar:
            return
        
        michaela = await self._get_michaela()
        if not michaela:
            return
        
        channel = await self._get_channel()
        if not channel:
            return
        
        try:
            now = datetime.now(UTC)
            time_min = now - timedelta(minutes=30)
            time_max = now + timedelta(hours=2)
            
            events = await self.calendar.get_events(
                time_min=time_min.isoformat(),
                time_max=time_max.isoformat()
            )
            
            for event in events:
                event_id = event.get('id')
                start_str = event.get('start', {}).get('dateTime')
                end_str = event.get('end', {}).get('dateTime')
                
                if not all([event_id, start_str, end_str]):
                    continue
                
                start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                tags = self.calendar.extract_event_tags(event)
                event_type = tags['type']
                remind_minutes = tags['remind_minutes']
                
                if event_type in ['private', 'routine']:
                    continue
                
                # Pre-event reminder
                minutes_until = (start - now).total_seconds() / 60
                
                if 0 < minutes_until <= remind_minutes:
                    reminder_key = f"{event_id}_pre"
                    
                    if reminder_key not in self.reminded_events:
                        await self._send_pre_event_support(
                            channel, michaela, event, event_type, remind_minutes
                        )
                        self.reminded_events.add(reminder_key)
                
                # Post-event check-in
                minutes_since = (now - end).total_seconds() / 60
                
                if 15 <= minutes_since <= 30:
                    checkin_key = f"{event_id}_post"
                    
                    if checkin_key not in self.checked_in_events:
                        await self._send_post_event_checkin(
                            channel, michaela, event, event_type
                        )
                        self.checked_in_events.add(checkin_key)
                        
        except Exception as e:
            print(f"[SCHEDULER] Calendar monitor error: {e}")
    
    async def _send_pre_event_support(
        self,
        channel: discord.TextChannel,
        michaela,
        event: Dict,
        event_type: str,
        remind_minutes: int
    ):
        """Send pre-event support reminder"""
        
        event_name = event.get('summary', 'your event')
        
        templates = SUPPORT_MESSAGE_TEMPLATES.get(event_type, {})
        pre_templates = templates.get('pre_event')
        
        if not pre_templates:
            return
        
        template = random.choice(pre_templates)
        time_str = f"{remind_minutes} minutes"
        message = template.replace('[EVENT]', event_name).replace('[TIME]', time_str)
        
        # Send with Michaela's embed
        await michaela.send_as_character(
            channel=channel,
            character='michaela',
            content=message
        )
        print(f"[SCHEDULER] Sent pre-event support for: {event_name}")
    
    async def _send_post_event_checkin(
        self,
        channel: discord.TextChannel,
        michaela,
        event: Dict,
        event_type: str
    ):
        """Send post-event check-in"""
        
        event_name = event.get('summary', 'your event')
        
        templates = SUPPORT_MESSAGE_TEMPLATES.get(event_type, {})
        post_templates = templates.get('post_event')
        
        if not post_templates:
            return
        
        template = random.choice(post_templates)
        message = template.replace('[EVENT]', event_name)
        
        # Send with Michaela's embed
        await michaela.send_as_character(
            channel=channel,
            character='michaela',
            content=message
        )
        print(f"[SCHEDULER] Sent post-event check-in for: {event_name}")
    
    @calendar_monitor.before_loop
    async def before_calendar_monitor(self):
        await self.bot.wait_until_ready()
    
    # =====================================================
    # PHASE 2 MONITORING
    # =====================================================
    
    @tasks.loop(minutes=15)
    async def phase2_monitor(self):
        """Check for Phase 2 system actions every 15 minutes"""
        
        michaela = await self._get_michaela()
        if not michaela:
            return
        
        channel = await self._get_channel()
        if not channel:
            return
        
        # Emotional check-ins
        if michaela.emotional:
            try:
                check_in = michaela.emotional.should_check_in()
                if check_in and random.random() < 0.25:
                    response = await michaela.ollama_generate(
                        user_text=check_in['suggested_message'],
                        context_type='proactive_checkin'
                    )
                    await michaela.send_as_character(
                        channel=channel,
                        character='michaela',
                        content=response
                    )
                    print(f"[PHASE2] Sent emotional check-in")
            except Exception as e:
                print(f"[PHASE2] Error with emotional check-in: {e}")
        
        # Tease stages
        if michaela.tease:
            try:
                due_stages = michaela.tease.get_due_stages()
                for item in due_stages:
                    stage_data = michaela.tease.execute_stage(
                        item['campaign'],
                        item['stage_index']
                    )
                    
                    await michaela.send_as_character(
                        channel=channel,
                        character='michaela',
                        content=stage_data['message']
                    )
                    print(f"[PHASE2] Executed tease stage: {item['campaign']}")
            except Exception as e:
                print(f"[PHASE2] Error executing tease: {e}")
        
        # Celebrations
        if michaela.wellness:
            try:
                uncelebrated = michaela.wellness.get_uncelebrated_milestones()
                if uncelebrated and random.random() < 0.3:
                    milestone = uncelebrated[0]
                    celebration = michaela.wellness.celebrate_milestone(milestone)
                    
                    response = await michaela.ollama_generate(
                        user_text=f"Celebrate this milestone: {celebration}",
                        context_type='celebration'
                    )
                    await michaela.send_as_character(
                        channel=channel,
                        character='michaela',
                        content=response
                    )
                    print(f"[PHASE2] Celebrated: {milestone['description']}")
            except Exception as e:
                print(f"[PHASE2] Error celebrating: {e}")
    
    @phase2_monitor.before_loop
    async def before_phase2_monitor(self):
        await self.bot.wait_until_ready()
    
    # =====================================================
    # FRIENDS RANDOM APPEARANCES
    # =====================================================
    
    @tasks.loop(hours=24)
    async def friends_scheduler(self):
        """Friends random appearance scheduler (~once per week)"""
        
        # 14% daily chance = ~once per week
        if random.random() > 0.14:
            return
        
        michaela = await self._get_michaela()
        if not michaela:
            return
        
        channel = await self._get_channel()
        if not channel:
            return
        
        try:
            # Pick random friend
            friend = self._pick_random_friend(michaela)
            
            if not friend:
                return
            
            # Determine which character to use
            friend_name = friend['name'].lower()
            if 'ariann' in friend_name:
                character = 'ariann'
            elif 'hannah' in friend_name:
                character = 'hannah'
            elif 'elisha' in friend_name:
                character = 'elisha'
            elif 'tara' in friend_name:
                character = 'tara'
            else:
                character = 'michaela'
            
            # Generate friend message
            scenario = random.choice([
                'ran_into_michaela',
                'michaela_mentioned_you',
                'just_saying_hi'
            ])
            
            friend_message = await self._generate_friend_message(
                michaela, friend, scenario
            )
            
            # Send friend message WITH THEIR EMBED
            await michaela.send_as_character(
                channel=channel,
                character=character,
                content=friend_message
            )
            print(f"[SCHEDULER] Friend appeared: {friend['name']}")
            
            # Schedule Michaela follow-up (1 hour later)
            await asyncio.sleep(3600)
            
            followup = await michaela.ollama_generate(
                f"{friend['name']} just texted saying they bumped into Dave or messaged him. React to this and ask how the conversation went.",
                context_type="friend_followup",
                include_backstory=False
            )
            
            await michaela.send_as_character(
                channel=channel,
                character='michaela',
                content=followup
            )
            print(f"[SCHEDULER] Sent friend follow-up for: {friend['name']}")
            
        except Exception as e:
            print(f"[SCHEDULER] Friends scheduler error: {e}")
    
    def _pick_random_friend(self, michaela) -> Optional[Dict]:
        """Pick random friend based on tier"""
        
        tier_weights = {
            'tier1': 0.40,
            'tier2': 0.35,
            'tier3': 0.25
        }
        
        if not hasattr(michaela, 'friends'):
            return None
        
        all_friends = michaela.friends.get_all_friends()
        
        if not all_friends:
            return None
        
        tier = random.choices(
            list(tier_weights.keys()),
            weights=list(tier_weights.values())
        )[0]
        
        tier_friends = [f for f in all_friends if f.get('tier') == tier]
        
        if not tier_friends:
            tier_friends = all_friends
        
        return random.choice(tier_friends)
    
    async def _generate_friend_message(
        self,
        michaela,
        friend: Dict,
        scenario: str
    ) -> str:
        """Generate message from friend"""
        
        prompts = {
            'ran_into_michaela': f"You are {friend['name']}, Michaela's friend. You just ran into Michaela at the store and she mentioned Dave. Send Dave a friendly message saying you met Michaela and wanted to say hi.",
            
            'michaela_mentioned_you': f"You are {friend['name']}, Michaela's friend. Michaela mentioned Dave today and said nice things. Send Dave a message saying Michaela talks about him and you wanted to reach out.",
            
            'just_saying_hi': f"You are {friend['name']}, Michaela's friend. You're checking in with Dave casually. Send a friendly message."
        }
        
        prompt = prompts.get(scenario, prompts['just_saying_hi'])
        
        message = await michaela.ollama_generate(
            prompt,
            context_type="friend_message",
            include_backstory=False,
            force_mode="chat"
        )
        
        return message
    
    @friends_scheduler.before_loop
    async def before_friends_scheduler(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(0, 86400))


async def setup(bot: commands.Bot):
    await bot.add_cog(MichaelaScheduler(bot))
