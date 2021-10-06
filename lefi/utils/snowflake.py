from __future__ import annotations

from typing import Protocol

__all__ = ("Snowflake",)


class Snowflake(Protocol):
    id: int
