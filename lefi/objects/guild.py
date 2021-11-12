from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Union,
    overload,
    Any,
)

from ..utils import Snowflake
from .emoji import Emoji
from .enums import (
    ChannelType,
    ExplicitContentFilterLevel,
    GuildPremiumTier,
    MessageNotificationLevel,
    MFALevel,
    NSFWLevel,
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
    """
    Represents a Guild.
    """

    def __init__(self, state: State, data: Dict) -> None:
        """
        Creates a new Guild instance.

        Parameters:
            state (lefi.State): The state instance.
            data (Dict): The guild data.
        """
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
        threads = {
            int(thread["id"]): Thread(self._state, self, thread)
            for thread in data.get("threads", [])
        }

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
        features: Optional[List[str]] = None,
        system_channel: Optional[TextChannel] = None,
        system_channel_flags: Optional[SystemChannelFlags] = None,
        preferred_locale: Optional[str] = None,
        rules_channel: Optional[TextChannel] = None,
        public_updates_channel: Optional[TextChannel] = None,
    ) -> Guild:
        """
        Edits the guild.

        Parameters:
            **kwargs (Any): Options to pass to [lefi.HTTPClient.modify_guild][]

        Returns:
            The [Guild](./guild.md) after editing
        """
        region = region.name if isinstance(region, VoiceRegion) else region
        notif = (
            default_message_notifications.value
            if default_message_notifications
            else None
        )

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
            public_updates_channel_id=public_updates_channel.id
            if public_updates_channel
            else None,
            preferred_locale=preferred_locale,
            features=features,
            system_channel_flags=system_channel_flags.value
            if system_channel_flags
            else None,
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
        """
        Creates a new text channel in the guild.

        Parameters:
            name (str): The name of the channel.
            topic (str): The topic of the channel.
            position (int): The position of the channel.
            nsfw (bool): Whether the channel is nsfw.
            parent (lefi.CategoryChannel): The parent category of the channel.

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
        """
        Creates a new voice channel in the guild.

        Parameters:
            name (str): The name of the channel.
            bitrate (int): The bitrate of the channel.
            user_limit (int): The user limit of the channel.
            position (int): The position of the channel.
            parent (lefi.CategoryChannel): The parent category of the channel.
            overwrites (Dict[Union[lefi.Member, lefi.Role], lefi.Permissions]): The overwrites of the channel.

        Returns:
            The newly created [lefi.VoiceChannel] instance.

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
        """
        Creates a new category in the guild.

        Parameters:
            name (str): The name of the category.
            position (int): The position of the category.
            parent (lefi.CategoryChannel): The parent category of the category.
            overwrites (Dict[Union[lefi.Member, lefi.Role], lefi.Permissions]): The overwrites of the category.

        Returns:
            The newly created [lefi.CategoryChannel] instance.

        """
        data = await self._create_channel(
            name=name,
            type=ChannelType.CATEGORY,
            position=position,
            overwrites=overwrites,
        )

        channel = self._state.create_channel(data, self)
        return channel  # type: ignore

    async def create_role(self, name: str, **kwargs) -> Role:
        """
        Creates a new role in the guild.

        Parameters:
            name (str): The name of the role.
            **kwargs (Any): Extra options to pass to [lefi.HTTPClient.create_guild_role][].

        Returns:
            The newly created [lefi.Role](./role.md) instance.

        """
        data = await self._state.http.create_guild_role(self.id, name=name, **kwargs)
        role = Role(self._state, data, self)

        self._roles[role.id] = role
        return role

    async def kick(self, user: Snowflake) -> None:
        """
        Kicks a member from the guild.

        Parameters:
            user (lefi.User): The user to kick.

        """
        await self._state.http.remove_guild_member(self.id, user.id)

    async def ban(self, user: Snowflake, *, delete_message_days: int = 0) -> None:
        """
        Bans a member from the guild.

        Parameters:
            member (lefi.Member): The member to ban.
            delete_message_days (int): The number of days to delete messages for.

        """
        await self._state.http.create_guild_ban(
            self.id, user.id, delete_message_days=delete_message_days
        )

    async def unban(self, user: Snowflake) -> None:
        """
        Unbans a member from the guild.

        Parameters:
            user (lefi.User): The user to unban.

        """
        await self._state.http.remove_guild_ban(self.id, user.id)

    async def fetch_bans(self) -> List[BanEntry]:
        """
        Fetches the bans from the guild.

        Returns:
            A list of [lefi.BanEntry](./banentry.md) instances.

        """
        data = await self._state.http.get_guild_bans(self.id)

        return [
            BanEntry(User(self._state, payload["user"]), payload["reason"])
            for payload in data
        ]

    async def fetch_ban(self, user: Snowflake) -> BanEntry:
        """
        Fetches the ban from the guild.

        Parameters:
            user (lefi.User): The user to fetch the ban for.

        Returns:
            The [lefi.BanEntry](./banentry.md) instance.

        """
        data = await self._state.http.get_guild_ban(self.id, user.id)
        user = User(self._state, data["user"])

        return BanEntry(user, data["reason"])

    async def fetch_invites(self) -> List[Invite]:
        """
        Fetches the guild's invites.

        Returns:
            A list of [lefi.Invite](./invite.md) instances.

        """
        data = await self._state.http.get_guild_invites(self.id)
        return [Invite(self._state, payload) for payload in data]

    async def fetch_integrations(self) -> List[Integration]:
        """
        Fetches the guild's integrations.

        Returns:
            A list of [lefi.Integration](./integration.md) instances.

        """
        data = await self._state.http.get_guild_integrations(self.id)
        return [Integration(self._state, payload, self) for payload in data]

    async def fetch_vanity_url(self):
        """
        Fetches the guild's vanity url.

        Returns:
            The vanity url.

        """
        data = await self._state.http.get_guild_vanity_url(self.id)
        return PartialInvite(data)

    async def fetch_templates(self) -> List[GuildTemplate]:
        """
        Fetches the guild's templates.

        Returns:
            A list of [lefi.GuildTemplate](./template.md) instances.

        """
        data = await self._state.http.get_guild_templates(self.id)
        return [GuildTemplate(self._state, payload) for payload in data]

    async def fetch_member(self, user_id: int) -> Member:
        """
        Fetches a member from the guild.

        Parameters:
            user_id (int): The id of the user to fetch.

        Returns:
            The [lefi.Member](./member.md) instance.

        """
        data = await self._state.http.get_guild_member(self.id, user_id)
        return self._state.create_member(data, self)

    async def fetch_members(
        self, *, limit: int = 100, after: Optional[int] = None
    ) -> List[Member]:
        """
        Fetches the guild's members.

        Parameters:
            limit (int): The number of members to fetch.
            after (int): The id of the member to start at.

        Returns:
            A list of [lefi.Member](./member.md) instances.

        """
        data = await self._state.http.list_guild_members(
            self.id, limit=limit, after=after
        )
        return [self._state.create_member(payload, self) for payload in data]

    async def fetch_roles(self) -> List[Role]:
        """
        Fetches the guild's roles.

        Returns:
            A list of [lefi.Role](./role.md) instances.

        """
        data = await self._state.http.get_guild_roles(self.id)
        return [Role(self._state, payload, self) for payload in data]

    async def fetch_prune_count(
        self, *, days: int = 7, roles: Optional[List[Role]] = None
    ) -> int:
        """
        Fetches the number of members that would be pruned.

        Parameters:
            days (int): The number of days to prune for.
            roles (List[lefi.Role]): The roles to include.

        Returns:
            The number of members that would be pruned.

        """
        include_roles = [r.id for r in roles] if roles else None

        data = await self._state.http.get_guild_prune_count(
            guild_id=self.id, days=days, include_roles=include_roles
        )
        return data["pruned"]

    @overload
    async def prune(
        self,
        *,
        days: int = 7,
        roles: Optional[List[Role]] = None,
        compute_prune_count: Literal[True],
    ) -> int:
        ...

    @overload
    async def prune(
        self,
        *,
        days: int = 7,
        roles: Optional[List[Role]] = None,
        compute_prune_count: Literal[False],
    ) -> None:
        ...

    async def prune(
        self,
        *,
        days: int = 7,
        roles: Optional[List[Role]] = None,
        compute_prune_count: bool = True,
    ) -> Optional[int]:
        """
        Prunes the guild.

        Parameters:
            days (int): The number of days to prune for.
            roles (List[lefi.Role]): The roles to include.

        Returns:
            The number of members that were pruned.

        """
        include_roles = [r.id for r in roles] if roles else None
        data = await self._state.http.begin_guild_prune(
            guild_id=self.id,
            days=days,
            include_roles=include_roles,
            compute_prune_count=compute_prune_count,
        )

        if compute_prune_count:
            return data["pruned"]

        return None

    async def fetch_voice_regions(self) -> List[VoiceRegion]:
        """
        Fetches the guild's voice regions.

        Returns:
            A list of [lefi.VoiceRegion](./voiceregion.md) instances.

        """
        data = await self._state.http.get_guild_voice_regions(self.id)
        return [VoiceRegion(payload) for payload in data]

    def query(self, q: str, *, limit: int = 1) -> MemberIterator:
        """
        Queries the guild for a specific string.

        Parameters:
            q (str): The query string.
            limit (int): The maximum number of results to return.

        Returns:
            A list of [lefi.Member](./member.md) instances.

        """
        coro = self._state.http.search_guild_members(self.id, query=q, limit=limit)
        return MemberIterator(self._state, self, coro)

    def audit_logs(
        self,
        *,
        user: Optional[Snowflake] = None,
        action: Optional[AuditLogsEvent] = None,
        limit: Optional[int] = None,
    ) -> AuditLogIterator:
        """
        Returns an iterator for the guild's audit logs.

        Example:
            ```py
            async for entry in guild.audit_logs():
                print(f"Action: {entry.action.name}. Target: {entry.target}. Reason: {entry.reason}")

                for change in entry.changes:
                    print(f"Change: {change.key} - {change.before} -> {change.after}")
            ```

        """
        user_id = user.id if user else None
        action_type = action.value if action else None

        coro = self._state.http.get_guild_audit_log(
            guild_id=self.id, user_id=user_id, action_type=action_type, limit=limit
        )
        return AuditLogIterator(self._state, self, coro)

    async def fetch_active_threads(self) -> List[Thread]:
        """
        Fetches the guild's active threads.

        Returns:
            A list of [lefi.Thread](./thread.md) instances.

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
        """
        Changes the guild's voice state.

        Parameters:
            channel (lefi.VoiceChannel): The voice channel to move to.
            self_mute (bool): Whether to mute the bot.
            self_deaf (bool): Whether to deafen the bot.

        """
        ws = self._state.get_websocket(self.id)
        await ws.change_guild_voice_state(
            self.id, channel.id if channel else None, self_mute, self_deaf
        )

    def get_member(self, member_id: int) -> Optional[Member]:
        """
        Gets a member from the guilds member cache.

        Parameters:
            member_id (int): The ID of the member.

        Returns:
            The [lefi.Member](./member.md) instance corresponding to the ID if found.

        """
        return self._members.get(member_id)

    def get_channel(self, channel_id: int) -> Optional[GuildChannels]:
        """
        Gets a channel from the guilds channel cache.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The [lefi.Channel](./channel.md) instance corresponding to the ID if found.

        """
        return self._channels.get(channel_id)

    def get_role(self, role_id: int) -> Optional[Role]:
        """
        Gets a role from the guilds role cache.

        Parameters:
            role_id (int): The ID of the role.

        Returns:
            The [lefi.Role](./role.md) instance corresponding to the ID if found.

        """
        return self._roles.get(role_id)

    def get_emoji(self, emoji_id: int) -> Optional[Emoji]:
        """
        Gets an emoji from the guilds emoji cache.

        Parameters:
            emoji_id (int): The ID of the emoji.

        Returns:
            The [lefi.Emoji](./emoji.md) instance corresponding to the ID if found.

        """
        return self._emojis.get(emoji_id)

    def get_voice_state(self, member_id: int) -> Optional[VoiceState]:
        """
        Gets a voice state from the guilds voice state cache.

        Parameters:
            member_id (int): The ID of the member.

        Returns:
            The [lefi.VoiceState][] instance corresponding to the ID if found.

        """
        return self._voice_states.get(member_id)

    def get_thread(self, thread_id: int) -> Optional[Thread]:
        """
        Gets a thread from the guilds thread cache.

        Parameters:
            thread_id (int): The ID of the thread.

        Returns:
            The [lefi.Thread](./thread.md) instance corresponding to the ID if found.

        """
        return self._threads.get(thread_id)

    @property
    def voice_client(self) -> Optional[VoiceClient]:
        """
        The guild's voice client if it exists.
        """
        return self._state.get_voice_client(self.id)

    @property
    def id(self) -> int:
        """
        The ID of the guild.
        """
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """
        The name of the guild.
        """
        return self._data["name"]

    @property
    def description(self) -> Optional[str]:
        return self._data["description"]

    @property
    def banner(self) -> Optional[CDNAsset]:
        banner_hash = self._data["banner"]
        if not banner_hash:
            return None

        return CDNAsset.from_guild_banner(self._state, self.id, banner_hash)

    @property
    def icon(self) -> Optional[CDNAsset]:
        """
        The icon of the guild.
        """
        icon_hash = self._data["icon"]
        if not icon_hash:
            return None

        return CDNAsset.from_guild_icon(self._state, self.id, icon_hash)

    @property
    def icon_hash(self) -> str:
        """
        The icon hash of the guild.
        """
        return self._data["icon_hash"]

    @property
    def splash(self) -> Optional[CDNAsset]:
        """
        The guild's splash.
        """
        splash_hash = self._data["splash"]
        if not splash_hash:
            return None

        return CDNAsset.from_guild_splash(self._state, self.id, splash_hash)

    @property
    def discovery_splash(self) -> Optional[CDNAsset]:
        """
        The guilds discovery splash.
        """
        discovery_splash = self._data["discovery_splash"]
        if not discovery_splash:
            return None

        return CDNAsset.from_guild_discovery_splash(
            self._state, self.id, discovery_splash
        )

    @property
    def owner(self) -> Optional[Union[User, Member]]:
        """
        The owner of the guild.
        """
        if owner := self.get_member(self.owner_id):
            return owner
        else:
            return self._state.get_user(self.owner_id)

    @property
    def owner_id(self) -> int:
        """
        The ID of the owner.
        """
        return int(self._data["owner_id"])

    @property
    def channels(self) -> List[GuildChannels]:
        """
        The list of [lefi.Channel](./channel.md) instances belonging to the guild.
        """
        return list(self._channels.values())

    @property
    def members(self) -> List[Member]:
        """
        The list of [lefi.Member](./member.md) instances belonging to the guild.
        """
        return list(self._members.values())

    @property
    def roles(self) -> List[Role]:
        """
        The list of [lefi.Role](./role.md) instances belonging to the guild.
        """
        return list(self._roles.values())

    @property
    def emojis(self) -> List[Emoji]:
        """
        The list of [lefi.Emoji](./emoji.md) instances belonging to the guild.
        """
        return list(self._emojis.values())

    @property
    def default_role(self) -> Role:
        """
        The guild's default role.
        """
        return self.get_role(self.id)  # type: ignore

    @property
    def member_count(self) -> int:
        """
        The guild's member count.
        """
        return len(self._members)

    @property
    def afk_channel_id(self) -> int:
        """
        The ID of the guild's AFK channel.
        """
        return int(self._data["afk_channel_id"])

    @property
    def afk_channel(self) -> Optional[GuildChannels]:
        """
        The guild's AFK channel.
        """
        return self.get_channel(self.afk_channel_id)

    @property
    def afk_timeout(self) -> int:
        """
        The guild's AFK timeout.
        """
        return int(self._data["afk_timeout"])

    @property
    def verification_level(self) -> VerificationLevel:
        """
        The guild's verification level.
        """
        return VerificationLevel(self._data["verification_level"])

    @property
    def default_message_notifications(self) -> MessageNotificationLevel:
        """
        The guild's default message notification level.
        """
        return MessageNotificationLevel(self._data["default_message_notifications"])

    @property
    def explicit_content_filter(self) -> ExplicitContentFilterLevel:
        """
        The guild's explicit content filter level.
        """
        return ExplicitContentFilterLevel(self._data["explicit_content_filter"])

    @property
    def features(self) -> List[str]:
        """
        The guild's features.
        """
        return self._data["features"]

    @property
    def mfa_level(self) -> MFALevel:
        """
        The guild's MFA level.
        """
        return MFALevel(self._data["mfa_level"])

    @property
    def application_id(self) -> Optional[int]:
        """
        The ID of the guild's application.
        """
        return self._data["application_id"]
