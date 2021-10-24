from __future__ import annotations

import ast
import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Union

from lefi import Cache

if TYPE_CHECKING:
    from lefi import Message


__all__ = (
    "CooldownType",
    "Cooldown",
)


class CooldownType(Enum):
    member = "{0.guild.id}, {0.author.id}"
    user = "{0.author.id}"
    guild = "{0.guild.id}"


class CooldownData:
    def __init__(
        self,
        reset_seconds: datetime.timedelta,
        reset_time: Optional[datetime.datetime],
        uses_left: int,
    ) -> None:
        self.reset_seconds = reset_seconds
        self.reset_time = reset_time
        self.uses_left = uses_left
        self.retry_after: float


class Cooldown:
    def __init__(self, amount: int, time: float, type: CooldownType) -> None:
        self.members_cooldowns_cache = Cache[Dict[int, CooldownData]]()
        self.cooldowns_cache = Cache[CooldownData]()
        self.amount = amount
        self.time = time
        self.type = type

    def _update_cooldown(self, message: Message) -> None:
        cooldown = self.get_cooldown_reset(message)

        if cooldown is not None:
            cooldown.uses_left -= 1

            if cooldown.uses_left == 0:
                cooldown.reset_time = datetime.datetime.now() + cooldown.reset_seconds

    def _check_cooldown(self, message: Message) -> bool:
        cooldown = self.get_cooldown_reset(message)

        if cooldown is not None and cooldown.reset_time is not None:
            if datetime.datetime.now() >= cooldown.reset_time:
                self.delete_cooldown(message)
                return True
            else:
                cooldown.retry_after = (
                    cooldown.reset_time - datetime.datetime.now()
                ).total_seconds()
                return False

        return True

    def set_cooldown_time(self, message: Message) -> None:
        cooldown_id = self.get_cooldown_id(message)

        if not isinstance(cooldown_id, tuple):
            self.cooldowns_cache[cooldown_id] = CooldownData(
                datetime.timedelta(seconds=self.time), None, self.amount
            )
            return

        guild_id, member_id = cooldown_id
        self.members_cooldowns_cache[guild_id] = {
            member_id: CooldownData(
                datetime.timedelta(seconds=self.time), None, self.amount
            )
        }

    def get_cooldown_reset(self, message: Message) -> Optional[CooldownData]:
        cooldown_id = self.get_cooldown_id(message)

        if not isinstance(cooldown_id, tuple):
            return self.cooldowns_cache.get(cooldown_id)

        guild_id, member_id = cooldown_id
        if guild := self.members_cooldowns_cache.get(guild_id):
            return guild.get(member_id)

        return None

    def get_cooldown_id(self, message: Message) -> Union[int, Tuple[int, int]]:
        cooldown_id = self.type.value.format(message)

        if self.type is CooldownType.member:
            return ast.literal_eval(cooldown_id)

        return int(cooldown_id)

    def delete_cooldown(self, message) -> None:
        cooldown_id = self.get_cooldown_id(message)

        if not isinstance(cooldown_id, tuple):
            del self.cooldowns_cache[cooldown_id]
            return

        guild_id, member_id = cooldown_id
        del self.members_cooldowns_cache[guild_id][member_id]
