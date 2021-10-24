from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from .command import Command

__all__ = ("Context",)

if TYPE_CHECKING:
    from lefi import Channel, DMChannel, Guild, Member, Message, User

    from ..bot import Bot
    from .parser import StringParser


class Context:
    def __init__(self, message: Message, parser: StringParser, bot: Bot) -> None:
        self.command: Optional[Command] = None
        self._message = message
        self.parser = parser
        self.bot = bot

    def __repr__(self) -> str:
        return f"<Context valid={self.valid!r}>"

    async def send(self, **kwargs) -> Message:
        return await self._message.channel.send(**kwargs)

    @property
    def author(self) -> Union[User, Member]:
        return self._message.author

    @property
    def channel(self) -> Union[Channel, DMChannel]:
        return self._message.channel

    @property
    def message(self) -> Message:
        return self._message

    @property
    def guild(self) -> Optional[Guild]:
        return self._message.guild

    @property
    def valid(self) -> bool:
        return self.command is not None
