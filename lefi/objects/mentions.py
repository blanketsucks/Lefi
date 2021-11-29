from __future__ import annotations
from typing import Any, Dict, List, Union

from ..utils import Snowflake

__all__ = ("AllowedMentions",)


class AllowedMentions:
    """Represents an allowed mentions object.

    Parameters
    ----------
    everyone: :class:`bool`
        If mentioning everyone should be allowed or not

    roles: Union[:class:`bool`, List[:class:`.Snowflake`]]
        If mentioning a list of roles or any role is allowed or not

    users: Union[:class:`bool`, List[:class:`.Snowflake`]]
        If mentioning a list of users or any user is allowed or not

    replied_user: :class:`bool`
        If mentioning replied users is allowed or not

    Attributes
    ----------
    everyone: :class:`bool`
        If mentioning everyone is allowed or not

    roles: :class:`bool`
        If mentioning roles is allowed or not

    users: :class:`bool`
        If mentioning users is allowed or not

    replied_user: :class:`bool`
        If mentioning replied users is allowed or not
    """
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
        """Creates an :class:`.AllowedMentions` instance which
        doesn't allow any mentions.
        """
        return cls(everyone=False, roles=False, users=False, replied_user=False)

    def to_dict(self) -> dict:
        """Creates a dict from the allowed mentions.

        Returns
        -------
        :class:`dict`
            The dict representing the allowed mentions.
        """
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
