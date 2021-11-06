from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from functools import cached_property

from .enums import AuditLogsEvent
from .user import User
from ..utils import to_snowflake

_member_events = (
    AuditLogsEvent.MEMBER_ROLE_UPDATE,
    AuditLogsEvent.MEMBER_UPDATE,
    AuditLogsEvent.MEMBER_PRUNE,
    AuditLogsEvent.MEMBER_BAN_ADD,
    AuditLogsEvent.MEMBER_BAN_REMOVE,
    AuditLogsEvent.MEMBER_KICK,
    AuditLogsEvent.MEMBER_DISCONNECT,
)

_channel_events = (
    AuditLogsEvent.CHANNEL_CREATE,
    AuditLogsEvent.CHANNEL_UPDATE,
    AuditLogsEvent.CHANNEL_DELETE,
    AuditLogsEvent.CHANNEL_OVERWRITE_CREATE,
    AuditLogsEvent.CHANNEL_OVERWRITE_UPDATE,
    AuditLogsEvent.CHANNEL_OVERWRITE_DELETE,
)

_role_events = (
    AuditLogsEvent.ROLE_CREATE,
    AuditLogsEvent.ROLE_UPDATE,
    AuditLogsEvent.ROLE_DELETE,
)

_thread_events = (
    AuditLogsEvent.THREAD_CREATE,
    AuditLogsEvent.THREAD_UPDATE,
    AuditLogsEvent.THREAD_DELETE,
)

_message_events = (
    AuditLogsEvent.MESSAGE_DELETE,
    AuditLogsEvent.MESSAGE_BULK_DELETE,
    AuditLogsEvent.MESSAGE_PIN,
    AuditLogsEvent.MESSAGE_UNPIN,
)

if TYPE_CHECKING:
    from ..state import State

    from .channel import Channel
    from .guild import Guild
    from .role import Role
    from .member import Member
    from .threads import Thread
    from .message import Message

    Target = Union[User, Member, Role, Channel, Guild, Thread, Message]

__all__ = (
    "AuditLogChange",
    "AuditLogEntry",
)


class AuditLogChange:
    def __init__(self, data: Dict) -> None:
        self._data = data

    def __repr__(self) -> str:
        return f"<AuditLogChange key={self.key!r}>"

    @property
    def key(self) -> str:
        return self._data["key"]

    @property
    def old(self) -> Any:
        return self._data["old_value"]

    @property
    def new(self) -> Any:
        return self._data["new_value"]


class AuditLogEntry:
    def __init__(self, state: State, guild: Guild, data: Dict) -> None:
        self._state = state
        self._guild = guild
        self._data = data

    @property
    def guild(self) -> Guild:
        return self._guild

    @property
    def changes(self) -> List[AuditLogChange]:
        return [AuditLogChange(change) for change in self._data["changes"]]

    @property
    def type(self) -> AuditLogsEvent:
        return AuditLogsEvent(self._data["action_type"])

    @property
    def target_id(self) -> int:
        return int(self._data["target_id"])

    @cached_property
    def target(self) -> Optional[Target]:
        if self.type is AuditLogsEvent.GUILD_UPDATE:
            return self._guild

        if self.type in _member_events:
            member = self._guild.get_member(self.target_id)
            if not member:
                return self._state.get_user(self.target_id)

            return member

        if self.type in _role_events:
            return self._guild.get_role(self.target_id)

        if self.type in _channel_events:
            return self._guild.get_channel(self.target_id)

        if self.type in _thread_events:
            return self._guild.get_thread(self.target_id)

        if self.type in _message_events:
            return self._state.get_message(self.target_id)

        return None

    @property
    def user_id(self) -> Optional[int]:
        return to_snowflake(self._data, "user_id")

    @property
    def user(self) -> Optional[User]:
        return self._state.get_user(self.user_id)  # type: ignore

    @property
    def reason(self) -> Optional[str]:
        return self._data.get("reason")
