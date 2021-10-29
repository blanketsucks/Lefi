from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild

__all__ = ("GuildTemplate",)


class GuildTemplate:
    """
    Represents a guild template.
    """

    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        """
        Creates a GuildTemplate.

        Parameters:
            state (State): The [State](./state.md) of the client.
            data (Dict[str, Any]): The data of the guild template.
        """
        self._state = state
        self._data = data

    @property
    def code(self) -> str:
        """
        The template code.
        """
        return self._data["code"]

    @property
    def name(self) -> str:
        """
        The template name.
        """
        return self._data["name"]

    @property
    def description(self) -> str:
        """
        The template description.
        """
        return self._data["description"]

    @property
    def usage_count(self) -> int:
        """
        The number of times this template has been used.
        """
        return self._data["usage_count"]

    @property
    def creator_id(self) -> int:
        """
        The ID of the user who created this template.
        """
        return int(self._data["creator_id"])

    @property
    def creator(self) -> Optional[User]:
        """
        The user who created this template.
        """
        return self._state.get_user(self.creator_id)

    @property
    def created_at(self) -> datetime.datetime:
        """
        When this template was created.
        """
        return datetime.datetime.fromisoformat(self._data["created_at"])

    @property
    def updated_at(self) -> datetime.datetime:
        """
        When this template was last updated.
        """
        return datetime.datetime.fromisoformat(self._data["updated_at"])

    @property
    def source_guild_id(self) -> int:
        """
        The ID of the guild this template was created from.
        """
        return int(self._data["source_guild_id"])

    @property
    def source_guild(self) -> Optional[Guild]:
        """
        The [Guild](./guild.md) this template was created from.
        """
        return self._state.get_guild(self.source_guild_id)

    @property
    def is_dirty(self) -> Optional[bool]:
        """
        Whether this template is dirty.
        """
        return self._data["is_dirty"]

    async def create_guild(self, name: str, *, icon: Optional[bytes] = None) -> Guild:
        """
        Creates a [Guild](./guild.md) from this template.

        Parameters:
            name: The name of the guild.
            icon: The icon of the guild.
        """
        from .guild import Guild

        data = await self._state.http.create_guild_from_template(
            code=self.code, name=name, icon=icon
        )

        return Guild(state=self._state, data=data)
