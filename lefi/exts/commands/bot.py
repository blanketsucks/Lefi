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
)

import lefi

from .command import Command
from .context import Context
from .parser import StringParser

CTX = TypeVar("CTX", bound=Context)
CMD = TypeVar("CMD", bound=Command)


class Bot(lefi.Client):
    def __init__(self, prefix: str, token: str, *args, **kwargs) -> None:
        super().__init__(token, *args, **kwargs)
        self.add_listener(self.parse_commands, "message_create")

        self.checks: List[Callable[..., bool]] = []
        self.commands: Dict = {}
        self.prefix = prefix

    def command(
        self, name: Optional[str] = None, *, cls: Type[CMD] = Command  # type: ignore
    ) -> Callable[..., CMD]:
        def inner(func: Callable[..., Coroutine]) -> CMD:
            command = cls(name or func.__name__, func)
            self.commands[command.name] = command

            return command

        return inner

    def get_command(self, name: str) -> Optional[Command]:
        return self.commands.get(name)

    async def get_context(
        self, message: lefi.Message, *, cls: Type[CTX] = Context  # type: ignore
    ) -> CTX:
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

    async def execute(self, ctx: Context) -> None:
        if ctx.command is not None:
            await ctx.command(ctx, *ctx.parser.arguments)
