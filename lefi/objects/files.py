from typing import Optional, Union
import io

__all__ = ("File",)


class File:
    def __init__(
        self, fp: Union[str, io.BytesIO], *, filename: Optional[str] = None
    ) -> None:
        if isinstance(fp, str):
            self.fd = open(fp, "rb")
        else:
            self.fd = fp  # type: ignore

        self.filename = filename or getattr(self.fd, "name", None)

    def close(self) -> None:
        self.fd.close()
