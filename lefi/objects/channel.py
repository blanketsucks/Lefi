from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Union,
)
import asyncio
import datetime
from functools import cached_property

from .enums import ChannelType, InviteTargetType
from .permissions import Overwrite
from .flags import Permissions
from .invite import Invite
from ..errors import VoiceException
from ..utils import to_snowflake, grouper
from ..voice import VoiceClient
from .threads import Thread
from .enums import ChannelType
from .flags import Permissions
from .permissions import Overwrite
from .base import Messageable, BaseTextChannel

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild
    from .member import Member
    from .message import Message
    from .role import Role
    from .user import User

__all__ = ("TextChannel", "DMChannel", "VoiceChannel", "CategoryChannel", "Channel")


class Channel:
    """
    A class representing a discord channel.
    """

    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        """
        Creates a new Channel from the given data.

        Parameters:
            state (lefi.State): The [State](./state.md) of the client.
            data (dict): The data to create the channel from.
        """
        self._state = state
        self._data = data
        self._guild = guild
        self._overwrites: Dict[Union[Member, Role], Overwrite] = {}

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} name={self.name!r} id={self.id} position={self.position} type={self.type!r}>"

    def _copy(self):
        copy = self.__class__(self._state, self._data, self._guild)
        copy._overwrites = self._overwrites.copy()

        return copy

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Channel):
            return NotImplemented

        return self.id == o.id

    async def delete(self) -> None:
        """
        Deletes the channel.
        """
        await self._state.http.delete_channel(self.id)

    async def edit_permissions(
        self, target: Union[Role, Member], **permissions: bool
    ) -> None:
        """
        Edits the permissions for the given target.

        Parameters:
            target (lefi.Role or lefi.Member): The target to edit the permissions for.
            **permissions (bool): The permissions to set.

        """
        if not isinstance(target, (Role, Member)):
            raise TypeError("target must be either a Role or Member")

        perms = Permissions(**permissions)

        allow, deny = perms.to_overwrite_pair()
        type = 0 if isinstance(target, Role) else 1

        await self._state.http.edit_channel_permissions(
            channel_id=self.id,
            overwrite_id=target.id,
            allow=allow.value,
            deny=deny.value,
            type=type,
        )

    async def delete_permission(self, target: Union[Member, Role]) -> None:
        """
        Deletes the permission for the given target.

        Parameters:
            target (lefi.Member or lefi.Role): The target to delete the permission for.
        """
        if not isinstance(target, (Member, Role)):
            raise TypeError("target must be either a Member or Role")

        await self._state.http.delete_channel_permissions(
            channel_id=self.id,
            overwrite_id=target.id,
        )

        self._overwrites.pop(target, None)

    @property
    def guild(self) -> Guild:
        """
        A [lefi.Guild](./guild.md) instance which the channel belongs to.
        """
        return self._guild

    @property
    def id(self) -> int:
        """
        The channels id.
        """
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """
        The channels name.
        """
        return self._data["name"]

    @property
    def type(self) -> ChannelType:
        """
        The type of the channel.
        """
        return ChannelType(self._data["type"])

    @property
    def nsfw(self) -> bool:
        """
        Whether or not the channel is marked as NSFW.
        """
        return self._data.get("nsfw", False)

    @property
    def position(self) -> int:
        """
        The position of the channel.
        """
        return self._data["position"]

    @property
    def overwrites(self) -> Dict[Union[Member, Role], Overwrite]:
        """
        A list of [lefi.Overwrite](./overwrite.md)s for the channel.
        """
        return self._overwrites

    def overwrites_for(self, target: Union[Member, Role]) -> Optional[Overwrite]:
        """
        Returns the [lefi.Overwrite](./overwrite.md) for the given target.
        """
        return self._overwrites.get(target)

    def permissions_for(self, target: Union[Member, Role]) -> Permissions:
        """
        Returns the permissions for the given target.

        Parameters:
            target (lefi.Member or lefi.Role): The target to get the permissions for.

        Returns:
            The [Permission]()s for the target.
        """
        base = target.permissions

        if base & Permissions.administrator:
            return Permissions.all()

        everyone = self.overwrites_for(self.guild.default_role)
        if everyone is not None:
            base |= everyone.allow
            base &= ~everyone.deny

        allow = Permissions(0)
        deny = Permissions(0)

        if isinstance(target, Member):
            for role in target.roles:
                overwrite = self.overwrites_for(role)
                if overwrite is not None:
                    allow |= overwrite.allow
                    deny |= overwrite.deny

            base |= allow
            base &= ~deny

            member_overwrite = self.overwrites_for(target)
            if member_overwrite:
                base |= member_overwrite.allow
                base &= ~member_overwrite.deny

            return base

        return base


