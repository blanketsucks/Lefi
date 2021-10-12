from __future__ import annotations

from typing import Any, Callable, Coroutine

__all__ = ("Command",)


class Command:
    def __init__(self, name: str, callback: Callable[..., Coroutine]) -> None:
        self.callback = callback
        self.name = name

    def __repr__(self) -> str:
        return f"<Command name{self.name!r}>"

    def __str__(self) -> str:
        return self.name

    async def __call__(self, *args, **kwargs) -> Any:
        return await self.callback(*args, **kwargs)
