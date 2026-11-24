"""Entry point: health endpoint, database, then the Discord connection.

Configuration problems (no token, wrong token, no database) never crash the
service. They are logged with what to fix, and the process stays up with a
200 health endpoint, so a deploy with a placeholder token succeeds and a
fixed variable plus redeploy is all it takes.
"""
from __future__ import annotations

import asyncio
import logging
import re
import signal

import aiohttp
import discord

from . import config as config_module
from . import db
from .bot import StarterBot
from .health import Health

log = logging.getLogger("bot")
TOKEN_HELP = (
    "Set DISCORD_TOKEN on the Bot service to your bot token "
    "(discord.com/developers/applications, your app, Bot, Reset Token) and redeploy."
)


def redact(text: str) -> str:
    """Remove passwords from connection URLs in error messages."""
    return re.sub(r"(://[^:/@\s]+:)[^@\s]+@", r"\1***@", text)


async def idle(health: Health, state: str, detail: str) -> None:
    health.set(state, detail)
    await asyncio.Event().wait()  # until Railway stops or redeploys the service


async def open_database(cfg: config_module.Config, health: Health):
    if not cfg.database_url:
        log.warning("DATABASE_URL is empty: /remind and /tag are disabled.")
        return None

    def on_wait(attempt: int, err: Exception) -> None:
        health.set("waiting-for-database", type(err).__name__)
        log.warning("Database not reachable yet (attempt %d): %s: %s",
                    attempt, type(err).__name__, redact(str(err))[:200])

    health.set("waiting-for-database")
    return await db.connect(cfg.database_url, on_wait)


async def run(cfg: config_module.Config, health: Health) -> None:
    if not cfg.token or any(ch.isspace() for ch in cfg.token):
        log.error("DISCORD_TOKEN is not set. %s", TOKEN_HELP)
        await idle(health, "not-configured", "DISCORD_TOKEN missing")
        return

    pool = await open_database(cfg, health)
    delay = 5.0
    try:
        while True:
            health.set("connecting")
            bot = StarterBot(cfg, pool, health)
            try:
                async with bot:
                    await bot.start(cfg.token, reconnect=True)
                return  # closed on purpose
            except discord.LoginFailure:
                log.error("Discord rejected DISCORD_TOKEN (wrong, reset or revoked). %s", TOKEN_HELP)
                # Retrying a bad token only risks a temporary IP ban from Discord.
                await idle(health, "token-invalid", "Discord rejected DISCORD_TOKEN")
                return
            except discord.PrivilegedIntentsRequired:
                log.error("A privileged intent is enabled in the code but not in the Developer Portal "
                          "(Bot, Privileged Gateway Intents). Enable it there or remove it from the code.")
                await idle(health, "intents-missing", "privileged intent not enabled")
                return
            except (aiohttp.ClientError, discord.GatewayNotFound, discord.HTTPException, OSError) as err:
                log.warning("Discord connection failed: %s: %s. Retrying in %.0f s",
                            type(err).__name__, str(err)[:200], delay)
                health.set("retrying", type(err).__name__)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 300.0)
    finally:
        if pool is not None:
            await pool.close()


async def main() -> None:
    logging.basicConfig(
        level=config_module.log_level(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    cfg = config_module.load()
    health = Health(cfg.port)
    await health.start()

    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)
    try:
        await run(cfg, health)
    except asyncio.CancelledError:
        log.info("Stopping")
    finally:
        await health.stop()


if __name__ == "__main__":
    asyncio.run(main())
