from __future__ import annotations

import typing

__all__ = ("MISSING",)


class _MISSING:
    def __bool__(self) -> bool:
        return False

    def __eq__(self, other) -> bool:
        return False

    def __len__(self) -> int:
        return 0


MISSING: typing.Any = _MISSING()
