from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .channel import TextChannel, VoiceChannel, CategoryChannel, Channel
    from .member import Member
    from .role import Role
    from ..state import State

    GuildChannels = typing.Union[TextChannel, VoiceChannel, CategoryChannel, Channel]

__all__ = ("Guild",)


class Guild:
    def __init__(self, state: State, data: typing.Dict):
        self._channels: typing.Dict[int, GuildChannels] = {}
        self._members: typing.Dict[int, Member] = {}
        self._roles: typing.Dict[int, Role] = {}
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Guild id={self.id}>"

    @property
    def id(self) -> int:
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def icon(self) -> str:
        return self._data["icon"]

    @property
    def icon_hash(self) -> str:
        return self._data["icon_hash"]

    @property
    def splash(self) -> str:
        return self._data["splash"]

    @property
    def discovery_splash(self) -> str:
        return self._data["discovery_splash"]

    @property
    def owner(self) -> bool:
        return self._data["owner"]

    @property
    def owner_id(self) -> int:
        return self._data["owner_id"]

    @property
    def channels(self):
        return list(self._channels.values())
    
    @property
    def members(self) -> typing.List[Member]:
        return list(self._members.values())

    @property
    def roles(self) -> typing.List[Role]:
        return list(self._roles.values())
    
    def get_member(self, member_id: int):
        return self._members.get(member_id)

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)

    def get_role(self, role_id: int):
        return self._roles.get(role_id)