from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, Optional, List

from .ratelimiter import Ratelimiter
from .shard import Shard
from .basews import BaseWebsocketClient

if TYPE_CHECKING:
    from ..client import Client
    from .. import Intents

__all__ = ("WebSocketClient",)

logger = logging.getLogger(__name__)


class WebSocketClient(BaseWebsocketClient):
    def __init__(
        self,
        client: Client,
        intents: Optional[Intents],
        shard_ids: Optional[List[int]] = None,
        sharded: bool = False,
    ) -> None:
        super().__init__(client, intents)
        self.shard_count = len(shard_ids) if shard_ids is not None else 0
        self.sharded: bool = sharded
        self.shard_ids = shard_ids
        self.sharded = sharded

    async def start(self) -> None:
        data = await self._get_gateway()

        if self.sharded and not self.shard_count:
            self.shard_count = data["shards"]
            self.shard_ids = list(range(self.shard_count))

        max_concurrency: int = data["session_start_limit"]["max_concurrency"]
        url = data["url"]

        if self.sharded and not self.shard_count:
            self.shard_ids = list(range(data["shards"]))
            self.shard_count = len(self.shard_ids)

        async with Ratelimiter(max_concurrency, 1) as handler:
            if self.shard_ids is not None:
                shards = [Shard(self, id_) for id_ in self.shard_ids]
                self.client.shards = {shard.id: shard for shard in shards}

                for shard in shards:
                    await shard.start(url, max_concurrency)

                return None

            self.websocket = await self.client.http.ws_connect(url)

            await self.identify()
            asyncio.gather(self.start_heartbeat(), self.read_messages())

            handler.release()
