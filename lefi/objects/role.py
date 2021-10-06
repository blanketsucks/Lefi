from __future__ import annotations

import typing

from .flags import Permissions
from ..utils import MISSING

if typing.TYPE_CHECKING:
    from .guild import Guild
    from ..state import State

__all__ = ("Role",)

class Role:
    def __init__(self, state: State, data: typing.Dict, guild: Guild) -> None:
        self._state = state
        self._data = data
        self._guild = guild

    async def delete(self) -> None:
        await self._state.http.delete_guild_role(self.guild.id, self.id)

    async def edit(
        self, 
        *, 
        name: str=MISSING, 
        permissions: Permissions=MISSING, 
        color: int=MISSING, 
        hoist: bool=MISSING, 
        mentionable: bool=MISSING
    ) -> Role:
        data = await self._state.http.modifiy_guild_role(
            guild_id=self.guild.id, 
            role_id=self.id,
            name=name,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable
        )

        self._data = data
        return self

    @property
    def guild(self) -> Guild:
        return self._guild

    @property
    def id(self) -> int:
        return int(self._data['id'])

    @property
    def name(self) -> str:
        return self._data['name']

    @property
    def color(self) -> int:
        return int(self._data['color'])

    @property
    def hoist(self) -> bool:
        return self._data['hoist']

    @property
    def position(self) -> int:
        return int(self._data['position'])

    @property
    def permissions(self) -> Permissions:
        return Permissions(int(self._data['permissions']))

    @property
    def managed(self) -> bool:
        return self._data['managed']

    @property
    def mentionable(self) -> bool:
        return self._data['mentionable']
