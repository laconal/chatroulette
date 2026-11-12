from redis.asyncio import Redis

from chatroullete.cache.client import RedisCache
from chatroullete.schemas import UserDTO

TTL = 24 * 60 * 60


def _key(user_id: int) -> str:
    return f"cr:user:{user_id}:settings"


def _telegram_key(telegram_user_id: int) -> str:
    return f"cr:tg:{telegram_user_id}:settings"


class UserCache:
    """User settings in Redis, reachable both by the internal id (room members)
    and by the Telegram id (incoming updates)."""

    def __init__(self, cache: RedisCache) -> None:
        self._cache = cache

    async def get(self, user_id: int) -> UserDTO | None:
        return await self._get(_key(user_id))

    async def get_by_telegram_id(self, telegram_user_id: int) -> UserDTO | None:
        return await self._get(_telegram_key(telegram_user_id))

    async def put(self, user: UserDTO) -> None:
        """Store the settings just committed to the database."""
        await self._set(user, only_if_absent=False)

    async def backfill(self, user: UserDTO) -> None:
        """Store settings read from the database, never overwriting a fresher ``put``."""
        await self._set(user, only_if_absent=True)

    async def _get(self, key: str) -> UserDTO | None:
        raw = await self._cache.read(lambda r: r.get(key))
        if not raw:
            return None
        try:
            return UserDTO.from_json(raw)
        except (ValueError, KeyError):
            return None

    async def _set(self, user: UserDTO, *, only_if_absent: bool) -> None:
        keys = [_key(user.id), _telegram_key(user.telegram_user_id)]
        payload = user.to_json()

        async def op(redis: Redis) -> None:
            pipe = redis.pipeline(transaction=True)
            for key in keys:
                pipe.set(key, payload, ex=TTL, nx=only_if_absent)
            await pipe.execute()

        await self._cache.write(keys, op)
