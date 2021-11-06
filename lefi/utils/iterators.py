from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Coroutine, Dict, Generic, TypeVar, List

_T = TypeVar("_T")

from ..objects import User, AuditLogEntry

if TYPE_CHECKING:
    from ..objects import Member, Guild, Message, TextChannel, AuditLogEntry
    from ..state import State

__all__ = (
    "MemberIterator",
    "AsyncIterator",
    "ChannelHistoryIterator",
    "AuditLogIterator",
)


class AsyncIterator(Generic[_T]):
    def __init__(self, coroutine: Coroutine[None, None, Any]) -> None:
        self.coroutine = coroutine
        self.queue = asyncio.Queue[_T]()
        self.filled = False
        self.loop = asyncio.get_running_loop()

    async def _fill_queue(self) -> None:
        values = await self.coroutine

        for value in values:
            await self.queue.put(value)

    async def all(self) -> List[_T]:
        return [val async for val in self]

    async def next(self) -> _T:
        if not self.filled:
            await self._fill_queue()
            self.filled = True

        return self.queue.get_nowait()

    def __await__(self):
        return self.all().__await__()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            value = await self.next()
        except asyncio.QueueEmpty:
            raise StopAsyncIteration
        else:
            return value


class MemberIterator(AsyncIterator["Member"]):
    def __init__(
        self, state: State, guild: Guild, coroutine: Coroutine[None, None, List[Dict]]
    ) -> None:
        self._state = state
        self.guild = guild

        super().__init__(coroutine)

    async def _fill_queue(self) -> None:
        values = await self.coroutine

        for value in values:
            user_id = int(value["user"]["id"])
            member = self.guild.get_member(user_id)

            if not member:
                member = self._state._create_member(value, self.guild)

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

    async def _fill_queue(self) -> None:
        values = await self.coroutine

        for value in values:
            message = self.state.create_message(value, self.channel)
            await self.queue.put(message)


class AuditLogIterator(AsyncIterator["AuditLogEntry"]):
    def __init__(
        self,
        state: State,
        guild: Guild,
        coroutine: Coroutine[None, None, Dict],
    ) -> None:
        self.state = state
        self.guild = guild
        self.users: Dict[int, User] = {}
        super().__init__(coroutine)

    async def _fill_queue(self) -> None:
        logs = await self.coroutine

        users = logs["users"]
        values = logs["audit_log_entries"]

        for user in users:
            u = User(self.state, user)
            self.users[u.id] = u

        for value in values:
            entry = AuditLogEntry(self.users, self.state, self.guild, value)
            await self.queue.put(entry)
