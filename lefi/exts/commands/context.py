from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .command import Command

__all__ = ("Context",)


class Context:
    if TYPE_CHECKING:
        from .parser import StringParser
        from lefi import Message
        from .bot import Bot

    def __init__(self, message: Message, parser: StringParser, bot: Bot) -> None:
        self.command: Optional[Command] = None
        self.message = message
        self.parser = parser
        self.bot = bot

    @property
    def valid(self) -> bool:
        return self.command is not None
