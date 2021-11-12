from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from functools import cached_property

from .enums import (
    AuditLogsEvent,
    ChannelType,
    VerificationLevel,
    ExplicitContentFilterLevel,
)
from .user import User
from ..utils import to_snowflake, Object
from .permissions import Permissions
from .role import PartialRole
from .attachments import CDNAsset

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

    Change = Union[
        int,
        bool,
        Dict[Union[Role, Member, Object], Permissions],
        List[Union[Role, PartialRole]],
        Channel,
        Permissions,
        Member,
        User,
        Guild,
        Object,
        ExplicitContentFilterLevel,
        ChannelType,
        VerificationLevel,
        CDNAsset,
        None,
    ]

    Target = Union[User, Member, Role, Channel, Guild, Thread, Message, Object]

    T = TypeVar("T")

__all__ = (
    "AuditLogChange",
    "AuditLogEntry",
)


def _get(
    getter: Callable[[int], Optional[T]], value: Optional[int]
) -> Union[T, Object]:
    return getter(value) or Object(id=value)  # type: ignore


def _handle_channel_snowflake(
    change: AuditLogChange, value: str
) -> Union[Channel, Object]:
    guild = change.entry.guild
    return _get(guild.get_channel, int(value))


def _handle_snowflake(change: AuditLogChange, value: str) -> int:
    return int(value)


def _handle_permission(change: AuditLogChange, value: str) -> Permissions:
    return Permissions(int(value))


def _handle_permission_overwrites(
    change: AuditLogChange, value: List[Dict[str, Any]]
) -> Dict[Union[Role, Member, Object], Permissions]:
    overwrites = {}
    guild = change.entry.guild

    for data in value:
        allow = Permissions(int(data["allow"]))
        deny = Permissions(int(data["deny"]))

        ow = Permissions.from_overwrite_pair(allow, deny)

        type = data["type"]
        target_id = int(data["id"])

        target: Union[Role, Member, Object, None]

        if type == "1":
            target = guild.get_role(target_id)
        else:
            target = guild.get_member(target_id)

        if target is None:
            target = Object(id=target_id)

        overwrites[target] = ow

    return overwrites


def _handle_member(change: AuditLogChange, value: str) -> Union[Member, User, Object]:
    entry = change.entry
    return _get(entry._get_member, int(value))


def _handle_guild(change: AuditLogChange, value: str) -> Union[Guild, Object]:
    state = change.entry._state
    return _get(state.get_guild, int(value))


def _handle_roles(
    change: AuditLogChange, value: List[Dict[str, Any]]
) -> List[Union[Role, PartialRole]]:
    guild = change.entry.guild
    roles = []

    for payload in value:
        role: Union[Role, PartialRole, None]
        role = guild.get_role(int(payload["id"]))

        if not role:
            role = PartialRole(payload, guild)

        roles.append(role)

    return roles


def _handle_enum(cls: Type[T]) -> Callable[[AuditLogChange, int], T]:
    def _handle(change: AuditLogChange, value: int) -> T:
        return cls(int(value))  # type: ignore

    return _handle


def _handle_type(change: AuditLogChange, value: int) -> int:
    entry = change.entry
    if entry.action.name.startswith("CHANNEL") or entry.action.name.startswith(
        "THREAD"
    ):
        return ChannelType(value)

    return value


def _handle_icon_hash(change: AuditLogChange, value: str) -> CDNAsset:
    entry = change.entry
    return CDNAsset.from_guild_icon(entry._state, entry.guild.id, value)


def _handle_avatar_hash(change: AuditLogChange, value: str) -> CDNAsset:
    entry = change.entry
    return CDNAsset.from_user_avatar(entry._state, entry.target_id, value)  # type: ignore


def _handle_splash_hash(change: AuditLogChange, value: str) -> CDNAsset:
    entry = change.entry
    return CDNAsset.from_guild_splash(entry._state, entry.guild.id, value)


def _handle_banner_hash(change: AuditLogChange, value: str) -> CDNAsset:
    entry = change.entry
    return CDNAsset.from_guild_banner(entry._state, entry.guild.id, value)


def _handle_discovery_splash_hash(change: AuditLogChange, value: str) -> CDNAsset:
    entry = change.entry
    return CDNAsset.from_guild_discovery_splash(entry._state, entry.guild.id, value)


