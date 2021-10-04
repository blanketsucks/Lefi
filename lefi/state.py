from __future__ import annotations

import typing
import collections

import asyncio

from .objects import Message, Guild, Channel
from .utils import MISSING

if typing.TYPE_CHECKING:
    from .client import Client

__all__ = (
    "State",
    "Cache",
)

T = typing.TypeVar("T")


class Cache(collections.OrderedDict[typing.Union[str, int], T]):
    def __init__(self, maxlen: typing.Optional[int] = MISSING, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxlen: typing.Optional[int] = maxlen
        self._max: int = 0

    def __repr__(self) -> str:
        return f"<Cache maxlen={self.maxlen}"

    def __setitem__(self, key: typing.Union[str, int], value: T) -> None:
        super().__setitem__(key, value)
        self._max += 1

        if self.maxlen is not None and self._max > self.maxlen:
            self.popitem(False)


class State:
    def __init__(self, client: Client, loop: asyncio.AbstractEventLoop):
        self.client = client
        self.loop = loop

        self._messages = Cache[Message](1000)
        self._guilds = Cache[Guild]()
        self._channels = Cache[Channel]()

    async def dispatch(self, event: str, payload: typing.Any) -> None:
        name = event.lower()
        if name in self.client.events:
            for callback in self.client.events[name]:
                await callback(payload)

    async def parse_guild_create(self, data: typing.Dict) -> None:
        channels = [Channel(self, payload) for payload in data["channels"]]
        for channel in channels:
            self._channels[channel.id] = channel

        guild = Guild(self, data)
        guild.channels.extend(channels)

        await self.dispatch("guild_create", guild)

    async def parse_message_create(self, data: typing.Dict) -> None:
        channel = self._channels.get(data["channel_id"]) or Channel(
            self, {"id": data["channel_id"]}
        )
        channel._guild = self._guilds.get(data.get("guild_id"))  # type: ignore
        message = Message(self, data, channel)
        self._messages[int(message.id)] = message
        await self.dispatch("message_create", message)

    def create_message(self, data: typing.Dict, channel: Channel):
        return Message(self, data, channel)
