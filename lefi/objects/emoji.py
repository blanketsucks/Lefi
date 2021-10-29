from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild
    from .role import Role
    from .user import User

__all__ = ("Emoji",)


class Emoji:
    """
    A class representing an Emoji.
    """

    def __init__(self, state: State, data: Dict[str, Any], guild: Guild) -> None:
        """
        Creates a new Emoji.

        Parameters:
            state (lefi.State): The parent [State](./state.md).
            data (dict): The data for this emoji.
            guild (lefi.Guild): The parent [Guild](./guild.md).
        """
        self._data = data
        self._state = state
        self._guild = guild

    @property
    def guild(self) -> Guild:
        """
        The [Guild](./guild.md) this emoji belongs to.
        """
        return self._guild

    @property
    def id(self) -> int:
        """
        The emoji's ID.
        """
        return int(self._data["id"])

    @property
    def name(self) -> Optional[str]:
        """
        The emoji's name.
        """
        return self._data["name"]

    @property
    def roles(self) -> List[Role]:
        """
        The list of [Role](./role.md)s that can use this emoji.
        """
        return [self._guild.get_role(int(role)) for role in self._data.get("roles", [])]  # type: ignore

    @property
    def user(self) -> Optional[User]:
        """
        The [User](./user.md) that created this emoji.
        """
        return self._state.get_user(self._data.get("user", {}).get("id", 0))

    @property
    def requires_colons(self) -> bool:
        """
        Whether this emoji requires colons to be used.
        """
        return self._data.get("require_colons", False)

    @property
    def managed(self) -> bool:
        """
        Whether this emoji is managed.
        """
        return self._data.get("managed", False)

    @property
    def animated(self) -> bool:
        """
        Whether this emoji is animated.
        """
        return self._data.get("animated", False)

    @property
    def available(self) -> bool:
        """
        Whether this emoji is available.
        """
        return self._data.get("available", False)

    async def delete(self) -> Emoji:
        """
        Deletes this [Emoji](./emoji.md).
        """
        await self._state.http.delete_guild_emoji(self.guild.id, self.id)
        return self

    async def edit(self, *, name: str, roles: List[Role] = None) -> Emoji:
        """
        Edits this [Emoji]().

        Parameters:
            name: The new name for this emoji.
            roles: The new list of [Role](./role.md)s that can use this emoji.

        Returns:
            The updated [Emoji](./emoji.md).
        """
        roles = roles or []
        data = await self._state.http.modify_guild_emoji(
            guild_id=self.guild.id,
            emoji_id=self.id,
            name=name,
            roles=[role.id for role in roles],
        )

        self._data = data
        return self
