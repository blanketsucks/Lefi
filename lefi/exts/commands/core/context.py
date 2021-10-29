from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from .command import Command

__all__ = ("Context",)

if TYPE_CHECKING:
    from lefi import Channel, DMChannel, Guild, Member, Message, User

    from ..bot import Bot
    from .parser import StringParser


class Context:
    """
    The Context of a command.

    Attributes:
        command (Command): The [Command](./command.md) that was called.
        parser (StringParser): The [Parser](./parser.md) that was used to parse the command.
        bot (Bot): The [Bot](../bot.md) that is running the command.
    """

    def __init__(self, message: Message, parser: StringParser, bot: Bot) -> None:
        """
        Initialize the Context.

        Parameters:
            message (Message): The [Message](../../message.md) that was sent.
            parser (StringParser): The [Parser](./parser.md) that was used to parse the command.
            bot (Bot): The [Bot](../bot.md) that is running the command.
        """
        self.command: Optional[Command] = None
        self._message = message
        self.parser = parser
        self.bot = bot

    def __repr__(self) -> str:
        return f"<Context valid={self.valid!r}>"

    async def send(self, *args, **kwargs) -> Message:
        """
        Send a message to the channel.

        Parameters:
            args: The arguments to pass when sending the message
            kwargs: The keyword arguments to pass to the message.

        Returns:
            Message: The [Message](../../message.md) that was sent.
        """
        return await self._message.channel.send(*args, **kwargs)

    @property
    def author(self) -> Union[User, Member]:
        """
        The author of the message.
        """
        return self._message.author

    @property
    def channel(self) -> Union[Channel, DMChannel]:
        """
        The [Channel](../../channel.md) that the message was sent in.
        """
        return self._message.channel

    @property
    def message(self) -> Message:
        """
        The [Message](../../message.md) that was sent.
        """
        return self._message

    @property
    def guild(self) -> Optional[Guild]:
        """
        The [Guild](../../guild.md) that the message was sent in.
        """
        return self._message.guild

    @property
    def valid(self) -> bool:
        """
        Whether or not the context is valid.
        """
        return self.command is not None
