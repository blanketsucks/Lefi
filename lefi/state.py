from __future__ import annotations

import asyncio
import collections
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar, Union

from .objects import (
    CategoryChannel,
    DeletedMessage,
    DMChannel,
    Emoji,
    Guild,
    Member,
    Message,
    Overwrite,
    OverwriteType,
    Role,
    TextChannel,
    User,
    VoiceChannel,
)
from .objects.channel import Channel

if TYPE_CHECKING:
    from .client import Client

__all__ = (
    "State",
    "Cache",
)

T = TypeVar("T")


class Cache(collections.OrderedDict[Union[int, str], T]):
    """
    A class which acts as a cache for objects.

    Attributes:
        maxlen (Optional[int]): The max amount the cache can hold.

    """

    def __init__(self, maxlen: Optional[int] = None, *args, **kwargs):
        """
        Parameters:
            maxlen (Optional[int]): The max amount the cache can hold.

        """
        super().__init__(*args, **kwargs)
        self.maxlen: Optional[int] = maxlen
        self._max: int = 0

    def __repr__(self) -> str:
        return f"<Cache maxlen={self.maxlen}>"

    def __setitem__(self, key: Union[int, str], value: T) -> None:
        super().__setitem__(key, value)
        self._max += 1

        if self.maxlen and self._max > self.maxlen:
            self.popitem(False)


