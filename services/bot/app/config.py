"""Settings from environment variables.

Values typed into Railway's deploy form must never stop the service: an
invalid value falls back to its default with a warning in the log.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

log = logging.getLogger("bot.config")

DEFAULT_PORT = 8080
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass(frozen=True)
class Config:
    token: str
    database_url: str
    guild_id: int | None
    port: int
    log_level: str
    activity: str


def _port() -> int:
    value = os.environ.get("PORT", "").strip()
    if value.isdigit() and 1 <= int(value) <= 65535:
        return int(value)
    if value:
        log.warning("PORT=%r is not a port number; using %s", value, DEFAULT_PORT)
    return DEFAULT_PORT


def _guild_id() -> int | None:
    value = os.environ.get("DISCORD_GUILD_ID", "").strip()
    if not value:
        return None
    if value.isdigit() and 15 <= len(value) <= 21:
        return int(value)
    log.warning("DISCORD_GUILD_ID=%r is not a server id; syncing commands globally", value)
    return None


def _token() -> str:
    token = os.environ.get("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    # People often paste the header form "Bot <token>".
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    return token


def log_level() -> str:
    value = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    return value if value in LOG_LEVELS else "INFO"


def load() -> Config:
    return Config(
        token=_token(),
        database_url=os.environ.get("DATABASE_URL", "").strip(),
        guild_id=_guild_id(),
        port=_port(),
        log_level=log_level(),
        activity=os.environ.get("BOT_ACTIVITY", "/help").strip()[:120],
    )
