from __future__ import annotations

import typing
import inspect

import asyncio

from .http import HTTPClient
from .state import State
from .ws import WebSocketClient
from .utils import MISSING

from .interactions import App

if typing.TYPE_CHECKING:
    from .objects import Message

__all__ = ("Client",)


class Client:
    def __init__(
        self,
        token: str,
        *,
        pub_key: typing.Optional[str] = MISSING,
        loop: typing.Optional[asyncio.AbstractEventLoop] = MISSING,
    ):
        self.pub_key: typing.Optional[str] = pub_key
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self.http: HTTPClient = HTTPClient(token, self.loop)
        self._state: State = State(self, self.loop)
        self.ws: WebSocketClient = WebSocketClient(self)

        self.events: typing.Dict[str, typing.List[typing.Callable]] = {}

    def add_listener(
        self,
        func: typing.Callable[..., typing.Coroutine],
        event_name: typing.Optional[str],
    ) -> None:
        name = event_name or func.__name__
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Callback must be a coroutine")

        callbacks = self.events.setdefault(name, [])
        callbacks.append(func)

    def on(
        self, event_name: typing.Optional[str] = MISSING
    ) -> typing.Callable[..., typing.Callable[..., typing.Coroutine]]:
        def inner(
            func: typing.Callable[..., typing.Coroutine]
        ) -> typing.Callable[..., typing.Coroutine]:
            self.add_listener(func, event_name)
            return func

        return inner

    async def connect(self) -> None:
        await self.ws.start()

    async def login(self) -> None:
        await self.http.login()

    async def start(self) -> None:
        if self.pub_key:
            self.server = App(self, self.pub_key)
            await self.server.run()

        await asyncio.gather(self.login(), self.connect())

    def get_message(self, id: int) -> typing.Optional[Message]:
        return self._state._messages.get(id)