class State:
    """
    A class which represents the connection state between the client and discord.

    Attributes:
        client (lefi.Client): The [lefi.Client][] instance being used.
        loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] being used.
        http (lefi.HTTPClient): The [lefi.HTTPClient][] handling requests

    Danger:
        This class is used internally. **It is not meant to called directly**

    """

    CHANNEL_MAPPING: Dict[
        int,
        Union[
            Type[TextChannel],
            Type[DMChannel],
            Type[VoiceChannel],
            Type[CategoryChannel],
            Type[Channel],
        ],
    ] = {
        0: TextChannel,
        1: DMChannel,
        2: VoiceChannel,
        3: CategoryChannel,
    }

    def __init__(self, client: Client, loop: asyncio.AbstractEventLoop):
        """
        Parameters:
            client (lefi.Client): The client being used.
            loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] being used.

        """
        self.client = client
        self.loop = loop
        self.http = client.http

        self._messages = Cache[Message](1000)
        self._users = Cache[User]()
        self._guilds = Cache[Guild]()
        self._channels = Cache[
            Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel]
        ]()
        self._emojis = Cache[Emoji]()

    def dispatch(self, event: str, *payload: Any) -> None:
        """
        Dispatches data to callbacks registered to events after parsing is finished.

        Parameters:
            event (str): The name of the event to dispatch to.
            *payload (Any): The data after parsing is finished.

        """
        events: dict = self.client.events.get(event, {})
        futures = self.client.futures.get(event, [])

        if callbacks := self.client.once_events.get(event):
            for index, callback in enumerate(callbacks):
                self.loop.create_task(callback(*payload))
                callbacks.pop(index)

            return

        for future, check in futures:
            if check(*payload):
                future.set_result(*payload)
                futures.remove((future, check))

                break

        for callback in events.values():
            self.loop.create_task(callback(*payload))

    async def parse_ready(self, data: Dict) -> None:
        """
        Parses the `READY` event. Creates a User then dispatches it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        user = self.add_user(data["user"])
        self.client.user = user

        self.dispatch("ready", user)

    async def parse_guild_create(self, data: Dict) -> None:
        """
        Parses `GUILD_CREATE` event. Creates a Guild then caches it, as well as dispatching it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        guild = Guild(self, data)

        self.create_guild_channels(guild, data)
        self.create_guild_roles(guild, data)
        self.create_guild_members(guild, data)

        self._guilds[guild.id] = guild
        self.dispatch("guild_create", guild)

    async def parse_message_create(self, data: Dict) -> None:
        """
        Parses `MESSAGE_CREATE` event. Creates a Message then caches it, as well as dispatching it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        self.add_user(data["author"])
        channel = self._channels.get(int(data["channel_id"]))
        message = Message(self, data, channel)  # type: ignore

        self._messages[message.id] = message
        self.dispatch("message_create", message)

    async def parse_message_delete(self, data: Dict) -> None:
        """
        Parses `MESSAGE_DELETE` event. Retrieves the message from cache if possible.
        Else it dispatches a `DeletedMessage`.

        Parameters:
            data (Dict): The raw data.

        """
        deleted = DeletedMessage(data)
        message = self._messages.get(deleted.id)

        if message:
            self._messages.pop(message.id)
        else:
            message = deleted  # type: ignore

        self.dispatch("message_delete", message)

    async def parse_message_update(self, data: Dict) -> None:
        """
        Parses `MESSAGE_UPDATE` event. Dispatches `before` and `after`.

        Parameters:
            data (Dict): The raw data.

        """
        channel = self.get_channel(int(data["channel_id"]))
        if not channel:
            return

        after = self.create_message(data, channel)

        if not (before := self.get_message(after.id)):
            msg = await self.http.get_channel_message(channel.id, after.id)  # type: ignore
            before = self.create_message(msg, channel)
        else:
            self._messages.pop(before.id)

        self._messages[after.id] = after
        self.dispatch("message_update", before, after)

    async def parse_channel_create(self, data: Dict) -> None:
        """
        Parses `CHANNEL_CREATE` event. Creates a Channel then caches it, as well as dispatching it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        if guild_id := data.get("guild_id"):
            guild = self.get_guild(int(guild_id))
            channel = self.create_channel(data, guild)
        else:
            channel = self.create_channel(data)

        self._channels[channel.id] = channel
        self.dispatch("channel_create", channel)

    async def parse_channel_update(self, data: Dict) -> None:
        """
        Parses `CHANNEL_UPDATE` event. Dispatches `before` and `after`.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))

        before = self.get_channel(int(data["id"]))
        after = self.create_channel(data, guild)

        self._channels[after.id] = after
        self.dispatch("channel_update", before, after)

    async def parse_channel_delete(self, data: Dict) -> None:
        """
        Parses `CHANNEL_DELETE` event. Dispatches the deleted channel.

        Parameters:
            data (Dict): The raw data.

        """
        channel = self.get_channel(int(data["id"]))
        self._channels.pop(channel.id)  # type: ignore

        self.dispatch("channel_delete", channel)

    def get_message(self, message_id: int) -> Optional[Message]:
        """
        Grabs a message from the cache.

        Parameters:
            message_id (int): The ID of the message.

        Returns:
            The [lefi.Message][] insance corresponding to the ID if found.

        """
        return self._messages.get(message_id)

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Grabs a user from the cache.

        Parameters:
            user_id (int): The ID of the user.

        Returns:
            The [lefi.User][] instance corresponding to the ID if found.

        """
        return self._users.get(user_id)

    def add_user(self, data: Dict) -> User:
        """
        Creates a user then caches it.

        Parameters:
            data (Dict): The data of the user.

        Returns:
            The created [lefi.User][] instance.

        """
        user = User(self, data)

        self._users[user.id] = user
        return user

    def get_guild(self, guild_id: int) -> Optional[Guild]:
        """
        Grabs a guild from the cache.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The [lefi.Guild][] instance corresponding to the ID if found.

        """
        return self._guilds.get(guild_id)

    def get_channel(
        self, channel_id: int
    ) -> Optional[
        Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel]
    ]:
        """
        Grabs a channel from the cache.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The [lefi.Channel][] instance corresponding to the ID if found.

        """
        return self._channels.get(channel_id)

    def get_emoji(self, emoji_id: int) -> Optional[Emoji]:
        """
        Grabs an emoji from the cache.

        Parameters:
            emoji_id (int): The ID of the emoji.

        Returns:
            The [lefi.Emoji][] instance corresponding to the ID if found.

        """
        return self._emojis.get(emoji_id)

    def create_message(self, data: Dict, channel: Any) -> Message:
        """
        Creates a Message instance.

        Parameters:
            data (Dict): The data of the message.
            channel (Any): The channel of the message.

        Returns:
            The created [lefi.Message][] instance.

        """
        return Message(self, data, channel)

    def create_channel(
        self, data: Dict, *args
    ) -> Union[TextChannel, VoiceChannel, CategoryChannel, Channel]:
        """
        Creates a Channel instance.

        Parameters:
            data (Dict): The data of the channel.
            *args (Any): Extra arguments to pass to the channels constructor.

        Returns:
            The created [lefi.Channel][] instance.

        """
        cls = self.CHANNEL_MAPPING.get(int(data["type"]), Channel)
        channel = cls(self, data, *args)

        self.create_overwrites(channel)
        return channel  # type: ignore

    def create_guild_channels(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the channels of a guild.

        Parameters:
            guild (lefi.Guild): The guild which to create the channels for.
            data (Dict): The data of the channels.

        Returns:
            The [lefi.Guild][] instance passed in.

        """
        channels = {
            int(payload["id"]): self.create_channel(payload, guild)
            for payload in data["channels"]
        }

        for id, channel in channels.items():
            self._channels[id] = channel

        guild._channels = channels
        return guild

    def create_guild_members(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the members of a guild.

        Parameters:
            guild (lefi.Guild): The guild which to create the channels for.
            data (Dict): The data of the members.

        Returns:
            The [lefi.Guild][] instance passed in.

        """
        members: Dict[int, Member] = {}
        for member_data in data["members"]:
            member = Member(self, member_data, guild)
            member._roles = {  # type: ignore
                int(role): guild.get_role(int(role)) for role in member_data["roles"]  # type: ignore
            }

            members[member.id] = member

        guild._members = members
        return guild

    def create_guild_roles(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the roles of a guild.

        Parameters:
            guild (lefi.Guild): The guild which to create the channels for.
            data (Dict): The data of the roles.

        Returns:
            The [lefi.Guild][] instance passed in.

        """
        roles = {
            int(payload["id"]): Role(self, payload, guild) for payload in data["roles"]
        }
        guild._roles = roles
        return guild

    def create_guild_emojis(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the emojis of a guild.

        Parameters:
            guild (lefi.Guild): The guild which to create the emojis for.
            data (Dict): The data of the emojis.

        Returns:
            The [lefi.Guild][] instance passed in.

        """
        emojis = {
            int(payload["id"]): Emoji(self, payload, guild)
            for payload in data["emojis"]
        }

        for id, emoji in emojis.items():
            self._emojis[id] = emoji

        guild._emojis = emojis
        return guild

    def create_overwrites(
        self,
        channel: Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel],
    ) -> None:
        if isinstance(channel, DMChannel):
            return

        overwrites = [
            Overwrite(data) for data in channel._data["permission_overwrites"]
        ]
        ows: Dict[Union[Member, Role], Overwrite] = {}

        for overwrite in overwrites:
            if overwrite.type is OverwriteType.MEMBER:
                target = channel.guild.get_member(overwrite.id)

            else:
                target = channel.guild.get_role(overwrite.id)  # type: ignore

            ows[target] = overwrite  # type: ignore

        channel._overwrites = ows
