from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from .flags import Permissions
from .user import User
from ..voice import VoiceState
from .attachments import CDNAsset

if TYPE_CHECKING:
    from ..state import State
    from .channel import VoiceChannel
    from .guild import Guild
    from .role import Role

__all__ = ("Member",)


class Member(User):
    """Represents a member of a guild.
    """

    def __init__(self, state: State, data: dict, guild: Guild) -> None:
        super().__init__(state, data["user"])
        state.add_user(data["user"])
        self._roles: Dict[int, Role] = {}
        self._member = data
        self._guild = guild

    async def add_roles(self, *roles: Role) -> None:
        """Adds role(s) to the member.

        Parameters
        ----------
        roles: :class:`.Role`
            The role(s) to add to the member.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to add roles to this user.
        """
        for role in roles:
            await self._state.http.add_guild_member_role(self._guild.id, self.id, role.id)
            self._roles[role.id] = role

    async def remove_roles(self, *roles: Role) -> None:
        """Removes role(s) from the member.

        Parameters
        ----------
        role: :class:`.Role`
            The role(s) to remove from the member.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to remove roles from this user.
        """
        for role in roles:
            await self._state.http.remove_guild_member_role(self._guild.id, self.id, role.id)
            self._roles.pop(role.id, None)

    async def edit(
        self,
        *,
        nick: Optional[str] = None,
        roles: Optional[List[Role]] = None,
        mute: Optional[bool] = None,
        deaf: Optional[bool] = None,
        channel: Optional[VoiceChannel] = None
    ) -> Member:
        """Edits the member.

        Parameters
        ----------
        nick: Optional[:class:`str`]
            The new nickname of the member

        roles: Optional[List[:class:`.Role`]]
            The list of roles the member should have.
            Pass an empty list to remove all roles

        mute: Optional[:class:`bool`]
            Whether the member should be muted or not

        deaf: Optional[:class:`bool`]
            Whether the member should be deafend or not

        channel: Optional[:class:`.VoiceChannel`]
            The new voice channel to put the member in.
            Pass None to kick them out of a voice channel

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to edit this member.

        Returns
        -------
        :class:`.Member`
            The member after editting.
        """
        channel_id = channel.id if channel else None
        roles = roles or []

        data = await self._state.http.edit_guild_member(
            guild_id=self._guild.id,
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
        """Kicks the member from the guild.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to kick this member.
        """
        await self._guild.kick(self)

    async def ban(self, *, delete_message_days: int = 0) -> None:
        """Bans the member from the guild.

        Parameters
        ----------
        delete_message_days: :class:`int`
            Number of days to delete messages for

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to ban this member.
        """
        await self._guild.ban(self, delete_message_days=delete_message_days)

    async def unban(self) -> None:
        """Unbans the member from the guild.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to unban this member.
        """
        await self._guild.unban(self)

    @property
    def voice(self) -> Optional[VoiceState]:
        """The voice state of the member.
        """
        return self._guild.get_voice_state(self.id)

    @property
    def nick(self) -> Optional[str]:
        """The nickname of of member.
        """
        return self._member.get("nick")

    @property
    def roles(self) -> List[Role]:
        """The roles which the member has.
        """
        return list(self._roles.values())

    @property
    def joined_at(self) -> datetime.datetime:
        """The time at which the member joined the guild.
        """
        return datetime.datetime.fromisoformat(self._member["joined_at"])

    @property
    def premium_since(self) -> Optional[datetime.datetime]:
        """How long the member has been a premium.
        """
        timestamp = self._member.get("premium_since")
        if timestamp is None:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def deaf(self) -> bool:
        """Whether or not the member is deafend.
        """
        return self._member["deaf"]

    @property
    def mute(self) -> bool:
        """Whether or not the member is muted.
        """
        return self._member["mute"]

    @property
    def permissions(self) -> Permissions:
        """The permissions of the member.
        """
        base = Permissions.none()

        if self._guild.owner_id == self.id:
            return Permissions.all()

        for role in self.roles:
            base |= role.permissions

        if base.value & Permissions.administrator:
            return Permissions.all()

        return base

    @property
    def guild_avatar(self) -> Optional[CDNAsset]:
        """The guild avatar of the member.
        """
        guild_avatar_hash = self._member.get("avatar")
        if not guild_avatar_hash:
            return None

        return CDNAsset.from_guild_member_avatar(
            self._state, self._guild.id, self.id, guild_avatar_hash
        )
