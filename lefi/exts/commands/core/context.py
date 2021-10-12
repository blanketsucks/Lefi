from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from .command import Command

__all__ = ("Context",)

if TYPE_CHECKING:
    from lefi import Message, User

    from ..bot import Bot
    from .parser import StringParser


class Context:
    def __init__(self, message: Message, parser: StringParser, bot: Bot) -> None:
        self.command: Optional[Command] = None
        self.author: User = message.author
        self.message = message
        self.parser = parser
        self.bot = bot

    async def send(self, **kwargs) -> Message:
        return await self.message.channel.send(**kwargs)

    @property
    def valid(self) -> bool:
        return self.command is not None
