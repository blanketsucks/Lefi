from __future__ import annotations

import typing

import asyncio
import aiohttp

__all__ = ("HTTPClient",)

BASE: str = "https://discord.com/api/v9"


class HTTPClient:
    def __init__(self, token: str, loop: asyncio.AbstractEventLoop):
        self.loop: asyncio.AbstractEventLoop = loop
        self.session: aiohttp.ClientSession = None  # type:ignore
        self.token: str = token

    def build_url(self, url) -> str:
        return f"{BASE}{url}"

    async def _create_session(
        self, loop: typing.Optional[asyncio.AbstractEventLoop] = None
    ) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            loop=self.loop or loop, headers={"Authorization": f"Bot {self.token}"}
        )

    async def request(
        self, method: str, url: str, *args, **kwargs
    ) -> aiohttp.ClientResponse:
        if self.session is None or self.session.closed:
            self.session = await self._create_session()

        return await self.session.request(method, url, *args, **kwargs)

    async def get_bot_gateway(self) -> typing.Dict:
        resp = await self.request("GET", f"{BASE}/gateway/bot")
        return await resp.json()

    async def ws_connect(self, url: str) -> aiohttp.ClientWebSocketResponse:
        return await self.session.ws_connect(url)
