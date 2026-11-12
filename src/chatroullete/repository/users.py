from collections.abc import Iterable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.enums import Language
from chatroullete.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int, *, for_update: bool = False) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return await self._session.scalar(stmt)

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        return await self._session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )

    async def lock_many(self, user_ids: Iterable[int]) -> dict[int, User]:
        """Lock user rows one by one in ascending id order, so that concurrent
        transactions locking the same users can never deadlock."""
        users: dict[int, User] = {}
        for user_id in sorted(set(user_ids)):
            user = await self.get(user_id, for_update=True)
            if user is not None:
                users[user_id] = user
        return users

    async def create_if_absent(
        self,
        telegram_user_id: int,
        ui_language: Language,
        username: str | None = None,
        full_name: str | None = None,
    ) -> None:
        stmt = (
            insert(User)
            .values(
                telegram_user_id=telegram_user_id,
                ui_language=ui_language,
                username=username,
                full_name=full_name,
            )
            .on_conflict_do_nothing(index_elements=[User.telegram_user_id])
        )
        await self._session.execute(stmt)

    async def update_profile(
        self, user_id: int, username: str | None, full_name: str | None
    ) -> None:
        await self._session.execute(
            update(User).where(User.id == user_id).values(username=username, full_name=full_name)
        )
