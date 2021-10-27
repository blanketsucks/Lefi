from __future__ import annotations

import asyncio
import enum
import logging
import sys
from typing import TYPE_CHECKING, Callable, Dict, Optional

import aiohttp

from ..objects import Intents

if TYPE_CHECKING:
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
    """
    A class which is used to communicate to the gateway.

    Attributes:
        intents (lefi.Intents): The intents to use when connecting.
        ws (aiohttp.ClientWebSocketResponse): The websocket which we are connected to.
        heartbeat_deylay (float): The delay inbetween sending each heartbeat.
        client (lefi.Client): The [lefi.Client][] currently connected.
        closed (bool): Whether or not the websocket is closed.
        seq (int): The sequence received from `READY`.

    Danger:
        This class is used internally. **THIS IS NOT MEANT TO BE TOUCHED.**. Doing so can cause bugs.

    """

    def __init__(self, client: Client, intents: Optional[Intents] = None) -> None:
        """
        Parameters:
            client (lefi.Client): The [lefi.Client][] instance connected.
            intents (lefi.Intents): The [lefi.Intents][] to pass when connecting.

        """
        self.intents = Intents.default() if intents is None else intents
        self.ws: aiohttp.ClientWebSocketResponse = None  # type: ignore
        self.heartbeat_delay: float = 0
        self.client: Client = client
        self.closed: bool = False
        self.seq: int = 0

        self.EVENT_MAPPING: Dict[str, Callable] = {
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
        """
        Starts the connection to the websocket and begins parsing messages received from the websocket.
        """
        headers = {"Authorization": f"Bot {self.client.http.token}"}
        session = self.client.http.session or await self.client.http._create_session()
        data = await session.request(
            "GET", "https://discord.com/api/v9/gateway/bot", headers=headers
        )

        self.ws = await self.client.http.ws_connect((await data.json())["url"])

        await self.identify()
        await asyncio.gather(self.start_heartbeat(), self.read_messages())

    async def parse_event_data(self, event_name: str, data: Dict) -> None:
        """
        Finds the parsers for the passed in event.

        Parameters:
            event_name (str): The name of the event.
            data (Dict): The raw data to parse.

        """
        if event_parse := self.EVENT_MAPPING.get(event_name):
            await event_parse(data)

    async def reconnect(self) -> None:
        """
        Closes the websocket if it isn't then tries to establish a new connection.
        """
        if not self.ws.closed and self.ws:
            await self.ws.close()
            self.closed = True

        await self.start()

    async def read_messages(self) -> None:
        """
        Reads the messages from received from the websocket and parses them.
        """
        async for message in self.ws:
            if message.type is aiohttp.WSMsgType.TEXT:
                recieved_data = message.json()

                if recieved_data["op"] == OpCodes.DISPATCH:
                    await self.dispatch(recieved_data["t"], recieved_data["d"])

                if recieved_data["op"] == OpCodes.HEARTBEAT_ACK:
                    logger.info("HEARTBEAT ACKNOWLEDGED")

                if recieved_data["op"] == OpCodes.RESUME:
                    logger.info("RESUMED")
                    await self.resume()

                if recieved_data["op"] == OpCodes.RECONNECT:
                    logger.info("RECONNECT")
                    await self.reconnect()

    async def dispatch(self, event: str, data: Dict) -> None:
        """
        Dispatches an event and its data to the parsers.

        Parameters:
            event (str): The event being dispatched.
            data (Dict): The raw data of the event.

        """
        logger.debug(f"DISPATCHED EVENT: {event}")
        if event == "READY":
            self.session_id = data["session_id"]

        await self.parse_event_data(event.lower(), data)

    async def resume(self) -> None:
        """
        Sends a resume payload to the websocket.
        """
        payload = {
            "op": 6,
            "token": self.client.http.token,
            "session_id": self.session_id,
            "seq": self.seq,
        }
        await self.ws.send_json(payload)

    async def identify(self) -> None:
        """
        Sends an identify payload to the websocket.
        """
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
        """
        Starts the heartbeat loop.

        Info:
            This can be blocked, which causes the heartbeat to stop.

        """
        while not self.closed:
            self.seq += 1
            await self.ws.send_json({"op": 1, "d": self.seq})
            logger.info("HEARTBEAT SENT")
            await asyncio.sleep(self.heartbeat_delay / 1000)
