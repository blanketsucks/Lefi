from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Dict, List, NamedTuple, Optional, Union

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
)
from .integration import Integration
from .invite import Invite, PartialInvite
from .template import GuildTemplate
from ..voice import VoiceState, VoiceClient
from ..utils import MemberIterator, AuditLogIterator
from .threads import Thread

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

    async def edit(self, **kwargs) -> Guild:
        """
        Edits the guild.

        Parameters:
            **kwargs (Any): Options to pass to [lefi.HTTPClient.modify_guild][]

        Returns:
            The [Guild](./guild.md) after editing
        """
        data = await self._state.http.modify_guild(self.id, **kwargs)
        self._data = data
        return self

    async def create_text_channel(
        self,
        *,
        name: str,
        topic: Optional[str] = None,
        position: Optional[int] = None,
        nsfw: Optional[bool] = None,
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
        data = await self._state.http.create_guild_channel(
            guild_id=self.id,
            name=name,
            type=ChannelType.TEXT.value,
            topic=topic,
            position=position,
            parent_id=parent.id if parent else None,
            nsfw=nsfw,
        )

        channel = self._state.create_channel(data, self)
        self._channels[channel.id] = channel
        self._state._channels[channel.id] = channel

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
        return [BanEntry(payload["user"], payload["reason"]) for payload in data]

    async def fetch_ban(self, user: Snowflake) -> BanEntry:
        """
        Fetches the ban from the guild.

        Parameters:
            user (lefi.User): The user to fetch the ban for.

        Returns:
            The [lefi.BanEntry](./banentry.md) instance.

        """
        data = await self._state.http.get_guild_ban(self.id, user.id)
        return BanEntry(data["user"], data["reason"])

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

    def audit_logs(self) -> AuditLogIterator:
        coro = self._state.http.get_guild_audit_log(self.id)
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
    ):
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
