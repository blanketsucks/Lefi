from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union

from .http import HTTPClient
from .objects import (
    CategoryChannel,
    Channel,
    DMChannel,
    Emoji,
    Guild,
    GuildTemplate,
    Intents,
    Invite,
    Message,
    TextChannel,
    User,
    VoiceChannel,
)
from .state import Cache, State
from .ws import WebSocketClient

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
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Parameters:
            token (str): The clients token, used for authorization (logging in, etc...) This is required.
            intents (Optional[lefi.Intents]): The intents to be used for the client.
            loop (Optional[asyncio.AbstractEventLoop]): The loop to use.

        """
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_running_loop()
        self.http: HTTPClient = HTTPClient(token, self.loop)
        self._state: State = State(self, self.loop)
        self.ws: WebSocketClient = WebSocketClient(self, intents)

        self.events: Dict[str, Cache[Callable[..., Any]]] = {}
        self.once_events: Dict[str, List[Callable[..., Any]]] = {}
        self.futures: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}

        self.user: User = None  # type: ignore

    def add_listener(
        self,
        func: Callable[..., Coroutine],
        event_name: Optional[str],
        overwrite: bool = False,
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

        callbacks = self.events.setdefault(
            name, Cache[Callable[..., Coroutine]](maxlen=1 if overwrite else None)
        )

        if overwrite is False:
            callbacks.maxlen = None

        elif overwrite is True:
            callbacks.maxlen = 1

        callbacks[func] = func  # type: ignore

    def on(
        self, event_name: Optional[str] = None, overwrite: bool = False
    ) -> Callable[..., Callable[..., Coroutine]]:
        """
        A decorator that registers the decorated function to an event.

        Parameters:
            event_name (Optional[str]): The event to register.
            overwrite (bool): Whether or not to clear every callback except for the current one being registered.

        Note:
            The function being decorated must be a coroutine.
            Multiple functions can be decorated with the same event.
            Although you will need to pass the event name and give functions different names.
            And if no event name is passed it defaults to the functions name.

        Returns:
            The decorated function after registering it as a listener.

        Example:
            ```py
            @client.on("message_create")
            async def on_message(message: lefi.Message) -> None:
                await message.channel.send("Got your message!")
            ```

            ```py
            @client.on("message_create")
            async def on_message(message: lefi.Message) -> None:
                await message.channel.send("Got your message!")

            @client.on("message_create")
            async def on_message2(message: lefi.Message) -> None:
                print(message.content)
            ```

        """

        def inner(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            self.add_listener(func, event_name, overwrite)
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

        Example:
            ```py
            @client.once("ready")
            async def on_ready(client_user: lefi.User) -> None:
                print(f"logged in as {client_user.username}")
            ```

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
        """
        await asyncio.gather(self.login(), self.connect())

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

        Example:
            ```py
            @client.on("message_create")
            async def on_message(message: lefi.Message) -> None:
                if message.content == "wait for next!":
                    next_message = await client.wait_for(
                        "message_create",
                        check=lambda msg: msg.author.id == 270700034985558017
                    )
                await message.channel.send(f"got your message! `{next_message.content}`")
            ```

        """
        future = self.loop.create_future()
        futures = self.futures.setdefault(event, [])

        if check is None:
            check = lambda *_: True

        futures.append((future, check))
        return await asyncio.wait_for(future, timeout=timeout)

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

    def get_emoji(self, id: int) -> Optional[Emoji]:
        """
        Grabs a [lefi.Emoji][] instance if cached.

        Parameters:
            id (int): The emoji's ID.

        Returns:
            The [lefi.Emoji][] instance related to the ID. Else None if not found

        """
        return self._state.get_emoji(id)

    async def fetch_invite(self, code: str, **kwargs) -> Invite:
        """
        Fetches an invite from the API.

        Parameters:
            code (str): The invite code.

        Returns:
            The [lefi.Invite][] instance related to the code.

        """
        data = await self.http.get_invite(code, **kwargs)
        return Invite(data=data, state=self._state)

    async def fetch_guild(self, guild_id: int) -> Guild:
        """
        Fetches a guild from the API.

        Parameters:
            guild_id (int): The guild's ID.

        Returns:
            The [lefi.Guild][] instance related to the ID.

        """
        data = await self.http.get_guild(guild_id)
        return Guild(data=data, state=self._state)

    async def fetch_template(self, code: str) -> GuildTemplate:
        """
        Fetches a template from the API.

        Parameters:
            code (str): The template code.

        Returns:
            The [lefi.GuildTemplate][] instance related to the code.

        """
        data = await self.http.get_guild_template(code)
        return GuildTemplate(data=data, state=self._state)
