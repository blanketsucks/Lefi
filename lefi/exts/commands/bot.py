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

from .core import Command, Context, StringParser

CTX = TypeVar("CTX", bound=Context)
CMD = TypeVar("CMD", bound=Command)


class Bot(lefi.Client):
    def __init__(self, prefix: str, token: str, *args, **kwargs) -> None:
        super().__init__(token, *args, **kwargs)
        self.add_listener(self.parse_commands, "message_create")
        self.add_listener(self.handle_command_error, "command_error")

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

    def handler(self, func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        self.events["command_error"][0] = func
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
        await self.execute(ctx)

    async def handle_command_error(self, ctx: Context, error: Any) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)

    async def execute(self, ctx: Context) -> None:
        if ctx.command is not None:
            ctx.parser.command = ctx.command
            try:
                kwargs, args = await ctx.parser.parse_arguments()
                await ctx.command(ctx, *args, **kwargs)
            except Exception as error:
                self._state.dispatch("command_error", ctx, error)
