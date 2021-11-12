from typing import BinaryIO, Optional, Union
from os import PathLike

__all__ = ("File",)


class File:
    def __init__(
        self, fp: Union[str, PathLike[str], BinaryIO], *, filename: Optional[str] = None
    ) -> None:
        if isinstance(fp, (str, PathLike)):
            self.source = open(fp, "rb")
        else:
            self.source = fp

        self.filename = filename or getattr(self.source, "name", None)

    def read(self, n: int) -> bytes:
        return self.source.read(n)

    def close(self) -> None:
        self.source.close()
