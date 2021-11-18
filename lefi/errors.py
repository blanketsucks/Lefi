from __future__ import annotations

from typing import Any, Dict, Union

__all__ = (
    "ClientException",
    "VoiceException",
    "OpusNotFound",
    "HTTPException",
    "Unauthorized",
    "BadRequest",
    "Forbidden",
    "NotFound",
)


class ClientException(Exception):
    """Base class for all exceptions."""

    pass


class VoiceException(ClientException):
    """Base class for all voice exceptions."""

    pass


class OpusNotFound(VoiceException):
    """Raised whenever a user attempts to use voice without having the Opus library installed."""

    pass


class HTTPException(ClientException):
    """Error representing an error received from the API.

    Attributes
    ----------
    data: Union[Dict[str, Any], str]
        Error data received from the API.
    message: :class:`str`
        The message for the error.
    code: :class:`int`
        The error code.
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
    """Represents a 401 HTTP error."""

    pass


class BadRequest(HTTPException):
    """Represents a 400 HTTP error."""

    pass


class Forbidden(HTTPException):
    """Represents a 403 HTTP error."""

    pass


class NotFound(HTTPException):
    """Represents a 404 HTTP error."""

    pass
