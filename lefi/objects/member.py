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
    def __init__(self, state: State, data: Dict, guild: Guild):
        self._member = data
        self.guild = guild
        state.add_user(data["user"])
        super().__init__(state, data["user"])

    @property
    def nick(self) -> Optional[str]:
        return self._member.get("nick")

    @property
    def roles(self) -> List[Role]:
        return []

    @property
    def joined_at(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self._member["joined_at"])

    @property
    def premium_since(self) -> Optional[datetime.datetime]:
        timestamp = self._member.get("premium_since")
        if timestamp is None:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def deaf(self) -> bool:
        return self._member["deaf"]

    @property
    def mute(self) -> bool:
        return self._member["mute"]
