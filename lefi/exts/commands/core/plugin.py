from __future__ import annotations

from typing import Dict, Type, Tuple, TYPE_CHECKING, ClassVar

from .command import Command

if TYPE_CHECKING:
    from ..bot import Bot

__all__ = ("Plugin",)


class PluginMeta(type):
    __commands__: Dict[str, Command]

    def __new__(
        cls: Type[PluginMeta], name: str, bases: Tuple[Type], attrs: Dict
    ) -> PluginMeta:
        commands: Dict[str, Command] = {}

        for attr, value in attrs.copy().items():
            if isinstance(value, Command):
                commands[attr] = value

        attrs["__commands__"] = commands
        return super().__new__(cls, name, bases, attrs)


class Plugin(metaclass=PluginMeta):
    __commands__: ClassVar[Dict[str, Command]]

    def _attach_commands(self, bot: Bot):
        for name, command in self.__commands__.items():
            command.parent = self
            bot.commands[name] = command