def _handle_value(change: AuditLogChange, value: Any) -> Change:
    key = change._data["key"]
    handler = _handlers.get(key)

    if value is None:
        return None

    if not handler:
        return value

    return handler(change, value)


_names: Dict[str, str] = {
    "channel_id": "channel",
    "guild_id": "guild",
    "target_id": "target",
    "owner_id": "owner",
    "inviter_id": "inviter",
    "afk_channel_id": "afk_channel",
    "widget_channel_id": "widget_channel",
    "rules_channel_id": "rules_channel",
    "public_updates_channel_id": "public_updates_channel",
    "icon_hash": "icon",
    "splash_hash": "splash",
    "discovery_splash_hash": "discovery_splash",
    "banner_hash": "banner",
    "avatar_hash": "avatar",
}

_handlers: Dict[str, Callable[[AuditLogChange, Any], Change]] = {
    "allow": _handle_permission,
    "deny": _handle_permission,
    "permissions": _handle_permission,
    "permission_overwrites": _handle_permission_overwrites,
    "id": _handle_snowflake,
    "channel_id": _handle_channel_snowflake,
    "guild_id": _handle_guild,
    "owner_id": _handle_member,
    "inviter_id": _handle_member,
    "afk_channel_id": _handle_channel_snowflake,
    "system_channel_id": _handle_channel_snowflake,
    "widget_channel_id": _handle_channel_snowflake,
    "rules_channel_id": _handle_channel_snowflake,
    "public_updates_channel_id": _handle_channel_snowflake,
    "explicit_content_filter": _handle_enum(ExplicitContentFilterLevel),
    "verification_level": _handle_enum(VerificationLevel),
    "type": _handle_type,
    "icon_hash": _handle_icon_hash,
    "avatar_hash": _handle_avatar_hash,
    "splash_hash": _handle_splash_hash,
    "banner_hash": _handle_banner_hash,
    "discovery_splash_hash": _handle_discovery_splash_hash,
    "$add": _handle_roles,
    "$remove": _handle_roles,
}


class AuditLogChange:
    def __init__(self, entry: AuditLogEntry, data: Dict) -> None:
        self._data = data
        self._entry = entry

    def __repr__(self) -> str:
        return f"<AuditLogChange key={self.key!r}>"

    @property
    def entry(self) -> AuditLogEntry:
        return self._entry

    @property
    def key(self) -> str:
        name = self._data["key"]
        return _names.get(name, name)

    @cached_property
    def before(self) -> Change:
        value = self._data.get("old_value")
        return _handle_value(self, value)

    @cached_property
    def after(self) -> Change:
        value = self._data.get("new_value", None)
        return _handle_value(self, value)


class AuditLogEntry:
    def __init__(
        self, users: Dict[int, User], state: State, guild: Guild, data: Dict
    ) -> None:
        self._state = state
        self._guild = guild
        self._data = data
        self._users = users

    def _get_member(self, value: int) -> Optional[Union[Member, User]]:
        return self._guild.get_member(value) or self._users.get(value)

    @property
    def guild(self) -> Guild:
        return self._guild

    @property
    def changes(self) -> List[AuditLogChange]:
        return [
            AuditLogChange(self, change) for change in self._data.get("changes", [])
        ]

    @property
    def action(self) -> AuditLogsEvent:
        return AuditLogsEvent(self._data["action_type"])

    @property
    def target_id(self) -> Optional[int]:
        return to_snowflake(self._data, "target_id")

    @cached_property
    def target(self) -> Target:
        if self.action is AuditLogsEvent.GUILD_UPDATE:
            return self._guild

        if self.action in _member_events:
            return _get(self._get_member, self.target_id)

        if self.action in _role_events:
            return _get(self._guild.get_role, self.target_id)

        if self.action in _channel_events:
            return _get(self._guild.get_channel, self.target_id)

        if self.action in _thread_events:
            return _get(self._guild.get_thread, self.target_id)

        if self.action in _message_events:
            return _get(self._state.get_message, self.target_id)

        return Object(id=self.target_id)  # type: ignore

    @property
    def user_id(self) -> Optional[int]:
        return to_snowflake(self._data, "user_id")

    @property
    def user(self) -> Optional[User]:
        return self._state.get_user(self.user_id)  # type: ignore

    @property
    def reason(self) -> Optional[str]:
        return self._data.get("reason")
