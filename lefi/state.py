from __future__ import annotations

import typing
import collections

import asyncio
import re

from .objects import Message

if typing.TYPE_CHECKING:
    from .client import Client

__all__ = (
    "State",
    "Cache",
)

T = typing.TypeVar("T")


class Cache(collections.OrderedDict[typing.Union[str, int], T]):
    def __init__(self, maxlen: typing.Optional[int], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxlen: typing.Optional[int] = maxlen
        self._max: int = 0

    def __repr__(self) -> str:
        origin = str(self.__dict__["__orig_class__"])
        if final := re.search("\[(.*)\]", origin):
            return f"<Cache type={final.group(1)}>"

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

    async def dispatch(self, event: str, payload: typing.Any) -> None:
        name = event.lower()
        if name in self.client.events:
            for callback in self.client.events[name]:
                await callback(payload)

    async def parse_message_create(self, data: typing.Dict) -> None:
        await self.dispatch("message_create", Message(data))
