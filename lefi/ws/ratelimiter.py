from __future__ import annotations

import asyncio


class Ratelimiter:
    """A simple max concurrency ratelimiter

    Parameters
    ----------
    limit: :class:`int`
        Thread limit for the semaphore

    delay: :class:`int`
        The delay to wait when releasing
    """

    def __init__(self, limit: int, delay: float) -> None:
        self.loop = asyncio.get_running_loop()
        self.limit = limit
        self.delay = delay

        self.semaphore = asyncio.Semaphore(limit)

    def release(self) -> None:
        """Unlocks the semaphore after set delay."""
        self.loop.call_later(self.delay, self.semaphore.release)

    async def __aenter__(self) -> Ratelimiter:
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, *_) -> None:
        pass
