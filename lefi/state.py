from __future__ import annotations

import typing
import collections

import asyncio


from .objects import ( 
    Message,
    Guild,
    TextChannel,
    VoiceChannel,
    Guild,
    User,
    DMChannel,
    CategoryChannel,
    Member,
    Role,
    DeletedMessage
)
from .objects.channel import Channel
from .utils import MISSING

if typing.TYPE_CHECKING:
    from .client import Client

__all__ = (
    "State",
    "Cache",
)

T = typing.TypeVar("T")


class Cache(collections.OrderedDict[typing.Union[str, int], T]):
    def __init__(self, maxlen: typing.Optional[int] = MISSING, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxlen: typing.Optional[int] = maxlen
        self._max: int = 0

    def __repr__(self) -> str:
        return f"<Cache maxlen={self.maxlen}"

    def __setitem__(self, key: typing.Union[str, int], value: T) -> None:
        super().__setitem__(key, value)
        self._max += 1

        if self.maxlen and self._max > self.maxlen:
            self.popitem(False)

class State:
    def __init__(self, client: Client, loop: asyncio.AbstractEventLoop):
        self.client = client
        self.loop = loop
        self.http = client.http

        self._messages = Cache[Message](1000)
        self._guilds = Cache[Guild]()
        self._channels = Cache[typing.Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel]]()
        self._users = Cache[User]()

        self._channel_mapping = {
            0: TextChannel,
            1: DMChannel,
            2: VoiceChannel,
            3: CategoryChannel
        }

    def dispatch(self, event: str, *payload: typing.Any) -> None:
        events = self.client.events.get(event, [])
        futures = self.client.futures.get(event, [])

        for (future, check) in futures:
            if check(*payload):
                future.set_result(*payload)
                futures.remove((future, check))

                break

        for callback in events:
            self.loop.create_task(callback(*payload))
                
    async def parse_guild_create(self, data: typing.Dict) -> None:
        guild = Guild(self, data)

        self.create_guild_channels(guild, data)
        self.create_guild_members(guild, data)
        self.create_guild_roles(guild, data)

        self._guilds[guild.id] = guild
        self.dispatch("guild_create", guild)

    async def parse_message_create(self, data: typing.Dict) -> None:
        channel = self._channels.get(int(data["channel_id"]))
        message = Message(self, data, channel)

        self._messages[message.id] = message
        self.dispatch("message_create", message)

    async def parse_message_delete(self, data: typing.Dict) -> None:
        deleted = DeletedMessage(data)
        message = self._messages.get(deleted.id)

        if message:
            self._messages.pop(message.id)
        else:
            message = deleted

        self.dispatch("message_delete", message)

    async def parse_message_update(self, data: typing.Dict) -> None:
        channel = self.get_channel(int(data["channel_id"]))
        if not channel:
            return

        after = self.create_message(data, channel)

        if not (before := self.get_message(after.id)):
            msg = await self.http.get_channel_message(channel.id, after.id)
            before = self.create_message(msg, channel)
        else:
            self._messages.pop(before.id)

        self._messages[after.id] = after
        self.dispatch("message_update", before, after)

    async def parse_channel_create(self, data: typing.Dict) -> None:
        if guild_id := data.get('guild_id'):
            guild = self.get_guild(int(guild_id))
            channel = self.create_channel(data, guild)
        else:
            channel = self.create_channel(data)

        self._channels[channel.id] = channel
        self.dispatch("channel_create", channel)

    async def parse_channel_update(self, data: typing.Dict) -> None:
        guild = self.get_guild(int(data["guild_id"]))

        before = self.get_channel(int(data["id"]))
        after = self.create_channel(data, guild)

        self._channels[after.id] = after
        self.dispatch("channel_update", before, after)

    async def parse_channel_delete(self, data: typing.Dict) -> None:
        channel = self.get_channel(int(data["id"]))
        self._channels.pop(channel.id)

        self.dispatch("channel_delete", channel)

    def get_message(self, message_id: int) -> typing.Optional[Message]:
        return self._messages.get(message_id)

    def get_user(self, user_id: int) -> typing.Optional[User]:
        return self._users.get(user_id)

    def add_user(self, data: typing.Dict) -> User:
        user = User(self, data)

        self._users[user.id] = user
        return user

    def get_guild(self, guild_id: int) -> typing.Optional[Guild]:
        return self._guilds.get(guild_id)

    def get_channel(self, channel_id: int) -> typing.Optional[
        typing.Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel]]:
        return self._channels.get(channel_id)

    def create_message(self, data: typing.Dict, channel: typing.Any) -> Message:
        return Message(self, data, channel)

    def create_channel(self, data: typing.Dict, *args) -> typing.Union[TextChannel, VoiceChannel, CategoryChannel, Channel]:
        cls = self._channel_mapping.get(int(data["type"]), Channel)
        return cls(self, data, *args)
    
    def create_guild_channels(self, guild: Guild, data: typing.Dict) -> Guild:
        channels = {
            int(payload['id']): self.create_channel(payload, guild)
            for payload in data['channels']
        }

        for channel in channels.values():
            self._channels[channel.id] = channel

        guild._channels = channels
        return guild

    def create_guild_members(self, guild: Guild, data: typing.Dict) -> Guild:
        members = {
            int(payload['user']['id']): Member(self, payload, guild)
            for payload in data['members']
        }

        guild._members = members
        return guild

    def create_guild_roles(self, guild: Guild, data: typing.Dict) -> Guild:
        roles = {
            int(payload['id']): Role(self, payload, guild)
            for payload in data['roles']
        }

        guild._roles = roles
        return guild
