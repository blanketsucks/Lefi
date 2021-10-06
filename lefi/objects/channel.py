from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Any, List, Dict

from .enums import ChannelType
from .permissions import Overwrite
from .embed import Embed

from ..utils import MISSING

if TYPE_CHECKING:
    from .user import User
    from ..state import State
    from .message import Message
    from .guild import Guild

__all__ = ("TextChannel", "DMChannel", "VoiceChannel", "CategoryChannel", "Channel")


class Channel:
    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        self._state = state
        self._data = data
        self._guild = guild

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} name={self.name!r} id={self.id} position={self.position} type={self.type!r}>"

    @property
    def guild_id(self) -> int:
        return self._guild.id

    @property
    def guild(self) -> Guild:
        return self._guild

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def type(self) -> ChannelType:
        return ChannelType(self._data["type"])

    @property
    def nsfw(self) -> bool:
        return self._data.get("nsfw", False)

    @property
    def position(self) -> int:
        return self._data["position"]

    @property
    def overwrites(self) -> List[Overwrite]:
        return [Overwrite(data) for data in self._data["permission_overwrites"]]


class TextChannel(Channel):
    async def send(
        self, content: str = MISSING, *, embeds: List[Embed] = MISSING
    ) -> Message:
        embeds = [] if embeds is MISSING else embeds

        data = await self._state.client.http.send_message(
            channel_id=self.id,
            content=content,
            embeds=[embed.to_dict() for embed in embeds],
        )
        return self._state.create_message(data, self)

    async def fetch_message(self, message_id: int) -> Message:
        data = await self._state.http.get_channel_message(self.id, message_id)
        return self._state.create_message(data, self)

    @property
    def topic(self) -> str:
        return self._data["topic"]

    @property
    def last_message_id(self) -> int:
        return int(self._data["last_message_id"])

    @property
    def last_message(self) -> Optional[Message]:
        return self._state.get_message(self.last_message_id)

    @property
    def rate_limit_per_user(self) -> int:
        return self._data["rate_limit_per_user"]

    @property
    def default_auto_archive_duration(self) -> int:
        return self._data["default_auto_archive_duration"]

    @property
    def parent_id(self) -> int:
        return self._data["parent_id"]

    @property
    def parent(self):
        return self.guild.get_channel(self.parent_id)


class VoiceChannel(Channel):
    @property
    def user_limit(self) -> int:
        return self._data["user_limit"]

    @property
    def bitrate(self) -> int:
        return self._data["bitrate"]

    @property
    def rtc_region(self) -> Optional[str]:
        return self._data["rtc_region"]

    @property
    def parent_id(self) -> int:
        return self._data["parent_id"]

    @property
    def parent(self):
        return self.guild.get_channel(self.parent_id)


class CategoryChannel(Channel):
    pass


class DMChannel:
    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        self._state = state
        self._data = data

        self.guild = None

    def __repr__(self) -> str:
        return f"<DMChannel id={self.id} type={self.type!r}>"

    async def send(
        self, content: str = MISSING, *, embeds: List[Embed] = MISSING
    ) -> Message:
        embeds = [] if embeds is MISSING else embeds

        data = await self._state.client.http.send_message(
            channel_id=self.id,
            content=content,
            embeds=[embed.to_dict() for embed in embeds],
        )
        return self._state.create_message(data, self)

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def last_message_id(self) -> int:
        return int(self._data["last_message_id"])

    @property
    def last_message(self) -> Optional[Message]:
        return self._state.get_message(self.last_message_id)

    @property
    def type(self) -> int:
        return int(self._data["type"])

    @property
    def receipients(self) -> List[User]:
        return [self._state.get_user(int(data["id"])) for data in self._data["recipients"]]  # type: ignore
