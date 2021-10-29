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
    """
    The base class for Invite and PartialInvite.
    """

    _data: Dict[str, Any]

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} code={self.code!r} url={self.url!r}>"

    @property
    def code(self) -> str:
        """
        The invite code.
        """
        return self._data["code"]

    @property
    def url(self) -> str:
        """
        The invite URL.
        """
        return f"https://discord.gg/{self.code}"


class PartialInvite(InviteMixin):
    """
    Represents a partial invite.

    This is a partial invite, which is an invite that has not been fully parsed.

    Attributes:
        code: The invite code.
        url: The invite URL.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Creates a partial invite.

        Parameters:
            data: The data to create the invite from.
        """
        self._data = data

    @property
    def uses(self) -> int:
        """
        The number of times this invite has been used.
        """
        return self._data["uses"]


class Invite(InviteMixin):
    """
    Represents an invite.

    Attributes:
        code: The invite code.
        url: The invite URL.
    """

    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        """
        Creates an Invite.

        Parameters:
            state (lefi.State): The [State](./state.md) to create the invite in.
            data: The data to create the invite from.
        """
        self._data = data
        self._state = state

    @property
    def guild(self) -> Optional[Guild]:
        """
        The [Guild](./guild.md) this invite is for.
        """
        return self._state.get_guild(self._data.get("guild", {}).get("id", 0))

    @property
    def channel(self) -> Optional[Union[TextChannel, VoiceChannel]]:
        """
        The [Channel](./channel.md) this invite is for.
        """
        return self._state.get_channel(int(self._data["channel"]["id"]))  # type: ignore

    @property
    def inviter(self) -> Optional[User]:
        """
        The [User](./user.md) who created this invite.
        """
        return self._state.get_user(self._data.get("inviter", {}).get("id", 0))

    @property
    def uses(self) -> Optional[int]:
        """
        The number of times this invite has been used.
        """
        return self._data.get("uses")

    @property
    def max_uses(self) -> Optional[int]:
        """
        The maximum number of times this invite can be used.
        """
        return self._data.get("max_uses")

    @property
    def max_age(self) -> Optional[int]:
        """
        The maximum age of this invite.
        """
        return self._data.get("max_age")

    @property
    def temporary(self) -> bool:
        """
        Whether this invite is temporary.
        """
        return self._data.get("temporary", False)

    @property
    def created_at(self) -> Optional[datetime.datetime]:
        """
        The creation time of this invite.
        """
        created_at = self._data.get("created_at")
        if created_at:
            return datetime.datetime.fromisoformat(created_at)

        return created_at

    @property
    def target_type(self) -> Optional[InviteTargetType]:
        """
        The target [Type]() of this invite.
        """
        target_type = self._data.get("target_type")
        if target_type is None:
            return None

        return InviteTargetType(target_type)

    @property
    def target_user(self) -> Optional[User]:
        """
        The target [User](./user.md) of this invite.
        """
        user = self._data.get("target_user")
        if not user:
            return None

        return User(self._state, user)

    @property
    def approximate_presence_count(self) -> Optional[int]:
        """
        The approximate number of members in the guild this invite is for.
        """
        return self._data.get("approximate_presence_count")

    @property
    def approximate_member_count(self) -> Optional[int]:
        """
        The approximate number of members in the guild this invite is for.
        """
        return self._data.get("approximate_member_count")

    async def delete(self) -> Invite:
        """
        Deletes this invite.

        Returns:
            The deleted invite.
        """
        await self._state.http.delete_invite(self.code)
        return self
