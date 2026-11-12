from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.models import Review
from chatroullete.schemas import Rating


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, room_id: int, author_id: int, target_id: int, score: int) -> bool:
        """Return False if the author has already reviewed this room."""
        stmt = (
            insert(Review)
            .values(room_id=room_id, author_id=author_id, target_id=target_id, score=score)
            .on_conflict_do_nothing(index_elements=[Review.room_id, Review.author_id])
            .returning(Review.id)
        )
        return await self._session.scalar(stmt) is not None

    async def get_rating(self, target_id: int) -> Rating:
        stmt = select(func.avg(Review.score), func.count()).where(Review.target_id == target_id)
        average, count = (await self._session.execute(stmt)).one()
        return Rating(average=float(average) if average is not None else None, count=count)