class TextChannel(Channel, BaseTextChannel):  # type: ignore
    """
    A class that represents a TextChannel.
    """

    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        """
        Creates a new TextChannel from the given data.

        Parameters:
            state (lefi.State): The [State](./state.md) of the client.
            data (dict): The data to create the channel from.
        """
        super().__init__(state, data, guild)

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        type: Optional[ChannelType] = None,
        position: Optional[int] = None,
        topic: Optional[str] = None,
        nsfw: Optional[bool] = None,
        slowmode: Optional[int] = None,
        overwrites: Optional[Dict[Union[Member, Role], Permissions]],
    ) -> TextChannel:
        """
        Edits the channel.

        Parameters:
            **kwargs (Any): The options to pass to
            [lefi.HTTPClient.edit_text_channel](./http.md#lefi.http.HTTPClient.edit_text_channel).

        Returns:
            The lefi.TextChannel instance after editting.

        """
        permission_overwrites = self.guild._make_permission_overwrites(overwrites)
        data = await self._state.http.edit_text_channel(
            channel_id=self.id,
            name=name,
            type=type.value if type else None,
            position=position,
            topic=topic,
            nsfw=nsfw,
            rate_limit_per_user=slowmode,
            permission_overwrites=permission_overwrites,
        )
        self._data = data
        return self

    async def create_invite(
        self,
        *,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
    ) -> Invite:
        """
        Creates an invite for the channel.

        Parameters:
            max_age (int): The max age of the invite.
            max_uses (int): The max uses of the invite.
            temporary (bool): Whether or not the invite is temporary.
            unique (bool): Whether or not the invite is unique.

        Returns:
            The [lefi.Invite](./invite.md) instance.

        """
        data = await self._state.http.create_channel_invite(
            channel_id=self.id,
            max_age=max_age,
            max_uses=max_uses,
            temporary=temporary,
            unique=unique,
        )

        return Invite(self._state, data)

    async def trigger_typing(self) -> None:
        """
        Triggers typing in this text channel.
        """
        await self._state.http.trigger_typing(channel_id=self.id)

    async def create_thread(
        self,
        *,
        name: str,
        auto_archive_duration: Optional[int] = None,
        type: Optional[ChannelType] = None,
        invitable: Optional[bool] = None,
    ) -> Thread:
        """
        Creates a thread in this text channel.

        Parameters:
            name (str): The name of the thread.
            auto_archive_duration (int): The duration of the thread.
            type (lefi.ChannelType): The type of the thread.
            invitable (bool): Whether or not the thread is invitable.

        Returns:
            The [lefi.Thread](./thread.md) instance.

        """
        if auto_archive_duration is not None:
            if auto_archive_duration not in (60, 1440, 4320, 10080):
                raise ValueError(
                    "auto_archive_duration must be 60, 1440, 4320 or 10080"
                )

        if not type:
            type = ChannelType.PRIVATE_THREAD

        data = await self._state.http.start_thread_without_message(
            channel_id=self.id,
            name=name,
            auto_archive_duration=auto_archive_duration,
            type=type.value,
            invitable=invitable,
        )

        return Thread(self._state, self.guild, data)

    async def fetch_archived_threads(
        self,
        *,
        public: bool = True,
        before: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Thread]:
        """
        Fetches archived threads in this text channel.

        Parameters:
            public (bool): Whether or not to fetch public threads.
            before (int): The timestamp to fetch threads before.
            limit (int): The limit of the messages to fetch.

        Returns:
            A list of [lefi.Thread](./thread.md) instances.

        """
        if public:
            data = await self._state.http.list_public_archived_threads(
                channel_id=self.id,
                before=before,
                limit=limit,
            )
        else:
            data = await self._state.http.list_private_archived_threads(
                channel_id=self.id, before=before, limit=limit
            )

        return self.guild._create_threads(data)

    async def fetch_joined_private_archived_threads(self) -> List[Thread]:
        """
        Fetches joined private archived threads in this text channel.

        Returns:
            A list of [lefi.Thread](./thread.md) instances.

        """
        data = await self._state.http.list_private_archived_threads(channel_id=self.id)

        return self.guild._create_threads(data)

    @property
    def topic(self) -> str:
        """
        The topic of the channel.
        """
        return self._data["topic"]

    @property
    def last_message_id(self) -> Optional[int]:
        return to_snowflake(self._data, "last_message_id")

    @property
    def last_message(self) -> Optional[Message]:
        """
        The last [lefi.Message](./message.md) instance sent in the channel.
        """
        return (
            self._state.get_message(self.last_message_id)
            if self.last_message_id
            else None
        )

    @property
    def rate_limit_per_user(self) -> int:
        """
        The amount of time needed before another message can be sent in the channel.
        """
        return self._data["rate_limit_per_user"]

    @property
    def default_auto_archive_duration(self) -> int:
        """
        The amount of time it takes to archive a thread inside of the channel.
        """
        return self._data["default_auto_archive_duration"]

    @property
    def parent_id(self) -> Optional[int]:
        """
        The ID of the parent channel.
        """
        return to_snowflake(self._data, "parent_id")

    @property
    def parent(self) -> Optional[CategoryChannel]:
        """
        The channels parent.
        """
        return self.guild.get_channel(self.parent_id)  # type: ignore

    @property
    def category(self) -> Optional[CategoryChannel]:
        """
        An alias of `parent`
        """
        return self.parent


