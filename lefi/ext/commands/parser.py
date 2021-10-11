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

        if tokens[0].startswith(self.prefix):
            self.command = tokens[0][len(self.prefix) :]

        self.arguments = tokens[1:]

        return self.command

    def parse_prefix(self) -> str:
        ...
