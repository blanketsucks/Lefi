from __future__ import annotations

from typing import TYPE_CHECKING, Union, Dict, Optional

from ..utils import Snowflake

if TYPE_CHECKING:
    from .channel import TextChannel, DMChannel
    from .guild import Guild
    from ..state import State

    from .user import User
    from .member import Member

    Channels = Union[TextChannel, DMChannel]

__all__ = ("Message", "DeletedMessage")


class DeletedMessage:
    def __init__(self, data: Dict) -> None:
        self.id: int = int(data["id"])
        self.channel_id: int = int(data["channel_id"])
        self.guild_id: Optional[int] = int(data["guild_id"]) if "guild_id" in data else None


class Message:
    def __init__(self, state: State, data: Dict, channel: Channels):
        self._channel = channel
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Message id={self.id}>"

    @property
    def id(self) -> int:
        return self._data["id"]

    @property
    def channel(self) -> Channels:
        return self._channel

    @property
    def guild(self) -> Optional[Guild]:
        return self._channel.guild

    @property
    def content(self) -> str:
        return self._data["content"]

    @property
    def author(self) -> Union[User, Member]:
        guild = self.guild
        if guild is None:
            return self._state.get_user(int(self._data["author"]["id"]))  # type: ignore

        return guild.get_member(int(self._data["author"]["id"]))  # type: ignore

    async def crosspost(self) -> Message:
        data = await self._state.http.crosspost_message(self.channel.id, self.id)
        return self._state.create_message(data, self.channel)

    async def add_reaction(self, reaction: str) -> None:
        await self._state.http.create_reaction(channel_id=self.channel.id, message_id=self.id, emoji=reaction)

    async def remove_reaction(self, reaction: str, user: Snowflake = None) -> None:
        await self._state.http.delete_reaction(
            channel_id=self.channel.id,
            message_id=self.id,
            emoji=reaction,
            user_id=user.id if user is not None else user,
        )

    async def delete(self) -> None:
        await self._state.http.delete_message(self.channel.id, self.id)
        self._state._messages.pop(self.id, None)