class VoiceChannel(Channel):
    """
    Represents a VoiceChannel.
    """

    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        """
        Creates a new VoiceChannel from the given data.

        Parameters:
            state (lefi.State): The [State](./state.md) of the client.
            data (dict): The data to create the channel from.
            guild (lefi.Guild): The [Guild](./guild.md) the channel belongs to.
        """
        super().__init__(state, data, guild)

    async def create_invite(
        self,
        *,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: Optional[InviteTargetType] = None,
        target_user: Optional[User] = None,
        target_application_id: Optional[int] = None,
    ) -> Invite:
        """
        Creates an invite for the channel.

        Parameters:
            max_age (int): The max age of the invite.
            max_uses (int): The max uses of the invite.
            temporary (bool): Whether or not the invite is temporary.
            unique (bool): Whether or not the invite is unique.
            target_type (Optional[lefi.InviteTargetType]): The target type of the invite.
            target_user (Optional[lefi.User]): The target user of the invite.
            target_application_id (Optional[int]): The target application ID of the invite.

        Returns:
            The [lefi.Invite](./invite.md) instance.

        """
        data = await self._state.http.create_channel_invite(
            channel_id=self.id,
            max_age=max_age,
            max_uses=max_uses,
            temporary=temporary,
            unique=unique,
            target_type=target_type,
            target_user_id=target_user.id if target_user is not None else None,
            target_application_id=target_application_id,
        )

        return Invite(self._state, data)

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        position: Optional[int] = None,
        bitrate: Optional[int] = None,
        user_limit: Optional[int] = None,
        rtc_region: Optional[str] = None,
        video_quality_mode: Optional[int] = None,
        sync_permissions: Optional[bool] = None,
        overwrites: Optional[Dict[Union[Member, Role], Permissions]],
    ) -> VoiceChannel:
        """
        Edits the channel.

        Parameters:
            **kwargs (Any): The options to pass to
            [lefi.HTTPClient.edit_voice_channel](./http.md#lefi.http.HTTPClient.edit_voice_channel).

        Returns:
            The lefi.VoiceChannel instance after editting.

        """
        permission_overwrites = self.guild._make_permission_overwrites(overwrites)
        data = await self._state.http.edit_voice_channel(
            channel_id=self.id,
            name=name,
            position=position,
            bitrate=bitrate,
            user_limit=user_limit,
            rtc_region=rtc_region,
            video_quality_mode=video_quality_mode,
            sync_permissions=sync_permissions,
            permission_overwrites=permission_overwrites,
        )
        self._data = data
        return self

    async def connect(self) -> VoiceClient:
        """
        Connects to this voice channel and returns the created voice client.

        Returns:
            The [lefi.VoiceClient][] instance.
        """
        if self.guild.voice_client:
            raise VoiceException("Client Already connected to a voice channel.")

        voice = VoiceClient(self._state, self)
        self._state.add_voice_client(self.guild.id, voice)

        await voice.connect()
        return voice

    async def disconnect(self) -> None:
        """
        Disconnects the voice client from the channel.
        """
        voice = self._state.get_voice_client(self.guild.id)
        if not voice:
            raise VoiceException("Client not connected to a voice channel")

        if voice.channel != self:
            raise VoiceException("Client not connected to the voice channel")

        await voice.disconnect()
        self._state.remove_voice_client(self.guild.id)

    @property
    def user_limit(self) -> int:
        """
        The user limit of the voice channel.
        """
        return self._data["user_limit"]

    @property
    def bitrate(self) -> int:
        """
        The bitrate of the voice channel.
        """
        return self._data["bitrate"]

    @property
    def rtc_region(self) -> Optional[str]:
        """
        THe rtc region of the voice channel.
        """
        return self._data["rtc_region"]

    @property
    def parent_id(self) -> Optional[int]:
        """
        The ID of the parent channel.
        """
        return to_snowflake(self._data, "parent_id")

    @property
    def parent(self) -> Optional[CategoryChannel]:
        """
        The channels parent.
        """
        return self.guild.get_channel(self.parent_id)  # type: ignore

    @property
    def category(self) -> Optional[CategoryChannel]:
        """
        An alias of `parent`
        """
        return self.parent

    @cached_property
    def members(self) -> List[Member]:
        """
        The members in the voice channel.
        """
        members = []

        for user_id, voice in self.guild._voice_states.items():
            if voice.channel_id == self.id:
                member = self.guild.get_member(user_id)

                if member:
                    members.append(member)

        return members


