from __future__ import annotations

from typing import Any, Callable, Coroutine

__all__ = ("Command",)


class Command:
    def __init__(self, name: str, callback: Callable[..., Coroutine]) -> None:
        self.callback = callback
        self.name = name

    async def __call__(self, *args, **kwargs) -> Any:
        return await self.callback(*args, **kwargs)
