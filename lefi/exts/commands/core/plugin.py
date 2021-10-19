from __future__ import annotations

from typing import (
    Dict,
    Type,
    Tuple,
    TYPE_CHECKING,
    ClassVar,
    Coroutine,
    Callable,
    Optional,
    Protocol,
    List,
    Any,
)

import functools
import inspect

from .command import Command

if TYPE_CHECKING:
    from ..bot import Bot

__all__ = ("Plugin",)


class PluginMeta(type):
    __commands__: Dict[str, Command]
    __listeners__: Dict[str, List[Tuple[Coroutine, bool]]]

    def __new__(
        cls: Type[PluginMeta], name: str, bases: Tuple[Type], attrs: Dict
    ) -> PluginMeta:
        commands: Dict[str, Command] = {}
        listeners: Dict[str, List[Tuple[Coroutine, bool]]] = {}

        for attr, value in attrs.copy().items():
            if isinstance(value, Command):
                commands[attr] = value

            elif inspect.iscoroutinefunction(value):
                if data := getattr(value, "__listener_data__", None):
                    name, func, overwrite = data
                    callbacks = listeners.setdefault(name, [])
                    callbacks.append((func, overwrite))

        attrs["__commands__"] = commands
        attrs["__listeners__"] = listeners
        return super().__new__(cls, name, bases, attrs)

    @staticmethod
    def on(name: Optional[str] = None, overwrite: bool = False) -> Callable[..., Coroutine]:
        def inner(func: Coroutine) -> Coroutine:
            func.__listener_data__ = (name or func.__name__, func, overwrite)  # type: ignore
            return func
        return inner


class Plugin(metaclass=PluginMeta):
    __listeners__: ClassVar[Dict[str, List[Tuple[Coroutine, bool]]]]
    __commands__: ClassVar[Dict[str, Command]]

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    def _attach_commands(self, bot: Bot) -> None:
        for name, command in self.__commands__.items():
            command.parent = self
            self.bot.commands[name] = command

        for event, callback in self.__listeners__.items():
            for listener_data in callback:
                func, overwrite = listener_data
                self.bot.add_listener(functools.partial(func, self), event, overwrite)  # type: ignore
