from __future__ import annotations

import typing

import asyncio
import aiohttp

from .objects import Message
from .utils import MISSING

__all__ = ("HTTPClient",)

BASE: str = "https://discord.com/api/v9"


class HTTPClient:
    def __init__(self, token: str, loop: asyncio.AbstractEventLoop):
        self.token: str = token
        self.loop: asyncio.AbstractEventLoop = loop
        self.session: aiohttp.ClientSession = MISSING

    async def _create_session(
        self, loop: typing.Optional[asyncio.AbstractEventLoop] = MISSING
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
        return await (await self.request("GET", f"{BASE}/gateway/bot")).json()

    async def ws_connect(self, url: str) -> aiohttp.ClientWebSocketResponse:
        return await self.session.ws_connect(url)

    async def login(self) -> None:
        resp = await self.request("GET", f"{BASE}/users/@me")
        if resp.status == 401:
            raise ValueError("Invalid login token")

    async def send_message(self, channel_id: int, content: str) -> typing.Dict:
        payload = {"content": content}

        return await (
            await self.request(
                "POST", f"{BASE}/channels/{channel_id}/messages", json=payload
            )
        ).json()
