from __future__ import annotations

import inspect
import asyncio

from typing import (
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
    """
    A class used to communicate with the discord API and its gateway.

    Attributes:
        pub_key (Optional[str]): The client's public key. Used when handling interactions over HTTP.
        loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] which is being used.
        http (lefi.HTTPClient): The [HTTPClient](./http.md) to use for handling requests to the API.
        ws (lefi.WebSocketClient): The [WebSocketClient](./wsclient.md) which handles the gateway.

    """

    def __init__(
        self,
        token: str,
        *,
        intents: Intents = None,
        pub_key: Optional[str] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Parameters:
            token (str): The clients token, used for authorization (logging in, etc...) This is required.
            intents (Optional[lefi.Intents]): The intents to be used for the client.
            pub_key (Optional[str]): The public key of the client. Only pass if you want interactions over HTTP.
            loop (Optional[asyncio.AbstractEventLoop]): The loop to use.

        """

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
        func: Callable[..., Coroutine],
        event_name: Optional[str],
    ) -> None:
        """
        Registers listener, basically connecting an event to a callback.

        Parameters:
            func (Callable[..., Coroutine]): The callback to register for an event.
            event_name (Optional[str]): The event to register, if None it will pass the decorated functions name.

        """
        name = event_name or func.__name__
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Callback must be a coroutine")

        callbacks = self.events.setdefault(name, [])
        callbacks.append(func)

    def on(
        self, event_name: Optional[str] = None
    ) -> Callable[..., Callable[..., Coroutine]]:
        """
        A decorator that registers the decorated function to an event.

        Parameters:
            event_name (Optional[str]): The event to register.

        Note:
            The function being decorated must be a coroutine.
            Multiple functions can be decorated with the same event.
            Although you will need to pass the event name and give functions different names.
            And if no event name is passed it defaults to the functions name.

        Returns:
            The decorated function after registering it as a listener.

        """

        def inner(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            self.add_listener(func, event_name)
            return func

        return inner

    def once(
        self, event_name: Optional[str] = None
    ) -> Callable[..., Callable[..., Coroutine]]:
        """
        A decorator that registers the decorated function to an event.
        Similar to [lefi.Client.on][] but also cuts itself off the event after firing once.
        Meaning it will only run once.

        Parameters:
            event_name (Optional[str]): The event to register.

        Note:
            Functions must be coroutines.
            Multiple functions can be decorated with this that have the same event.
            Functions decorated with [lefi.Client.once][] take precedence over the regular events.

        Returns:
            The decorated function after registering it as a listener.

        """

        def inner(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            name = event_name or func.__name__
            if not inspect.iscoroutinefunction(func):
                raise TypeError("Callback must be a coroutine")

            callbacks = self.once_events.setdefault(name, [])
            callbacks.append(func)
            return func

        return inner

    async def connect(self) -> None:
        """
        A method which starts the connection to the gateway.
        """
        await self.ws.start()

    async def login(self) -> None:
        """
        A method which "logs" in with the token to make sure it is valid.
        This is to make sure that proper authorization has been passed.
        """
        await self.http.login()

    async def start(self) -> None:
        """
        A method which calls [lefi.Client.login][] and [lefi.Client.connect][] in that order.
        If `pub_key` is passed to the clients constructor it also creates an HTTP server to handle interactions.
        """
        if self.pub_key:
            self.server = App(self, self.pub_key)
            await self.server.run()

        await asyncio.gather(self.login(), self.connect())

    def get_message(self, id: int) -> Optional[Message]:
        """
        Grabs a [lefi.Message][] instance if cached.

        Parameters:
            id (int): The message's ID.

        Returns:
            The [lefi.Message][] instance related to the ID. Else None if not found.

        """
        return self._state.get_message(id)

    def get_guild(self, id: int) -> Optional[Guild]:
        """
        Grabs a [lefi.Guild][] instance if cached.

        Parameters:
            id (int): The guild's ID.

        Returns:
            The [lefi.Guild][] instance related to the ID. Else None if not found

        """
        return self._state.get_guild(id)

    def get_channel(
        self, id: int
    ) -> Optional[
        Union[TextChannel, VoiceChannel, DMChannel, CategoryChannel, Channel]
    ]:
        """
        Grabs a [lefi.Channel][] instance if cached.

        Parameters:
            id (int): The channel's ID.

        Returns:
            The [lefi.Channel][] instance related to the ID. Else None if not found

        """
        return self._state.get_channel(id)

    def get_user(self, id: int) -> Optional[User]:
        """
        Grabs a [lefi.User][] instance if cached.

        Parameters:
            id (int): The user's ID.

        Returns:
            The [lefi.User][] instance related to the ID. Else None if not found

        """
        return self._state.get_user(id)

    async def wait_for(
        self, event: str, *, check: Callable[..., bool] = None, timeout: float = None
    ) -> Any:
        """
        Waits for an event to be dispatched that passes the check.

        Parameters:
            event (str): The event to wait for.
            check (Callable[..., bool]): A function that takes the same args as the event, and returns a bool.
            timeout (float): The time to wait before stopping.

        Returns:
            The return from a callback that matches with the event you are waiting for.

        Note:
            The check has to take in the same args as the event.
            If no check is passed, everything will complete the check.

        """
        future = self.loop.create_future()
        futures = self.futures.setdefault(event, [])

        if check is None:
            check = lambda *args: True

        futures.append((future, check))
        return await asyncio.wait_for(future, timeout=timeout)
