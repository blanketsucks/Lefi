from __future__ import annotations

from typing import Dict, List, Callable, Union, Tuple, TypeVar, Type

import lefi

from .context import Context
from .parser import StringParser

CTX = TypeVar("CTX", bound=Context)


class Bot(lefi.Client):
    def __init__(self, prefix: str, token: str, *args, **kwargs) -> None:
        super().__init__(token, *args, **kwargs)
        self.add_listener(self.parse_commands, "message_create")
        self.add_listener(self.handle_command_error, "command_error")

        self.checks: List[Callable[..., bool]] = []
        self.commands: Dict = {}
        self.prefix = prefix

    async def execute(self, ctx: Context) -> None:
        ...

    async def get_context(
        self, message: lefi.Message, *, cls: Type[CTX] = Context
    ) -> CTX:
        return cls(
            message, StringParser(message.content, await self.get_prefix(message)), self
        )

    async def get_prefix(self, message: lefi.Message) -> Union[Tuple[str], str]:
        if callable(self.prefix):
            return await self.prefix(message)

        return self.prefix

    async def parse_commands(self, message: lefi.Message) -> None:
        ctx = await self.get_context(message)  # type: ignore
        await self.execute(ctx)

    async def handle_command_error(self) -> None:
        ...
