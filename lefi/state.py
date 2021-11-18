from __future__ import annotations

import asyncio
import collections
from functools import cached_property
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    List,
)

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
    Channel,
    Thread,
    ThreadMember,
    Interaction,
    Component,
    InteractionType,
    ComponentType,
    Integration,
    DeletedIntegration,
    Invite,
    DeletedInvite,
    Sticker,
)
from .voice import VoiceClient, VoiceState

if TYPE_CHECKING:
    from .client import Client
    from .ws import BaseWebsocketClient

__all__ = (
    "State",
    "Cache",
)

T = TypeVar("T")

logger = logging.getLogger(__name__)


class Chunk:
    def __init__(self, state: State, data: Dict) -> None:
        self._state = state
        self._data = data

    @property
    def guild_id(self) -> int:
        return int(self._data["guild_id"])

    @property
    def guild(self) -> Guild:
        return self._state.get_guild(self.guild_id)  # type: ignore

    @cached_property
    def members(self) -> List[Member]:
        return [self._state.create_member(m, self.guild) for m in self._data["members"]]

    @property
    def index(self) -> int:
        return self._data["chunk_index"]

    @property
    def count(self) -> int:
        return self._data["chunk_count"]

    @property
    def not_found(self) -> List[int]:
        return self._data.get("not_found", [])

    @property
    def nonce(self) -> Optional[str]:
        return self._data.get("nonce")


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
        client (lefi.Client): The [lefi.Client](./client.md) instance being used.
        loop (asyncio.AbstractEventLoop): The asyncio.AbstractEventLoop being used.
        http (lefi.HTTPClient): The [lefi.HTTPClient](./http.md) handling requests

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
        5: TextChannel,
    }

    def __init__(self, client: Client, loop: asyncio.AbstractEventLoop) -> None:
        """
        Parameters:
            client (lefi.Client): The [Client](./client.md) being used.
            loop (asyncio.AbstractEventLoop): The asyncio.AbstractEventLoop being used.

        """
        self.client = client
        self.loop = loop
        self.http = client.http
        self._messages = Cache[Message](1000)
        self._users = Cache[User]()
        self._guilds = Cache[Guild]()
        self._emojis = Cache[Emoji]()
        self._components = Cache[Tuple[Callable, Component]]()
        self._channels = Cache[
            Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel]
        ]()
        self._emojis = Cache[Emoji]()
        self._voice_clients = Cache[VoiceClient]()
        self._stickers = Cache[Sticker]()

    @property
    def user(self) -> User:
        return self.client.user

    def get_websocket(self, guild_id: int) -> BaseWebsocketClient:
        if not self.client.shards:
            return self.client.ws

        shard_id = (guild_id >> 22) % len(self.client.shards)
        return self.client.shards[shard_id]

    def dispatch(self, event: str, *payload: Any) -> None:
        """
        Dispatches data to callbacks registered to events after parsing is finished.

        Parameters:
            event (str): The name of the event to dispatch to.
            *payload (Any): The data after parsing is finished.

        """
        events: Optional[dict] = self.client.events.get(event)
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

        if events is not None:
            for callback in events.values():
                self.loop.create_task(callback(*payload))

    async def parse_interaction_create(self, data: Dict) -> None:
        interaction: Interaction = Interaction(
            self, data, type=InteractionType(data["type"])
        )

        if interaction.type is InteractionType.COMPONENT:
            if component := self._components.get(data["data"]["custom_id"]):
                callback, instance = component

                if int(data["data"]["component_type"]) == int(ComponentType.SELECTMENU):
                    instance.values = data["data"]["values"]  # type: ignore

                await callback(interaction, instance)

        elif interaction.type is InteractionType.COMMAND:
            if command := self.client.application_commands.get(data["data"]["name"]):
                arguments = []

                if options := data["data"].get("options"):
                    arguments.extend(await command.parser.create_arguments(options))

                await command.callback(interaction, *arguments)

        self.dispatch("interaction_create", interaction)

    async def parse_ready(self, data: Dict) -> None:
        """
        Parses the `READY` event. Creates a User then dispatches it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        user = self.add_user(data["user"])
        self.client.user = user

        if shard := data.get("shard"):
            logger.info(f"CONNECTED: SHARD ID: {shard[0]}")
        else:
            logger.info(f"CONNECTED: CLIENT ID: {user.id}")

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
        self.create_guild_emojis(guild, data)
        self.create_guild_voice_states(guild, data)
        self.create_guild_stickers(guild, data)

        self._guilds[guild.id] = guild
        self.dispatch("guild_create", guild)

    async def parse_guild_update(self, data: Dict) -> None:
        """
        Parses `GUILD_UPDATE` event. Updates a Guild then dispatches it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["id"]))
        if not guild:
            return

        before, after = self.update_guild(guild, data)
        self.dispatch("guild_update", before, after)

    async def parse_guild_delete(self, data: Dict) -> None:
        """
        Parses `GUILD_DELETE` event. Deletes a Guild then dispatches it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["id"]))
        if not guild:
            return

        self.dispatch("guild_delete", guild)
        self._guilds.pop(guild.id)

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
        channel = self.get_channel(int(data["id"]))
        if not channel:
            return

        before, after = self.update_channel(channel, data)  # type: ignore
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

    async def parse_voice_state_update(self, data: Dict) -> None:
        """
        Parses `VOICE_STATE_UPDATE` event. Creates a VoiceState then caches it, as well as dispatching it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        after = VoiceState(self, data)

        if after.guild:
            if after.user_id == self.client.user.id:
                voice = self.get_voice_client(after.guild.id)
                if voice:
                    await voice.voice_state_update(data)

            before = after.guild.get_voice_state(after.user_id)
            if not before:
                after.guild._voice_states[after.user_id] = after
            else:
                if not after.channel:
                    after.guild._voice_states.pop(after.user_id)
                else:
                    before._data = after._data

            self.dispatch("voice_state_update", before, after)

    async def parse_voice_server_update(self, data: Dict):
        guild_id = int(data["guild_id"])
        voice = self.get_voice_client(guild_id)

        if voice:
            await voice.voice_server_update(data)

    async def parse_thread_create(self, data: Dict) -> None:
        """
        Parses `THREAD_CREATE` event. Creates a Thread then caches it, as well as dispatching it afterwards.

        Parameters:
            data (Dict): The raw data.

        """
        guild_id = int(data["guild_id"])
        guild = self.get_guild(guild_id)

        if not guild:
            return

        thread = Thread(self, guild, data)
        guild._threads[thread.id] = thread

        self.dispatch("thread_create", thread)

    async def parse_thread_update(self, data: Dict) -> None:
        """
        Parses `THREAD_UPDATE` event. Dispatches `before` and `after`.

        Parameters:
            data (Dict): The raw data.

        """
        guild_id = int(data["guild_id"])
        guild = self.get_guild(guild_id)

        if not guild:
            return

        thread_id = int(data["id"])
        thread = guild.get_thread(thread_id)

        if not thread:
            return

        before, after = self.update_thread(thread, data)
        self.dispatch("thread_update", before, after)

    async def parse_thread_delete(self, data: Dict) -> None:
        """
        Parses `THREAD_DELETE` event. Dispatches the deleted thread.

        Parameters:
            data (Dict): The raw data.

        """
        guild_id = int(data["guild_id"])
        guild = self.get_guild(guild_id)

        if not guild:
            return

        thread_id = int(data["id"])
        thread = guild.get_thread(thread_id)

        if not thread:
            return

        guild._threads.pop(thread.id)
        self.dispatch("thread_delete", thread)

    async def parse_thread_list_sync(self, data: Dict) -> None:
        """
        Parses `THREAD_LIST_SYNC` event.
        Dispatches the created threads under `THREAD_CREATE` and the removed ones under `THREAD_DELETE`.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        channel_ids = data.get("channel_ids")
        if not channel_ids:
            previous = guild._threads.copy()
            guild._threads.clear()
        else:
            previous = {
                t.id: t for t in guild._threads.values() if t.parent_id in channel_ids
            }
            for thread_id in previous:
                del guild._threads[thread_id]

        threads = {
            int(d["id"]): Thread(self, guild, d) for d in data.get("threads", [])
        }
        guild._threads.update(threads)

        for member in data.get("members", []):
            thread = threads.get(int(member["id"]))
            if thread:
                thread._create_member(member)

        for thread in threads.values():
            self.dispatch("thread_create", thread)

        for thread in previous.values():
            self.dispatch("thread_delete", thread)

    async def parse_thread_members_update(self, data: Dict) -> None:
        """
        Parses `THREAD_MEMBERS_UPDATE` event.
        Dispatches the added thread members under `thread_member_add` and the removed ones
        under `thread_member_remove`.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        thread = guild.get_thread(int(data["id"]))
        if not thread:
            return

        new: List[ThreadMember] = [
            ThreadMember(self, m, thread) for m in data.get("added_members", [])
        ]
        removed: List[int] = [int(id) for id in data.get("removed_member_ids", [])]

        for member in new:
            thread._members[member.id] = member
            self.dispatch("thread_member_add", member)

        for member_id in removed:
            member = thread._members.pop(member_id, None)  # type: ignore
            if member:
                self.dispatch("thread_member_remove", member)

    async def parse_channel_pins_update(self, data: Dict) -> None:
        """
        Parses the `CHANNEL_PINS_UPDATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        channel = self.get_channel(int(data["channel_id"]))
        if not channel:
            return

        self.dispatch("channel_pins_update", channel)

    async def parse_guild_ban_add(self, data: Dict) -> None:
        """
        Parses the `GUILD_BAN_ADD` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        user = self.create_user(data["user"])
        guild._members.pop(user.id, None)

        self.dispatch("guild_ban_add", guild, user)

    async def parse_guild_ban_remove(self, data: Dict) -> None:
        """
        Parses the `GUILD_BAN_REMOVE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        user = self.create_user(data["user"])
        self.dispatch("guild_ban_remove", guild, user)

    async def parse_guild_emojis_update(self, data: Dict) -> None:
        """
        Parses the `GUILD_EMOJIS_UPDATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        emojis = {int(e["id"]): Emoji(self, e, guild) for e in data.get("emojis", [])}

        guild._emojis.update(emojis)
        self.dispatch("guild_emojis_update", guild, emojis.values())

    async def parse_guild_intergration_update(self, data: Dict) -> None:
        """
        Parses the `GUILD_INTEGRATIONS_UPDATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        self.dispatch("guild_integrations_update", guild)

    async def parse_guild_member_add(self, data: Dict) -> None:
        """
        Parses the `GUILD_MEMBER_ADD` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        member = Member(self, data, guild)
        guild._members[member.id] = member

        self.dispatch("guild_member_add", member)

    async def parse_guild_member_remove(self, data: Dict) -> None:
        """
        Parses the `GUILD_MEMBER_REMOVE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        user = self.create_user(data["user"])
        guild._members.pop(user.id, None)

        self.dispatch("guild_member_remove", guild, user)

    async def parse_guild_member_update(self, data: Dict) -> None:
        """
        Parses the `GUILD_MEMBER_UPDATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        member = guild.get_member(int(data["user"]["id"]))
        if member is None:
            return

        after = self.create_member(data, guild)

        guild._members[member.id] = after
        self.dispatch("guild_member_update", member, after)

    async def parse_guild_members_chunk(self, data: Dict) -> None:
        """
        Parses the `GUILD_MEMBERS_CHUNK` event.

        Parameters:
            data (Dict): The raw data.

        """
        chunk = Chunk(self, data)

        for member in chunk.members:
            chunk.guild._members[member.id] = member

        self.dispatch("guild_members_chunk", chunk)

    async def parse_guild_role_create(self, data: Dict) -> None:
        """
        Parses the `GUILD_ROLE_CREATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        role = Role(self, data, guild)
        guild._roles[role.id] = role

        self.dispatch("guild_role_create", role)

    async def parse_guild_role_update(self, data: Dict) -> None:
        """
        Parses the `GUILD_ROLE_UPDATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        role = guild.get_role(int(data["role"]["id"]))
        if role is None:
            return

        before = role._copy()
        role._data = data["role"]

        self.dispatch("guild_role_update", before, role)

    async def parse_guild_role_delete(self, data: Dict) -> None:
        """
        Parses the `GUILD_ROLE_DELETE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        role_id = int(data["role_id"])
        role = guild._roles.pop(role_id, None)
        if role is None:
            return

        self.dispatch("guild_role_delete", role)

    async def parse_integration_create(self, data: Dict) -> None:
        """
        Parses the `INTEGRATION_CREATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        integration = Integration(self, data, guild)
        self.dispatch("integration_create", integration)

    async def parse_integration_update(self, data: Dict) -> None:
        """
        Parses the `INTEGRATION_UPDATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        integration = Integration(self, data, guild)
        self.dispatch("integration_update", integration)

    async def parse_integration_delete(self, data: Dict) -> None:
        """
        Parses the `INTEGRATION_DELETE` event.

        Parameters:
            data (Dict): The raw data.

        """
        guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            return

        integration = DeletedIntegration(self, data, guild)
        self.dispatch("integration_delete", integration)

    async def parse_invite_create(self, data: Dict) -> None:
        """
        Parses the `INVITE_CREATE` event.

        Parameters:
            data (Dict): The raw data.

        """
        invite = Invite(self, data)
        self.dispatch("invite_create", invite)

    async def parse_invite_delete(self, data: Dict) -> None:
        """
        Parses the `INVITE_DELETE` event.

        Parameters:
            data (Dict): The raw data.

        """
        invite = DeletedInvite(self, data)
        self.dispatch("invite_delete", invite)

    async def parse_message_delete_bulk(self, data: Dict) -> None:
        """
        Parses the `MESSAGE_DELETE_BULK` event.

        Parameters:
            data (Dict): The raw data.

        """
        messages = []
        for message_id in data["ids"]:

            message = self._messages.pop(message_id, None)
            if not message:
                d = data.copy()
                d["id"] = message_id

                message = DeletedMessage(d)  # type: ignore

            messages.append(message)

        self.dispatch("message_delete_bulk", messages)

    def get_message(self, message_id: int) -> Optional[Message]:
        """
        Grabs a message from the cache.

        Parameters:
            message_id (int): The ID of the message.

        Returns:
            The [lefi.Message](./message.md) insance corresponding to the ID if found.

        """
        return self._messages.get(message_id)

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Grabs a user from the cache.

        Parameters:
            user_id (int): The ID of the user.

        Returns:
            The [lefi.User](./user.md) instance corresponding to the ID if found.

        """
        return self._users.get(user_id)

    def add_user(self, data: Dict) -> User:
        """
        Creates a user then caches it.

        Parameters:
            data (Dict): The data of the user.

        Returns:
            The created [lefi.User](./user.md) instance.

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
            The [lefi.Guild](./guild.md) instance corresponding to the ID if found.

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
            The [lefi.Emoji](./emoji.md) instance corresponding to the ID if found.

        """
        return self._emojis.get(emoji_id)

    def create_message(self, data: Dict, channel: Any) -> Message:
        """
        Creates a Message instance.

        Parameters:
            data (Dict): The data of the message.
            channel (Any): The [Channel](./channel.md) of the message.

        Returns:
            The created [lefi.Message](./message.md) instance.

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
            The created [lefi.Channel](./channel.md) instance.

        """
        cls = self.CHANNEL_MAPPING.get(int(data["type"]), Channel)
        channel = cls(self, data, *args)

        self.create_overwrites(channel)
        return channel  # type: ignore

    def create_guild_channels(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the channels of a guild.

        Parameters:
            guild (lefi.Guild): The [Guild](./guild.md) which to create the channels for.
            data (Dict): The data of the channels.

        Returns:
            The [lefi.Guild](./guild.md) instance passed in.

        """
        if "channels" not in data:
            return guild

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
            guild (lefi.Guild): The [Guild](./guild.md) which to create the channels for.
            data (Dict): The data of the members.

        Returns:
            The [lefi.Guild](./guild.md) instance passed in.

        """
        if "members" not in data:
            return guild

        members: Dict[int, Member] = {}
        for member_data in data["members"]:
            member = self.create_member(member_data, guild)
            members[member.id] = member

        guild._members = members
        return guild

    def create_guild_roles(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the roles of a guild.

        Parameters:
            guild (lefi.Guild): The [Guild](./guild.md) which to create the channels for.
            data (Dict): The data of the roles.

        Returns:
            The [lefi.Guild][] instance passed in.

        """
        if "roles" not in data:
            return guild

        roles = {
            int(payload["id"]): Role(self, payload, guild) for payload in data["roles"]
        }
        guild._roles = roles
        return guild

    def create_guild_emojis(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the emojis of a guild.

        Parameters:
            guild (lefi.Guild): The [Guild](./guild.md) which to create the emojis for.
            data (Dict): The data of the emojis.

        Returns:
            The [lefi.Guild][] instance passed in.

        """
        if "emojis" not in data:
            return guild

        emojis = {
            int(payload["id"]): Emoji(self, payload, guild)
            for payload in data["emojis"]
        }

        for id, emoji in emojis.items():
            self._emojis[id] = emoji

        guild._emojis = emojis
        return guild

    def create_guild_voice_states(self, guild: Guild, data: Dict) -> Guild:
        """
        Creates the voice states of a guild.

        Parameters:
            guild (lefi.Guild): The guild which to create the voice states for.
            data (Dict): The data of the voice states.

        Returns:
            The [lefi.Guild][] instance passed in.

        """
        voice_states = {
            int(payload["user_id"]): VoiceState(self, payload)
            for payload in data["voice_states"]
        }

        guild._voice_states = voice_states
        return guild

    def create_guild_stickers(self, guild: Guild, data: Dict) -> Guild:
        payload = data.get("stickers")
        if not payload:
            return guild

        stickers = {int(sticker["id"]): Sticker(self, sticker) for sticker in payload}

        self._stickers.update(stickers)  # type: ignore
        guild._stickers = stickers

        return guild

    def get_sticker(self, sticker_id: int) -> Optional[Sticker]:
        """
        Grabs a sticker from the cache.

        Returns:
            The [lefi.Sticker](./sticker.md) instance corresponding to the ID if found.

        """
        return self._stickers.get(sticker_id)

    def create_overwrites(
        self,
        channel: Union[TextChannel, DMChannel, VoiceChannel, CategoryChannel, Channel],
    ) -> None:
        """
        Creates the overwrites of a channel.

        Parameters:
            channel (lefi.Channel): The [Channel](./channel.md) which to create the overwrites for.
        """
        if isinstance(channel, DMChannel):
            return

        if "permission_overwrites" not in channel._data:
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

    def update_guild(self, guild: Guild, data: Dict):
        before = guild._copy()

        self.create_guild_channels(guild, data)
        self.create_guild_roles(guild, data)
        self.create_guild_members(guild, data)
        self.create_guild_emojis(guild, data)
        self.create_guild_voice_states(guild, data)
        self.create_guild_stickers(guild, data)

        guild._data = data
        return before, guild

    def update_channel(self, channel: Channel, data: Dict):
        before = channel._copy()

        channel._data = data
        self.create_overwrites(channel)

        return before, channel

    def update_thread(self, thread: Thread, data: Dict):
        before = thread._copy()
        thread._data = data

        if metadata := data.get("metadata"):
            thread._metadata = metadata

        return before, thread

    def add_voice_client(self, guild_id: int, voice_client: VoiceClient) -> None:
        """
        Adds a voice client to the cache.

        Parameters:
            guild_id (int): The ID of the guild.
            voice_client (lefi.VoiceClient): The voice client to add.

        """
        self._voice_clients[guild_id] = voice_client

    def get_voice_client(self, guild_id: int) -> Optional[VoiceClient]:
        """
        Grabs a voice client from the cache.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The [lefi.VoiceClient][] instance corresponding to the ID if found.

        """
        return self._voice_clients.get(guild_id)

    def remove_voice_client(self, guild_id: int) -> None:
        """
        Removes a voice client from the cache.

        Parameters:
            guild_id (int): The ID of the guild.

        """
        self._voice_clients.pop(guild_id, None)

    def create_member(self, data: Dict, guild: Guild) -> Member:
        member = Member(self, data, guild)

        for role_data in data["roles"]:
            role = guild.get_role(int(role_data))
            member._roles.setdefault(role.id, role)  # type: ignore

        return member

    def create_user(self, data: Dict) -> User:
        return User(self, data)
