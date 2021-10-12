from __future__ import annotations

from typing import Any, Callable, Coroutine, Union

__all__ = (
    "Command",
    "check",
)


class Command:
    def __init__(self, name: str, callback: Callable[..., Coroutine]) -> None:
        self.check: Callable = callback._check or (lambda _: True)
        self.callback = callback
        self.name = name

    def __repr__(self) -> str:
        return f"<Command name{self.name!r}>"

    def __str__(self) -> str:
        return self.name

    async def __call__(self, *args, **kwargs) -> Any:
        return await self.callback(*args, **kwargs)


def check(check: Callable[..., bool]) -> Callable[..., Union[Command, Coroutine]]:
    def inner(func: Union[Command, Coroutine]) -> Union[Command, Coroutine]:
        if isinstance(func, Command):
            func.check = check

        elif isinstance(func, Coroutine):
            func.check = check  # type: ignore

        return func

    return inner
