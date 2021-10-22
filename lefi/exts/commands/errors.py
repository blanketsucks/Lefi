from __future__ import annotations

from typing import Optional


class CheckFailed(Exception):
    pass


class CommandOnCooldown(Exception):
    def __init__(self, retry_after: float, message: Optional[str] = None) -> None:
        self.message = message
        self.retry_after = retry_after
