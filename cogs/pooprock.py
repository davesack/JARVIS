# cogs/pooprock.py
import json
import random
from pathlib import Path
from datetime import datetime, timedelta, date
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from discord import app_commands

from config import POOPROCK_CONFIG


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def now():
    return datetime.utcnow()


def brown():
    return discord.Color.from_rgb(139, 69, 19)


def format_duration(td: timedelta) -> str:
    seconds = int(td.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)

    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or not parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return ", ".join(parts)


def month_key(d: date):
    return f"{d.year}-{d.month:02d}"


def quarter_key(d: date):
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def year_key(d: date):
    return str(d.year)


def pick_gif(folder: Path):
    if not folder.exists():
        return None
    files = list(folder.glob("*"))
    return random.choice(files) if files else None


# ──────────────────────────────────────────────────────────────
# Ceremonial subtitles
# ──────────────────────────────────────────────────────────────

TRANSFER_SUBTITLES = [
    "The burden has been ceremonially reassigned.",
    "A sacred passing of questionable responsibility.",
    "The rock chooses its next victim.",
    "Balance in the universe has been… adjusted.",
    "The ritual transfer is complete.",
    "History repeats itself, messily.",
    "The Poop Rock has found fresh hands.",
    "A moment of silence for the former holder.",
    "Another chapter in the saga is written.",
    "The curse migrates onward.",
    "No refunds. No takebacks.",
    "Destiny smells faintly worse.",
    "And so the cycle continues.",
    "The throne has changed occupants.",
    "Witnessed by all. Envied by none.",
    "A bold move. A terrible fate.",
    "The burden travels ever onward.",
    "Ceremony complete. Consequences pending.",
    "The rock demands novelty.",
    "A new era begins."
]

FOUND_SUBTITLES = [
    "Oh no. Oh *no*.",
    "This is not what today was supposed to be.",
    "Mistakes were made.",
    "So close to being clean.",
    "You can practically hear the sigh.",
    "Fate has a cruel sense of humor.",
    "The universe points and laughs.",
    "An unfortunate discovery.",
    "Hope was briefly alive.",
    "Denial lasted mere seconds.",
    "You *almost* got away with it.",
    "This is how legends fall.",
    "Tragic. Predictable. Hilarious.",
    "You touched it. That’s on you.",
    "A terrible realization dawns.",
    "Clean hands? Not anymore.",
    "The rock reveals itself.",
    "All victories are temporary.",
    "So much for a clean streak.",
    "Acceptance comes quickly."
]

REMINDER_SUBTITLES = [
    "It still remembers you.",
    "Time has not absolved you.",
    "The rock grows impatient.",
    "It has been watching.",
    "Your watch continues.",
    "Still holding. Still accountable.",
    "No one has forgotten.",
    "The burden remains.",
    "Tick. Tock.",
    "Clean hands remain a dream.",
    "History is being recorded.",
    "Others grow suspicious.",
    "How long can this last?",
    "Responsibility weighs heavy.",
    "Time does not heal this.",
    "Still yours. Still awkward.",
    "The clock keeps ticking.",
    "The rock waits.",
    "This could have been avoided.",
    "Yet here we are."
]


# ──────────────────────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────────────────────

