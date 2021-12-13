from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from ..utils import Snowflake
from .flags import Permissions

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild

__all__ = ("Role", "PartialRole")


class PartialRole(Snowflake):
    """A role object with limited information."""

    def __init__(self, data: dict, guild: Guild):
        self._data = data
        self._guild = guild

    @property
    def guild(self) -> Guild:
        """The guild which the role belongs to."""
        return self._guild

    @property
    def name(self) -> str:
        """The name of the role."""
        return self._data["name"]

    @property
    def id(self) -> int:  # type: ignore
        """The id of the role."""
        return int(self._data["id"])


class Role(Snowflake):
    """Represents a role."""

    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        self._state = state
        self._data = data
        self._guild = guild

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r} position={self.position}>"

    def _copy(self) -> Role:
        return Role(self._state, self._data, self._guild)

    async def delete(self) -> None:
        """Deletes the role.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete this role.
        """
        await self._state.http.delete_guild_role(self.guild.id, self.id)

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        permissions: Optional[Permissions] = None,
        color: Optional[int] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None,
    ) -> Role:
        """Edits the role.

        Parameters
        ----------
        name: Optional[:class:`str`]
            The new name of the role

        permissions: Optional[:class:`.Permissions`]
            The new permissions of the role

        color: Optional[:class:`int`]
            The new color of the role

        hoist: Optional[:class:`bool`]
            Whether to hoist the role or not

        mentionable: Optional[:class:`bool`]
            Whether to make the role mentionable or not

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to edit this role.

        Returns
        -------
        :class:`.Role`
            The role after editting.
        """
        data = await self._state.http.modify_guild_role(
            guild_id=self.guild.id,
            role_id=self.id,
            name=name,
            permissions=permissions.value if permissions else None,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
        )

        return self

    @property
    def guild(self) -> Guild:
        """The guild of the role."""
        return self._guild

    @property
    def id(self) -> int:  # type: ignore
        """The id of the role."""
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """The name of the role."""
        return self._data["name"]

    @property
    def color(self) -> int:
        """The color of the role."""
        return int(self._data["color"])

    @property
    def hoist(self) -> bool:
        """Whether or not the role is hoisted."""
        return self._data["hoist"]

    @property
    def position(self) -> int:
        """The position of the role."""
        return int(self._data["position"])

    @property
    def permissions(self) -> Permissions:
        """The permissions of the role."""
        return Permissions(int(self._data["permissions"]))

    @property
    def managed(self) -> bool:
        """Whether the role is managed or not."""
        return self._data["managed"]

    @property
    def mentionable(self) -> bool:
        """Whether or not the role is mentionable."""
        return self._data["mentionable"]
