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
    """
    A class representing a Command.

    Attributes:
        checks (List[Callable[..., bool]]): A list of checks to be run before the command is executed.
        parent (Optional[Plugin]): The parent plugin of the command.
        cooldown (Cooldown): The cooldown of the command.
        callback (Callable[..., Coroutine]): The callback of the command.
        name (str): The name of the command.
    """

    def __init__(self, name: str, callback: Callable[..., Coroutine]) -> None:
        """
        Initialize a Command.

        Parameters:
            name (str): The name of the command.
            callback (Callable[..., Coroutine]): The callback of the command.
        """
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
    """
    A decorator to add a check to a command.

    Parameters:
        check (Callable[..., bool]): The check to be added.

    Returns:
        The command with the check added.
    """

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
    """
    A decorator to add a cooldown to a command.

    Parameters:
        uses (int): The amount of uses the cooldown has.
        time (float): The time the cooldown lasts.
        type (CooldownType): The type of the cooldown.

    Returns:
        The command with the cooldown added.
    """

    def inner(func: Union[Command, Coroutine]) -> Union[Command, Coroutine]:
        cooldown = Cooldown(uses, time, type)
        if isinstance(func, Command):
            func.cooldown = cooldown

        elif isinstance(func, Callable):  # type: ignore
            func.cooldown = cooldown  # type: ignore

        return func

    return inner


def command(name: Optional[str] = None) -> Callable[..., Command]:
    """
    A decorator to add a command to a plugin.

    Parameters:
        name (Optional[str]): The name of the command.

    Returns:
        The command with the plugin added.
    """

    def inner(func: Coroutine) -> Command:
        return Command(name or func.__name__, func)  # type: ignore

    return inner
