from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild

__all__ = ("GuildTemplate",)


class GuildTemplate:
    """Represents a guild template."""

    def __init__(self, state: State, data: dict) -> None:
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<GuildTemplate code={self.code!r} name={self.name!r}>"

    @property
    def code(self) -> str:
        """The template code."""
        return self._data["code"]

    @property
    def name(self) -> str:
        """The template name."""
        return self._data["name"]

    @property
    def description(self) -> str:
        """The template description."""
        return self._data["description"]

    @property
    def usage_count(self) -> int:
        """The number of times this template has been used."""
        return self._data["usage_count"]

    @property
    def creator_id(self) -> int:
        """The id of the user who created this template."""
        return int(self._data["creator_id"])

    @property
    def creator(self) -> Optional[User]:
        """The user who created this template."""
        return self._state.get_user(self.creator_id)

    @property
    def created_at(self) -> datetime.datetime:
        """When this template was created."""
        return datetime.datetime.fromisoformat(self._data["created_at"])

    @property
    def updated_at(self) -> datetime.datetime:
        """When this template was last updated."""
        return datetime.datetime.fromisoformat(self._data["updated_at"])

    @property
    def source_guild_id(self) -> int:
        """The id of the guild this template was created from."""
        return int(self._data["source_guild_id"])

    @property
    def source_guild(self) -> Optional[Guild]:
        """The guild which the template was created from."""
        return self._state.get_guild(self.source_guild_id)

    @property
    def is_dirty(self) -> Optional[bool]:
        """Whether this template is dirty or not."""
        return self._data["is_dirty"]

    async def create_guild(self, name: str, *, icon: Optional[bytes] = None) -> Guild:
        """Creates a guild from the template.

        Parameters
        ----------
        name: :class:`str`
            The name of the guild

        icon: Optional[:class:`bytes`]
            The icon of the guild

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`.Guild`
            The newly created guild.
        """
        from .guild import Guild

        data = await self._state.http.create_guild_from_template(
            code=self.code, name=name, icon=icon
        )

        return Guild(state=self._state, data=data)
