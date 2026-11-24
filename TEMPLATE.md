# TEMPLATE: Discord Bot Starter (discord.py 2.7, Postgres)

Composer spec. `template.json` is the machine-readable copy.

## Services

| Field | Bot | Postgres |
|---|---|---|
| Source | repo `baranberkay96/discord-bot-railway`, root `/services/bot` | `ghcr.io/railwayapp-templates/postgres-ssl:18.6@sha256:4fc833b4…` |
| Base / versions | `python:3.13.18-slim-trixie@sha256:6d68eb63…` (2026-11-24); discord.py 2.7.1, asyncpg 0.32.0, aiohttp 3.14.5, all transitive packages pinned | PostgreSQL 18.6 |
| Public domain | none | none |
| Healthcheck | `/healthz` on `PORT` 8080, 300 s; always 200 while the process runs, body = state | none (Railway base definition) |
| Restart | ALWAYS | ON_FAILURE (10) |
| Volume | none | `/var/lib/postgresql/data` |

Required input: `DISCORD_TOKEN`. Optional: `DISCORD_GUILD_ID`, `BOT_ACTIVITY` (/help), `LOG_LEVEL` (INFO), `PORT` (8080), `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` (15). `DATABASE_URL` references `${{Postgres.DATABASE_URL}}`.

## Design

- `python -m app`: starts the health server, validates the token's shape, waits for Postgres (backoff to 30 s), creates the schema idempotently, then connects to Discord.
- Token missing → state `not-configured`; Discord answers 401 → `token-invalid`. Both log what to set and idle without retrying (repeated bad logins can get the IP banned by Discord). Network/HTTP errors → retry with backoff up to 5 min. Never exits on configuration (STANDARD 8.29).
- Slash commands sync only when the command payload's SHA-256 differs from the one stored in `bot_meta` (avoids Discord's sync rate limit on every redeploy). `DISCORD_GUILD_ID` copies the commands to one server for instant updates.
- Default intents only (no message content, members or presences). `AllowedMentions.none()` globally; reminders allow only their author.
- Reminders: rows in `reminders`, a 10 s loop claims due rows with `FOR UPDATE SKIP LOCKED`, posts to the channel, falls back to a DM. Tags: `(guild_id, name)` rows with owner checks.
- SIGTERM cancels the main task: the gateway connection and the pool close cleanly.

## Improvements over market templates

- The most-used market template (Discord Python Bot, `railwayapp-templates/discordpy-bot`) is a prefix-command `!ping` example that needs the privileged message-content intent and has no storage, healthcheck or pinned versions. This one uses slash commands, no privileged intents, Postgres-backed features and pinned dependencies.
- Missing/wrong token no longer crash-loops (the market bots exit and Railway restarts them until the deploy fails).
- Private `/healthz` so Railway's health score counts successful deploys (STANDARD 8.34).
- Command sync only on change; invite link printed when the bot is in no server.

## Resources

| Service | Idle RAM | Typical RAM | CPU |
|---|---|---|---|
| Bot | ≈60 MB (measured) | 80–200 MB with many servers | ≈0 idle |
| Postgres | ≈70 MB (measured) | 100–200 MB | ≈0 idle |

Estimated cost: about $1–2/month (RAM $10/GB-month, volume $0.15/GB-month). Minimum plan: Trial.

## Verification checklist

- Default deploy with a placeholder token: Bot SUCCESS, `/healthz` 200 `ok token-invalid`, log explains the fix, no restarts.
- Empty token: `ok not-configured`.
- Postgres tables `bot_meta`, `reminders`, `tags` exist after the first start.
- With a real token (needs a Discord application; not created by the agent): `Logged in as`, `/ping`, `/remind me 1m test` arrives after a minute, `/tag set` + `/tag show`, redeploy keeps tags and reminders.

## Open questions

- A full login needs a real bot token from the user; the agent tested the no-token and invalid-token paths and the database layer on Railway.
