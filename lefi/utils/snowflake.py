from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

__all__ = ("Snowflake", "Object", "to_snowflake")


class Snowflake(Protocol):
    """
    A class that represents a Snowflake.

    Attributes:
        id (int): The Snowflake ID.
    """

    id: int


class Object(Snowflake):
    """
    A class that represents an object.

    Attributes:
        id (int): The Snowflake ID.

    """

    def __init__(self, id: int) -> None:
        self.id = id

    def __repr__(self) -> str:
        return f"<Object id={self.id}>"


def to_snowflake(data: Dict[str, Any], key: str) -> Optional[int]:
    value = data.get(key)
    if not value:
        return None

    return int(value)
