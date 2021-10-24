from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild

__all__ = ("GuildTemplate",)


class GuildTemplate:
    def __init__(self, state: State, data: Dict[str, Any]):
        self._state = state
        self._data = data

    @property
    def code(self) -> str:
        return self._data["code"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def description(self) -> str:
        return self._data["description"]

    @property
    def usage_count(self) -> int:
        return self._data["usage_count"]

    @property
    def creator_id(self) -> int:
        return int(self._data["creator_id"])

    @property
    def creator(self) -> Optional[User]:
        return self._state.get_user(self.creator_id)

    @property
    def created_at(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self._data["created_at"])

    @property
    def updated_at(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self._data["updated_at"])

    @property
    def source_guild_id(self) -> int:
        return int(self._data["source_guild_id"])

    @property
    def source_guild(self) -> Optional[Guild]:
        return self._state.get_guild(self.source_guild_id)

    @property
    def is_dirty(self) -> Optional[bool]:
        return self._data["is_dirty"]

    async def create_guild(self, name: str, *, icon: Optional[bytes] = None) -> Guild:
        from .guild import Guild

        data = await self._state.http.create_guild_from_template(
            code=self.code, name=name, icon=icon
        )

        return Guild(state=self._state, data=data)
