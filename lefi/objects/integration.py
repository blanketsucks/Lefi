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
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data["name"]


class IntegrationApplication:
    def __init__(self, state: State, data: Dict[str, Any]) -> None:
        self._state = state
        self._data = data

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def icon(self) -> Optional[str]:
        return self._data["icon"]

    @property
    def description(self) -> str:
        return self._data["description"]

    @property
    def summary(self) -> str:
        return self._data["summary"]

    @property
    def bot(self) -> Optional[User]:
        bot = self._data.get("bot")
        if not bot:
            return None

        return User(self._state, bot)


class Integration:
    def __init__(self, state: State, data: Dict[str, Any], guild: Guild):
        self._state = state
        self._data = data
        self._guild = guild

    @property
    def guild(self) -> Guild:
        return self._guild

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def type(self) -> str:
        return self._data["type"]

    @property
    def enabled(self) -> bool:
        return self._data["enabled"]

    @property
    def syncing(self) -> bool:
        return self._data.get("syncing", False)

    @property
    def role_id(self) -> Optional[int]:
        return self._data.get("role_id")

    @property
    def role(self) -> Optional[Role]:
        return self._guild.get_role(self.role_id) if self.role_id else None

    @property
    def enable_emoticons(self) -> bool:
        return self._data.get("enable_emoticons", False)

    @property
    def expire_behavior(self) -> Optional[int]:
        return self._data.get("expire_behavior")

    @property
    def expire_grace_period(self) -> Optional[int]:
        return self._data.get("expire_grace_period")

    @property
    def account(self) -> IntegrationAccount:
        return IntegrationAccount(self._data["account"])

    @property
    def application(self) -> Optional[IntegrationApplication]:
        application = self._data.get("application")
        if not application:
            return None

        return IntegrationApplication(self._state, application)

    @property
    def synced_at(self) -> Optional[datetime.datetime]:
        timestamp = self._data.get("synced_at")
        if not timestamp:
            return None

        return datetime.datetime.fromisoformat(timestamp)

    @property
    def subscriber_count(self) -> Optional[int]:
        return self._data.get("subscriber_count")

    @property
    def revoked(self) -> bool:
        return self._data.get("revoked", False)

    async def delete(self) -> None:
        await self._state.http.delete_guild_integration(self._guild.id, self.id)
