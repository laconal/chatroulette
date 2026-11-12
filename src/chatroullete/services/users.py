from typing import Any

from chatroullete.cache import UserCache
from chatroullete.db import SessionFactory
from chatroullete.enums import Language
from chatroullete.i18n import TELEGRAM_LANGUAGES
from chatroullete.repository import UserRepository
from chatroullete.schemas import UserDTO

SETTINGS_FIELDS = frozenset(
    {
        "gender",
        "age",
        "chat_language",
        "ui_language",
        "pref_gender",
        "pref_age_min",
        "pref_age_max",
    }
)


class UserService:
    def __init__(
        self, sessions: SessionFactory, cache: UserCache, default_language: Language
    ) -> None:
        self._sessions = sessions
        self._cache = cache
        self._default_language = default_language

    async def get(self, user_id: int) -> UserDTO | None:
        """User settings from Redis, or from the database if Redis has none."""
        cached = await self._cache.get(user_id)
        if cached is not None:
            return cached
        async with self._sessions() as session:
            user = await UserRepository(session).get(user_id)
        if user is None:
            return None
        dto = UserDTO.from_model(user)
        await self._cache.backfill(dto)
        return dto

    async def get_or_create(
        self,
        telegram_user_id: int,
        username: str | None = None,
        full_name: str | None = None,
        language_code: str | None = None,
    ) -> UserDTO:
        """Find the user by Telegram id (Redis first), registering them if new."""
        cached = await self._cache.get_by_telegram_id(telegram_user_id)
        if cached is not None:
            return cached
        ui_language = TELEGRAM_LANGUAGES.get(language_code or "", self._default_language)
        async with self._sessions.begin() as session:
            repo = UserRepository(session)
            user = await repo.get_by_telegram_id(telegram_user_id)
            if user is None:
                await repo.create_if_absent(telegram_user_id, ui_language, username, full_name)
                user = await repo.get_by_telegram_id(telegram_user_id)
                assert user is not None
            dto = UserDTO.from_model(user)
        await self._cache.backfill(dto)
        return dto

    async def update_profile(
        self, user_id: int, username: str | None, full_name: str | None
    ) -> None:
        async with self._sessions.begin() as session:
            await UserRepository(session).update_profile(user_id, username, full_name)

    async def update_settings(self, user_id: int, **changes: Any) -> UserDTO:
        """Change settings under a row lock, then refresh them in Redis."""
        unknown = changes.keys() - SETTINGS_FIELDS
        if unknown:
            raise ValueError(f"Unknown settings: {sorted(unknown)}")
        async with self._sessions.begin() as session:
            user = await UserRepository(session).get(user_id, for_update=True)
            if user is None:
                raise LookupError(f"User {user_id} does not exist")
            for field, value in changes.items():
                setattr(user, field, value)
            await session.flush()
            dto = UserDTO.from_model(user)
        await self._cache.put(dto)
        return dto
