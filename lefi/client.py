from __future__ import annotations

import asyncio
import inspect

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from .http import HTTPClient
from .objects import (
    CategoryChannel,
    Channel,
    DMChannel,
    Emoji,
    Guild,
    GuildTemplate,
    Invite,
    Message,
    TextChannel,
    User,
    VoiceChannel,
    AppCommand,
)
from .state import Cache, State
from .ws import Shard, WebSocketClient
from .voice import VoiceClient

if TYPE_CHECKING:
    from .objects import Intents

__all__ = ("Client",)


class Client:
    """The class used to communicate with the discord API and its gateway.
    A class used to communicate with the discord API and its gateway.

    Parameters
    ----------
    token: :class:`str`
        The token used for authorization to the discord API.

    intents: :class:`.Intents`
        The intents to IDENTIFY with, this will determine which events you receive.

    sharded: :class:`bool`
        Whether or not the client should be sharded. If no shard_ids are passed
        the amount of shards will be determined by the discord API. Defaults to False if not passed.

    shard_ids: Optional[List[:class:`int`]]
        The shard IDs to use when sharding the client.

    loop: Optional[:class:`asyncio.AbstractEventLoop`]
        The :class:`asyncio.AbstractEventLoop` to use. If no loop is passed then the
        library will set a new event loop.

    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop to use.

    http: :class:`.HTTPClient`
        The HTTPClient to use for API calls. This class handles both requesting ratelimiting.

        .. warning::
            This is used internally and should not be called directly on.

    ws: :class:`.WebSocketClient`
        The internal websocket which listens to the gateway.

        .. warning::
            This is only used internally and any changes to this class can break everything.

    user: :class:`.User`
        The :class:`.User` representing the client's discord user.

    shards: Optional[List[:class:`.Shard`]]
        A list of shards the connected to the client.
        This is set if the client is sharded. Otherwise it will be None.

    application_commands: List[:class:`.AppCommand`]
        A list of application commands connected to the client.
    """

    def __init__(
        self,
        token: str,
        *,
        intents: Intents = None,
        sharded: bool = False,
        shard_ids: Optional[List[int]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self.loop: asyncio.AbstractEventLoop = loop or self._create_loop()
        self.http: HTTPClient = HTTPClient(token, self.loop)
        self._state: State = State(self, self.loop)
        self.ws: WebSocketClient = WebSocketClient(self, intents, shard_ids, sharded)

        self.events: Dict[str, Cache[Callable[..., Any]]] = {}
        self.once_events: Dict[str, List[Callable[..., Any]]] = {}
        self.futures: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}

        self.user: User = None  # type: ignore
        self.shards: Optional[List[Shard]] = None
        self.application_commands: Dict[str, AppCommand] = {}

    def _create_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            return loop

    def add_listener(
        self,
        func: Callable[..., Coroutine],
        event_name: Optional[str],
        overwrite: bool = False,
    ) -> None:
        """Registers listeners, connecting an event to a callback.

        Parameters
        ----------
        func: Callable[..., Coroutine]
            The callback of the event. This will be ran everytime the event is dispatched.

        event_name: :class:`str`
            The name of the event to register.

        overwrite: :class:`bool`
            Whether or not to overwrite previous callbacks registered to this event.

        Raises
        ------
        :exc:`TypeError`
            The callback being added is not a Coroutine.
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
        """A decorator that registers the decorated function to an event.

        Parameters
        ----------
        event_name: Optional[:class:`str`]
            The event which to register the callback under. Defaults to the
            functions name if no event name is passed.

        overwrite: :class:`bool`
            Whether or not to overwrite the events previous callbacks.

        Examples
        --------
        Registering an event callback ::

            @client.on("message_create")
            async def on_message(message: lefi.Message) -> None:
                await message.channel.send(f"Received a message from {message.author}")

        Registering two event callbacks ::

            @client.on("message_create")
            async def on_message(message: lefi.Message) -> None:
                await message.channel.send("Got your message!")

            @client.on("message_create")
            async def on_message2(message: lefi.Message) -> None:
                print(message.content)
            @client.on("message_create")


        Returns
        -------
        :class:`Coroutine`
            The decorated function.
        """

        def inner(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            self.add_listener(func, event_name, overwrite)
            return func

        return inner

    def once(
        self, event_name: Optional[str] = None
    ) -> Callable[..., Callable[..., Coroutine]]:
        """A decorator that registers one time callbacks.

        Similar to :meth:`on` it registers a callback to an event, but also
        after an event is dispatched the callback will be cutoff and thus running only once per lifetime.

        .. note::

            events decorated with this method take precedence over regular events.

        Parameters
        ----------
        event_name: Optional[:class:`str`]
            The name of the vent to register the callback to.

        Examples
        --------
        Registering a one-time event callback ::

            @client.once("ready")
            async def on_ready(user: lefi.User) -> None:
                print(f"Logged in as {user.id}")

        Raises
        ------
        :exc:`TypeError`
            The callback being added is not a :class:`Coroutine`

        Returns
        -------
        :class:`Coroutine`
            The decorated function.
        """

        def inner(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            name = event_name or func.__name__
            if not inspect.iscoroutinefunction(func):
                raise TypeError("Callback must be a coroutine")

            callbacks = self.once_events.setdefault(name, [])
            callbacks.append(func)
            return func

        return inner

    def application_command(
        self, name: str, description: Optional[str] = None, **kwargs
    ) -> Callable[..., AppCommand]:
        """A decorator which adds an application command.

        This decorator added an application command. Currently only supporting
        slash commands. The function being decorator will be called when this command is invoked.

        Parameters
        ----------
        name: :class:`str`
            The name of the command

        description: Optional[:class:`str`]
            The description of the command

        **kwargs: Any
            Extra arguments to create the command with.

        Returns
        -------
        :class:`lefi.AppCommand`
            The created application command.
        """

        def inner(func: Coroutine) -> AppCommand:
            command = AppCommand(name, description, client=self, **kwargs)
            command.callback = func  # type: ignore

            self.loop.create_task(command.register())

            self.application_commands[command.name] = command
            return command

        return inner

    async def connect(self) -> None:
        """Starts the connection between the client and the gateway.

        Unless completely sure, you should run :meth:`login` before call this.
        That would ensure that the token passed is valid and allow for authorization.
        """
        await self.ws.start()

    async def close(self) -> None:
        """Closes the :class:`aiohttp.ClientSession` and the websocket connection.

        This method essentially closing the client.
        """
        await self.http.close()

        for voice in self.voice_clients:
            await voice.disconnect()

        if self.shards:
            for shard in self.shards:
                await shard.close()
        else:
            await self.ws.close()

        return None

    def run(self) -> None:
        """A blocking version of :meth:`start`"""
        try:
            self.loop.run_until_complete(self.start())
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.close())

    async def login(self) -> None:
        """A method which attempts to login
        This is done to verify if the token is valid.

        Raises
        ------
        :exc:`ValueError`
            The token is invalid.
        """
        await self.http.login()

    async def start(self) -> None:
        """An async method which starts the connection to the API.
        Calls :meth:`login` and :meth:`connect` in that order.
        """
        await self.login()
        await self.connect()

    async def wait_for(
        self, event: str, *, check: Callable[..., bool] = None, timeout: float = None
    ) -> Any:
        """A method which waits for an event to be dispatched.

        This method will wait until the specified event is dispatched
        and if the passed check returns truthy.

        Parameters
        ----------
        event: :class:`str`
            The name of the event to wait for

        check: Callable[..., :class:`bool`]
            The check that needs to be passed. Defaults to always return True
            if not passed to the method.

        timeout: :class:`float`
            The amount of time in seconds to wait before canceling

        Returns
        ------
        Any
            The parameters of the event which the client was waiting for
        """
        future = self.loop.create_future()
        futures = self.futures.setdefault(event, [])

        if check is None:
            check = lambda *_: True

        futures.append((future, check))
        return await asyncio.wait_for(future, timeout=timeout)

    @property
    def guilds(self) -> List[Guild]:
        """List[:class:`lefi.Guild`] The list of guilds the client is in."""
        return list(self._state._guilds.values())

    @property
    def channels(self) -> List[Union[Channel, DMChannel]]:
        """List[Union[:class:`Channel`, :class:`DMChannel`]] The list of channels the client can see."""
        return list(self._state._channels.values())

    @property
    def users(self) -> List[User]:
        """List[:class:`lefi.User`] The list of users that the client can see."""
        return list(self._state._users.values())

    @property
    def voice_clients(self) -> List[VoiceClient]:
        """List[:class:`lefi.VoiceClient`] The list of voice clients the client has."""
        return list(self._state._voice_clients.values())

    def get_message(self, id: int) -> Optional[Message]:
        """A method which grabs a message from the cache.

        Grabs a :class:`lefi.Message` in the cache corresponding to the passed in id.
        If the message isn't found in the cache this method will return None.

        Parameters
        ----------
        id: :class:`int`
            The message's ID

        Returns
        -------
        Optional[:class:`lefi.Message`]
            The message instance if cached.
        """
        return self._state.get_message(id)

    def get_guild(self, id: int) -> Optional[Guild]:
        """A method which grabs a guild from the cache.

        Grabs a :class:`lefi.Guild` in the cache corresponding to the passed in id.
        If the guild isn't found in the cache this method will return None.

        Parameters
        ----------
        id: :class:`int`
            The guild's ID

        Returns
        -------
        Optional[:class:`lefi.Guild`]
            The guild instance if cached.
        """
        return self._state.get_guild(id)

    def get_channel(self, id: int) -> Optional[Union[Channel, DMChannel]]:
        """A method which grabs a channel from the cache.

        Grabs a :class:`lefi.Channel` or a :class:`lefi.DMChannel` in the cache
        corresponding to the passed in id. If the channel isn't found in the cache
        this method will return None.

        Parameters
        ----------
        id: :class:`int`
            The channel's ID

        Returns
        -------
        Optional[Union[:class:`lefi.Channel`, :class:`lefi.DMChannel`]]
            The channel instance if cached.
        """
        return self._state.get_channel(id)

    def get_user(self, id: int) -> Optional[User]:
        """A method which grabs a user from the cache.

        Grabs a :class:`lefi.User` in the cache corresponding to the passed in id.
        If the channel isn't found in the cache this method will return None.

        Parameters
        ----------
        id: :class:`int`
            The user's ID

        Returns
        -------
        Optional[:class:`lefi.User`]
            The user instance if cached.
        """
        return self._state.get_user(id)

    def get_emoji(self, id: int) -> Optional[Emoji]:
        """A method which grabs an emoji from the cache.

        Grabs a :class:`lefi.Emoji` in the cache corresponding to the passed in id.
        If the emoji isn't found in the cache this method will return None.

        Parameters
        ----------
        id: :class:`int`
            The emoji's ID

        Returns
        -------
        Optional[:class:`lefi.Emoji`]
            The emoji instance if cached.
        """
        return self._state.get_emoji(id)

    async def fetch_user(self, user_id: int) -> User:
        """A method which makes an API call to fetch a user.

        This method does an API call to fetch a user corresponding to the id passed in.

        .. note ::

            This should only really be used when the corresponding `get_` method returns None.

        Parameters
        ----------
        user_id: :class:`int`
            The user's ID

        Returns
        -------
        :class:`lefi.User`
            The fetched user.
        """
        data = await self.http.get_user(user_id)
        return self._state.add_user(data)

    async def fetch_invite(self, code: str, **kwargs) -> Invite:
        """A method which makes an API call to fetch an invite.

        This method does an API call to fetch an invite corresponding to the code passed in.

        .. note ::

            This should only really be used when the corresponding `get_` method returns None.

        Parameters
        ----------
        code: :class:`str`
            The invite's code

        **kwargs: Any
            Any extra options to pass to :meth:`lefi.HTTPClient.get_invite`

        Returns
        -------
        :class:`lefi.Invite`
            The fetched invite.
        """
        data = await self.http.get_invite(code, **kwargs)
        return Invite(data=data, state=self._state)

    async def fetch_guild(self, guild_id: int) -> Guild:
        """A method which makes an API call to fetch a guild.

        This method does an API call to fetch a guild corresponding to the id passed in.

        .. note ::

            This should only really be used when the corresponding `get_` method returns None.

        Parameters
        ----------
        guild_id: :class:`int`
            The guild's ID

        Returns
        -------
        :class:`lefi.Guild`
            The fetched guild.
        """
        data = await self.http.get_guild(guild_id)
        return Guild(data=data, state=self._state)

    async def fetch_template(self, code: str) -> GuildTemplate:
        """A method which makes an API call to fetch a guild template.

        This method does an API call to fetch a guild template corresponding to the code passed in.

        .. note ::

            This should only really be used when the corresponding `get_` method returns None.

        Parameters
        ----------
        code: :class:`str`
            The guild template's code

        Returns
        -------
        :class:`lefi.GuildTemplate`
            The fetched guild template.
        """
        data = await self.http.get_guild_template(code)
        return GuildTemplate(data=data, state=self._state)
