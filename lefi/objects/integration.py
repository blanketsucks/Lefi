from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from .role import Role
from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild

__all__ = ("IntegrationAccount", "IntegrationApplication", "Integration")


class IntegrationAccount:
    """
    Represents an IntegrationAccount.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Creates an IntegrationAccount.

        Parameters:
            data (Dict[str, Any]): The data to use to create the object.
        """
        self._data = data

    @property
    def id(self) -> str:
        """
        Returns the ID of the integration account.
        """
        return self._data["id"]

    @property
    def name(self) -> str:
        """
        Returns the name of the integration account.
        """
        return self._data["name"]


class IntegrationApplication:
    """
    Represents an IntegrationApplication.
    """

    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        """
        Represents an integration application.

        Parameters:
            state (State): The state to use.
            data (Dict[str, Any]): The data to use to create the object.
        """
        self._state = state
        self._data = data

    @property
    def id(self) -> int:
        """
        Returns the ID of the integration application.
        """
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """
        Returns the name of the integration application.
        """
        return self._data["name"]

    @property
    def icon(self) -> Optional[str]:
        """
        Returns the icon of the integration application.
        """
        return self._data["icon"]

    @property
    def description(self) -> str:
        """
        Returns the description of the integration application.
        """
        return self._data["description"]

    @property
    def summary(self) -> str:
        """
        Returns the summary of the integration application.
        """
        return self._data["summary"]

    @property
    def bot(self) -> Optional[User]:
        """
        Returns the bot [User](./user.md) of the integration application.
        """
        bot = self._data.get("bot")
        if not bot:
            return None

        return User(self._state, bot)


class Integration:
    """
    Represents an Integration.
    """

    def __init__(self, state: State, data: Dict[str, Any], guild: Guild) -> None:
        """
        Creates an Integration.

        Parameters:
            state (State): The [State](./state.md) to use.
            data (Dict[str, Any]): The data to use to create the object.
        """
        self._state = state
        self._data = data
        self._guild = guild

    @property
    def guild(self) -> Guild:
        """
        Returns the [Guild](./guild.md) of the integration.
        """
        return self._guild

    @property
    def id(self) -> int:
        """
        Returns the ID of the integration.
        """
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """
        Returns the name of the integration.
        """
        return self._data["name"]

    @property
    def type(self) -> str:
        """
        Returns the type of the integration.
        """
        return self._data["type"]

    @property
    def enabled(self) -> bool:
        """
        Returns whether the integration is enabled.
        """
        return self._data["enabled"]

    @property
    def syncing(self) -> bool:
        """
        Returns whether the integration is syncing.
        """
        return self._data.get("syncing", False)

    @property
    def role_id(self) -> Optional[int]:
        """
        Returns the ID of the role.
        """
        return self._data.get("role_id")

    @property
    def role(self) -> Optional[Role]:
        """
        Returns the [Role](./role.md).
        """
        return self._guild.get_role(self.role_id) if self.role_id else None

    @property
    def enable_emoticons(self) -> bool:
        """
        Returns whether emoticons are enabled.
        """
        return self._data.get("enable_emoticons", False)

    @property
    def expire_behavior(self) -> Optional[int]:
        """
        Returns the expire behavior.
        """
        return self._data.get("expire_behavior")

    @property
    def expire_grace_period(self) -> Optional[int]:
        """
        Returns the expire grace period.
        """
        return self._data.get("expire_grace_period")

    @property
    def account(self) -> IntegrationAccount:
        """
        Returns the [IntegrationAccount]().
        """
        return IntegrationAccount(self._data["account"])

    @property
    def application(self) -> Optional[IntegrationApplication]:
        """
        Returns the [IntegrationApplication]().
        """
        application = self._data.get("application")
        if not application:
            return None

        return IntegrationApplication(self._state, application)

    @property
    def synced_at(self) -> Optional[datetime.datetime]:
        """
        Returns the time the integration was last synced.
        """
        timestamp = self._data.get("synced_at")
        if not timestamp:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def subscriber_count(self) -> Optional[int]:
        """
        Returns the subscriber count.
        """
        return self._data.get("subscriber_count")

    @property
    def revoked(self) -> bool:
        """
        Returns whether the integration is revoked.
        """
        return self._data.get("revoked", False)

    async def delete(self) -> None:
        """
        Deletes the integration.
        """
        await self._state.http.delete_guild_integration(self._guild.id, self.id)
