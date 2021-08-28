from __future__ import annotations

import typing

import asyncio
import aiohttp

import logging

if typing.TYPE_CHECKING:
    from ..client import Client

__all__ = ("WebSocketClient",)

logger = logging.getLogger(__name__)


class WebSocketClient:
    def __init__(self, client: Client):
        self.ws: aiohttp.ClientWebSocketResponse = None  # type: ignore
        self.client: Client = client
        self.seq: int = 0

    async def start(self) -> None:
        data = await self.client.http.get_bot_gateway()
        self.ws = await self.client.http.ws_connect(data["url"])

        await asyncio.gather(
            self.identify(), self.start_heartbeat(), self.read_messages()
        )

    async def read_messages(self):
        async for message in self.ws:
            if message.type is aiohttp.WSMsgType.TEXT:
                recieved_data = message.json()

                if recieved_data["op"] == 11:
                    logger.info("HEARTBEAT ACKNOWLEDGED")

                elif recieved_data["op"] == 0:
                    await self.dispatch(recieved_data["t"], recieved_data["d"])

    async def dispatch(self, event: str, data: typing.Dict) -> None:
        logger.info(f"DISPATCHED EVENT: {event}")

        if event.lower() in self.client.events:
            for callback in self.client.events[event.lower()]:
                await callback(data)

    async def identify(self) -> None:
        data = await self.ws.receive()
        self.heartbeat_delay = data.json()["d"]["heartbeat_interval"]

        payload = {
            "op": 2,
            "d": {"token": self.client.http.token, "intents": 32511, "properties": {}},
        }
        await self.ws.send_json(payload)

    async def start_heartbeat(self) -> None:
        while True:
            self.seq += 1
            await self.ws.send_json({"op": 1, "d": self.seq})
            await asyncio.sleep(self.heartbeat_delay / 1000)
