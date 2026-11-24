"""/remind: reminders stored in Postgres, so they survive restarts and redeploys."""
from __future__ import annotations

import datetime as dt
import logging
import re

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger("bot.reminders")

MAX_PER_USER = 25
MAX_DELAY = dt.timedelta(days=365)
UNITS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}
PART = re.compile(r"(\d+)\s*([wdhms])")


def parse_delay(text: str) -> dt.timedelta | None:
    """'90' (minutes), '10m', '1h30m', '2d 4h', '1w' -> timedelta; None if invalid."""
    text = text.strip().lower()
    if text.isdigit():
        seconds = int(text) * 60
    else:
        compact = text.replace(" ", "")
        parts = PART.findall(compact)
        if not parts or "".join(n + u for n, u in parts) != compact:
            return None
        seconds = sum(int(n) * UNITS[u] for n, u in parts)
    if seconds < 1:
        return None
    delay = dt.timedelta(seconds=seconds)
    return delay if delay <= MAX_DELAY else None


class Reminders(commands.GroupCog, group_name="remind", group_description="Reminders"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    async def cog_load(self) -> None:
        if self.bot.pool is not None:
            self.deliver.start()

    async def cog_unload(self) -> None:
        self.deliver.cancel()

    async def _need_db(self, interaction: discord.Interaction) -> bool:
        if self.bot.pool is None:
            await interaction.response.send_message("Reminders need the database (DATABASE_URL).", ephemeral=True)
            return False
        return True

    @app_commands.command(name="me", description="Remind you in this channel later")
    @app_commands.describe(when="Delay, e.g. 10m, 1h30m, 2d (a plain number means minutes)", message="What to remind you of")
    async def me(self, interaction: discord.Interaction, when: str, message: app_commands.Range[str, 1, 1500]) -> None:
        if not await self._need_db(interaction):
            return
        delay = parse_delay(when)
        if delay is None:
            await interaction.response.send_message(
                "I couldn't read that delay. Use e.g. `10m`, `1h30m`, `2d` (up to 365 days).", ephemeral=True
            )
            return
        pool = self.bot.pool
        count = await pool.fetchval("SELECT count(*) FROM reminders WHERE user_id = $1", interaction.user.id)
        if count >= MAX_PER_USER:
            await interaction.response.send_message(
                f"You already have {MAX_PER_USER} reminders. Cancel one with `/remind cancel`.", ephemeral=True
            )
            return
        due = discord.utils.utcnow() + delay
        reminder_id = await pool.fetchval(
            "INSERT INTO reminders (user_id, channel_id, guild_id, message, due_at) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING id",
            interaction.user.id, interaction.channel_id, interaction.guild_id, message, due,
        )
        await interaction.response.send_message(
            f"Reminder #{reminder_id} set for {discord.utils.format_dt(due, 'F')} "
            f"({discord.utils.format_dt(due, 'R')}).",
            ephemeral=True,
        )

    @app_commands.command(name="list", description="Your pending reminders")
    async def list_(self, interaction: discord.Interaction) -> None:
        if not await self._need_db(interaction):
            return
        rows = await self.bot.pool.fetch(
            "SELECT id, message, due_at FROM reminders WHERE user_id = $1 ORDER BY due_at LIMIT $2",
            interaction.user.id, MAX_PER_USER,
        )
        if not rows:
            await interaction.response.send_message("You have no pending reminders.", ephemeral=True)
            return
        lines = [
            f"#{r['id']} {discord.utils.format_dt(r['due_at'], 'R')}: {discord.utils.escape_markdown(r['message'][:80])}"
            for r in rows
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="cancel", description="Cancel one of your reminders")
    @app_commands.describe(reminder_id="The number shown by /remind list")
    async def cancel(self, interaction: discord.Interaction, reminder_id: int) -> None:
        if not await self._need_db(interaction):
            return
        deleted = await self.bot.pool.fetchval(
            "DELETE FROM reminders WHERE id = $1 AND user_id = $2 RETURNING id", reminder_id, interaction.user.id
        )
        text = f"Reminder #{reminder_id} cancelled." if deleted else f"You have no reminder #{reminder_id}."
        await interaction.response.send_message(text, ephemeral=True)

    @tasks.loop(seconds=10)
    async def deliver(self) -> None:
        try:
            rows = await self.bot.pool.fetch(
                "DELETE FROM reminders WHERE id IN ("
                " SELECT id FROM reminders WHERE due_at <= now() ORDER BY due_at LIMIT 20 FOR UPDATE SKIP LOCKED"
                ") RETURNING id, user_id, channel_id, message, created_at"
            )
        except (OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as err:
            log.warning("Reminder loop: database error %s; retrying in 10 s", type(err).__name__)
            return
        for row in rows:
            try:
                await self._send(row)
            except Exception:  # one bad reminder must not stop the loop
                log.exception("Reminder #%s failed", row["id"])

    @deliver.before_loop
    async def _wait_ready(self) -> None:
        await self.bot.wait_until_ready()

    async def _send(self, row) -> None:
        text = (
            f"<@{row['user_id']}> reminder from {discord.utils.format_dt(row['created_at'], 'R')}: "
            f"{row['message']}"
        )
        mentions = discord.AllowedMentions(everyone=False, roles=False, users=[discord.Object(row["user_id"])])
        try:
            channel = self.bot.get_channel(row["channel_id"]) or await self.bot.fetch_channel(row["channel_id"])
            await channel.send(text, allowed_mentions=mentions)
            return
        except (discord.Forbidden, discord.NotFound, AttributeError):
            pass
        except discord.HTTPException as err:
            log.warning("Reminder #%s: channel send failed: %s", row["id"], err)
        try:  # channel gone or not writable: try a direct message
            user = await self.bot.fetch_user(row["user_id"])
            await user.send(text)
        except discord.HTTPException as err:
            log.warning("Reminder #%s could not be delivered: %s", row["id"], err)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reminders(bot))
