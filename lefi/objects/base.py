from __future__ import annotations

import dataclasses

from ..http import HTTPClient

__all__ = ("BaseObject",)


@dataclasses.dataclass
class BaseObject:
    http: HTTPClient
    data: dict

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}"

    @property
    def id(self) -> int:
        return self.data["id"]

    @property
    def raw_dict(self) -> dict:
        return self.data
