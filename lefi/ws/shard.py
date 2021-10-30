from __future__ import annotations

import asyncio
import sys

from typing import TYPE_CHECKING, Dict

from .basews import BaseWebsocketClient
from .opcodes import OpCodes
from .ratelimiter import Ratelimiter

if TYPE_CHECKING:
    from .wsclient import WebSocketClient

__all__ = ("Shard",)


class Shard(BaseWebsocketClient):
    def __init__(self, parent: WebSocketClient, id: int) -> None:
        super().__init__(parent.client, parent.intents)
        self.intents = parent.intents
        self.parent = parent
        self.id = id

    def __repr__(self) -> str:
        return f"<Shard id={self.id}>"

    def __int__(self) -> int:
        return self.id

    async def start(self, data: Dict) -> None:  # type: ignore
        max_concurrency: int = data["session_start_limit"]["max_concurrency"]

        self.ratelimiter = Ratelimiter(max_concurrency, 1)
        await self.ratelimiter.acquire()

        self.websocket = await self.client.http.ws_connect(data["url"])

        await self.identify()
        asyncio.gather(self.start_heartbeat(), self.read_messages())

    async def identify(self) -> None:
        """
        Sends an identify payload to the websocket with the shard array.
        """
        data = await self.websocket.receive()
        self.heartbeat_delay = data.json()["d"]["heartbeat_interval"]

        payload = {
            "op": OpCodes.IDENTIFY,
            "d": {
                "token": self.client.http.token,
                "intents": self.intents.value,
                "shard": [self.id, self.parent.shard_count],
                "properties": {
                    "$os": sys.platform,
                    "$browser": "Lefi",
                    "$device": "Lefi",
                },
            },
        }
        await self.websocket.send_json(payload)