class PoopRock(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = POOPROCK_CONFIG

        self.guild_id = self.cfg["guild_id"]
        self.channel_id = self.cfg["channel_id"]

        self.data_dir = Path(self.cfg.get("data_dir", "data/pooprock"))
        self.media_dir = Path("media/pooprock_gifs")

        self.state_f = self.data_dir / "state.json"
        self.history_f = self.data_dir / "history.json"
        self.stats_f = self.data_dir / "stats.json"
        self.meta_f = self.data_dir / "meta.json"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._ensure_files()

        self.reminder_loop.start()
        self.monthly_recap_loop.start()
        self.quarterly_recap_loop.start()
        self.yearly_recap_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()
        self.monthly_recap_loop.cancel()
        self.quarterly_recap_loop.cancel()
        self.yearly_recap_loop.cancel()

    # ───────────────────────────────
    # File handling
    # ───────────────────────────────

    def _ensure_files(self):
        if not self.state_f.exists():
            self._write(self.state_f, {"holder": None, "since": None})

        if not self.history_f.exists():
            self._write(self.history_f, [])

        if not self.stats_f.exists():
            self._write(self.stats_f, {"users": {}, "buckets": {}})

        if not self.meta_f.exists():
            self._write(self.meta_f, {
                "version": 1,
                "last_monthly": None,
                "last_quarterly": None,
                "last_yearly": None
            })

    def _read(self, path):
        return json.loads(path.read_text("utf-8"))

    def _write(self, path, data):
        path.write_text(json.dumps(data, indent=2), "utf-8")

    # ───────────────────────────────
    # Stats recording
    # ───────────────────────────────

    def _record_hold(self, user_id: int, duration: timedelta, ts: datetime):
        stats = self._read(self.stats_f)

        u = stats["users"].setdefault(str(user_id), {
            "total_holds": 0,
            "total_time": 0,
            "longest_hold": 0
        })

        u["total_holds"] += 1
        u["total_time"] += int(duration.total_seconds())
        u["longest_hold"] = max(u["longest_hold"], int(duration.total_seconds()))

        for key in (
            month_key(ts.date()),
            quarter_key(ts.date()),
            year_key(ts.date())
        ):
            b = stats["buckets"].setdefault(key, {"holds": 0, "time": 0})
            b["holds"] += 1
            b["time"] += int(duration.total_seconds())

        self._write(self.stats_f, stats)

    # ───────────────────────────────
    # Core state
    # ───────────────────────────────

    def _get_state(self):
        return self._read(self.state_f)

    def _set_state(self, holder_id):
        self._write(self.state_f, {
            "holder": holder_id,
            "since": now().isoformat() if holder_id else None
        })

    # ───────────────────────────────
    # Slash commands (transfer + found)
    # ───────────────────────────────

    @app_commands.command(name="pooprock_transfer", description="Transfer the Poop Rock.")
    async def transfer(self, interaction: discord.Interaction, member: discord.Member):
        state = self._get_state()

        if interaction.user.id != state["holder"]:
            await interaction.response.send_message("❌ You don’t have the Poop Rock.", ephemeral=True)
            return

        since = datetime.fromisoformat(state["since"])
        duration = now() - since

        self._record_hold(interaction.user.id, duration, now())
        self._set_state(member.id)

        embed = discord.Embed(
            title="💩 Poop Rock Transferred",
            description=random.choice(TRANSFER_SUBTITLES),
            color=brown()
        )

        embed.set_thumbnail(url="attachment://profile.webp")
        embed.add_field(name="From", value=interaction.user.mention)
        embed.add_field(name="To", value=member.mention)
        embed.add_field(name="Time Held", value=format_duration(duration), inline=False)
        embed.set_footer(text="Pooprock Accountability System™")

        gif = pick_gif(self.media_dir / "transfer")
        files = []
        if gif:
            files.append(discord.File(gif, filename=gif.name))
            embed.set_image(url=f"attachment://{gif.name}")

        await interaction.response.send_message(
            embed=embed,
            files=[discord.File("media/pooprock_gifs/profile.webp", "profile.webp")] + files
        )

    @app_commands.command(name="pooprock_found", description="You found the Poop Rock.")
    async def found(self, interaction: discord.Interaction):
        state = self._get_state()

        prev = state["holder"]
        prev_since = datetime.fromisoformat(state["since"]) if state["since"] else None

        if prev_since:
            duration = now() - prev_since
            self._record_hold(prev, duration, now())

        self._set_state(interaction.user.id)

        embed = discord.Embed(
            title="😬 Poop Rock Found",
            description=random.choice(FOUND_SUBTITLES),
            color=brown()
        )

        embed.set_thumbnail(url="attachment://profile.webp")
        embed.add_field(name="New Holder", value=interaction.user.mention)

        if prev_since:
            embed.add_field(
                name="Previous Hold",
                value=format_duration(duration),
                inline=False
            )

        embed.set_footer(text="Pooprock Accountability System™")

        gif = pick_gif(self.media_dir / "found")
        files = []
        if gif:
            files.append(discord.File(gif, filename=gif.name))
            embed.set_image(url=f"attachment://{gif.name}")

        await interaction.response.send_message(
            embed=embed,
            files=[discord.File("media/pooprock_gifs/profile.webp", "profile.webp")] + files
        )

    # ───────────────────────────────
    # Reminder loop
    # ───────────────────────────────

    @tasks.loop(hours=24)
    async def reminder_loop(self):
        if not self.cfg.get("enabled", True):
            return

        state = self._get_state()
        if not state["holder"]:
            return

        since = datetime.fromisoformat(state["since"])
        if (now() - since).days < self.cfg.get("reminder_days", 3):
            return

        guild = self.bot.get_guild(self.guild_id)
        channel = guild.get_channel(self.channel_id)
        member = guild.get_member(state["holder"])

        embed = discord.Embed(
            title="⏰ Poop Rock Reminder",
            description=random.choice(REMINDER_SUBTITLES),
            color=discord.Color.red()
        )

        embed.add_field(
            name="Time Held",
            value=format_duration(now() - since),
            inline=False
        )
        embed.set_footer(text="Pooprock Accountability System™")

        gif = pick_gif(self.media_dir / "reminders")
        if gif:
            embed.set_image(url=f"attachment://{gif.name}")
            await channel.send(
                embed=embed,
                files=[discord.File(gif, filename=gif.name)]
            )
        else:
            await channel.send(embed=embed)

    # ───────────────────────────────
    # Automatic Recaps
    # ───────────────────────────────

    @tasks.loop(hours=24)
    async def monthly_recap_loop(self):
        today = date.today()
        if today.day != 1:
            return

        meta = self._read(self.meta_f)
        last_month = month_key(today.replace(day=1) - timedelta(days=1))

        if meta["last_monthly"] == last_month:
            return

        await self._post_recap("recap_monthly", last_month)
        meta["last_monthly"] = last_month
        self._write(self.meta_f, meta)

    @tasks.loop(hours=24)
    async def quarterly_recap_loop(self):
        today = date.today()
        if today.month not in (1, 4, 7, 10) or today.day != 1:
            return

        meta = self._read(self.meta_f)
        prev = today.replace(day=1) - timedelta(days=1)
        qk = quarter_key(prev)

        if meta["last_quarterly"] == qk:
            return

        await self._post_recap("recap_quarterly", qk)
        meta["last_quarterly"] = qk
        self._write(self.meta_f, meta)

    @tasks.loop(hours=24)
    async def yearly_recap_loop(self):
        today = date.today()
        if today.month != 1 or today.day != 1:
            return

        meta = self._read(self.meta_f)
        y = str(today.year - 1)

        if meta["last_yearly"] == y:
            return

        await self._post_recap("recap_yearly", y)
        meta["last_yearly"] = y
        self._write(self.meta_f, meta)

    async def _post_recap(self, folder_name: str, label: str):
        guild = self.bot.get_guild(self.guild_id)
        channel = guild.get_channel(self.channel_id)

        embed = discord.Embed(
            title="📊 Poop Rock Recap",
            description=f"**Period:** {label}",
            color=brown()
        )
        embed.set_footer(text="Pooprock Accountability System™")

        gif = pick_gif(self.media_dir / folder_name)
        if gif:
            embed.set_image(url=f"attachment://{gif.name}")
            await channel.send(
                embed=embed,
                files=[discord.File(gif, filename=gif.name)]
            )
        else:
            await channel.send(embed=embed)

    @reminder_loop.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(PoopRock(bot))
