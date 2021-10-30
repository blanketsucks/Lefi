from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING, Optional, List

from .ratelimiter import Ratelimiter
from .shard import Shard
from .basews import BaseWebsocketClient

if TYPE_CHECKING:
    from ..client import Client
    from .. import Intents

__all__ = ("WebSocketClient",)


class WebSocketClient(BaseWebsocketClient):
    def __init__(
        self,
        client: Client,
        intents: Optional[Intents],
        shard_ids: Optional[List[int]] = None,
    ) -> None:
        super().__init__(client, intents)
        self.shard_count = len(shard_ids) if shard_ids is not None else 0
        self.shard_ids = shard_ids

    async def start(self) -> None:
        data = await self._get_gateway()
        max_concurrency: int = data["session_start_limit"]["max_concurrency"]

        async with Ratelimiter(max_concurrency, 1) as handler:
            if self.shard_ids is not None:
                shards = [Shard(self, id_) for id_ in self.shard_ids]
                self.client.shards = shards

                for shard in shards:
                    await shard.start()

                return None

            self.websocket = await self.client.http.ws_connect(data["url"])

            await self.identify()
            await asyncio.gather(self.start_heartbeat(), self.read_messages())

            handler.release()
