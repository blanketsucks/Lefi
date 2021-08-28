from __future__ import annotations

import typing

import asyncio

from .http import HTTPClient
from .ws import WebSocketClient

__all__ = ("Client",)


class Client:
    def __init__(
        self, token: str, loop: typing.Optional[asyncio.AbstractEventLoop] = None
    ):
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self.http: HTTPClient = HTTPClient(token, self.loop)
        self.ws: WebSocketClient = None  # type: ignore

    async def start(self) -> None:
        data = await self.http.get_bot_gateway()
        ws = await self.http.ws_connect(data["url"])
        self.ws = WebSocketClient(self, ws)

        await self.ws.start()
