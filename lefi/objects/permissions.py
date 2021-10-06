from __future__ import annotations

import typing

from .enums import OverwriteType
from .flags import Permissions


__all__ = ('Overwrite',)

class Overwrite:
    def __init__(self, data: typing.Dict) -> None:
        self._data = data

    @property
    def id(self) -> int:
        return int(self._data['id'])

    @property
    def type(self) -> OverwriteType:
        return OverwriteType(self._data['type'])

    @property
    def allow(self) -> Permissions:
        return Permissions(int(self._data.get('allow', 0)))

    @property
    def deny(self) -> Permissions:
        return Permissions(int(self._data.get('deny', 0)))

    