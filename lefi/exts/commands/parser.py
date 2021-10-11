from __future__ import annotations

from typing import Optional, List, Tuple, Union

__all__ = ("StringParser",)


class StringParser:
    def __init__(self, content: str, prefix: Union[Tuple[str], str]) -> None:
        self.command: Optional[str] = None
        self.arguments: List[str] = []
        self.content = content
        self.prefix = prefix

    def find_command(self) -> Optional[str]:
        tokens = self.content.split(" ")

        if prefix := self.parse_prefix():

            if tokens[0].startswith(prefix):
                self.command = tokens[0][len(prefix) :]

            self.arguments = tokens[1:]

            return self.command

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

    @property
    def invoker(self) -> Optional[str]:
        return self.command

    @property
    def invoked_with(self) -> Optional[str]:
        return self.parse_prefix()
