from collections.abc import Collection

from sqlalchemy import ColumnElement, and_, delete, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.models import Block, SearchQueue, User


class SearchQueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: int) -> bool:
        """Return False if the user is already waiting."""
        stmt = (
            insert(SearchQueue)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=[SearchQueue.user_id])
            .returning(SearchQueue.user_id)
        )
        return await self._session.scalar(stmt) is not None

    async def remove(self, user_ids: Collection[int]) -> int:
        result = await self._session.execute(
            delete(SearchQueue).where(SearchQueue.user_id.in_(user_ids))
        )
        return result.rowcount

    async def present(self, user_ids: Collection[int]) -> set[int]:
        """Subset of ``user_ids`` that is waiting in the queue."""
        stmt = select(SearchQueue.user_id).where(SearchQueue.user_id.in_(user_ids))
        return set(await self._session.scalars(stmt))

    async def find_candidate(self, me: User, exclude: Collection[int] = ()) -> int | None:
        """Longest-waiting user who fits ``me`` and whom ``me`` fits.

        Mirrors ``services.matchmaking.is_compatible``; the row is not locked
        here, so the caller has to re-check after locking both users.
        """
        blocked = exists().where(
            or_(
                and_(Block.blocker_id == me.id, Block.blocked_id == User.id),
                and_(Block.blocker_id == User.id, Block.blocked_id == me.id),
            )
        )
        stmt = (
            select(SearchQueue.user_id)
            .join(User, User.id == SearchQueue.user_id)
            .where(
                User.id != me.id,
                User.id.not_in(exclude),
                *_candidate_fits_me(me),
                *_me_fits_candidate(me),
                ~blocked,
            )
            .order_by(SearchQueue.created_at, SearchQueue.user_id)
            .limit(1)
        )
        return await self._session.scalar(stmt)


def _candidate_fits_me(me: User) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if me.pref_gender is not None:
        conditions.append(User.gender == me.pref_gender)
    if me.pref_age_min is not None:
        conditions.append(User.age >= me.pref_age_min)
    if me.pref_age_max is not None:
        conditions.append(User.age <= me.pref_age_max)
    if me.chat_language is not None:
        # Symmetric: someone without a chosen language fits any language
        conditions.append(
            or_(User.chat_language.is_(None), User.chat_language == me.chat_language)
        )
    return conditions


def _me_fits_candidate(me: User) -> list[ColumnElement[bool]]:
    # A preference the candidate has set can only be met by a known value of mine
    def any_or(column: ColumnElement, matches: ColumnElement[bool] | None) -> ColumnElement[bool]:
        return column.is_(None) if matches is None else or_(column.is_(None), matches)

    return [
        any_or(User.pref_gender, User.pref_gender == me.gender if me.gender else None),
        any_or(User.pref_age_min, User.pref_age_min <= me.age if me.age is not None else None),
        any_or(User.pref_age_max, User.pref_age_max >= me.age if me.age is not None else None),
    ]
