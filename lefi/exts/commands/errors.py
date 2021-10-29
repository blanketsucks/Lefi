from __future__ import annotations

from typing import Optional


class CheckFailed(Exception):
    pass


class CommandOnCooldown(Exception):
    def __init__(self, retry_after: float, message: Optional[str] = None) -> None:
        """
        Parameters:
            retry_after: The amount of time in seconds that the command is on cooldown for.
            message: The message to send to the user.
        """
        self.message = message
        self.retry_after = retry_after
