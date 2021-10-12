from __future__ import annotations

from typing import (
    Dict,
    List,
    Union,
    Tuple,
    TypeVar,
    Type,
    Callable,
    Coroutine,
    Optional,
    Any,
)

import lefi

import traceback
import contextlib

from .core import Command, Context, StringParser

CTX = TypeVar("CTX", bound=Context)
CMD = TypeVar("CMD", bound=Command)


class Handler:
    def __init__(self, ctx: Context):
        self.context = ctx

    async def invoke(self) -> Any:
        assert self.context.command is not None

        self.context.parser.command = self.context.command
        kwargs, args = await self.context.parser.parse_arguments()

        return await self.context.command(self.context, *args, **kwargs)

    def __enter__(self) -> Handler:
        with contextlib.suppress():
            self.can_run = self.context.bot._check(self.context)

        return self

    def __exit__(self, *exception) -> bool:
        _, error, _ = exception

        if error is not None:
            self.context.bot._state.dispatch("command_error", self.context, error)

        return True


class Bot(lefi.Client):
    def __init__(self, prefix: str, token: str, *args, **kwargs) -> None:
        super().__init__(token, *args, **kwargs)
        self.add_listener(self.parse_commands, "message_create", False)
        self.add_listener(self.handle_command_error, "command_error", False)

        self._check: Callable[..., bool] = lambda _: True
        self.checks: List[Callable[..., bool]] = []
        self.commands: Dict[str, Command] = {}
        self.prefix = prefix

    def command(
        self, name: Optional[str] = None, *, cls: Type[CMD] = Command  # type: ignore
    ) -> Callable[..., CMD]:
        def inner(func: Callable[..., Coroutine]) -> CMD:
            command = cls(name or func.__name__, func)
            self.commands[command.name] = command

            return command

        return inner

    def check(self, func: Callable[..., bool]) -> Callable[..., bool]:
        self._check = func
        return func

    def get_command(self, name: str) -> Optional[Command]:
        return self.commands.get(name)

    async def get_context(self, message: lefi.Message, *, cls: Type[CTX] = Context) -> CTX:  # type: ignore
        context = cls(
            message, StringParser(message.content, await self.get_prefix(message)), self
        )

        if command_name := context.parser.find_command():
            context.command = self.get_command(command_name)

        return context

    async def get_prefix(self, message: lefi.Message) -> Union[Tuple[str], str]:
        if callable(self.prefix):
            return await self.prefix(message)

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

            self._state.dispatch("command_error", ctx, TypeError("Err"))
