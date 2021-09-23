from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .channel import Channel
    from .guild import Guild
    from ..state import State

__all__ = ("Message",)


class Message:
    def __init__(self, state: State, data: typing.Dict, channel: Channel):
        self._channel = channel
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Message id={self.id}>"

    @property
    def id(self) -> int:
        return self._data["id"]

    @property
    def channel(self) -> typing.Optional[Channel]:
        return self._channel

    @property
    def guild(self) -> typing.Optional[Guild]:
        return self._channel.guild

    @property
    def content(self) -> str:
        return self._data["content"]
