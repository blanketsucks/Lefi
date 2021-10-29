from __future__ import annotations

import contextlib
import inspect
import traceback
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import lefi

from .core import Command, Context, Plugin, StringParser, Handler
from .errors import CheckFailed

CTX = TypeVar("CTX", bound=Context)
CMD = TypeVar("CMD", bound=Command)


class Bot(lefi.Client):
    """
    A subclass of [Client](../client.md) that adds Pluign, commands and some more functionality to it.

    Attributes:
        prefix (str): The prefix to use for commands.
        commands (Dict[str, Command]): The commands registered.
        plugins (Dict[str, Plugin]): The plugins registered.
        checks (List[Callable[..., bool]]): The checks registered.
        pub_key (Optional[str]): The client's public key. Used when handling interactions over HTTP.
        loop (asyncio.AbstractEventLoop): The event loop to use.
        which is being used.
        http (lefi.HTTPClient): The [HTTPClient](../http.md) to use for handling requests to the API.
        ws (lefi.WebSocketClient): The [WebSocketClient](../wsclient.md) which handles the gateway.

    """

    def __init__(self, prefix: str, token: str, *args, **kwargs) -> None:
        """
        Parameters:
            prefix (str): The prefix to use for commands.
            token (str): The clients token, used for authorization (logging in, etc...) This is required.
            intents (Optional[lefi.Intents]): The intents to be used for the client.
            loop (Optional[asyncio.AbstractEventLoop]): The loop to use.
        """
        super().__init__(token, *args, **kwargs)
        self.add_listener(self.parse_commands, "message_create", False)
        self.add_listener(self.handle_command_error, "command_error", False)

        self._check: Callable[..., bool] = lambda _: True
        self.checks: List[Callable[..., bool]] = []
        self.commands: Dict[str, Command] = {}
        self.plugins: Dict[str, Plugin] = {}
        self.prefix = prefix

    def command(
        self, name: Optional[str] = None, *, cls: Type[CMD] = Command  # type: ignore
    ) -> Callable[..., CMD]:
        """
        Decorator to register a command.

        Parameters:
            name (Optional[str]): The name of the command.
            cls (Optional[Type[CMD]]): The class to use for the command.

        Returns:
            The decorated function after registering the command.

        Example:
            ```py
            @bot.command()
            async def ping(ctx):
                await ctx.send("Pong!")
            ```
        """

        def inner(func: Callable[..., Coroutine]) -> CMD:
            func.checks: List[Callable[..., bool]] = []  # type: ignore
            command = cls(name or func.__name__, func)
            self.commands[command.name] = command

            return command

        return inner

    def check(self, func: Callable[..., bool]) -> Callable[..., bool]:
        """
        A method to register a check.

        Parameters:
            func (Callable[..., bool]): The function to register.

        Returns:
            The function passed.
        """
        self._check = func
        return func

    def get_command(self, name: str) -> Optional[Command]:
        """
        Get a command by name.

        Parameters:
            name (str): The name of the command.

        Returns:
            The [Command](./core/command.md) if found, otherwise None.
        """
        return self.commands.get(name)

    def remove_command(self, name: str) -> Command:
        """
        Remove a command by name.

        Parameters:
            name (str): The name of the command.

        Returns:
            The [Command](./core/command.md) removed.
        """
        return self.commands.pop(name)

    def add_plugin(self, plugin: Type[Plugin]) -> None:
        """
        Add a plugin to the bot.

        Parameters:
            plugin (Type[Plugin]): The [Plugin](./core/plugin.md) to add.
        """
        plugin_ = plugin(self)
        self.plugins[plugin_.name] = plugin_
        plugin_._attach_commands(self)

    def remove_plugin(self, name: str) -> Optional[Plugin]:
        """
        Remove a plugin by name.

        Parameters:
            name (str): The name of the plugin.

        Returns:
            The [Plugin](./core/plugin.md) removed.
        """
        return self.plugins.pop(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.

        Parameters:
            name (str): The name of the plugin.

        Returns:
            The instance of [Plugin](./core/plugin.md) if found, otherwise None.
        """
        return self.plugins.get(name)

    async def get_context(self, message: lefi.Message, *, cls: Type[CTX] = Context) -> CTX:  # type: ignore
        """
        Get a context for a message.

        Parameters:
            message (lefi.Message): The [Message](../message.md) to get the context for.
            cls (Optional[Type[CTX]]): The class to use for the context.

        Returns:
            An instance of [Context](./core/context.md).
        """
        prefix = await self.get_prefix(message)
        parser = StringParser(message.content, prefix)
        ctx = cls(message, parser, self)

        if command_name := ctx.parser.find_command():
            ctx.command = self.get_command(command_name)

        return ctx

    async def get_prefix(self, message: lefi.Message) -> Union[Tuple[str], str]:
        """
        Get the prefix for a message.

        Parameters:
            message (lefi.Message): The [Message](../message.md) from which prefix needs to be extracted.

        Returns:
            The prefix or a tuple of prefixes.
        """
        if callable(self.prefix) and inspect.iscoroutinefunction(self.prefix):
            return await self.prefix(message)

        elif callable(self.prefix):
            return self.prefix(message)

        return self.prefix

    async def parse_commands(self, message: lefi.Message) -> None:
        """
        Parse a message for looking up commands.

        Parameters:
            message (lefi.Message): The [Message](../message.md) to parse.
        """
        ctx = await self.get_context(message)  # type: ignore

        if ctx.valid and not ctx.author.bot:
            await self.execute(ctx)

    async def handle_command_error(self, ctx: Context, error: Any) -> None:
        """
        Handle a command error.

        Parameters:
            ctx (Context): The [Context](./core/context.md) of the command.
            error (Any): The error that occured.
        """
        traceback.print_exception(type(error), error, error.__traceback__)

    async def execute(self, ctx: Context) -> Any:
        """
        Execute a command.

        Parameters:
            ctx (Context): The [Context](./core/context.md) of the command.

        Returns:
            The result of the command.
        """
        with Handler(ctx) as handler:
            if handler.can_run and ctx.command:
                return await handler.invoke()

            elif not handler.can_run:
                self._state.dispatch("command_error", ctx, CheckFailed)
