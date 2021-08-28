from __future__ import annotations

import typing

import asyncio
import aiohttp

import sys
import logging

import enum

if typing.TYPE_CHECKING:
    from ..client import Client

__all__ = ("WebSocketClient",)

logger = logging.getLogger(__name__)


class OpCodes(enum.IntFlag):
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE_UPDATE = 3
    VOICE_STATE_UPDATE = 4
    RESUME = 6
    RECONNECT = 7
    REQUEST_GUILD_MEMBERS = 8
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11


class WebSocketClient:
    def __init__(self, client: Client):
        self.ws: aiohttp.ClientWebSocketResponse = None  # type: ignore
        self.heartbeat_delay: float = None  # type: ignore
        self.client: Client = client
        self.closed: bool = False
        self.seq: int = 0

    async def start(self) -> None:
        data = await self.client.http.get_bot_gateway()
        self.ws = await self.client.http.ws_connect(data["url"])

        await asyncio.gather(
            self.identify(), self.start_heartbeat(), self.read_messages()
        )

    async def reconnect(self) -> None:
        if not self.ws.closed and self.ws:
            await self.ws.close()
            self.closed = True

        await self.start()

    async def read_messages(self):
        async for message in self.ws:
            if message.type is aiohttp.WSMsgType.TEXT:
                recieved_data = message.json()

                if recieved_data["op"] == OpCodes.DISPATCH:
                    await self.dispatch(recieved_data["t"], recieved_data["d"])

                if recieved_data["op"] == OpCodes.HEARTBEAT_ACK:
                    logger.info("HEARTBEAT ACKNOWLEDGED")

                if recieved_data["op"] == OpCodes.RESUME:
                    await self.resume()

                if recieved_data["op"] == OpCodes.RECONNECT:
                    await self.reconnect()

    async def dispatch(self, event: str, data: typing.Dict) -> None:
        logger.info(f"DISPATCHED EVENT: {event}")

        if event == "READY":
            self.session_id = data["session_id"]

        if event.lower() in self.client.events:
            for callback in self.client.events[event.lower()]:
                await callback(data)

    async def resume(self) -> None:
        payload = {
            "op": 6,
            "token": self.client.http.token,
            "session_id": self.session_id,
            "seq": self.seq
        }
        await self.ws.send_json(payload)

    async def identify(self) -> None:
        data = await self.ws.receive()
        self.heartbeat_delay = data.json()["d"]["heartbeat_interval"]

        payload = {
            "op": 2,
            "d": {
                "token": self.client.http.token,
                "intents": 32511,
                "properties": {
                    "$os": sys.platform,
                    "$browser": "Lefi",
                    "$device": "Lefi",
                },
            },
        }
        await self.ws.send_json(payload)

    async def start_heartbeat(self) -> None:
        while True:
            self.seq += 1
            await self.ws.send_json({"op": 1, "d": self.seq})
            await asyncio.sleep(self.heartbeat_delay / 1000)
