from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        room_id: int,
        sender_id: int,
        content_type: str,
        text: str | None,
        file_id: str | None,
        sender_message_id: int,
        raw: dict[str, Any],
    ) -> Message:
        message = Message(
            room_id=room_id,
            sender_id=sender_id,
            content_type=content_type,
            text=text,
            file_id=file_id,
            sender_message_id=sender_message_id,
            raw=raw,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def find_counterpart_id(self, room_id: int, user_id: int, message_id: int) -> int | None:
        """Map a message in the user's chat to the same message in the partner's chat."""
        stmt = (
            select(Message.sender_id, Message.sender_message_id, Message.delivered_message_id)
            .where(
                Message.room_id == room_id,
                or_(
                    and_(Message.sender_id == user_id, Message.sender_message_id == message_id),
                    and_(Message.sender_id != user_id, Message.delivered_message_id == message_id),
                ),
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        return row.delivered_message_id if row.sender_id == user_id else row.sender_message_id

    async def last_created_at(self, room_id: int) -> datetime | None:
        return await self._session.scalar(
            select(func.max(Message.created_at)).where(Message.room_id == room_id)
        )

    async def last_created_at_many(self, room_ids: list[int]) -> dict[int, datetime]:
        if not room_ids:
            return {}
        stmt = (
            select(Message.room_id, func.max(Message.created_at).label("last"))
            .where(Message.room_id.in_(room_ids))
            .group_by(Message.room_id)
        )
        return {row.room_id: row.last for row in await self._session.execute(stmt)}
