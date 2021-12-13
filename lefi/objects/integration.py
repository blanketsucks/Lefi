from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from .role import Role
from .user import User

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild

__all__ = (
    "IntegrationAccount",
    "IntegrationApplication",
    "Integration",
    "DeletedIntegration",
)


class DeletedIntegration:
    def __init__(self, state: State, data: Dict, guild: Guild) -> None:
        self._state = state
        self._data = data
        self._guild = guild

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def guild(self) -> Guild:
        """
        Returns the guild that the integration is for.
        """
        return self._guild

    @property
    def application_id(self) -> int:
        return int(self._data["application_id"])


class IntegrationAccount:
    """Represents an IntegrationAccount."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def __repr__(self) -> str:
        return f"<IntegrationAccount id={self.id!r} name={self.name!r}>"

    @property
    def id(self) -> str:
        """the id of the integration account."""
        return self._data["id"]

    @property
    def name(self) -> str:
        """The name of the integration account."""
        return self._data["name"]


class IntegrationApplication:
    """Represents an IntegrationApplication."""

    def __init__(self, state: State, data: dict) -> None:
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<IntegrationApplication id={self.id} name={self.name!r}>"

    @property
    def id(self) -> int:
        """the id of the integration application."""
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """The name of the integration application."""
        return self._data["name"]

    @property
    def icon(self) -> Optional[str]:
        """The icon of the integration application."""
        return self._data["icon"]

    @property
    def description(self) -> str:
        """The description of the integration application."""
        return self._data["description"]

    @property
    def summary(self) -> str:
        """The summary of the integration application."""
        return self._data["summary"]

    @property
    def bot(self) -> Optional[User]:
        """The user of the integration application."""
        bot = self._data.get("bot")
        if not bot:
            return None

        return User(self._state, bot)


class Integration:
    """Represents an Integration."""

    def __init__(self, state: State, data: dict, guild: Guild) -> None:
        self._state = state
        self._data = data
        self._guild = guild

    def __repr__(self) -> str:
        return f"<Integration id={self.id} name={self.name!r} enabled={self.enabled}>"

    @property
    def guild(self) -> Guild:
        """The guild of the integration."""
        return self._guild

    @property
    def id(self) -> int:
        """The ID of the integration."""
        return int(self._data["id"])

    @property
    def name(self) -> str:
        """The name of the integration."""
        return self._data["name"]

    @property
    def type(self) -> str:
        """The type of integration."""
        return self._data["type"]

    @property
    def enabled(self) -> bool:
        """Whether the integration is enabled or not."""
        return self._data["enabled"]

    @property
    def syncing(self) -> bool:
        """Whether the integration is syncing or not."""
        return self._data.get("syncing", False)

    @property
    def role_id(self) -> Optional[int]:
        """The id of the integration role."""
        return self._data.get("role_id")

    @property
    def role(self) -> Optional[Role]:
        """ """
        return self._guild.get_role(self.role_id) if self.role_id else None

    @property
    def enable_emoticons(self) -> bool:
        """Whether emoticons are enabled or not."""
        return self._data.get("enable_emoticons", False)

    @property
    def expire_behavior(self) -> Optional[int]:
        """The expire behavior of the integration."""
        return self._data.get("expire_behavior")

    @property
    def expire_grace_period(self) -> Optional[int]:
        """the expire grace period of the integration."""
        return self._data.get("expire_grace_period")

    @property
    def account(self) -> IntegrationAccount:
        """The integration's account."""
        return IntegrationAccount(self._data["account"])

    @property
    def application(self) -> Optional[IntegrationApplication]:
        """The integration's application."""
        application = self._data.get("application")
        if not application:
            return None

        return IntegrationApplication(self._state, application)

    @property
    def synced_at(self) -> Optional[datetime.datetime]:
        """The time which the integration was last synced."""
        timestamp = self._data.get("synced_at")
        if not timestamp:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def subscriber_count(self) -> Optional[int]:
        """The subscriber count of the integration."""
        return self._data.get("subscriber_count")

    @property
    def revoked(self) -> bool:
        """Whether the integration is revoked or not."""
        return self._data.get("revoked", False)

    async def delete(self) -> None:
        """Deletes the integration

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        await self._state.http.delete_guild_integration(self._guild.id, self.id)
