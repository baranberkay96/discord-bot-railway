# Deploy and Host Discord Bot Starter with Railway

A Python Discord bot that works as soon as you paste its token: slash commands for help, latency, reminders and per-server tags, with state in Postgres so nothing is lost on redeploy. Built on discord.py 2.7 with no privileged intents. It is a starter: eject the repo and add your own commands.

## About Hosting Discord Bot Starter

A Discord bot is a long-running process that keeps a WebSocket connection to Discord's gateway and answers slash commands. It needs no public port, but it must stay online, reconnect after network blips, and keep its data somewhere safer than the container disk. This community template runs the bot from a pinned Python 3.13 image with every dependency pinned, connects it to a Railway Postgres over the private network, and creates its tables on first start. Slash commands are registered with Discord only when they change. A small private `/healthz` endpoint answers Railway's healthcheck, and a missing or wrong token is logged clearly instead of crash-looping the deploy.

## Common Use Cases

- A community bot with FAQ tags (`/tag show rules`) and personal reminders
- A starting point for your own commands: moderation helpers, role menus, integrations with your APIs
- A bot that talks to other services in your Railway project over the private network
- Learning discord.py with a deployment that already handles reconnects, health and storage

## Dependencies for Discord Bot Starter Hosting

- A Discord application with a bot user and its token
- The Bot service (built from this repo, Python 3.13, discord.py 2.7.1, asyncpg)
- Postgres 18 (Railway's `postgres-ssl` image) with a volume

### Deployment Dependencies

- [Discord Developer Portal](https://discord.com/developers/applications)
- [discord.py documentation](https://discordpy.readthedocs.io/en/stable/)
- [discord.py on GitHub](https://github.com/Rapptz/discord.py)
- [Discord Developer Terms of Service](https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service)
- [Railway Fair Use Policy](https://railway.com/legal/fair-use)

### Implementation Details

| Service | What runs inside | Volume | Port |
|---|---|---|---|
| Bot | discord.py 2.7.1 bot (`python -m app`), private `/healthz` | none | 8080, private (healthcheck only) |
| Postgres | PostgreSQL 18 (reminders, tags, command-sync state) | `/var/lib/postgresql/data` | 5432, private |

**First start**

1. In the [Developer Portal](https://discord.com/developers/applications), create an application, open **Bot**, click **Reset Token** and copy it.
2. Paste it into `DISCORD_TOKEN` when you deploy (or later on the Bot service, then redeploy).
3. The deploy log prints `Logged in as ...` and, while the bot is in no server yet, an invite link. Open it to add the bot to your server (scopes `bot` and `applications.commands`).
4. Type `/` in your server. Global commands can take a few minutes to appear the first time; set `DISCORD_GUILD_ID` to your server id for instant updates while developing.

**Commands included**

| Command | What it does |
|---|---|
| `/help` | Lists all commands |
| `/ping` | Gateway latency and a database round trip |
| `/about` | Uptime, server count, versions |
| `/remind me when message` | Reminds you in the channel after `10m`, `1h30m`, `2d` (up to 365 days, 25 per user); survives redeploys |
| `/remind list`, `/remind cancel` | Your pending reminders |
| `/tag set`, `/tag show`, `/tag list`, `/tag delete` | Saved snippets per server; creators or members with Manage Messages can edit and delete |

The bot uses only default intents, so nothing has to be enabled under Privileged Gateway Intents. Mentions in repeated text are disabled; reminders ping only their author.

**When something is wrong**

If `DISCORD_TOKEN` is empty or Discord rejects it, the service stays up, `/healthz` reports `not-configured` or `token-invalid`, and the log says what to do. Fix the variable and redeploy. While Postgres starts, the bot waits and retries.

**Extend it**

The deployed code comes from this template's GitHub repo. To change it, use **Eject** in the Bot service's settings (Railway copies the repo to your GitHub account and deploys from it), then add a module under `app/cogs/` with an `async def setup(bot)` function and list it in `EXTENSIONS` in `app/bot.py`. Tables go into `SCHEMA` in `app/db.py`. Pushing to your repo redeploys.

**Scaling and versions**

Run one replica: a second copy of the same token would answer every command twice. One bot process handles thousands of servers; very large bots need discord.py's sharding (`AutoShardedBot`). Versions are pinned in `services/bot/requirements.txt` and the Dockerfile (`python:3.13.18-slim-trixie` by digest); change them there to upgrade.

**Resources**

Measured on Railway: the bot idles at about 60 MB RAM and Postgres at about 70 MB, near 0 vCPU. Trial plan is enough; cost is roughly $1–2/month.

**Not included, on purpose**

No music or YouTube playback, no selfbot or user-token features, no mass-DM tools: they break Discord's or Railway's terms.

### Why Deploy Discord Bot Starter on Railway?

Railway keeps the bot online, restarts it when it stops, and gives it a private Postgres in the same project, with logs and redeploys from Git in one place. You paste a token and have a working bot to build on. This is a community template, not affiliated with Discord or the discord.py project.
