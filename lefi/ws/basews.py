from __future__ import annotations

import asyncio
import datetime
import logging
import sys
from typing import TYPE_CHECKING, Dict, Optional

import aiohttp

from ..objects import Intents
from .opcodes import OpCodes
from .ratelimiter import Ratelimiter

if TYPE_CHECKING:
    from ..client import Client

__all__ = ("BaseWebsocketClient",)

logger = logging.getLogger(__name__)


class BaseWebsocketClient:
    """The base websocket client

    This is the base websocket client classed used
    for all of the websocket clients in this library. This is used
    to communicate with the discord gateway. This class handles event receiving
    and event dispatching as well as keeping the client alive.

    Parameters
    ----------
    client: :class:`.Client`
        The client which is being connected

    intents: :class:`.Intents`
        The intents to IDENTIFY with

    Attributes
    ----------
    intents: :class:`.Intents`
        The intents used when IDENTIFYING

    websocket: :class:`.aiohttp.ClientWebSocketResponse`
        The internal websocket. This is the one that is connected to discord

    client: :class:`.Client`
        The connected client

    closed: :class:`bool`
        If the websocket is closed or not

    seq: :class:`int`
        The last sequence number received

    last_heartbeat: Optional[:class:`.datetime.datetime`]
        The time of the last sent heartbeat

    latency: :class:`float`
        The time inbetween sending a heartbeat and then
        discord acknowledging the heartbeat. This is in miliseconds

    heartbeat_delay: :class:`float`
        How long to wait before sending another heartbeat
    """

    def __init__(
        self,
        client: Client,
        intents: Optional[Intents] = None,
    ) -> None:
        self.intents: Intents = Intents.default() if intents is None else intents
        self.websocket: aiohttp.ClientWebSocketResponse = None  # type: ignore
        self.client: Client = client
        self.closed: bool = False
        self.seq: int = 0

        self.last_heartbeat: Optional[datetime.datetime] = None
        self.latency: float = float("inf")
        self.heartbeat_delay: float = 0

    async def start(self) -> None:
        """Connects to the gateway.

        This method calls :meth:`.HTTPClient.get_bot_gateway`, this gets the url
        and other information such as max_concurrency and shards. We connect to the websocket
        with a ratelimiter. This is to ensure we follow the max concurreny given to us.

        Raises
        ------
        :exc:`KeyError`
            This is likely due to invalid authorization.
        """
        data = await self.client.http.get_bot_gateway()
        max_concurrency: int = data["session_start_limit"]["max_concurrency"]

        async with Ratelimiter(max_concurrency, 1) as handler:
            self.websocket = await self.client.http.ws_connect(data["url"])

            await self.identify()
            asyncio.gather(self.start_heartbeat(), self.read_messages())

            handler.release()

    async def close(self):
        """Handles closing the websocket."""
        if self.websocket is not None:
            await self.websocket.close()

    async def read_messages(self) -> None:
        """Reads messages sent from the websocket.

        This method reads all sent messages from the websocket
        then decides what action to take depending on the message's OpCode.
        This is where the library handles events. For every heartbeat acknowledge we
        also calculate the latency.
        """
        async for message in self.websocket:
            if message.type is aiohttp.WSMsgType.TEXT:
                recieved_data = message.json()

                if recieved_data["op"] == OpCodes.DISPATCH:
                    await self.dispatch(recieved_data["t"], recieved_data["d"])

                if recieved_data["op"] == OpCodes.HEARTBEAT_ACK:
                    if self.last_heartbeat is not None:
                        self.latency = (
                            datetime.datetime.now() - self.last_heartbeat
                        ).total_seconds() * 1000

                    logger.info("HEARTBEAT ACKNOWLEDGED")

                if recieved_data["op"] == OpCodes.RESUME:
                    logger.info("RESUMED")
                    await self.resume()

                if recieved_data["op"] == OpCodes.RECONNECT:
                    logger.info("RECONNECT")
                    await self.reconnect()

        await self.websocket.close()
        logger.info("WEBSOCKET CLOSED")

    async def dispatch(self, event: str, data: dict) -> None:
        """Dispatches an event and its data to the parsers.

        Basically just calls the corresponding parser.
        If a ``READY`` event is passed, we set `session_id`.

        Parameters
        ----------
        event: :class:`str`
            The name of the event to dispatch

        data: :class:`dict`
            The raw data of the event
        """
        logger.info(f"DISPATCHED EVENT: {event}")
        if event == "READY":
            self.session_id = data["session_id"]

        if parser := getattr(self.client._state, f"parse_{event.lower()}", None):
            try:
                return await parser(data)
            except Exception as error:
                logger.exception(error)

    async def reconnect(self) -> None:
        """Reconnects the websocket.

        This the websocket is not closed this method
        will close it manually and restart the connection.
        """
        if not self.websocket and self.websocket.closed:
            await self.websocket.close()
            self.closed = True

        await self.start()

    async def resume(self) -> None:
        """Sends a ``RESUME`` payload

        This method sends a ``RESUME`` payload to the websocket
        This is done when we receive a ``RESUME`` OpCode
        """
        payload = {
            "op": OpCodes.RESUME,
            "token": self.client.http.token,
            "session_id": self.session_id,
            "seq": self.seq,
        }
        await self.websocket.send_json(payload)

    async def identify(self) -> None:
        """Sends a ``IDENTIFY`` payload

        This method sends a ``IDENTIFY`` payload to the websocket
        This is done when we receive a ``IDENTIFY`` OpCode
        """
        data = await self.websocket.receive()
        self.heartbeat_delay = data.json()["d"]["heartbeat_interval"]

        payload = {
            "op": OpCodes.IDENTIFY,
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
        await self.websocket.send_json(payload)

    async def change_guild_voice_state(
        self,
        guild_id: int,
        channel_id: Optional[int] = None,
        self_mute: bool = False,
        self_deaf: bool = False,
    ) -> None:
        """Sends a ``VOICE_STATE_UPDATE`` payload

        This method sends a ``VOICE_STATE_UPDATE`` payload
        when we receive a ``VOICE_STATE_UPDATE`` OpCode
        """
        payload = {
            "op": OpCodes.VOICE_STATE_UPDATE,
            "d": {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "self_mute": self_mute,
                "self_deaf": self_deaf,
            },
        }
        await self.websocket.send_json(payload)

    async def start_heartbeat(self) -> None:
        """Starts the heartbeat loop.

        This method starts a loop, which sends heartbeats.
        This is used to keep the client alive. We set :attr:`.BaseWebsocketClient.last_heartbeat` here
        """
        while self.websocket and not self.websocket.closed:

            await self.websocket.send_json({"op": OpCodes.HEARTBEAT, "d": self.seq})
            self.last_heartbeat = datetime.datetime.now()

            self.seq += 1
            logger.info("HEARTBEAT SENT")

            try:
                await asyncio.sleep(self.heartbeat_delay / 1000)
            except asyncio.CancelledError:
                pass
