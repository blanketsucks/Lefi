from __future__ import annotations

import typing
import datetime

from .user import User

if typing.TYPE_CHECKING:
    from ..state import State
    from .guild import Guild
    from .role import Role

__all__ = ('Member',)

class Member(User):
    def __init__(self, state: State, data: typing.Dict, guild: Guild):
        self._member = data

        state.add_user(data['user'])
        super().__init__(state, data['user'])

        self.guild = guild

    @property
    def nick(self) -> typing.Optional[str]:
        return self._member.get('nick')

    @property
    def roles(self) -> typing.List[Role]:
        return []

    @property
    def joined_at(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self._member['joined_at'])

    @property
    def premium_since(self) -> typing.Optional[datetime.datetime]:
        timestamp = self._member.get('premium_since')
        if timestamp is None:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def deaf(self) -> bool:
        return self._member['deaf']

    @property
    def mute(self) -> bool:
        return self._member['mute']

    