from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from ..state import State
    from .message import Message
    from .guild import Guild

__all__ = ("Channel",)


class Channel:
    def __init__(self, state: State, data: typing.Dict):
        self._state = state
        self._data = data

        self._guild: typing.Optional[Guild] = None

    def __repr__(self) -> str:
        return f"<Channel id={self.id}, name={self.name}>"

    async def send(self, content: str) -> Message:
        data = await self._state.client.http.send_message(self.id, content)
        return self._state.create_message(data, self)

    @property
    def id(self) -> int:
        return self._data["id"]

    @property
    def guild(self) -> typing.Optional[Guild]:
        return self._guild

    @property
    def type(self) -> int:
        return self._data["type"]

    @property
    def guild_id(self) -> int:
        return self._data["guild_id"]

    @property
    def position(self) -> int:
        return self._data["position"]

    @property
    def permission_overwrites(self) -> typing.List:
        return self._data["permission_overwrites"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def topic(self) -> str:
        return self._data["topic"]

    @property
    def nsfw(self) -> bool:
        return self._data["nsfw"]

    @property
    def last_message_id(self) -> int:
        return self._data["last_message_id"]

    @property
    def bitrate(self) -> int:
        return self._data["bitrate"]

    @property
    def user_limit(self) -> int:
        return self._data["user_limit"]

    @property
    def rate_limit_per_user(self) -> int:
        return self._data["rate_limit_per_user"]

    @property
    def recipients(self) -> typing.List:
        return self._data["recipients"]

    @property
    def icon(self) -> str:
        return self._data["icon"]

    @property
    def owner_id(self) -> int:
        return self._data["owner_id"]

    @property
    def application_id(self) -> int:
        return self._data["application_id"]

    @property
    def parent_id(self) -> int:
        return self._data["parent_id"]

    @property
    def last_pin_timestamp(self) -> str:
        return self._data["last_pin_timestamp"]

    @property
    def rtc_region(self) -> str:
        return self._data["rtc_region"]

    @property
    def video_quality_mode(self) -> int:
        return self._data["video_quality_mode"]

    @property
    def message_count(self) -> int:
        return self._data["message_count"]

    @property
    def member_count(self) -> int:
        return self._data["member_count"]

    @property
    def default_auto_archive_duration(self) -> int:
        return self._data["default_auto_archive_duration"]

    @property
    def permissions(self) -> str:
        return self._data["permissions"]
