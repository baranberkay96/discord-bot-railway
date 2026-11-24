"""Postgres access (asyncpg pool) and the schema the starter commands use.

The schema is created with idempotent statements at every start, so a fresh
database and an existing one both work without a migration tool. Add your
own tables to SCHEMA (or switch to a migration tool when it grows).
"""
from __future__ import annotations

import asyncio
import logging

import asyncpg

log = logging.getLogger("bot.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_meta (
    key   text PRIMARY KEY,
    value text NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id         bigserial PRIMARY KEY,
    user_id    bigint      NOT NULL,
    channel_id bigint      NOT NULL,
    guild_id   bigint,
    message    text        NOT NULL,
    due_at     timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS reminders_due_at_idx ON reminders (due_at);
CREATE INDEX IF NOT EXISTS reminders_user_idx ON reminders (user_id);
CREATE TABLE IF NOT EXISTS tags (
    guild_id   bigint      NOT NULL,
    name       text        NOT NULL,
    content    text        NOT NULL,
    owner_id   bigint      NOT NULL,
    uses       integer     NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (guild_id, name)
);
"""


async def connect(url: str, on_wait) -> asyncpg.Pool:
    """Open the pool, retrying until the database answers.

    Railway starts all services at once, so Postgres may need a minute or
    two. on_wait(attempt, error) is called before every retry.
    """
    delay, attempt = 2.0, 0
    while True:
        attempt += 1
        try:
            pool = await asyncpg.create_pool(url, min_size=1, max_size=5, command_timeout=30)
            async with pool.acquire() as conn:
                await conn.execute(SCHEMA)
            log.info("Database ready")
            return pool
        except (OSError, ValueError, asyncpg.PostgresError, asyncpg.InterfaceError, asyncio.TimeoutError) as err:
            on_wait(attempt, err)
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 30.0)


async def get_meta(pool: asyncpg.Pool, key: str) -> str | None:
    return await pool.fetchval("SELECT value FROM bot_meta WHERE key = $1", key)


async def set_meta(pool: asyncpg.Pool, key: str, value: str) -> None:
    await pool.execute(
        "INSERT INTO bot_meta (key, value) VALUES ($1, $2) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        key,
        value,
    )
