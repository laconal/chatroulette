import logging
import time
from collections.abc import Awaitable, Callable, Iterable

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

FAILURES = (RedisError, OSError, TimeoutError)


class RedisCache:
    """Best-effort access to Redis.

    Any operation may fail: reads then report a miss and writes are dropped, so
    callers fall back to the database. While Redis is down it is probed at most
    once per ``retry_interval`` instead of on every call. Keys whose write was
    lost are remembered and deleted as soon as Redis answers again, so a value
    that went stale during an outage is never served afterwards.
    """

    def __init__(self, redis: Redis, retry_interval: float = 5.0) -> None:
        self._redis = redis
        self._retry_interval = retry_interval
        self._down_until = 0.0
        self._stale: set[str] = set()

    async def attempt[T](self, op: Callable[[], Awaitable[T]]) -> tuple[bool, T | None]:
        """Run a Redis-backed operation, returning ``(succeeded, result)``."""
        if not await self._ready():
            return False, None
        try:
            return True, await op()
        except FAILURES as exc:
            self._trip(exc)
            return False, None

    async def read[T](self, op: Callable[[Redis], Awaitable[T]]) -> T | None:
        _, value = await self.attempt(lambda: op(self._redis))
        return value

    async def write(self, keys: Iterable[str], op: Callable[[Redis], Awaitable[object]]) -> bool:
        """Run a write touching ``keys``; if it is lost the keys are invalidated later."""
        ok, _ = await self.attempt(lambda: op(self._redis))
        if not ok:
            self._stale.update(keys)
        return ok

    async def _ready(self) -> bool:
        if time.monotonic() < self._down_until:
            return False
        if self._stale:
            stale = tuple(self._stale)
            try:
                await self._redis.delete(*stale)
            except FAILURES as exc:
                self._trip(exc)
                return False
            self._stale.difference_update(stale)
            logger.info("Redis is back, invalidated %d stale keys", len(stale))
        return True

    def _trip(self, exc: BaseException) -> None:
        self._down_until = time.monotonic() + self._retry_interval
        logger.warning("Redis unavailable, falling back to the database: %r", exc)
