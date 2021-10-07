from __future__ import annotations

import inspect
import asyncio

from typing import (
    Literal,
    Optional,
    Any,
    Tuple,
    Union,
    Callable,
    Dict,
    List,
    TYPE_CHECKING,
    Coroutine,
)

from .http import HTTPClient
from .state import State
from .ws import WebSocketClient
from .utils import MISSING
from .objects import Intents
from .interactions import App

if TYPE_CHECKING:
    from .objects import (
        Message,
        Guild,
        Channel,
        TextChannel,
        VoiceChannel,
        CategoryChannel,
        DMChannel,
        User,
    )

__all__ = ("Client",)


class Client:
    def __init__(
        self,
        token: str,
        *,
        intents: Intents = MISSING,
        pub_key: Optional[str] = MISSING,
        loop: Optional[asyncio.AbstractEventLoop] = MISSING,
    ):
        self.pub_key: Optional[str] = pub_key
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self.http: HTTPClient = HTTPClient(token, self.loop)
        self._state: State = State(self, self.loop)
        self.ws: WebSocketClient = WebSocketClient(self, intents)

        self.events: Dict[str, List[Callable[..., Any]]] = {}
        self.once_events: Dict[str, List[Callable[..., Any]]] = {}
        self.futures: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}

    def add_listener(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        event_name: Optional[str],
    ) -> None:
        name = event_name or func.__name__
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Callback must be a coroutine")

        callbacks = self.events.setdefault(name, [])
        callbacks.append(func)

    def on(self, event_name: Optional[str] = MISSING) -> Callable[..., Callable[..., Coroutine]]:
        def inner(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            self.add_listener(func, event_name)
            return func

        return inner

    def once(self, event_name: Optional[str] = MISSING) -> Callable[..., Callable[..., Coroutine]]:
        def inner(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            name = event_name or func.__name__
            if not inspect.iscoroutinefunction(func):
                raise TypeError("Callback must be a coroutine")

            callbacks = self.once_events.setdefault(name, [])
            callbacks.append(func)
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

    def get_message(self, id: int) -> Optional[Message]:
        return self._state.get_message(id)

    def get_guild(self, id: int) -> Optional[Guild]:
        return self._state.get_guild(id)

    def get_channel(self, id: int) -> Optional[Union[TextChannel, VoiceChannel, DMChannel, CategoryChannel, Channel]]:
        return self._state.get_channel(id)

    def get_user(self, id: int) -> Optional[User]:
        return self._state.get_user(id)

    async def wait_for(self, event: str, *, check: Callable[..., bool] = MISSING, timeout: float = None) -> Any:
        future = self.loop.create_future()
        futures = self.futures.setdefault(event, [])

        if check is MISSING:
            check = lambda *args: True

        futures.append((future, check))
        return await asyncio.wait_for(future, timeout=timeout)
