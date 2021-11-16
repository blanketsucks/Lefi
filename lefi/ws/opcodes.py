from __future__ import annotations

import enum

__all__ = ("OpCodes",)


class OpCodes(enum.IntFlag):
    """OpCode enums

    Attributes
    ----------
    DISPATCH: :class:`int`
    HEARTBEAT: :class:`int`
    IDENTIFY: :class:`int`
    PRESENCE_UPDATE: :class:`int`
    VOICE_STATE_UPDATE: :class:`int`
    RESUME: :class:`int`
    REQUEST_GUILD_MEMBERS: :class:`int`
    INVALID_SESSION: :class:`int`
    HELLO: :class:`int`
    HEARTBEAT_ACK: :class:`int`
    """

    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE_UPDATE = 3
    VOICE_STATE_UPDATE = 4
    RESUME = 6
    RECONNECT = 7
    REQUEST_GUILD_MEMBERS = 8
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11
