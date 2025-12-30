import asyncio
from utils.arena.discovery_runner import run_arena_discovery

WEEKLY_INTERVAL = 7 * 24 * 60 * 60


async def start_arena_scheduler(bot):
    print("🧠 Arena discovery scheduler started (weekly schedule only)")
    
    # REMOVED startup run - it was blocking the bot for 30+ seconds!
    # Use /admin run_discovery to trigger manually if needed
    
    while True:
        await asyncio.sleep(WEEKLY_INTERVAL)
        try:
            # Run in executor to not block the event loop
            loop = asyncio.get_event_loop()
            print("🔎 Running weekly Arena discovery...")
            logs = await loop.run_in_executor(None, run_arena_discovery)
            for log in logs:
                print(log)
        except Exception as e:
            print(f"❌ Arena discovery error: {e}")
            import traceback
            traceback.print_exc()
