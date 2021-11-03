from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

__all__ = ("Snowflake", "to_snowflake")


class Snowflake(Protocol):
    """
    A class that represents a Snowflake.

    Attributes:
        id (int): The Snowflake ID.
    """

    id: int


def to_snowflake(data: Dict[str, Any], key: str) -> Optional[int]:
    value = data.get(key)
    if not value:
        return None

    return int(value)
