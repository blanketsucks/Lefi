from __future__ import annotations
from typing import Any, Dict, List, Union

from ..utils import Snowflake

__all__ = ("AllowedMentions",)


class AllowedMentions:
    def __init__(
        self,
        *,
        everyone: bool = True,
        roles: Union[bool, List[Snowflake]] = True,
        users: Union[bool, List[Snowflake]] = True,
        replied_user: bool = True
    ) -> None:
        self.everyone = everyone
        self.roles = roles
        self.users = users
        self.replied_user = replied_user

    @classmethod
    def none(cls) -> AllowedMentions:
        return cls(everyone=False, roles=False, users=False, replied_user=False)

    def to_dict(self) -> Dict[str, Any]:
        parse: List[str] = []
        payload = {}

        if self.replied_user:
            payload["replied_user"] = True

        if self.everyone:
            parse.append("everyone")

        if self.roles is True:
            parse.append("roles")
        elif isinstance(self.roles, list):
            payload["roles"] = [role.id for role in self.roles]  # type: ignore

        if self.users is True:
            parse.append("users")
        elif isinstance(self.users, list):
            payload["users"] = [user.id for user in self.users]  # type: ignore

        payload["parse"] = parse  # type: ignore
        return payload