class CategoryChannel(Channel):
    async def create_text_channel(self, *, name: str, **kwargs: Any) -> TextChannel:
        return await self.guild.create_text_channel(name=name, parent=self, **kwargs)

    async def create_voice_channel(self, *, name: str, **kwargs) -> VoiceChannel:
        return await self.guild.create_voice_channel(name=name, parent=self, **kwargs)


class DMChannel(Messageable):
    """
    A class that represents a Users DMChannel.

    Attributes:
        guild (lefi.Guild): The [Guild](./guild.md) the channel is in.
    """

    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        """
        Creates a new DMChannel from the given data.

        Parameters:
            state (lefi.State): The [State](./state.md) of the client.
            data (dict): The data to create the channel from.
        """
        self._state = state
        self._data = data
        self.guild = None

    def __repr__(self) -> str:
        return f"<DMChannel id={self.id} type={self.type!r}>"

    @property
    def id(self) -> int:  # type: ignore
        """
        The ID of the DMChannel.
        """
        return int(self._data["id"])

    @property
    def last_message_id(self) -> Optional[int]:
        return to_snowflake(self._data, "last_message_id")

    @property
    def last_message(self) -> Optional[Message]:
        """
        The last [lefi.Message](./message.md) instance sent in the channel.
        """
        return self._state.get_message(self.last_message_id)  # type: ignore

    @property
    def type(self) -> int:
        """
        The type of the channel.
        """
        return int(self._data["type"])

    @property
    def receipients(self) -> List[User]:
        """
        A list of [lefi.User](./user.md) instances which are the recipients.
        """
        return [self._state.get_user(int(data["id"])) for data in self._data["recipients"]]  # type: ignore
