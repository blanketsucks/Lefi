from enum import IntFlag

__all__ = (
    'UserFlags',
    'Intents',
    'Permissions'
)

class UserFlags(IntFlag):
    NONE = 0
    EMPLOYEE = 1 << 0
    PARTNERED_SERVER_OWNER = 1 << 1
    HYPERSQUAD_EVENTS = 1 << 2
    BUG_HUNTER_LEVEL_1 = 1 << 3
    HOUSE_BRAVERY = 1 << 6
    HOUSE_BRILLIANCE = 1 << 7
    HOUSE_BALANCE = 1 << 8
    EARLY_SUPPORTER = 1 << 9
    TEAM_USER = 1 << 10
    BUG_HUNTER_LEVEL_2 = 1 << 14
    VERIFIED_BOT = 1 << 16
    VERIFIED_DEVELOPER = 1 << 17
    CERTIFIED_MODERATOR = 1 << 18

class Intents(IntFlag):
    NONE = 0
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_BANS = 1 << 2
    GUILD_EMOJIS_AND_STICKERS = 1 << 3
    GUILD_INTEGRATIONS = 1 << 4
    GUILD_WEBHOOKS = 1 << 5
    GUILD_INVITES = 1 << 6
    GUILD_VOICE_STATES = 1 << 7
    GUILD_PRESENCES = 1 << 8
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGES = 1 << 12
    DIRECT_MESSAGE_REACTIONS = 1 << 13
    DIRECT_MESSAGE_TYPING = 1 << 14

    @classmethod
    def all(cls):
        return cls(
            cls.GUILDS |
            cls.GUILD_MEMBERS |
            cls.GUILD_BANS |
            cls.GUILD_EMOJIS_AND_STICKERS |
            cls.GUILD_INTEGRATIONS |
            cls.GUILD_WEBHOOKS |
            cls.GUILD_INVITES |
            cls.GUILD_VOICE_STATES |
            cls.GUILD_PRESENCES |
            cls.GUILD_MESSAGES |
            cls.GUILD_MESSAGE_REACTIONS |
            cls.GUILD_MESSAGE_TYPING |
            cls.DIRECT_MESSAGES |
            cls.DIRECT_MESSAGE_REACTIONS |
            cls.DIRECT_MESSAGE_TYPING   
        )

    @classmethod
    def default(cls):
        return cls(
            cls.GUILDS |
            cls.GUILD_BANS |
            cls.GUILD_EMOJIS_AND_STICKERS |
            cls.GUILD_INTEGRATIONS |
            cls.GUILD_WEBHOOKS |
            cls.GUILD_INVITES |
            cls.GUILD_VOICE_STATES |
            cls.GUILD_MESSAGES |
            cls.GUILD_MESSAGE_REACTIONS |
            cls.GUILD_MESSAGE_TYPING |
            cls.DIRECT_MESSAGES |
            cls.DIRECT_MESSAGE_REACTIONS |
            cls.DIRECT_MESSAGE_TYPING   
        )

class Permissions(IntFlag):
    CREATE_INSTANT_INVITE = 1 << 0
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_CHANNELS = 1 << 4
    MANAGE_GUILD = 1 << 5
    ADD_REACTIONS = 1 << 6
    VIEW_AUDIT_LOG = 1 << 7
    PRIORITY_SPEAKER = 1 << 8
    STREAM = 1 << 9
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    SEND_TTS_MESSAGES = 1 << 12
    MANAGE_MESSAGES = 1 << 13
    EMBED_LINKS = 1 << 14
    ATTACH_FILES = 1 << 15
    READ_MESSAGE_HISTORY = 1 << 16
    MENTION_EVERYONE = 1 << 17
    USE_EXTERNAL_EMOJIS = 1 << 18
    CONNECT = 1 << 20
    SPEAK = 1 << 21
    MUTE_MEMBERS = 1 << 22
    DEAFEN_MEMBERS = 1 << 23
    MOVE_MEMBERS = 1 << 24
    USE_VAD = 1 << 25
    CHANGE_NICKNAME = 1 << 26
    MANAGE_NICKNAMES = 1 << 27
    MANAGE_ROLES = 1 << 28
    MANAGE_WEBHOOKS = 1 << 29
    MANAGE_EMOJIS_AND_STICKERS = 1 << 30
    USE_APPLICATION_COMMANDS = 1 << 31
    REQUEST_TO_SPEAK = 1 << 32
    MANAGE_THREADS = 1 << 34
    CREATE_PUBLIC_THREADS = 1 << 35
    CREATE_PRIVATE_THREADS = 1 << 36
    USE_EXTERNAL_STICKERS = 1 << 37
    SEND_MESSAGES_IN_THREADS = 1 << 38
    START_EMBEDDED_ACTIVITIES = 1 << 39
