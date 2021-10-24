from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from .enums import InviteTargetType
from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .channel import Channel, TextChannel, VoiceChannel
    from .guild import Guild

__all__ = ("Invite", "PartialInvite")


class InviteMixin:
    _data: Dict[str, Any]

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} code={self.code!r} url={self.url!r}>"

    @property
    def code(self) -> str:
        return self._data["code"]

    @property
    def url(self) -> str:
        return f"https://discord.gg/{self.code}"


class PartialInvite(InviteMixin):
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    @property
    def uses(self) -> int:
        return self._data["uses"]


class Invite(InviteMixin):
    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        self._data = data
        self._state = state

    @property
    def guild(self) -> Optional[Guild]:
        return self._state.get_guild(self._data.get("guild", {}).get("id", 0))

    @property
    def channel(self) -> Optional[Union[TextChannel, VoiceChannel]]:
        return self._state.get_channel(int(self._data["channel"]["id"]))  # type: ignore

    @property
    def inviter(self) -> Optional[User]:
        return self._state.get_user(self._data.get("inviter", {}).get("id", 0))

    @property
    def uses(self) -> Optional[int]:
        return self._data.get("uses")

    @property
    def max_uses(self) -> Optional[int]:
        return self._data.get("max_uses")

    @property
    def max_age(self) -> Optional[int]:
        return self._data.get("max_age")

    @property
    def temporary(self) -> bool:
        return self._data.get("temporary", False)

    @property
    def created_at(self) -> Optional[datetime.datetime]:
        created_at = self._data.get("created_at")
        if created_at:
            return datetime.datetime.fromisoformat(created_at)

        return created_at

    @property
    def target_type(self) -> Optional[InviteTargetType]:
        target_type = self._data.get("target_type")
        if target_type is None:
            return None

        return InviteTargetType(target_type)

    @property
    def target_user(self) -> Optional[User]:
        user = self._data.get("target_user")
        if not user:
            return None

        return User(self._state, user)

    @property
    def approximate_presence_count(self) -> Optional[int]:
        return self._data.get("approximate_presence_count")

    @property
    def approximate_member_count(self) -> Optional[int]:
        return self._data.get("approximate_member_count")

    async def delete(self) -> Invite:
        await self._state.http.delete_invite(self.code)
        return self
