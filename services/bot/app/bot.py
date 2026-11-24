"""The bot: a discord.py commands.Bot with slash commands loaded from cogs.

To add a feature, create a module in app/cogs/ with an async setup(bot)
function and list it in EXTENSIONS.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from . import db
from .config import Config
from .health import Health

log = logging.getLogger("bot")

# This starter has no voice features (no music bots: see README), so the
# missing voice libraries are expected and need no warning.
discord.VoiceClient.warn_nacl = False
discord.VoiceClient.warn_dave = False

EXTENSIONS = ("app.cogs.general", "app.cogs.reminders", "app.cogs.tags")
VERSION = "1.0.0"


class StarterBot(commands.Bot):
    def __init__(self, config: Config, pool: asyncpg.Pool | None, health: Health) -> None:
        intents = discord.Intents.default()  # no privileged intents needed
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
            activity=discord.Game(name=config.activity) if config.activity else None,
            # Nobody gets pinged by text the bot repeats unless a command allows it.
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.config = config
        self.pool = pool
        self.health = health
        self.started_at = time.time()
        self.version = VERSION

    async def setup_hook(self) -> None:
        for name in EXTENSIONS:
            await self.load_extension(name)
        self.tree.on_error = self.on_app_command_error
        await self.sync_commands()

    async def sync_commands(self) -> None:
        """Register slash commands with Discord, only when they changed.

        Global commands can take a while to show up in every server, and
        Discord rate-limits syncing; DISCORD_GUILD_ID syncs to one server
        instantly (handy while developing).
        """
        guild = discord.Object(id=self.config.guild_id) if self.config.guild_id else None
        if guild:
            self.tree.copy_global_to(guild=guild)
        payload = [cmd.to_dict(self.tree) for cmd in self.tree.get_commands(guild=guild)]
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        key = f"commands:{self.application_id}:{self.config.guild_id or 'global'}"
        if self.pool is not None and await db.get_meta(self.pool, key) == digest:
            log.info("Slash commands unchanged; skipping sync")
            return
        synced = await self.tree.sync(guild=guild)
        where = f"server {self.config.guild_id}" if guild else "all servers (global)"
        log.info("Synced %d slash commands to %s", len(synced), where)
        if self.pool is not None:
            await db.set_meta(self.pool, key, digest)

    async def on_ready(self) -> None:
        user = self.user
        self.health.set("running", f"{user} in {len(self.guilds)} servers")
        log.info("Logged in as %s (id %s) in %d servers", user, user.id if user else "?", len(self.guilds))
        if user and not self.guilds:
            invite = discord.utils.oauth_url(
                user.id,
                permissions=discord.Permissions(view_channel=True, send_messages=True, embed_links=True),
                scopes=("bot", "applications.commands"),
            )
            log.info("The bot is in no server yet. Invite it with: %s", invite)

    async def on_resumed(self) -> None:
        self.health.set("running", f"{self.user} in {len(self.guilds)} servers")

    async def on_disconnect(self) -> None:
        self.health.set("reconnecting")

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            message = "You can't use this command here."
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"Slow down: try again in {error.retry_after:.0f} s."
        else:
            log.exception("Command %s failed", interaction.command and interaction.command.name, exc_info=error)
            message = "Something went wrong. The error is in the bot's log."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
