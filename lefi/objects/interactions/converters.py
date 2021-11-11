from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Callable, ClassVar

if TYPE_CHECKING:
    from ..user import User
    from ...client import Client

__all__ = ("Converter",)


class Converter:
    def __init__(self, client: Client) -> None:
        self.client = client

        self.CONVERTER_MAPPING: Dict[int, Callable] = {
            3: self._str,
            4: self._int,
            5: self._bool,
            6: self.user,
        }

    def _str(self, data: Dict) -> str:
        return data["value"]

    def _int(self, data: Dict) -> int:
        return int(data["value"])

    def _bool(self, data: Dict) -> bool:
        return bool(data["value"])

    async def user(self, data: Dict) -> User:
        user_id: int = int(data["value"])

        if user := self.client.get_user(user_id):
            return user

        data = await self.client.http.get_user(user_id)
        return self.client._state.add_user(data)
