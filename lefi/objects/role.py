from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from ..utils import Snowflake
from .flags import Permissions

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild

__all__ = ("Role",)


class Role(Snowflake):
    """
    Represents a role.
    """

    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        self._state = state
        self._data = data
        self._guild = guild

    async def delete(self) -> None:
        """
        Deletes the role from its guild.
        """
        await self._state.http.delete_guild_role(self.guild.id, self.id)

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        permissions: Optional[Permissions] = None,
        color: Optional[int] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None
    ) -> Role:
        """
        Edits the role.

        Parameters:
            name (Optional[str]): The new name of the role.
            permissions (Optional[Permissions]): The new permissions of the role.
            color (Optional[int]): The new color of the role.
            hoist (Optional[bool]): Whether or not to hoist the role.
            mentionable (Optional[bool]): Whether or not the role is mentionable.

        Returns:
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

        self._data = data
        return self

    @property
    def guild(self) -> Guild:
        """
        The [lefi.Guild][] instance which the role belongs to.
        """
        return self._guild

    @property
    def id(self) -> int:  # type: ignore
        """
        The ID of the role.
        """
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """
        The name of the role.
        """
        return self._data["name"]

    @property
    def color(self) -> int:
        """
        The color of the role.
        """
        return int(self._data["color"])

    @property
    def hoist(self) -> bool:
        """
        Whether or not the role is hoisted.
        """
        return self._data["hoist"]

    @property
    def position(self) -> int:
        """
        The position of the role.
        """
        return int(self._data["position"])

    @property
    def permissions(self) -> Permissions:
        """
        The permissions of the role.
        """
        return Permissions(int(self._data["permissions"]))

    @property
    def managed(self) -> bool:
        """
        Whether or not the role is managed.
        """
        return self._data["managed"]

    @property
    def mentionable(self) -> bool:
        """
        Whether or not the role is mentionable.
        """
        return self._data["mentionable"]
