from __future__ import annotations

from typing import Dict

from .enums import OverwriteType
from .flags import Permissions

__all__ = ("Overwrite",)


class Overwrite:
    """
    Represents an overwrite.
    """

    def __init__(self, data: Dict) -> None:
        self._data = data

    @property
    def id(self) -> int:
        """
        The ID of the overwrite.
        """
        return int(self._data["id"])

    @property
    def type(self) -> OverwriteType:
        """
        The type of the overwrite.
        """
        return OverwriteType(self._data["type"])

    @property
    def allow(self) -> Permissions:
        """
        Value of all allowed permissions.
        """
        return Permissions(int(self._data.get("allow", 0)))

    @property
    def deny(self) -> Permissions:
        """
        Value of all denied permissions.
        """
        return Permissions(int(self._data.get("deny", 0)))
