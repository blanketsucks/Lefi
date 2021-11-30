from __future__ import annotations

from typing import Dict

from .enums import OverwriteType
from .flags import Permissions

__all__ = ("Overwrite",)


class Overwrite:
    """Represents an overwrite."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def __repr__(self) -> str:
        return f"<Overwrite id={self.id}>"

    @property
    def id(self) -> int:
        """The id of the overwrite."""
        return int(self._data["id"])

    @property
    def type(self) -> OverwriteType:
        """The overwrite type."""
        return OverwriteType(self._data["type"])

    @property
    def allow(self) -> Permissions:
        """Values of all allowed permissions."""
        return Permissions(int(self._data.get("allow", 0)))

    @property
    def deny(self) -> Permissions:
        """Value of all denied permissions."""
        return Permissions(int(self._data.get("deny", 0)))
