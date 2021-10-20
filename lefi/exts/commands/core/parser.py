from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Tuple, Union

from .command import Command

__all__ = ("StringParser",)


class StringParser:
    def __init__(self, content: str, prefix: Union[Tuple[str], str]) -> None:
        self.command_name: Optional[str] = None
        self.command: Optional[Command] = None
        self.arguments: List[str] = []
        self.content = content
        self.prefix = prefix

    def find_command(self) -> Optional[str]:
        tokens = self.content.split(" ")

        if prefix := self.parse_prefix():

            if tokens[0].startswith(prefix):
                self.command_name = tokens[0][len(prefix) :]

            self.arguments = tokens[1:]

            return self.command_name

        assert False

    def parse_prefix(self) -> Optional[str]:
        if isinstance(self.prefix, tuple):
            find_prefix = [self.content.startswith(prefix) for prefix in self.prefix]

            for index, prefix in enumerate(find_prefix):
                if prefix is not True:
                    continue

                return self.prefix[index]

        elif not isinstance(self.prefix, tuple):
            return self.prefix

        assert False

    async def parse_arguments(self) -> Tuple[Dict, List]:
        keyword_arguments: Dict = {}
        arguments: List = []

        if self.command is not None:
            signature = inspect.signature(self.command.callback)

            for index, (argument, parameter) in enumerate(signature.parameters.items()):
                if index == 0:
                    continue

                if index == 1 and self.command.parent is not None:
                    continue

                if parameter.kind is parameter.POSITIONAL_OR_KEYWORD:
                    arguments.append(
                        await self.convert(parameter, self.arguments[index - 1])
                    )

                elif parameter.kind is parameter.KEYWORD_ONLY:
                    keyword_arguments[argument] = await self.convert(
                        parameter, " ".join(self.arguments[index - 1 :])
                    )

        return keyword_arguments, arguments

    async def convert(
        self, parameter: inspect.Parameter, data: Union[List[str], str]
    ) -> Any:
        if parameter.annotation is not parameter.empty and callable(
            parameter.annotation
        ):
            return parameter.annotation(data)

        return str(data)

    @property
    def invoker(self) -> Optional[Command]:
        return self.command

    @property
    def invoked_with(self) -> Optional[str]:
        return self.parse_prefix()
