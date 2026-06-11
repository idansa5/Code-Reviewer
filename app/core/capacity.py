from __future__ import annotations


# implementation of capacity limiter (as atomic operator)
class CapacityLimiter:
    """Non-blocking concurrency cap.

    try_acquire() either reserves a slot and returns True, or returns False
    immediately if at capacity. Callers must reject the request on False, not
    wait for a slot to free up. Safe in a single-threaded asyncio event loop:
    there is no `await` between the capacity check and the increment.
    """

    def __init__(self, max_concurrent: int) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        self._max_concurrent = max_concurrent
        self._in_use = 0

    def try_acquire(self) -> bool:
        if self._in_use >= self._max_concurrent:
            return False
        self._in_use += 1
        return True

    def release(self) -> None:
        if self._in_use <= 0:
            raise RuntimeError("release() called without a matching try_acquire()")
        self._in_use -= 1

    @property
    def in_use(self) -> int:
        return self._in_use
