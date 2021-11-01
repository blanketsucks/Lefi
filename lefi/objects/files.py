from typing import Union
import io

__all__ = ("File",)


class File:
    def __init__(self, fp: Union[str, io.BufferedIOBase]) -> None:
        if isinstance(fp, str):
            self.fd = open(fp, "rb")
        else:
            self.fd = fp  # type: ignore

    def close(self) -> None:
        self.fd.close()
