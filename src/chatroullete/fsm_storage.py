from collections.abc import Mapping
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from chatroullete.cache import RedisCache


class FallbackStorage(BaseStorage):
    """FSM storage in Redis that degrades to process memory while Redis is down.

    aiogram reads the state on every update, so without the fallback a Redis
    outage would stop the whole bot.
    """

    def __init__(self, primary: BaseStorage, cache: RedisCache) -> None:
        self._primary = primary
        self._cache = cache
        self._fallback = MemoryStorage()

    async def set_state(self, key: StorageKey, state: str | State | None = None) -> None:
        ok, _ = await self._cache.attempt(lambda: self._primary.set_state(key, state))
        if not ok:
            await self._fallback.set_state(key, state)

    async def get_state(self, key: StorageKey) -> str | None:
        ok, state = await self._cache.attempt(lambda: self._primary.get_state(key))
        return state if ok else await self._fallback.get_state(key)

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        ok, _ = await self._cache.attempt(lambda: self._primary.set_data(key, data))
        if not ok:
            await self._fallback.set_data(key, data)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        ok, data = await self._cache.attempt(lambda: self._primary.get_data(key))
        return data or {} if ok else await self._fallback.get_data(key)

    async def close(self) -> None:
        await self._fallback.close()
