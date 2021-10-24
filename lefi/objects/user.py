from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from ..utils import Snowflake
from .channel import DMChannel
from .enums import PremiumType
from .flags import UserFlags

if TYPE_CHECKING:
    from ..state import State
    from .message import Message

__all__ = ("User",)


class User(Snowflake):
    """
    Represents a user.
    """

    def __init__(self, state: State, data: Dict) -> None:
        self._state = state
        self._data = data

        self._channel: Optional[DMChannel] = None

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} username={self.username!r} discriminator={self.discriminator!r} id={self.id} bot={self.bot}>"

    async def create_dm_channel(self) -> DMChannel:
        """
        Creates a DMChannel for the user if one isn't open already.
        """
        if self._channel is not None:
            return self._channel

        data = await self._state.http.create_dm_channel(self.id)
        self._channel = DMChannel(self._state, data)

        return self._channel

    async def send(self, content: str) -> Message:
        """
        Sends a message to the user.

        Parameters:
            content (str): The content of the message.

        Returns:
            The [lefi.Message][] instance of the message sent.

        """
        if self._channel is None:
            self._channel = await self.create_dm_channel()

        return await self._channel.send(content)

    @property
    def username(self) -> str:
        """
        The username of the user.
        """
        return self._data["username"]

    @property
    def discriminator(self) -> str:
        """
        The discriminator of the user.
        """
        return self._data["discriminator"]

    @property
    def id(self) -> int:  # type: ignore
        """
        The ID of the user.
        """
        return int(self._data["id"])

    @property
    def bot(self) -> bool:
        """
        Whether or not the user is a bot.
        """
        return self._data.get("bot", False)

    @property
    def system(self) -> bool:
        """
        Whether or not the user is a discord system user..
        """
        return self._data.get("system", False)

    @property
    def mfa_enabled(self) -> bool:
        """
        Whether or not the user has 2fa enabled.
        """
        return self._data.get("mfa_enabled", False)

    @property
    def accent_color(self) -> int:
        """
        The accent color of the user.
        """
        return self._data.get("accent_color", 0)

    @property
    def locale(self) -> Optional[str]:
        """
        The locale of the user.
        """
        return self._data.get("locale")

    @property
    def verified(self) -> bool:
        """
        Whether the email on the users account is verified.
        """
        return self._data.get("verified", False)

    @property
    def email(self) -> Optional[str]:
        """
        The email of the user.
        """
        return self._data.get("email")

    @property
    def flags(self) -> UserFlags:
        """
        The flags of the user.
        """
        return UserFlags(self._data.get("flags", 0))

    @property
    def premium_type(self) -> PremiumType:
        """
        The premium type of the user.
        """
        return PremiumType(self._data.get("premium_type", 0))

    @property
    def public_flags(self) -> UserFlags:
        """
        The users public flags.
        """
        return UserFlags(self._data.get("public_flags", 0))

    @property
    def channel(self) -> Optional[DMChannel]:
        """
        The users DMChannel.
        """
        return self._channel
