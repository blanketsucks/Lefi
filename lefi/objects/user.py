from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from .flags import UserFlags
from .enums import PremiumType
from .channel import DMChannel

if TYPE_CHECKING:
    from .message import Message
    from ..state import State

__all__ = ("User",)


class ClientUser:
    def __init__(self, state: State, data: Dict) -> None:
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f""

    @property
    def username(self) -> str:
        return self._data["username"]

    @property
    def email(self) -> Optional[str]:
        return self._data.get("email")

    @property
    def flags(self) -> UserFlags:
        return UserFlags(self._data.get("flags", 0))

    @property
    def discriminator(self) -> str:
        return self._data["discriminator"]


class User:
    def __init__(self, state: State, data: Dict) -> None:
        self._state = state
        self._data = data

        self._channel: Optional[DMChannel] = None

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} username={self.username!r} discriminator={self.discriminator!r} id={self.id} bot={self.bot}>"

    @property
    def username(self) -> str:
        return self._data["username"]

    @property
    def discriminator(self) -> str:
        return self._data["discriminator"]

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def bot(self) -> bool:
        return self._data.get("bot", False)

    @property
    def system(self) -> bool:
        return self._data.get("system", False)

    @property
    def mfa_enabled(self) -> bool:
        return self._data.get("mfa_enabled", False)

    @property
    def accent_color(self) -> int:
        return self._data.get("accent_color", 0)

    @property
    def locale(self) -> Optional[str]:
        return self._data.get("locale")

    @property
    def verified(self) -> bool:
        return self._data.get("verified", False)

    @property
    def email(self) -> Optional[str]:
        return self._data.get("email")

    @property
    def flags(self) -> UserFlags:
        return UserFlags(self._data.get("flags", 0))

    @property
    def premium_type(self) -> PremiumType:
        return PremiumType(self._data.get("premium_type", 0))

    @property
    def public_flags(self) -> UserFlags:
        return UserFlags(self._data.get("public_flags", 0))

    @property
    def channel(self) -> Optional[DMChannel]:
        return self._channel

    async def create_dm_channel(self) -> DMChannel:
        if self._channel is not None:
            return self._channel

        data = await self._state.http.create_dm_channel(self.id)
        self._channel = DMChannel(self._state, data)

        return self._channel

    async def send(self, content: str) -> Message:
        if self._channel is None:
            self._channel = await self.create_dm_channel()

        return await self._channel.send(content)
