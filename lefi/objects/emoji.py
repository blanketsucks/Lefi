from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild
    from .role import Role
    from .user import User

__all__ = ("Emoji",)


class Emoji:
    def __init__(self, state: State, data: Dict[str, Any], guild: Guild) -> None:
        self._data = data
        self._state = state
        self._guild = guild

    @property
    def guild(self) -> Guild:
        return self._guild

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def name(self) -> Optional[str]:
        return self._data["name"]

    @property
    def roles(self) -> List[Role]:
        return [self._guild.get_role(int(role)) for role in self._data.get("roles", [])]  # type: ignore

    @property
    def user(self) -> Optional[User]:
        return self._state.get_user(self._data.get("user", {}).get("id", 0))

    @property
    def requires_colons(self) -> bool:
        return self._data.get("require_colons", False)

    @property
    def managed(self) -> bool:
        return self._data.get("managed", False)

    @property
    def animated(self) -> bool:
        return self._data.get("animated", False)

    @property
    def available(self) -> bool:
        return self._data.get("available", False)

    async def delete(self) -> Emoji:
        await self._state.http.delete_guild_emoji(self.guild.id, self.id)
        return self

    async def edit(self, *, name: str, roles: List[Role] = None) -> Emoji:
        roles = roles or []
        data = await self._state.http.modify_guild_emoji(
            guild_id=self.guild.id,
            emoji_id=self.id,
            name=name,
            roles=[role.id for role in roles],
        )

        self._data = data
        return self
