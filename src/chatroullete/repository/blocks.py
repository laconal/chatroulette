from sqlalchemy import and_, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.models import Block


class BlockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, blocker_id: int, blocked_id: int) -> bool:
        """Return False if the block already exists."""
        stmt = (
            insert(Block)
            .values(blocker_id=blocker_id, blocked_id=blocked_id)
            .on_conflict_do_nothing(index_elements=[Block.blocker_id, Block.blocked_id])
            .returning(Block.blocker_id)
        )
        return await self._session.scalar(stmt) is not None

    async def exists_between(self, first_id: int, second_id: int) -> bool:
        """True if either user has blocked the other."""
        stmt = select(
            exists().where(
                or_(
                    and_(Block.blocker_id == first_id, Block.blocked_id == second_id),
                    and_(Block.blocker_id == second_id, Block.blocked_id == first_id),
                )
            )
        )
        return bool(await self._session.scalar(stmt))
