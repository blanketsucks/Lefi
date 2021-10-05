
from enum import IntEnum

__all__ = ('PremiumType', 'ChannelType', 'OverwriteType')

class PremiumType(IntEnum):
    NONE = 0
    NITRO_CLASSIC = 1
    NITRO = 2

class ChannelType(IntEnum):
    TEXT = 0
    DM = 1
    VOICE = 2
    CATEGORY = 4
    NEWS = 5
    STORE = 6
    NEWS_THREAD = 10
    PUBLIC_THREAD = 11
    PRIVATE_THREAD = 12
    STAGE_VOICE = 13

class OverwriteType(IntEnum):
    ROLE = 0
    MEMBER = 1