from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Dict

import discord
from discord.ext import commands
from discord import app_commands

from config import DATA_ROOT

# ============================================================
# CONSTANTS
# ============================================================

ROWS = 6
COLS = 7

EMPTY = "⚫"
P1 = "🔴"
P2 = "🟡"

LOBBY_TIMEOUT = 60
TURN_TIMEOUT = 60
WARNING_TIME = 10  # seconds before turn timeout

ROOT = DATA_ROOT / "games" / "connect4"
ROOT.mkdir(parents=True, exist_ok=True)
STATE_FILE = ROOT / "state.json"


# ============================================================
# UTIL
# ============================================================

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def empty_board():
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]


def render_board(board):
    header = "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"
    rows = ["".join(row) for row in board]
    return header + "\n" + "\n".join(rows)


def drop_piece(board, col, token):
    for r in reversed(range(ROWS)):
        if board[r][col] == EMPTY:
            board[r][col] = token
            return True
    return False


def check_winner(board, token):
    for r in range(ROWS):
        for c in range(COLS - 3):
            if all(board[r][c+i] == token for i in range(4)):
                return True

    for r in range(ROWS - 3):
        for c in range(COLS):
            if all(board[r+i][c] == token for i in range(4)):
                return True

    for r in range(3, ROWS):
        for c in range(COLS - 3):
            if all(board[r-i][c+i] == token for i in range(4)):
                return True

    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            if all(board[r+i][c+i] == token for i in range(4)):
                return True

    return False


# ============================================================
# VIEWS
# ============================================================

