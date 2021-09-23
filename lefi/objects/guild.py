from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .channel import Channel
    from ..state import State

__all__ = ("Guild",)


class Guild:
    def __init__(self, state: State, data: typing.Dict):
        self._channels: typing.List[Channel] = []
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Guild id={self.id}>"

    @property
    def id(self) -> int:
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def icon(self) -> str:
        return self._data["icon"]

    @property
    def icon_hash(self) -> str:
        return self._data["icon_hash"]

    @property
    def splash(self) -> str:
        return self._data["splash"]

    @property
    def discovery_splash(self) -> str:
        return self._data["discovery_splash"]

    @property
    def owner(self) -> bool:
        return self._data["owner"]

    @property
    def owner_id(self) -> int:
        return self._data["owner_id"]

    @property
    def channels(self) -> typing.List[Channel]:
        return self._channels
