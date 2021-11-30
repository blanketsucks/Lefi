from typing import BinaryIO, Optional, Union
from os import PathLike

__all__ = ("File",)


class File:
    """Represents a file.

    Parameters
    ----------
    fp: Union[:class:`str`, :class:`os.PathLike`, :class:`typing.BinaryIO`]
        The file's path

    filename: Optional[:class:`str`]
        The name of the file

    Attributes
    ----------
    source: Union[:class:`io.BufferedReader`, :class:`typing.BinaryIO`]
        The source of the file

    filename: Optional[:class:`str`]
        The name of the file

    fp: Union[:class:`io.BufferedReader`, :class:`typing.BinaryIO`]
        The file's path
    """

    def __init__(
        self, fp: Union[str, PathLike[str], BinaryIO], *, filename: Optional[str] = None
    ) -> None:
        if isinstance(fp, (str, PathLike)):
            self.source = open(fp, "rb")
        else:
            self.source = fp

        self.filename = filename or getattr(self.source, "name", None)
        self.fp = fp

    def read(self, size: Optional[int]) -> bytes:
        """Reads the file.

        Parameters
        ----------
        size: Optional[:class:`int`]
            The size of bytes to read up to

        Returns
        -------
        :class:`bytes`
            The read bytes.
        """
        return self.source.read(size or -1)

    def close(self) -> None:
        """Closes the file."""
        self.source.close()
