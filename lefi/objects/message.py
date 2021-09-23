from __future__ import annotations

import typing

__all__ = ("Message",)


class Message:
    def __init__(self, data: typing.Dict):
        self._data = data

    @property
    def id(self) -> int:
        return self._data["id"]
