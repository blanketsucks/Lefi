from __future__ import annotations

from typing import Any, Dict, Union

__all__ = ("HTTPException", "Unauthorized", "BadRequest", "Forbidden", "NotFound")


class HTTPException(Exception):
    """
    Error representing an error received from the API.

    Attributes:
        data (Union[Dict[str, Any], str]): data received from the API.
        messsage (str): The message for the error.
        code (int): The code of the error.

    """

    def __init__(self, data: Union[Dict[str, Any], str]) -> None:
        self.data = data
        self.message: str = ""
        self.code: int = 0

        if isinstance(data, dict):
            self.code = data.get("code", 0)
            self.message = data.get("message", self.message)
        else:
            self.code = 0
            self.message = data

        super().__init__(f"(code: {self.code}) {self.message}")


class Unauthorized(HTTPException):
    """
    Represents a 401 error
    """

    pass


class BadRequest(HTTPException):
    """
    Represents a 400 error
    """

    pass


class Forbidden(HTTPException):
    """
    Represents a 403 error
    """

    pass


class NotFound(HTTPException):
    """
    Represents a 404 error
    """

    pass
