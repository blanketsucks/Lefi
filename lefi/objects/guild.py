from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    NamedTuple,
    Optional,
    Union,
    Any,
)

from ..utils import Snowflake
from .emoji import Emoji
from .enums import (
    ChannelType,
    ExplicitContentFilterLevel,
    MessageNotificationLevel,
    MFALevel,
    VerificationLevel,
    AuditLogsEvent,
)
from .integration import Integration
from .invite import Invite, PartialInvite
from .template import GuildTemplate
from ..voice import VoiceState, VoiceClient, VoiceRegion
from ..utils import MemberIterator, AuditLogIterator
from .threads import Thread
from .attachments import CDNAsset
from .flags import Permissions, SystemChannelFlags

if TYPE_CHECKING:
    from ..state import State
    from .channel import CategoryChannel, Channel, TextChannel, VoiceChannel
    from .member import Member
    from .role import Role
    from .user import User

    GuildChannels = Union[TextChannel, VoiceChannel, CategoryChannel, Channel]

__all__ = ("Guild",)


class BanEntry(NamedTuple):
    user: User
    reason: Optional[str]


class Guild:
    """Represents a Guild."""

    def __init__(self, state: State, data: Dict) -> None:
        self._channels: Dict[int, GuildChannels] = {}
        self._members: Dict[int, Member] = {}
        self._roles: Dict[int, Role] = {}
        self._emojis: Dict[int, Emoji] = {}
        self._voice_states: Dict[int, VoiceState] = {}
        self._threads: Dict[int, Thread] = {}

        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Guild id={self.id}>"

    def _copy(self) -> Guild:
        copy = self.__class__(self._state, self._data)

        copy._channels = self._channels.copy()
        copy._members = self._members.copy()
        copy._roles = self._roles.copy()
        copy._emojis = self._emojis.copy()
        copy._voice_states = self._voice_states.copy()
        copy._threads = self._threads.copy()

        return copy

    def _create_threads(self, data: Dict) -> List[Thread]:
        threads = {int(thread["id"]): Thread(self._state, self, thread) for thread in data.get("threads", [])}

        for member in data.get("members", []):
            thread = threads.get(int(member["id"]))

            if thread:
                thread._create_member(member)

        return list(threads.values())

    def _make_permission_overwrites(
        self, base: Optional[Dict[Union[Member, Role], Permissions]]
    ) -> Optional[List[Dict]]:
        if not base:
            return None

        permission_overwrites = []
        for target, overwrite in base.items():
            if not isinstance(target, (Member, Role)):
                raise TypeError("Target must be a Member or Role")

            if not isinstance(overwrite, Permissions):
                raise TypeError("Overwrite must be a Permissions instance")

            allow, deny = overwrite.to_overwrite_pair()

            ow = {
                "id": target.id,
                "type": 1 if isinstance(target, Member) else 0,
                "allow": allow.value,
                "deny": deny.value,
            }

            permission_overwrites.append(ow)

        return permission_overwrites

    async def _create_channel(
        self,
        *,
        name: str,
        type: ChannelType,
        overwrites: Dict[Union[Member, Role], Permissions] = None,
        parent: Optional[CategoryChannel] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        permission_overwrites = self._make_permission_overwrites(overwrites)
        return await self._state.http.create_guild_channel(
            guild_id=self.id,
            name=name,
            type=type.value,
            parent_id=parent.id if parent else None,
            permission_overwrites=permission_overwrites,
            **kwargs,
        )

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[bytes] = None,
        banner: Optional[bytes] = None,
        splash: Optional[bytes] = None,
        discovery_splash: Optional[bytes] = None,
        region: Optional[Union[str, VoiceRegion]] = None,
        afk_channel: Optional[VoiceChannel] = None,
        owner: Optional[Snowflake] = None,
        afk_timeout: Optional[int] = None,
        default_message_notifications: Optional[MessageNotificationLevel] = None,
        verification_level: Optional[VerificationLevel] = None,
        system_channel: Optional[TextChannel] = None,
        system_channel_flags: Optional[SystemChannelFlags] = None,
        preferred_locale: Optional[str] = None,
        rules_channel: Optional[TextChannel] = None,
        public_updates_channel: Optional[TextChannel] = None,
    ) -> Guild:
        """Edits the guild.

        Parameters
        ----------
        name: Optional[:class:`str`]
            The new name to set for the guild

        description: Optional[:class:`str`]
            The new description to set for the guild

        icon: Optional[:class:`bytes`]
            The new icon to set for the guild

        banner: Optional[:class:`bytes`]
            The new banner to set for the guild

        splash: Optional[:class:`bytes`]
            The new splash to set for the guild

        discovery_splash: Optional[:class:`bytes`]
            The new discovery splash to set for the guild

        region: Optional[Union[:class:`str`, :class:`.VoiceRegion`]]
            The new region to set for the guild

        afk_channel: Optional[:class:`.VoiceChannel`]
            The voice channel to put AFK users in

        owner: Optional[:class:`.Snowflake`]
            The new owner of the guild. This is used for transferring

        afk_timeout: Optional[:class:`int`]
            The new AFK timeout

        default_message_notifications: Optional[:class:`.MessageNotificationLevel`]
            The new default message notifcation level

        verification_level: Optional[:class:`.VerificationLevel`]
            The new verification level of the guild

        system_channel: Optional[:class:`.TextChannel`]
            The new system channel of the guild

        system_channel_flags: Optional[:class:`SystemChannelFlags`]
            The new system channel flags

        preferred_locale: Optional[:class:`str`]
            The new locale of the guild. This should be an ISO 639 code

        rules_channel: Optional[:class:`.TextChannel`]
            The new rules channel of the guild

        public_updates_channel: Optional[:class:`.TextChannel`]
            The new public updates channel of the guild

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to edit this guild.

        Returns
        -------
        :class:`.Guild`
            The guild after editting.
        """
        region = region.name if isinstance(region, VoiceRegion) else region
        notif = default_message_notifications.value if default_message_notifications else None

        data = await self._state.http.modify_guild(
            guild_id=self.id,
            name=name,
            description=description,
            icon=icon,
            banner=banner,
            splash=splash,
            discovery_splash=discovery_splash,
            region=region,
            afk_channel=afk_channel.id if afk_channel else None,
            owner_id=owner.id if owner else None,
            afk_timeout=afk_timeout,
            default_message_notifications=notif,
            verification_level=verification_level.value if verification_level else None,
            system_channel_id=system_channel.id if system_channel else None,
            rules_channel_id=rules_channel.id if rules_channel else None,
            public_updates_channel_id=public_updates_channel.id if public_updates_channel else None,
            preferred_locale=preferred_locale,
            system_channel_flags=system_channel_flags.value if system_channel_flags else None,
        )

        self._data = data
        return self

    async def create_text_channel(
        self,
        *,
        name: str,
        topic: Optional[str] = None,
        position: Optional[int] = None,
        nsfw: Optional[bool] = None,
        overwrites: Optional[Dict[Union[Member, Role], Permissions]] = None,
        parent: Optional[CategoryChannel] = None,
    ) -> TextChannel:
        """Creates a text channel in the guild.

        Parameters
        ----------
        name: :class:`str`
            The name of the channel

        topic: Optional[:class:`str`]
            The new topic of the channel

        position: Optional[:class:`int`]
            The new position of the channel

        nsfw: Optional[:class:`bool`]
            Whether or not the channel should be marked as NSFW

        overwrites: Optional[Dict[Union[:class:`.Member`, :class:`.Role`], :class:`.Permissions`]]
            The new overwrites of the channel

        parent: Optional[:class:`.CategoryChannel`]
            The category to create the channel in

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create this channel.

        Returns
        -------
        :class:`.TextChannel`
            The newly created text channel.
        """
        data = await self._create_channel(
            name=name,
            type=ChannelType.TEXT,
            topic=topic,
            position=position,
            nsfw=nsfw,
            parent=parent,
            overwrites=overwrites,
        )

        channel = self._state.create_channel(data, self)
        return channel  # type: ignore

    async def create_voice_channel(
        self,
        *,
        name: str,
        bitrate: Optional[int] = None,
        user_limit: Optional[int] = None,
        position: Optional[int] = None,
        overwrites: Optional[Dict[Union[Member, Role], Permissions]] = None,
        parent: Optional[CategoryChannel] = None,
    ) -> VoiceChannel:
        """Creates a voice channel in the guild.

        Parameters
        ----------
        name: :class:`str`
            The name of the channel

        bitrate: Optional[:class:`int`]
            The bitrate of the voice channel

        user_limit: Optional[:class:`int`]
            The max amount of users to allow in the voice channel

        position: Optional[:class:`int`]
            The new position of the channel

        overwrites: Optional[Dict[Union[:class:`.Member`, :class:`.Role`], :class:`.Permissions`]]
            The new overwrites of the channel

        parent: Optional[:class:`.CategoryChannel`]
            The category to create the channel in

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create this channel.

        Returns
        -------
        :class:`.VoiceChannel`
            The newly created voice channel.
        """
        data = await self._create_channel(
            name=name,
            type=ChannelType.VOICE,
            bitrate=bitrate,
            user_limit=user_limit,
            position=position,
            parent=parent,
            overwrites=overwrites,
        )

        channel = self._state.create_channel(data, self)
        return channel  # type: ignore

    async def create_category(
        self,
        *,
        name: str,
        position: Optional[int] = None,
        overwrites: Optional[Dict[Union[Member, Role], Permissions]] = None,
    ) -> CategoryChannel:
        """Creates a new category in the guild.

        Parameters
        ----------
        name: :class:`str`
            The name of the category channel

        position: Optional[:class:`int`]
            The position of the category channel

        overwrites: Optional[Dict[Union[:class:`.Member`, :class:`.Role`], :class:`.Permissions`]]
            The overwrites to create the channel with

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create this category.

        Returns
        -------
        :class:`.CategoryChannel`
            The newly created category channel.
        """
        data = await self._create_channel(
            name=name,
            type=ChannelType.CATEGORY,
            position=position,
            overwrites=overwrites,
        )

        channel = self._state.create_channel(data, self)
        return channel  # type: ignore

    async def create_role(
        self,
        name: str,
        permissions: Optional[Permissions] = None,
        color: Optional[int] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None,
        icon: Optional[bytes] = None,
        unicode_emoji: Optional[str] = None,
    ) -> Role:
        """Creates a new role in the guild.

        Parameters
        ----------
        name: :class:`str`
            The name of the role

        permissions: Optional[:class:`.Permissions`]
            The permissions to give the role

        color: Optional[:class:`int`]
            The color of the role

        hoist: Optional[:class:`bool`]
            If the role should be hoisted or not

        mentionable: Optional[:class:`bool`]
            If the role should be mentionable or not

        icon: Optional[:class:`bytes`]
            The icon of the role

        unicode_emoji: Optional[:class:`str`]
            The emoji for the role

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create this role.

        Returns
        -------
        :class:`.Role`
            The newly created role.
        """
        data = await self._state.http.create_guild_role(
            self.id,
            name=name,
            permissions=permissions.value if permissions else None,
            color=color,
            hoist=hoist or False,
            mentionable=mentionable or False,
            icon=icon,
            unicode_emoji=unicode_emoji,
        )

        role = Role(self._state, data, self)

        self._roles[role.id] = role
        return role

    async def kick(self, user: Snowflake) -> None:
        """Kicks a member from the guild.

        Parameters
        ----------
        user: :class:`.Snowflake`
            The user to kick from the guild

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to kick this user.
        """
        await self._state.http.remove_guild_member(self.id, user.id)

    async def ban(self, user: Snowflake, *, delete_message_days: int = 0) -> None:
        """Bans a member from the guild.

        Parameters
        ----------
        user: :class:`.Snowflake`
            The user to ban from the guild

        delete_message_days: :class:`int`
            The number of days to delete messages for

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to ban this user.
        """
        await self._state.http.create_guild_ban(self.id, user.id, delete_message_days=delete_message_days)

    async def unban(self, user: Snowflake) -> None:
        """Unbans a member from the guild.

        Parameters
        ----------
        user: :class:`.Snowflake`
            The user to unban from the guild

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to ban this user.
        """
        await self._state.http.remove_guild_ban(self.id, user.id)

    async def fetch_bans(self) -> List[BanEntry]:
        """Fetches the bans from the guild.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.BanEntry`]
            A list of ban entries for the guild.
        """
        data = await self._state.http.get_guild_bans(self.id)

        return [BanEntry(User(self._state, payload["user"]), payload["reason"]) for payload in data]

    async def fetch_ban(self, user: Snowflake) -> BanEntry:
        """Fetches the ban from the guild for a specific user.

        Parameters
        ----------
        user: :class:`.Snowflake`
            The user to fetch for

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`.BanEntry`
            The ban entry for the user.
        """
        data = await self._state.http.get_guild_ban(self.id, user.id)
        user = User(self._state, data["user"])

        return BanEntry(user, data["reason"])

    async def fetch_invites(self) -> List[Invite]:
        """Fetches the guild's invites.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.Invite`]
            A list of invites fetched from the guild.
        """
        data = await self._state.http.get_guild_invites(self.id)
        return [Invite(self._state, payload) for payload in data]

    async def fetch_integrations(self) -> List[Integration]:
        """Fetches the guild's integrations.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.Integration`]
            A list of the guild's integrations.
        """
        data = await self._state.http.get_guild_integrations(self.id)
        return [Integration(self._state, payload, self) for payload in data]

    async def fetch_vanity_url(self) -> PartialInvite:
        """Fetches the guild's vanity url.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`.PartialInvite`
            The guild's vanity url.
        """
        data = await self._state.http.get_guild_vanity_url(self.id)
        return PartialInvite(data)

    async def fetch_templates(self) -> List[GuildTemplate]:
        """Fetches the guild's templates.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.GuildTemplate`]
            A list of the guild's templates
        """
        data = await self._state.http.get_guild_templates(self.id)
        return [GuildTemplate(self._state, payload) for payload in data]

    async def fetch_member(self, user_id: int) -> Member:
        """Fetches a member from the guild.

        Parameters
        ----------
        user_id: :class:`int`
            The id of the user to fetch

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            The user id passed was invalid.

        Returns
        -------
        :class:`.Member`
            The fetched member.
        """
        data = await self._state.http.get_guild_member(self.id, user_id)
        return self._state.create_member(data, self)

    async def fetch_members(self, *, limit: int = 100, after: Optional[int] = None) -> List[Member]:
        """Fetches the guild's members.

        Parameters
        ----------
        limit: :class:`int`
            The max amount of members to return

        after: Optional[:class:`int`]
            Fetch members after this member's id

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.Member`]
            A list of fetched members.
        """
        data = await self._state.http.list_guild_members(self.id, limit=limit, after=after)
        return [self._state.create_member(payload, self) for payload in data]

    async def fetch_roles(self) -> List[Role]:
        """Fetches the guild's roles.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.Role`]
            A list of the fetched roles.
        """
        data = await self._state.http.get_guild_roles(self.id)
        return [Role(self._state, payload, self) for payload in data]

    async def fetch_prune_count(self, *, days: int = 7, roles: Optional[List[Role]] = None) -> int:
        """Fetches the number of members that would be pruned.

        Parameters
        ----------
        days: :class:`int`
            The number of days to prune for

        roles: List[:class:`.Role`]
            The roles to include

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`int`
            The amount of members that would be pruned.
        """
        include_roles = [r.id for r in roles] if roles else None

        data = await self._state.http.get_guild_prune_count(guild_id=self.id, days=days, include_roles=include_roles)
        return data["pruned"]

    async def prune(
        self,
        *,
        days: int = 7,
        roles: Optional[List[Role]] = None,
        compute_prune_count: bool = False,
    ) -> Optional[int]:
        """Prunes the guild.
        Prunes the guild.
        Parameters
        ----------
        days: :class:`int`
            The number of days to prune for

        roles: List[:class:`.Role`]
            The roles to include

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`int`
            The amount of members pruned.
        """
        include_roles = [r.id for r in roles] if roles else None
        data = await self._state.http.begin_guild_prune(
            guild_id=self.id,
            days=days,
            include_roles=include_roles,
            compute_prune_count=compute_prune_count,
        )

        if compute_prune_count and data is not None:
            return data["pruned"]

        return None

    async def fetch_voice_regions(self) -> List[VoiceRegion]:
        """Fetches the guild's voice regions.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.VoiceRegion`]
            A list of the fetched voice regions.
        """
        data = await self._state.http.get_guild_voice_regions(self.id)
        return [VoiceRegion(payload) for payload in data]

    def query(self, query: str, *, limit: int = 1) -> MemberIterator:
        """Queries the guild for a specific string.

        Parameters
        ----------
        query: :class:`str`
            The query string

        limit: :class:`int`
            The maximum number of results to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`.MemberIterator`
            A :class:`.AsyncIterator` for the fetched members.
        """
        coro = self._state.http.search_guild_members(self.id, query=query, limit=limit)
        return MemberIterator(self._state, self, coro)

    def audit_logs(
        self,
        *,
        user: Optional[Snowflake] = None,
        action: Optional[AuditLogsEvent] = None,
        limit: Optional[int] = None,
    ) -> AuditLogIterator:
        """Returns an iterator for the guild's audit logs.

        Examples
        --------
        Getting the guild's audit logs: ::

            async for entry in guild.audit_logs():
                print(f"Action: {entry.action.name}. Target: {entry.target}. Reason: {entry.reason}")

                for change in entry.changes:
                    print(f"Change: {change.key} - {change.before} -> {change.after}")

        Parameters
        ----------
        user: Optional[:class:`.Snowflake`]
            The user to filter audit logs for

        action: Optional[:class:`.AuditLogsEvent`]
            The action to filter by

        limit: Optional[:class:`int`]
            The max amount of audit log entries to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`.AuditLogIterator`
            An :class:`.AsyncIterator` for the fetched audit logs.
        """
        user_id = user.id if user else None
        action_type = action.value if action else None

        coro = self._state.http.get_guild_audit_log(
            guild_id=self.id, user_id=user_id, action_type=action_type, limit=limit
        )
        return AuditLogIterator(self._state, self, coro)

    async def fetch_active_threads(self) -> List[Thread]:
        """Fetches the guild's active threads.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`.Thread`]
            A list of threads currently active.
        """
        data = await self._state.http.list_active_threads(self.id)
        return self._create_threads(data)

    async def change_voice_state(
        self,
        *,
        channel: Optional[VoiceChannel] = None,
        self_mute: bool = False,
        self_deaf: bool = False,
    ) -> None:
        """Changes the guild's voice state.

        Parameters
        ----------
        channel: Optional[:class:`.VoiceChannel`]
            The voice channel to move to

        self_mute: :class:`bool`
            Whether the client user should be muted or not

        self_deaf: :class:`bool`
            Whether the client user should be deafened or not
        """
        ws = self._state.get_websocket(self.id)
        await ws.change_guild_voice_state(self.id, channel.id if channel else None, self_mute, self_deaf)

    def get_member(self, member_id: int) -> Optional[Member]:
        """Gets a member from the guild's member cache.

        Parameters
        ----------
        member_id: :class:`int`
            The id of the member to get

        Returns
        -------
        Optional[:class:`.Member`]
            The member grabbed from the cache.
        """
        return self._members.get(member_id)

    def get_channel(self, channel_id: int) -> Optional[GuildChannels]:
        """Gets a channel from the guilds channel cache.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to get

        Returns
        -------
        Optional[Union[:class:`TextChannel`, :class:`VoiceChannel`, :class:`CategoryChannel`]]
            The channel grabbed from the cache.
        """
        return self._channels.get(channel_id)

    def get_role(self, role_id: int) -> Optional[Role]:
        """Gets a role from the guilds role cache.

        Parameters
        ----------
        role_id: :class:`int`
            The id of the role to get

        Returns
        -------
        Optional[:class:`.Role`]
            The role grabbed from the cache.
        """
        return self._roles.get(role_id)

    def get_emoji(self, emoji_id: int) -> Optional[Emoji]:
        """Gets an emoji from the guilds emoji cache.

        Parameters
        ----------
        emoji_id: :class:`int`
            The id of the emoji to get

        Returns
        -------
        Optional[:class:`.Emoji`]
            The emoji grabbed from the cache.
        """
        return self._emojis.get(emoji_id)

    def get_voice_state(self, member_id: int) -> Optional[VoiceState]:
        """Gets a voice state from the guilds voice state cache.

        Parameters
        ----------
        member_id: :class:`int`
            The id of the member to get

        Returns
        -------
        Optional[:class:`.VoiceState`]
            The voice state grabbed from the cache.
        """
        return self._voice_states.get(member_id)

    def get_thread(self, thread_id: int) -> Optional[Thread]:
        """Gets a thread from the guilds thread cache.

        Parameters
        ----------
        thread_id: :class:`int`
            The id of the thread to get

        Returns
        -------
        Optional[:class:`.Thread`]
            The thread grabbed from the cache.
        """
        return self._threads.get(thread_id)

    @property
    def voice_client(self) -> Optional[VoiceClient]:
        """The guild's voice client if it exists."""
        return self._state.get_voice_client(self.id)

    @property
    def id(self) -> int:
        """The ID of the guild."""
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """The name of the guild."""
        return self._data["name"]

    @property
    def description(self) -> Optional[str]:
        """The description of the guild."""
        return self._data["description"]

    @property
    def banner(self) -> Optional[CDNAsset]:
        """The banner of the guild."""
        banner_hash = self._data["banner"]
        if not banner_hash:
            return None

        return CDNAsset.from_guild_banner(self._state, self.id, banner_hash)

    @property
    def icon(self) -> Optional[CDNAsset]:
        """The icon of the guild."""
        icon_hash = self._data["icon"]
        if not icon_hash:
            return None

        return CDNAsset.from_guild_icon(self._state, self.id, icon_hash)

    @property
    def icon_hash(self) -> str:
        """The icon hash of the guild."""
        return self._data["icon_hash"]

    @property
    def splash(self) -> Optional[CDNAsset]:
        """The guild's splash."""
        splash_hash = self._data["splash"]
        if not splash_hash:
            return None

        return CDNAsset.from_guild_splash(self._state, self.id, splash_hash)

    @property
    def discovery_splash(self) -> Optional[CDNAsset]:
        """The guilds discovery splash."""
        discovery_splash = self._data["discovery_splash"]
        if not discovery_splash:
            return None

        return CDNAsset.from_guild_discovery_splash(self._state, self.id, discovery_splash)

    @property
    def owner(self) -> Optional[Union[User, Member]]:
        """The owner of the guild."""
        if owner := self.get_member(self.owner_id):
            return owner
        else:
            return self._state.get_user(self.owner_id)

    @property
    def owner_id(self) -> int:
        """The ID of the owner."""
        return int(self._data["owner_id"])

    @property
    def channels(self) -> List[GuildChannels]:
        """The list of channels belonging to the guild."""
        return list(self._channels.values())

    @property
    def members(self) -> List[Member]:
        """A list of members belonging to the guild."""
        return list(self._members.values())

    @property
    def roles(self) -> List[Role]:
        """A list of roles belonging to the guild."""
        return list(self._roles.values())

    @property
    def emojis(self) -> List[Emoji]:
        """The list of emojis belonging to the guild."""
        return list(self._emojis.values())

    @property
    def default_role(self) -> Role:
        """The guild's default role."""
        return self.get_role(self.id)  # type: ignore

    @property
    def member_count(self) -> int:
        """The guild's member count."""
        return len(self._members)

    @property
    def afk_channel_id(self) -> int:
        """The ID of the guild's AFK channel."""
        return int(self._data["afk_channel_id"])

    @property
    def afk_channel(self) -> Optional[GuildChannels]:
        """The guild's AFK channel."""
        return self.get_channel(self.afk_channel_id)

    @property
    def afk_timeout(self) -> int:
        """The guild's AFK timeout."""
        return int(self._data["afk_timeout"])

    @property
    def verification_level(self) -> VerificationLevel:
        """The guild's verification level."""
        return VerificationLevel(self._data["verification_level"])

    @property
    def default_message_notifications(self) -> MessageNotificationLevel:
        """The guild's default message notification level."""
        return MessageNotificationLevel(self._data["default_message_notifications"])

    @property
    def explicit_content_filter(self) -> ExplicitContentFilterLevel:
        """The guild's explicit content filter level."""
        return ExplicitContentFilterLevel(self._data["explicit_content_filter"])

    @property
    def features(self) -> List[str]:
        """The guild's features."""
        return self._data["features"]

    @property
    def mfa_level(self) -> MFALevel:
        """The guild's MFA level."""
        return MFALevel(self._data["mfa_level"])

    @property
    def application_id(self) -> Optional[int]:
        """The ID of the guild's application."""
        return self._data["application_id"]
