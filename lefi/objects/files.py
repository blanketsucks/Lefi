from typing import BinaryIO, Optional, Union
import io

__all__ = ("File",)


class File:
    def __init__(
        self, fp: Union[str, BinaryIO], *, filename: Optional[str] = None
    ) -> None:
        if isinstance(fp, str):
            self.fd = open(fp, "rb")
        else:
            self.fd = fp

        self.filename = filename or getattr(self.fd, "name", None)

    def close(self) -> None:
        self.fd.close()
