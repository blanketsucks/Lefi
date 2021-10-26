from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ..objects import Guild, VoiceChannel, User
    from ..state import State

__all__ = ("VoiceState",)


class VoiceState:
    def __init__(self, state: State, data: Dict):
        self._state = state
        self._data = data

    @property
    def user_id(self) -> int:
        return int(self._data["user_id"])

    @property
    def user(self) -> Optional[User]:
        return self._state.get_user(self.user_id)

    @property
    def channel_id(self) -> Optional[int]:
        return int(self._data["channel_id"]) if self._data["channel_id"] else None

    @property
    def channel(self) -> Optional[VoiceChannel]:
        return self._state.get_channel(self.channel_id)  # type: ignore

    @property
    def guild_id(self) -> Optional[int]:
        return int(self._data["guild_id"]) if self._data["guild_id"] else None

    @property
    def guild(self) -> Optional[Guild]:
        return self._state.get_guild(self.guild_id) if self.guild_id else None

    @property
    def session_id(self) -> str:
        return self._data["session_id"]

    @property
    def deaf(self) -> bool:
        return self._data["deaf"]

    @property
    def mute(self) -> bool:
        return self._data["mute"]

    @property
    def self_deaf(self) -> bool:
        return self._data["self_deaf"]

    @property
    def self_mute(self) -> bool:
        return self._data["self_mute"]

    @property
    def self_stream(self) -> bool:
        return self._data.get("self_stream", False)

    @property
    def self_video(self) -> bool:
        return self._data["self_video"]

    @property
    def suppress(self) -> bool:
        return self._data["suppress"]
