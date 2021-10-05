from typing import Any, Dict, Union

class HTTPException(Exception):
    def __init__(self, data: Union[Dict[str, Any], str]) -> None:
        self.data = data

        if isinstance(data, dict):
            self.code: int = data.get('code', 0)
            self.message: str = data.get('message', '')
        else:
            self.code: int = 0
            self.message: str = data

        super().__init__(f'(code: {self.code}) {self.message}')

class Unauthorized(HTTPException):
    pass

class BadRequest(HTTPException):
    pass

class Forbidden(HTTPException):
    pass

class NotFound(HTTPException):
    pass