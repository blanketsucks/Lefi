from __future__ import annotations

from typing import Any, Dict, Union

__all__ = ("HTTPException", "Unauthorized", "BadRequest", "Forbidden", "NotFound")


class HTTPException(Exception):
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
    pass


class BadRequest(HTTPException):
    pass


class Forbidden(HTTPException):
    pass


class NotFound(HTTPException):
    pass
