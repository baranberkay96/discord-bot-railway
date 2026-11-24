"""Private /healthz endpoint for Railway's healthcheck.

The bot only dials out to Discord, so this tiny HTTP server is what Railway
probes. It answers 200 as long as the process runs, also while the token is
missing or wrong: a configuration problem must not fail the deploy or make
the service crash-loop (the log says what to fix). The body tells the state.
"""
from __future__ import annotations

import logging
import time

from aiohttp import web

log = logging.getLogger("bot.health")


class Health:
    """Holds the bot state and serves it on GET /healthz."""

    def __init__(self, port: int) -> None:
        self._port = port
        self._state = "starting"
        self._detail = ""
        self._since = time.time()
        self._runner: web.AppRunner | None = None

    @property
    def state(self) -> str:
        return self._state

    def set(self, state: str, detail: str = "") -> None:
        if (state, detail) != (self._state, self._detail):
            self._state, self._detail, self._since = state, detail, time.time()

    async def _handle(self, request: web.Request) -> web.StreamResponse:
        body = {
            "status": "ok",
            "state": self._state,
            "detail": self._detail,
            "since": int(self._since),
        }
        if request.query.get("format") == "json":
            return web.json_response(body)
        return web.Response(text=f"ok {self._state}\n")

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/healthz", self._handle)
        app.router.add_get("/", self._handle)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        # host=None binds every interface (IPv4 and IPv6) as separate sockets.
        site = web.TCPSite(self._runner, host=None, port=self._port)
        await site.start()
        log.info("Health endpoint listening on port %s (/healthz)", self._port)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()