class LobbyView(discord.ui.View):
    def __init__(self, cog, cid: str):
        super().__init__(timeout=LOBBY_TIMEOUT)
        self.cog = cog
        self.cid = cid

    @discord.ui.button(label="Accept Challenge", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.state.get(self.cid)
        if not game or game["status"] != "lobby":
            return

        uid = str(interaction.user.id)
        creator = game["players"][0]
        challenged = game.get("challenged")

        if uid == creator:
            await interaction.response.send_message(
                "❌ You can’t accept your own lobby.",
                ephemeral=True
            )
            return

        if challenged and uid != challenged:
            await interaction.response.send_message(
                "❌ This challenge isn’t for you.",
                ephemeral=True
            )
            return

        game["players"].append(uid)
        game["status"] = "active"
        save_json(STATE_FILE, self.cog.state)

        view = GameView(self.cog, self.cid)
        self.cog.views[self.cid] = view
        self.cog.start_warning_timer(self.cid)

        board = render_board(game["board"])
        await interaction.response.edit_message(
            content=f"{board}\n\n➡️ <@{creator}>'s turn",
            view=view
        )

    async def on_timeout(self):
        game = self.cog.state.get(self.cid)
        if not game or game["status"] != "lobby":
            return

        channel = self.cog.bot.get_channel(int(self.cid))
        if channel:
            await channel.send("⏱️ **Connect 4 lobby expired.**")

        self.cog.end_game(self.cid)


class GameView(discord.ui.View):
    def __init__(self, cog, cid: str):
        super().__init__(timeout=TURN_TIMEOUT)
        self.cog = cog
        self.cid = cid

        for i in range(COLS):
            self.add_item(GameButton(i))

    async def on_timeout(self):
        game = self.cog.state.get(self.cid)
        if not game or game["status"] != "active":
            return

        loser = game["players"][game["turn"]]
        winner = game["players"][1 - game["turn"]]

        self.cog.record_result(winner, loser, "timeout")

        channel = self.cog.bot.get_channel(int(self.cid))
        if channel:
            await channel.send(
                f"⏱️ <@{loser}> took too long.\n"
                f"🎉 <@{winner}> wins by forfeit!"
            )

        self.cog.end_game(self.cid)


class GameButton(discord.ui.Button):
    def __init__(self, col: int):
        super().__init__(
            label=str(col + 1),
            style=discord.ButtonStyle.secondary
        )
        self.col = col

    async def callback(self, interaction: discord.Interaction):
        cog: GamesConnect4 = interaction.client.get_cog("GamesConnect4")
        cid = str(interaction.channel_id)
        game = cog.state.get(cid)

        if not game or game["status"] != "active":
            return

        uid = str(interaction.user.id)

        if uid not in game["players"]:
            await interaction.response.send_message(
                "👀 You’re spectating.",
                ephemeral=True
            )
            return

        if game["players"][game["turn"]] != uid:
            await interaction.response.send_message(
                "⛔ Not your turn.",
                ephemeral=True
            )
            return

        token = P1 if game["turn"] == 0 else P2

        if not drop_piece(game["board"], self.col, token):
            await interaction.response.send_message(
                "❌ Column full.",
                ephemeral=True
            )
            return

        cog.cancel_warning_timer(cid)
        board = render_board(game["board"])

        if check_winner(game["board"], token):
            winner = uid
            loser = game["players"][1 - game["turn"]]

            cog.record_result(winner, loser, "win")

            await interaction.response.edit_message(
                content=f"{board}\n\n🎉 <@{winner}> wins!",
                view=None
            )
            cog.end_game(cid)
            return

        game["turn"] = 1 - game["turn"]
        save_json(STATE_FILE, cog.state)

        next_uid = game["players"][game["turn"]]
        view = GameView(cog, cid)
        cog.views[cid] = view
        cog.start_warning_timer(cid)

        await interaction.response.edit_message(
            content=f"{board}\n\n➡️ <@{next_uid}>'s turn",
            view=view
        )


# ============================================================
# COG
# ============================================================

class GamesConnect4(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state: Dict[str, Dict] = load_json(STATE_FILE, {})
        self.views: Dict[str, discord.ui.View] = {}
        self.warning_tasks: Dict[str, asyncio.Task] = {}

    # --------------------------------------------------------

    def end_game(self, cid: str):
        self.cancel_warning_timer(cid)
        self.state.pop(cid, None)
        save_json(STATE_FILE, self.state)
        self.views.pop(cid, None)

    # --------------------------------------------------------
    # TIMEOUT WARNING
    # --------------------------------------------------------

    def start_warning_timer(self, cid: str):
        self.cancel_warning_timer(cid)
        task = self.bot.loop.create_task(self._send_warning(cid))
        self.warning_tasks[cid] = task

    def cancel_warning_timer(self, cid: str):
        task = self.warning_tasks.pop(cid, None)
        if task:
            task.cancel()

    async def _send_warning(self, cid: str):
        try:
            await asyncio.sleep(TURN_TIMEOUT - WARNING_TIME)
            game = self.state.get(cid)
            if not game or game["status"] != "active":
                return

            uid = game["players"][game["turn"]]
            channel = self.bot.get_channel(int(cid))
            if channel:
                await channel.send(
                    f"⏰ <@{uid}> **10 seconds remaining!**"
                )
        except asyncio.CancelledError:
            pass

    # --------------------------------------------------------
    # LEADERBOARD HOOK
    # --------------------------------------------------------

    def record_result(self, winner_id: str, loser_id: str, reason: str):
        result = {
            "game": "connect4",
            "winner": winner_id,
            "loser": loser_id,
            "reason": reason,  # "win" | "timeout"
            "timestamp": int(time.time())
        }

        leaderboard = self.bot.get_cog("Rankings")  # adjust if needed
        if leaderboard:
            leaderboard.record_game(result)

    # --------------------------------------------------------
    # SLASH COMMAND
    # --------------------------------------------------------

    @app_commands.command(name="connect4_start", description="Open a Connect 4 lobby")
    async def connect4_start(self, interaction: discord.Interaction):
        cid = str(interaction.channel_id)

        if cid in self.state:
            await interaction.response.send_message(
                "❌ A game is already running here.",
                ephemeral=True
            )
            return

        self.state[cid] = {
            "players": [str(interaction.user.id)],
            "turn": 0,
            "board": empty_board(),
            "status": "lobby"
        }
        save_json(STATE_FILE, self.state)

        view = LobbyView(self, cid)
        self.views[cid] = view

        await interaction.response.send_message(
            f"🎮 **Connect 4 Lobby Open**\n"
            f"<@{interaction.user.id}> is waiting for an opponent.\n"
            f"⏱️ Lobby expires in 60s.",
            view=view
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesConnect4(bot))
