from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild
    from .role import Role
    from .user import User

__all__ = ("Emoji",)


class Emoji:
    """Represents an emoji."""

    def __init__(self, state: State, data: dict, guild: Guild) -> None:
        self._data = data
        self._state = state
        self._guild = guild

    def __repr__(self) -> str:
        return f"<Emoji id={self.id} animated={self.animated}>"

    @property
    def guild(self) -> Guild:
        """The guild which the emoji belongs to."""
        return self._guild

    @property
    def id(self) -> int:
        """The emoji's ID."""
        return int(self._data["id"])

    @property
    def name(self) -> Optional[str]:
        """The emoji's name."""
        return self._data["name"]

    @property
    def roles(self) -> List[Role]:
        """The list of roles which can use this emoji."""
        return [self._guild.get_role(int(role)) for role in self._data.get("roles", [])]  # type: ignore

    @property
    def user(self) -> Optional[User]:
        """The user which created the emoji."""
        return self._state.get_user(self._data.get("user", {}).get("id", 0))

    @property
    def requires_colons(self) -> bool:
        """Whether this emoji requires colons to be used."""
        return self._data.get("require_colons", False)

    @property
    def managed(self) -> bool:
        """Whether this emoji is managed or not."""
        return self._data.get("managed", False)

    @property
    def animated(self) -> bool:
        """Whether this emoji is animated or not."""
        return self._data.get("animated", False)

    @property
    def available(self) -> bool:
        """Whether this emoji is available or not."""
        return self._data.get("available", False)

    async def delete(self) -> Emoji:
        """Deletes the emoji."""
        await self._state.http.delete_guild_emoji(self.guild.id, self.id)
        return self

    async def edit(self, *, name: str, roles: List[Role] = None) -> Emoji:
        """Edits this emoji

        Parameters
        ----------
        name: :class:`str`
            The new name to set for the emoji

        roles: List[:class:`.Role`]
            The list of roles allowed to use the emoji

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to edit this emoji.

        Returns
        -------
        :class:`.Emoji`
            The emoji after editting.
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
