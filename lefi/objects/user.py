from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from ..utils import Snowflake
from .channel import DMChannel
from .enums import PremiumType
from .attachments import CDNAsset
from .flags import UserFlags
from .base import Messageable

if TYPE_CHECKING:
    from ..state import State

__all__ = ("User",)


class User(Messageable, Snowflake):
    """Represents a user.

    .. note::

        Some properties are only given when the user is the client's current user.

    """

    def __init__(self, state: State, data: Dict) -> None:
        self._state = state
        self._data = data

        self._channel: Optional[DMChannel] = None

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} username={self.username!r} discriminator={self.discriminator!r} id={self.id} bot={self.bot}>"

    async def create_dm_channel(self) -> DMChannel:
        """Creates a DMChannel for the user if one isn't open already.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`.DMChannel`
            The created DMChannel or the existing one.
        """
        if self._channel is not None:
            return self._channel

        data = await self._state.http.create_dm_channel(self.id)
        self._channel = DMChannel(self._state, data)

        return self._channel

    @property
    def username(self) -> str:
        """The username of the user."""
        return self._data["username"]

    @property
    def discriminator(self) -> int:
        """The discriminator of the user."""
        return int(self._data["discriminator"])

    @property
    def avatar(self) -> CDNAsset:
        """The avatar of the user."""
        avatar_hash = self._data["avatar"]
        if not avatar_hash:
            return CDNAsset.from_default_user_avatar(self._state, self.discriminator)

        return CDNAsset.from_user_avatar(self._state, self.id, avatar_hash)

    @property
    def banner(self) -> Optional[CDNAsset]:
        """The banner of the user."""
        banner_hash = self._data.get("banner")
        if not banner_hash:
            return None

        return CDNAsset.from_user_banner(self._state, self.id, banner_hash)

    @property
    def id(self) -> int:  # type: ignore
        """The id of the user."""
        return int(self._data["id"])

    @property
    def bot(self) -> bool:
        """Whether or not the user is a bot."""
        return self._data.get("bot", False)

    @property
    def system(self) -> bool:
        """Whether or not the user is a discord system user."""
        return self._data.get("system", False)

    @property
    def mfa_enabled(self) -> bool:
        """Whether or not the user has 2fa enabled."""
        return self._data.get("mfa_enabled", False)

    @property
    def accent_color(self) -> int:
        """The accent color of the user."""
        return self._data.get("accent_color", 0)

    @property
    def locale(self) -> Optional[str]:
        """The locale of the user."""
        return self._data.get("locale")

    @property
    def verified(self) -> bool:
        """Whether the email on the users account is verified."""
        return self._data.get("verified", False)

    @property
    def email(self) -> Optional[str]:
        """The email of the user."""
        return self._data.get("email")

    @property
    def flags(self) -> UserFlags:
        """The flags of the user."""
        return UserFlags(self._data.get("flags", 0))

    @property
    def premium_type(self) -> PremiumType:
        """The premium type of the user."""
        return PremiumType(self._data.get("premium_type", 0))

    @property
    def public_flags(self) -> UserFlags:
        """The users public flags."""
        return UserFlags(self._data.get("public_flags", 0))

    @property
    def channel(self) -> Optional[DMChannel]:
        """The DMChannel of the user."""
        return self._channel
