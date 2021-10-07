from __future__ import annotations

import asyncio
import aiohttp

import typing

import sys
import logging
import enum

from ..utils import MISSING
from ..objects import Intents, User

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
    def __init__(self, client: Client, intents: Intents = MISSING) -> None:
        self.intents = Intents.default() if intents is MISSING else intents
        self.ws: aiohttp.ClientWebSocketResponse = MISSING
        self.heartbeat_delay: float = MISSING
        self.client: Client = client
        self.closed: bool = False
        self.seq: int = 0

        self.EVENT_MAPPING: typing.Dict[str, typing.Callable] = {
            "ready": self.client._state.parse_ready,
            "message_create": self.client._state.parse_message_create,
            "message_update": self.client._state.parse_message_update,
            "message_delete": self.client._state.parse_message_delete,
            "guild_create": self.client._state.parse_guild_create,
            "channel_create": self.client._state.parse_channel_create,
            "channel_update": self.client._state.parse_channel_update,
            "channel_delete": self.client._state.parse_channel_delete,
        }

    async def start(self) -> None:
        data = await self.client.http.get_bot_gateway()
        self.ws = await self.client.http.ws_connect(data["url"])

        await self.identify()
        await asyncio.gather(self.start_heartbeat(), self.read_messages())

    async def parse_event_data(self, event_name: str, data: typing.Dict) -> None:
        if event_parse := self.EVENT_MAPPING.get(event_name):
            await event_parse(data)

    async def reconnect(self) -> None:
        if not self.ws.closed and self.ws:
            await self.ws.close()
            self.closed = True

        await self.start()

    async def read_messages(self) -> None:
        async for message in self.ws:
            if message.type is aiohttp.WSMsgType.TEXT:
                recieved_data = message.json()

                if recieved_data["op"] == OpCodes.DISPATCH:
                    await self.dispatch(recieved_data["t"], recieved_data["d"])

                if recieved_data["op"] == OpCodes.HEARTBEAT_ACK:
                    logger.debug("HEARTBEAT ACKNOWLEDGED")

                if recieved_data["op"] == OpCodes.RESUME:
                    logger.debug("RESUMED")
                    await self.resume()

                if recieved_data["op"] == OpCodes.RECONNECT:
                    logger.debug("RECONNECT")
                    await self.reconnect()

    async def dispatch(self, event: str, data: typing.Dict) -> None:
        logger.debug(f"DISPATCHED EVENT: {event}")
        if event == "READY":
            self.session_id = data["session_id"]

        await self.parse_event_data(event.lower(), data)

    async def resume(self) -> None:
        payload = {
            "op": 6,
            "token": self.client.http.token,
            "session_id": self.session_id,
            "seq": self.seq,
        }
        await self.ws.send_json(payload)

    async def identify(self) -> None:
        data = await self.ws.receive()
        self.heartbeat_delay = data.json()["d"]["heartbeat_interval"]

        payload = {
            "op": 2,
            "d": {
                "token": self.client.http.token,
                "intents": self.intents.value,
                "properties": {
                    "$os": sys.platform,
                    "$browser": "Lefi",
                    "$device": "Lefi",
                },
            },
        }
        await self.ws.send_json(payload)

    async def start_heartbeat(self) -> None:
        while not self.closed:
            self.seq += 1
            await self.ws.send_json({"op": 1, "d": self.seq})
            logger.info("HEARTBEAT SENT")
            await asyncio.sleep(self.heartbeat_delay / 1000)
