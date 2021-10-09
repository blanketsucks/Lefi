from __future__ import annotations

import asyncio
import collections

from typing import TYPE_CHECKING, Optional, TypeVar, Union, Dict, Any, Type

from .objects import (
    Message,
    Guild,
    TextChannel,
    VoiceChannel,
    User,
    DMChannel,
    CategoryChannel,
    Member,
    Role,
    DeletedMessage,
)
from .objects.channel import Channel

if TYPE_CHECKING:
    from .client import Client

__all__ = (
    "State",
    "Cache",
)

T = TypeVar("T")


class Cache(collections.OrderedDict[Union[str, int], T]):
    def __init__(self, maxlen: Optional[int] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxlen: Optional[int] = maxlen
        self._max: int = 0

    def __repr__(self) -> str:
        return f"<Cache maxlen={self.maxlen}"

    def __setitem__(self, key: Union[str, int], value: T) -> None:
        super().__setitem__(key, value)
        self._max += 1

        if self.maxlen and self._max > self.maxlen:
            self.popitem(False)

class State:
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
        self.client = client
        self.loop = loop
        self.http = client.http

        self._messages = Cache[Message](1000)
        self._users = Cache[User]()
        self._guilds = Cache[Guild]()
        self._channels = Cache[
            Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel]
        ]()

    def dispatch(self, event: str, *payload: Any) -> None:
        events = self.client.events.get(event, [])
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

        for callback in events:
            self.loop.create_task(callback(*payload))

    async def parse_ready(self, data: Dict) -> None:
        user = User(self, data["user"])
        self.dispatch("ready", user)

    async def parse_guild_create(self, data: Dict) -> None:
        guild = Guild(self, data)

        self.create_guild_channels(guild, data)
        self.create_guild_members(guild, data)
        self.create_guild_roles(guild, data)

        self._guilds[guild.id] = guild
        self.dispatch("guild_create", guild)

    async def parse_message_create(self, data: Dict) -> None:
        channel = self._channels.get(int(data["channel_id"]))
        message = Message(self, data, channel)  # type: ignore

        self._messages[message.id] = message
        self.dispatch("message_create", message)

    async def parse_message_delete(self, data: Dict) -> None:
        deleted = DeletedMessage(data)
        message = self._messages.get(deleted.id)

        if message:
            self._messages.pop(message.id)
        else:
            message = deleted  # type: ignore

        self.dispatch("message_delete", message)

    async def parse_message_update(self, data: Dict) -> None:
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

    async def parse_channel_create(self, data: Dict) -> None:
        if guild_id := data.get("guild_id"):
            guild = self.get_guild(int(guild_id))
            channel = self.create_channel(data, guild)
        else:
            channel = self.create_channel(data)

        self._channels[channel.id] = channel
        self.dispatch("channel_create", channel)

    async def parse_channel_update(self, data: Dict) -> None:
        guild = self.get_guild(int(data["guild_id"]))

        before = self.get_channel(int(data["id"]))
        after = self.create_channel(data, guild)

        self._channels[after.id] = after
        self.dispatch("channel_update", before, after)

    async def parse_channel_delete(self, data: Dict) -> None:
        channel = self.get_channel(int(data["id"]))
        self._channels.pop(channel.id)  # type: ignore

        self.dispatch("channel_delete", channel)

    def get_message(self, message_id: int) -> Optional[Message]:
        return self._messages.get(message_id)

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def add_user(self, data: Dict) -> User:
        user = User(self, data)

        self._users[user.id] = user
        return user

    def get_guild(self, guild_id: int) -> Optional[Guild]:
        return self._guilds.get(guild_id)

    def get_channel(
        self, channel_id: int
    ) -> Optional[
        Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel]
    ]:
        return self._channels.get(channel_id)

    def create_message(self, data: Dict, channel: Any) -> Message:
        return Message(self, data, channel)

    def create_channel(
        self, data: Dict, *args
    ) -> Union[TextChannel, VoiceChannel, CategoryChannel, Channel]:
        cls = self.CHANNEL_MAPPING.get(int(data["type"]), Channel)
        return cls(self, data, *args)  # type: ignore

    def create_guild_channels(self, guild: Guild, data: Dict) -> Guild:
        channels = {
            int(payload["id"]): self.create_channel(payload, guild)
            for payload in data["channels"]
        }

        for channel in channels.values():
            self._channels[channel.id] = channel

        guild._channels = channels
        return guild

    def create_guild_members(self, guild: Guild, data: Dict) -> Guild:
        members = {
            int(payload["user"]["id"]): Member(self, payload, guild)
            for payload in data["members"]
        }

        guild._members = members
        return guild

    def create_guild_roles(self, guild: Guild, data: Dict) -> Guild:
        roles = {
            int(payload["id"]): Role(self, payload, guild) for payload in data["roles"]
        }

        guild._roles = roles
        return guild
