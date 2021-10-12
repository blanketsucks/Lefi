from __future__ import annotations

from typing import Any, Callable, Coroutine, Union, List

__all__ = (
    "Command",
    "check",
)


class Command:
    def __init__(self, name: str, callback: Callable[..., Coroutine]) -> None:
        self.checks: List[Callable[..., bool]] = []
        self.callback = callback
        self.name = name

        if hasattr(self.callback, "check"):
            self.checks.append(self.callback.check)

    def __repr__(self) -> str:
        return f"<Command name{self.name!r}>"

    def __str__(self) -> str:
        return self.name

    async def __call__(self, *args, **kwargs) -> Any:
        return await self.callback(*args, **kwargs)


def check(check: Callable[..., bool]) -> Callable[..., Union[Command, Coroutine]]:
    def inner(func: Union[Command, Coroutine]) -> Union[Command, Coroutine]:
        if isinstance(func, Command):
            func.checks.append(check)

        elif isinstance(func, Callable):
            func.check = check  # type: ignore

        return func

    return inner
