# NOTICE: Discord Bot Starter template

This is a community template. It is not made, endorsed or supported by Discord Inc., the discord.py project or Railway. Discord is a trademark of Discord Inc.

## Components

| Component | Source | License | How it is used |
|---|---|---|---|
| discord.py 2.7.1 | https://github.com/Rapptz/discord.py | MIT (Copyright (c) 2015-present Rapptz) | Installed from PyPI at build time |
| asyncpg 0.32.0 | https://github.com/MagicStack/asyncpg | Apache-2.0 | Installed from PyPI |
| aiohttp 3.14.5 and its dependencies (aiohappyeyeballs, aiosignal, attrs, frozenlist, multidict, propcache, yarl, idna), audioop-lts | PyPI | Apache-2.0 / MIT / BSD / PSF (each package's own license) | Installed from PyPI |
| Python 3.13.18 (`python:3.13.18-slim-trixie@sha256:6d68eb6310a906f26c7638eb6ea7557d4261662df3181af2f80f1f9a7e34c549`) | https://hub.docker.com/_/python | PSF License; Debian packages under their own licenses | Base image |
| PostgreSQL 18.6 (`ghcr.io/railwayapp-templates/postgres-ssl:18.6`) | https://github.com/railwayapp-templates/postgres-ssl | PostgreSQL License | Database service, Railway's standard definition |

## Files written for this template

Everything under `services/bot/` (the bot code, Dockerfile, requirements) and the documentation was written for this template and is offered under the MIT License. You may copy and change it for your own bots.

## Upstream files checked

- discord.py v2.7.1: `discord/app_commands/commands.py` (`to_dict(tree)`), `discord/app_commands/tree.py` (`sync`, `copy_global_to`), `discord/ext/commands/cog.py` (GroupCog `guild_only`), `discord/client.py` (login errors, voice warnings).
- PyPI metadata of every pinned package (2026-11-24).

## Market templates

The three Discord bot templates on the Railway marketplace (`railwayapp-templates/discordpy-bot`, `railwayapp-templates/discordjs`, `caru-ini/discord-bot-template`) were reviewed for features only. No files or text were copied.

## Terms

Bots must follow the Discord Developer Terms of Service and Developer Policy. Selfbots (user tokens), music bots that stream from YouTube, spam and mass-DM tools are not allowed by Discord or by Railway's Fair Use Policy and are not part of this template.
