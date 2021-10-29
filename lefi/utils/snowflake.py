from __future__ import annotations

from typing import Protocol

__all__ = ("Snowflake",)


class Snowflake(Protocol):
    """
    A class that represents a Snowflake.

    Attributes:
        id (int): The Snowflake ID.
    """

    id: int
