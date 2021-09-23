from __future__ import annotations

import typing
import inspect

import asyncio

from .http import HTTPClient
from .state import State
from .ws import WebSocketClient

__all__ = ("Client",)


class Client:
    def __init__(
        self, token: str, loop: typing.Optional[asyncio.AbstractEventLoop] = None
    ):
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self.http: HTTPClient = HTTPClient(token, self.loop)
        self.ws: WebSocketClient = WebSocketClient(self)
        self._state: State = State(self, self.loop)

        self.events: typing.Dict[str, typing.List[typing.Callable]] = {}

    def add_listener(self, func: typing.Callable, event_name: typing.Optional[str]):
        name = event_name or func.__name__
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Callback must be a coroutine")

        if name in self.events:
            self.events[name].append(func)
            self.events[name] = [func]

    def on(
        self, event_name: typing.Optional[str] = None
    ) -> typing.Callable[..., typing.Callable]:
        def inner(func: typing.Callable) -> typing.Callable:
            self.add_listener(func, event_name)
            return func

        return inner

    async def connect(self) -> None:
        await self.ws.start()

    async def login(self, token: str) -> None:
        await self.http.login(token)

    async def start(self) -> None:
        await asyncio.gather(self.login(self.http.token), self.connect())
