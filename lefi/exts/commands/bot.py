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
    def __init__(self, prefix: str, token: str, *args, **kwargs) -> None:
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
        def inner(func: Callable[..., Coroutine]) -> CMD:
            func.checks: List[Callable[..., bool]] = []  # type: ignore
            command = cls(name or func.__name__, func)
            self.commands[command.name] = command

            return command

        return inner

    def check(self, func: Callable[..., bool]) -> Callable[..., bool]:
        self._check = func
        return func

    def get_command(self, name: str) -> Optional[Command]:
        return self.commands.get(name)

    def remove_command(self, name: str) -> Command:
        return self.commands.pop(name)

    def add_plugin(self, plugin: Type[Plugin]):
        plugin_ = plugin(self)
        self.plugins[plugin_.name] = plugin_
        plugin_._attach_commands(self)

    def remove_plugin(self, name: str) -> Optional[Plugin]:
        return self.plugins.pop(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self.plugins.get(name)

    async def get_context(self, message: lefi.Message, *, cls: Type[CTX] = Context) -> CTX:  # type: ignore
        prefix = await self.get_prefix(message)
        parser = StringParser(message.content, prefix)
        ctx = cls(message, parser, self)

        if command_name := ctx.parser.find_command():
            ctx.command = self.get_command(command_name)

        return ctx

    async def get_prefix(self, message: lefi.Message) -> Union[Tuple[str], str]:
        if callable(self.prefix) and inspect.iscoroutinefunction(self.prefix):
            return await self.prefix(message)

        elif callable(self.prefix):
            return self.prefix(message)

        return self.prefix

    async def parse_commands(self, message: lefi.Message) -> None:
        ctx = await self.get_context(message)  # type: ignore

        if ctx.valid and not ctx.author.bot:
            await self.execute(ctx)

    async def handle_command_error(self, ctx: Context, error: Any) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)

    async def execute(self, ctx: Context) -> Any:
        with Handler(ctx) as handler:
            if handler.can_run and ctx.command:
                return await handler.invoke()

            elif not handler.can_run:
                self._state.dispatch("command_error", ctx, CheckFailed)
