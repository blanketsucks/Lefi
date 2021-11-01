from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Coroutine, Dict, Generic, TypeVar, List

_T = TypeVar("_T")

if TYPE_CHECKING:
    from ..objects import Member, Guild, Message, TextChannel
    from ..state import State

__all__ = ("MemberIterator", "AsyncIterator", "ChannelHistoryIterator")


class AsyncIterator(Generic[_T]):
    def __init__(self, coroutine: Coroutine[None, None, List[Any]]) -> None:
        self.coroutine = coroutine
        self.queue = asyncio.Queue[_T]()

        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self._fill_queue())

    async def _fill_queue(self):
        values = await self.coroutine

        for value in values:
            await self.queue.put(value)

    async def all(self) -> List[_T]:
        return [val async for val in self]

    async def next(self) -> _T:
        value = await asyncio.wait_for(self.queue.get(), timeout=0.5)

        return value

    def __await__(self):
        return self.all().__await__()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            value = await self.next()
        except asyncio.TimeoutError:
            raise StopAsyncIteration
        else:
            return value


class MemberIterator(AsyncIterator["Member"]):
    def __init__(
        self, state: State, guild: Guild, coroutine: Coroutine[None, None, List[Dict]]
    ) -> None:
        self.state = state
        self.guild = guild

        super().__init__(coroutine)

    async def _fill_queue(self):
        from ..objects import Member

        values = await self.coroutine

        for value in values:
            user_id = int(value["user"]["id"])
            member = self.guild.get_member(user_id)

            if not member:
                member = Member(self.state, value, self.guild)

            await self.queue.put(member)


class ChannelHistoryIterator(AsyncIterator["Message"]):
    def __init__(
        self,
        state: State,
        channel: TextChannel,
        coroutine: Coroutine[None, None, List[Any]],
    ) -> None:
        self.state = state
        self.channel = channel
        super().__init__(coroutine)

    async def _fill_queue(self):
        values = await self.coroutine

        for value in values:
            message = self.state.create_message(value, self.channel)
            await self.queue.put(message)
