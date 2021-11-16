from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING
import asyncio

from .basews import BaseWebsocketClient
from .opcodes import OpCodes
from .ratelimiter import Ratelimiter

if TYPE_CHECKING:
    from .wsclient import WebSocketClient

__all__ = ("Shard",)

logger = logging.getLogger(__name__)


class Shard(BaseWebsocketClient):
    """A websocket client used when sharding.

    Parameters
    ----------
    parent: :class:`.WebSocketClient`
        The parent websocket client

    id: :class:`int`
        The shard's id

    Attributes
    ----------
    intents: :class:`.Intents`
        This is the parent's intents

    parent: :class:`.WebSocketClient`
        The parent websocket client

    id: :class:`int`
        The shard's id
    """

    def __init__(self, parent: WebSocketClient, id: int) -> None:
        super().__init__(parent.client, parent.intents)
        self.intents = parent.intents
        self.parent = parent
        self.id = id

    def __repr__(self) -> str:
        return f"<Shard id={self.id}>"

    def __int__(self) -> int:
        return self.id

    async def start(self, url: str, max_concurrency: int) -> None:  # type: ignore
        """Connects to the gateway.

        This method calls HTTPClient.get_bot_gateway(), this gets the url and other
        information such as max_concurrency and shards. We connect to the websocket
        with a ratelimiter. This is to ensure we follow the max concurreny given to us.

        Parameters
        ----------
        url: :class:`str`
            The websocket url

        max_concurrency: :class:`int`
            The max concurreny to use
        """
        async with Ratelimiter(max_concurrency, 1) as handler:
            self.websocket = await self.client.http.ws_connect(url)

            await self.identify()
            asyncio.gather(self.start_heartbeat(), self.read_messages())

            handler.release()

    async def identify(self) -> None:
        """Sends a IDENTIFY payload

        This method sends a IDENTIFY payload with a shards list
        to the websocket This is done when we receive a IDENTIFY OpCode
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
