from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from ..utils import Snowflake
from .flags import Permissions
from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .channel import VoiceChannel
    from .guild import Guild
    from .role import Role

__all__ = ("Member",)


class Member(User):
    """
    Represents a member of a guild.

    Attributes:
        guild (lefi.Guild): The [lefi.Guild](./guild.md) instance which the member belongs to.

    """

    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        """
        Creates a Member instance.

        Parameters:
            state (lefi.State): The [State](./state.md) instance.
            data (dict): The data of the [Member](./member.md).
            guild (lefi.Guild): The [Guild](./guild.md) instance.
        """
        super().__init__(state, data["user"])
        state.add_user(data["user"])
        self._roles: Dict[int, Role] = {}
        self._member = data
        self.guild = guild

    async def add_role(self, role: Role) -> Member:
        """
        Adds a role to the member.

        Parameters:
            role (lefi.Role): The [Role](./role.md) to add.

        Returns:
            The Member instance.
        """
        await self._state.http.add_guild_member_role(self.guild.id, self.id, role.id)
        self._roles[role.id] = role

        return self

    async def remove_role(self, role: Role) -> Member:
        """
        Removes a role from the member.

        Parameters:
            role (lefi.Role): The [Role](./role.md) to remove.

        Returns:
            The Member instance.
        """
        await self._state.http.remove_guild_member_role(self.guild.id, self.id, role.id)
        self._roles.pop(role.id, None)

        return self

    async def edit(
        self,
        *,
        nick: Optional[str] = None,
        roles: Optional[List[Role]] = None,
        mute: Optional[bool] = None,
        deaf: Optional[bool] = None,
        channel: Optional[VoiceChannel] = None
    ) -> Member:
        """
        Edits the member.

        Parameters:
            nick (str): The new nickname.
            roles (list): The new list of roles.
            mute (bool): Whether the member is muted or not.
            deaf (bool): Whether the member is deafened or not.
            channel (lefi.VoiceChannel): The new [VoiceChannel](./channel.md#lefi.VoiceChannel).

        """
        channel_id = channel.id if channel else None
        roles = roles or []

        data = await self._state.http.edit_guild_member(
            guild_id=self.guild.id,
            member_id=self.id,
            nick=nick,
            roles=[role.id for role in roles],
            mute=mute,
            deaf=deaf,
            channel_id=channel_id,
        )
        self._member = data

        return self

    async def kick(self) -> None:
        """
        Kicks the member from the guild.

        """
        await self.guild.kick(self)

    async def ban(self, *, delete_message_days: int = 0) -> None:
        """
        Bans the member from the guild.

        Parameters:
            delete_message_days (int): The number of days to delete messages for.

        """
        await self.guild.ban(self, delete_message_days=delete_message_days)

    async def unban(self) -> None:
        """
        Unbans the member from the guild.

        """
        await self.guild.unban(self)

    @property
    def nick(self) -> Optional[str]:
        """
        The nickname of of member.
        """
        return self._member.get("nick")

    @property
    def roles(self) -> List[Role]:
        """
        The [Role](./role.md)s of the member.
        """
        return list(self._roles.values())

    @property
    def joined_at(self) -> datetime.datetime:
        """
        A [datetime.datetime](https://docs.python.org/3/library/datetime.html#datetime.datetime) instance
        representing when the member joined the guild.
        """
        return datetime.datetime.fromisoformat(self._member["joined_at"])

    @property
    def premium_since(self) -> Optional[datetime.datetime]:
        """
        How long the member has been a premium.
        """
        timestamp = self._member.get("premium_since")
        if timestamp is None:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def deaf(self) -> bool:
        """
        Whether or not the member is deafend.
        """
        return self._member["deaf"]

    @property
    def mute(self) -> bool:
        """
        Whether or not the member is muted.
        """
        return self._member["mute"]

    @property
    def permissions(self) -> Permissions:
        """
        The permissions of the member.
        """
        base = Permissions.none()

        if self.guild.owner_id == self.id:
            return Permissions.all()

        for role in self.roles:
            base |= role.permissions

        if base.value & Permissions.administrator:
            return Permissions.all()

        return base
