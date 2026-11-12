from datetime import datetime
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.enums import RoomStatus
from chatroullete.models import Room


class RoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user1_id: int, user2_id: int) -> Room:
        room = Room(user1_id=user1_id, user2_id=user2_id, status=RoomStatus.OPEN)
        self._session.add(room)
        await self._session.flush()
        await self._session.refresh(room)
        return room

    async def get(
        self, room_id: int, *, lock: Literal["share", "update"] | None = None
    ) -> Room | None:
        """``share`` lets other senders in but blocks closing, ``update`` is exclusive."""
        stmt = select(Room).where(Room.id == room_id)
        if lock is not None:
            stmt = stmt.with_for_update(read=lock == "share")
        return await self._session.scalar(stmt)

    async def get_open_by_user(self, user_id: int, *, for_update: bool = False) -> Room | None:
        stmt = select(Room).where(
            Room.status == RoomStatus.OPEN,
            or_(Room.user1_id == user_id, Room.user2_id == user_id),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await self._session.scalar(stmt)

    async def list_open_created_before(self, moment: datetime) -> list[tuple[int, datetime]]:
        stmt = select(Room.id, Room.created_at).where(
            Room.status == RoomStatus.OPEN, Room.created_at < moment
        )
        return [(row.id, row.created_at) for row in await self._session.execute(stmt)]
