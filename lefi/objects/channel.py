from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Union,
)

from lefi.objects.flags import Permissions

from .embed import Embed
from .enums import ChannelType
from .permissions import Overwrite

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
        self._state = state
        self._data = data
        self._guild = guild
        self._overwrites: Dict[Union[Member, Role], Overwrite] = {}

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} name={self.name!r} id={self.id} position={self.position} type={self.type!r}>"

    @property
    def guild(self) -> Guild:
        """
        A [lefi.Guild][] instance which the channel belongs to.
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
        A list of [lefi.Overwrite][]s for the channel.
        """
        return self._overwrites

    def overwrites_for(self, target: Union[Member, Role]) -> Optional[Overwrite]:
        """
        Returns the [lefi.Overwrite][] for the given target.
        """
        return self._overwrites.get(target)

    def permissions_for(self, target: Union[Member, Role]) -> Permissions:
        """
        Returns the permissions for the given target.
        """
        base = target.permissions

        if base & Permissions.administrator:
            return Permissions.all()

        everyone = self.overwrites_for(self.guild.default_role)
        if everyone is not None:
            base |= everyone.allow
            base &= ~everyone.deny

        overwrites = self.overwrites
        allow = Permissions(0)
        deny = Permissions(0)

        if isinstance(target, Member):
            for role in target.roles:
                overwrite = overwrites.get(role)
                if overwrite is not None:
                    allow |= overwrite.allow
                    deny |= overwrite.deny

            base |= allow
            base &= ~deny

            member_overwrite = overwrites.get(target)
            if member_overwrite:
                base |= member_overwrite.allow
                base &= ~member_overwrite.deny

            return base

        return base


class TextChannel(Channel):
    """
    A class that represents a TextChannel.
    """

    def __init__(self, state: State, data: Dict, guild: Guild):
        super().__init__(state, data, guild)

    async def fetch_history(self, **kwargs) -> AsyncIterator[Message]:
        """
        Makes an API call to grab messages from the channel.

        Parameters:
            **kwargs (Any): The option to pass to [lefi.HTTPClient.get_channel_messages][].

        Returns:
            A list of the fetched [lefi.Message][] instances.

        """
        data = await self._state.http.get_channel_messages(self.id, **kwargs)
        for payload in data:
            yield self._state.create_message(payload, self)

    async def edit(self, **kwargs) -> TextChannel:
        """
        Edits the channel.

        Parameters:
            **kwargs (Any): The options to pass to [lefi.HTTPClient.edit_text_channel][].

        Returns:
            The [lefi.TextChannel][] instance after editting.

        """

        data = await self._state.http.edit_text_channel(self.id, **kwargs)
        self._data = data
        return self

    async def delete_messages(self, messages: Iterable[Message]) -> None:
        """
        Bulk deletes messages from the channel.

        Parameters:
            messages (Iterable[lefi.Message]): The list of messages to delete.

        """
        await self._state.http.bulk_delete_messages(
            self.id, message_ids=[msg.id for msg in messages]
        )

    async def purge(
        self,
        *,
        limit: int = 100,
        check: Optional[Callable[[Message], bool]] = None,
        around: Optional[int] = None,
        before: Optional[int] = None,
        after: Optional[int] = None,
    ) -> List[Message]:
        to_delete = []
        if not check:
            check = lambda message: True

        iterator = self.fetch_history(
            limit=limit, around=around, before=before, after=after
        )
        async for message in iterator:
            if check(message):
                to_delete.append(message)

        await self.delete_messages(to_delete)
        return to_delete

    async def send(
        self,
        content: Optional[str] = None,
        *,
        embeds: Optional[List[Embed]] = None,
        **kwargs,
    ) -> Message:
        """
        Sends a message to the channel.

        Parameters:
            content (Optional[str]): The content of the message.
            embeds (Optional[List[lefi.Embed]]): The list of embeds to send with the message.
            **kwargs (Any): Extra options to pass to [lefi.HTTPClient.send_message][]

        Returns:
            The sent [lefi.Message][] instance.

        """
        embeds = [] if embeds is None else embeds

        data = await self._state.client.http.send_message(
            channel_id=self.id,
            content=content,
            embeds=[embed.to_dict() for embed in embeds],
            **kwargs,
        )
        return self._state.create_message(data, self)

    async def fetch_message(self, message_id: int) -> Message:
        """
        Makes an API call to receive a message.

        Parameters:
            message_id (int): The ID of the message.

        Returns:
            The [lefi.Message][] instance corresponding to the ID if found.

        """
        data = await self._state.http.get_channel_message(self.id, message_id)
        return self._state.create_message(data, self)

    @property
    def topic(self) -> str:
        """
        The topic of the channel.
        """
        return self._data["topic"]

    @property
    def last_message(self) -> Optional[Message]:
        """
        The last [lefi.Message][] instance sent in the channel.
        """
        return self._state.get_message(self._data["last_message_id"])

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
    def parent(self) -> Optional[Channel]:
        """
        The channels parent.
        """
        return self.guild.get_channel(self._data["parent_id"])


class VoiceChannel(Channel):
    """
    Represents a VoiceChannel.
    """

    def __init__(self, state: State, data: Dict, guild: Guild):
        super().__init__(state, data, guild)

    async def edit(self, **kwargs) -> VoiceChannel:
        """
        Edits the channel.

        Parameters:
            **kwargs (Any): The options to pass to [lefi.HTTPClient.edit_voice_channel][].

        Returns:
            The [lefi.VoiceChannel][] instance after editting.

        """
        data = await self._state.http.edit_voice_channel(**kwargs)
        self._data = data
        return self

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
    def parent(self):
        """
        The parent of the voice channel.
        """
        return self.guild.get_channel(self._data["parent_id"])


class CategoryChannel(Channel):
    pass


class DMChannel:
    """
    A class that represents a Users DMChannel.
    """

    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        self._state = state
        self._data = data
        self.guild = None

    def __repr__(self) -> str:
        return f"<DMChannel id={self.id} type={self.type!r}>"

    async def send(
        self, content: Optional[str] = None, *, embeds: Optional[List[Embed]] = None
    ) -> Message:
        """
        Sends a message to the channel.

        Parameters:
            content (Optional[str]): The content of the message.
            embeds (Optional[List[lefi.Embed]]): The list of embeds to send with the message.

        Returns:
            The sent [lefi.Message][] instance.

        """
        embeds = [] if embeds is None else embeds

        data = await self._state.client.http.send_message(
            channel_id=self.id,
            content=content,
            embeds=[embed.to_dict() for embed in embeds],
        )
        return self._state.create_message(data, self)

    @property
    def id(self) -> int:
        """
        The ID of the DMChannel.
        """
        return int(self._data["id"])

    @property
    def last_message(self) -> Optional[Message]:
        return self._state.get_message(self._data["last_message_id"])

    @property
    def type(self) -> int:
        """
        The type of the channel.
        """
        return int(self._data["type"])

    @property
    def receipients(self) -> List[User]:
        """
        A list of [lefi.User][] instances which are the recipients.
        """
        return [self._state.get_user(int(data["id"])) for data in self._data["recipients"]]  # type: ignore
