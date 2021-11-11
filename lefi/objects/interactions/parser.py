from __future__ import annotations

import inspect

from typing import TYPE_CHECKING, List, Dict, Any, Tuple, Callable

from .converters import Converter

from ..enums import CommandOptionType

if TYPE_CHECKING:
    from .command import AppCommand

__all__ = ("ArgumentParser",)


class ArgumentParser:
    def __init__(self, command: AppCommand) -> None:
        self.converter = Converter(command.client)
        self.command = command

    async def create_arguments(self, data: List[Dict]) -> List:
        arguments: List = []

        for input in data:
            converter = self.converter.CONVERTER_MAPPING[input["type"]]
            if inspect.iscoroutinefunction(converter):
                arguments.append(await converter(input))

            elif callable(converter):
                arguments.append(converter(input))

        return arguments

    async def parse_arguments(self) -> List:
        arguments: List = []

        signature = inspect.signature(self.command.callback)

        for index, (argument, parameter) in enumerate(signature.parameters.items()):
            if index == 0:
                continue

            if parameter.kind is parameter.POSITIONAL_OR_KEYWORD:
                arguments.append(await self.convert(parameter, argument))

        return arguments

    async def convert(self, parameter: inspect.Parameter, data: str) -> Tuple[str, Any]:
        argument_types: Dict[Any, int] = {
            "str": CommandOptionType.STRING,
            "int": CommandOptionType.INTEGER,
            "bool": CommandOptionType.BOOLEAN,
            "User": CommandOptionType.USER,
        }

        if parameter.annotation is not parameter.empty:
            cleaned = parameter.annotation.removeprefix("lefi.")
            return data, argument_types[cleaned]

        return data, CommandOptionType.STRING
