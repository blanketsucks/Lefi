from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, List

import datetime

from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild
    from .role import Role

__all__ = ("Member",)


class Member(User):
    """
    Represents a member of a guild.

    Attributes:
        guild (lefi.Guild): The [lefi.Guild][] instance which the member belongs to.

    """

    def __init__(self, state: State, data: Dict, guild: Guild):
        self._member = data
        self.guild = guild
        state.add_user(data["user"])
        super().__init__(state, data["user"])

    @property
    def nick(self) -> Optional[str]:
        """
        The nickname of of member.
        """
        return self._member.get("nick")

    @property
    def roles(self) -> List[Role]:
        """
        The roles of the member.
        """
        return []

    @property
    def joined_at(self) -> datetime.datetime:
        """
        A [datetime.datetime][] instance representing when the member joined the guild.
        """
        return datetime.datetime.fromisoformat(self._member["joined_at"])

    @property
    def premium_since(self) -> Optional[datetime.datetime]:
        """
        How long the member has been a premium.
        """
        timestamp = self._member.get("premium_since")
        if timestamp is None:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def deaf(self) -> bool:
        """
        Whether or not the member is deafend.
        """
        return self._member["deaf"]

    @property
    def mute(self) -> bool:
        """
        Whether or not the member is muted.
        """
        return self._member["mute"]
