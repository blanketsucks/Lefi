from __future__ import annotations

from typing import Any

__all__ = ("MISSING",)


class _MISSING:
    def __bool__(self) -> bool:
        return False

    def __eq__(self, other) -> bool:
        return False

    def __len__(self) -> int:
        return 0


MISSING: Any = _MISSING()
