from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine, List, Optional, Union

from .cooldowns import Cooldown, CooldownType

if TYPE_CHECKING:
    from .plugin import Plugin

__all__ = (
    "Command",
    "check",
    "cooldown",
    "command",
)


class Command:
    def __init__(self, name: str, callback: Callable[..., Coroutine]) -> None:
        self.checks: List[Callable[..., bool]] = []
        self.parent: Optional[Plugin] = None
        self.cooldown: Cooldown
        self.callback = callback
        self.name = name

        if hasattr(self.callback, "check"):
            self.checks.append(self.callback.check)  # type: ignore

        elif hasattr(self.callback, "cooldown"):
            self.cooldown = self.callback.cooldown  # type: ignore

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

        elif isinstance(func, Callable):  # type: ignore
            func.check = check  # type: ignore

        return func

    return inner


def cooldown(
    uses: int, time: float, type: CooldownType
) -> Callable[..., Union[Command, Coroutine]]:
    def inner(func: Union[Command, Coroutine]) -> Union[Command, Coroutine]:
        cooldown = Cooldown(uses, time, type)
        if isinstance(func, Command):
            func.cooldown = cooldown

        elif isinstance(func, Callable):  # type: ignore
            func.cooldown = cooldown  # type: ignore

        return func

    return inner


def command(name: Optional[str] = None) -> Callable[..., Command]:
    def inner(func: Coroutine) -> Command:
        return Command(name or func.__name__, func)  # type: ignore

    return inner
