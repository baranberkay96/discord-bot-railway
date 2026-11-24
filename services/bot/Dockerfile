# syntax=docker/dockerfile:1
#
# Discord bot starter (discord.py 2.7.1, Postgres via asyncpg) for Railway.
#
# Base: python 3.13.18 on Debian 13 (slim). The digest is the multi-arch
# index of python:3.13.18-slim-trixie (checked 2026-11-24). To upgrade,
# replace tag and digest together.
FROM python:3.13.18-slim-trixie@sha256:6d68eb6310a906f26c7638eb6ea7557d4261662df3181af2f80f1f9a7e34c549

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /srv/bot

# All packages are pinned (direct and transitive) and installed from wheels.
COPY requirements.txt ./
RUN pip install --only-binary=:all: --retries 5 -r requirements.txt \
 && useradd --system --uid 10001 --home-dir /srv/bot --shell /usr/sbin/nologin bot

COPY app ./app

USER bot
EXPOSE 8080

# Railway's podman-init is PID 1 and forwards SIGTERM to python, which
# closes the Discord connection and the database pool cleanly.
CMD ["python", "-m", "app"]
