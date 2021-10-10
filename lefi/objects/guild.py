from __future__ import annotations

from typing import TYPE_CHECKING, Union, Dict, Optional, List


if TYPE_CHECKING:
    from .channel import TextChannel, VoiceChannel, CategoryChannel, Channel
    from .member import Member
    from .role import Role
    from .user import User
    from ..state import State

    GuildChannels = Union[TextChannel, VoiceChannel, CategoryChannel, Channel]

__all__ = ("Guild",)


class Guild:
    """
    Represents a Guild.
    """

    def __init__(self, state: State, data: Dict):
        self._channels: Dict[int, GuildChannels] = {}
        self._members: Dict[int, Member] = {}
        self._roles: Dict[int, Role] = {}
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Guild id={self.id}>"

    async def edit(self, **kwargs) -> Guild:
        """
        Edits the guild.

        Parameters:
            **kwargs (Any): Options to pass to [lefi.HTTPClient.modify_guild][]

        Returns:
            The guild after editting

        """
        await self._state.http.modify_guild(self.id, **kwargs)
        return self

    async def add_role(self, name: str, **kwargs) -> Role:
        """
        Creates a new role in the guild.
        
        Parameters:
            name (str): The name of the role.
            **kwargs (Any): Extra options to pass to [lefi.HTTPClient.create_guild_role][].

        Returns:
            The newly created [lefi.Role][] instance.

        """
        data = await self._state.http.create_guild_role(self.id, name=name, **kwargs)
        return Role(self._state, data, self)

    def get_member(self, member_id: int) -> Optional[Member]:
        """
        Gets a member from the guilds member cache.

        Parameters:
            member_id (int): The ID of the member.

        Returns:
            The [lefi.Member][] instance corresponding to the ID if found.

        """
        return self._members.get(member_id)

    def get_channel(self, channel_id: int) -> Optional[GuildChannels]:
        """
        Gets a channel from the guilds channel cache.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The [lefi.Channel][] instance corresponding to the ID if found.

        """
        return self._channels.get(channel_id)

    def get_role(self, role_id: int) -> Optional[Role]:
        """
        Gets a role from the guilds role cache.

        Parameters:
            role_id (int): The ID of the role.

        Returns:
            The [lefi.Role][] instance corresponding to the ID if found.

        """
        return self._roles.get(role_id)

    @property
    def id(self) -> int:
        """
        The ID of the guild.
        """
        return self._data["id"]

    @property
    def name(self) -> str:
        """
        The name of the guild.
        """
        return self._data["name"]

    @property
    def icon(self) -> str:
        """
        The icon of the guild.
        """
        return self._data["icon"]

    @property
    def icon_hash(self) -> str:
        """
        The icon hash of the guild.
        """
        return self._data["icon_hash"]

    @property
    def splash(self) -> str:
        """
        The guild's splash.
        """
        return self._data["splash"]

    @property
    def discovery_splash(self) -> str:
        """
        The guilds discovery splash.
        """
        return self._data["discovery_splash"]

    @property
    def owner(self) -> Optional[Union[User, Member]]:
        if owner := self.get_member(self.owner_id):
            return owner
        else:
            return self._state.get_user(self.owner_id)

    @property
    def owner_id(self) -> int:
        """
        The ID of the owner.
        """
        return self._data["owner_id"]

    @property
    def channels(self) -> List[GuildChannels]:
        """
        The list of [lefi.Channel][] instances belonging to the guild.
        """
        return list(self._channels.values())

    @property
    def members(self) -> List[Member]:
        """
        The list of [lefi.Member][] instances belonging to the guild.
        """
        return list(self._members.values())

    @property
    def roles(self) -> List[Role]:
        """
        The list of [lefi.Role][] instances belonging to the guild.
        """
        return list(self._roles.values())

    @property
    def default_role(self) -> Role:
        """
        The guild's default role.
        """
        return self.get_role(self.id)  # type: ignore

    @property
    def member_count(self) -> int:
        """
        The guild's member count
        """
        return len(self._members)
