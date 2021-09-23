from __future__ import annotations

import typing

__all__ = ("Snowflake",)


class Snowflake(typing.Protocol):
    id: int
