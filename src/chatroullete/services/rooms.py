from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.cache import RoomCache
from chatroullete.cache.rooms import NO_ROOM
from chatroullete.db import SessionFactory
from chatroullete.enums import CloseReason, RoomStatus
from chatroullete.models import Room
from chatroullete.repository import MessageRepository, RoomRepository
from chatroullete.schemas import RoomDTO


class RoomService:
    def __init__(self, sessions: SessionFactory, cache: RoomCache, idle_timeout: float) -> None:
        self._sessions = sessions
        self._cache = cache
        self._idle_timeout = idle_timeout

    async def get_active_room(self, user_id: int) -> RoomDTO | None:
        """The user's open room from Redis, or from the database if Redis has none.

        A cached answer may lag behind the database for a moment; every change
        made to a room re-checks its status under a row lock.
        """
        room_id = await self._cache.get_user_room_id(user_id)
        if room_id == NO_ROOM:
            return None
        if room_id is not None:
            cached = await self._cache.get_room(room_id)
            if cached is not None:
                if cached.status is RoomStatus.OPEN and user_id in cached.members:
                    return cached
                await self._cache.forget_user_room(user_id, room_id)

        async with self._sessions() as session:
            room = await RoomRepository(session).get_open_by_user(user_id)
        if room is None:
            await self._cache.mark_no_room(user_id)
            return None
        dto = RoomDTO.from_model(room)
        await self._cache.put_open(dto)
        return dto

    async def leave(self, user_id: int) -> RoomDTO | None:
        """Close the room the user is in. Returns None if they are not in one."""
        async with self._sessions.begin() as session:
            room = await RoomRepository(session).get_open_by_user(user_id, for_update=True)
            if room is None:
                return None
            dto = _close(room, CloseReason.LEFT, closed_by=user_id)
        await self._cache.put_closed(dto)
        return dto

    async def close(self, room_id: int, reason: CloseReason) -> RoomDTO | None:
        """Close the room. Returns None if it is already closed."""
        async with self._sessions.begin() as session:
            room = await RoomRepository(session).get(room_id, lock="update")
            if room is None or room.status is not RoomStatus.OPEN:
                return None
            dto = _close(room, reason)
        await self._cache.put_closed(dto)
        return dto

    async def find_idle_candidates(self) -> list[int]:
        """Open rooms that look idle; ``close_if_idle`` confirms it under a lock."""
        deadline = datetime.now(UTC) - timedelta(seconds=self._idle_timeout)
        async with self._sessions() as session:
            rooms = await RoomRepository(session).list_open_created_before(deadline)
            if not rooms:
                return []
            room_ids = [room_id for room_id, _ in rooms]
            cached = await self._cache.last_message_at_many(room_ids)
            # Rooms unknown to Redis (no messages yet, or Redis is down)
            missing = [room_id for room_id in room_ids if room_id not in cached]
            stored = await MessageRepository(session).last_created_at_many(missing)

        idle: list[int] = []
        for room_id, created_at in rooms:
            if room_id in cached:
                last_activity = datetime.fromtimestamp(cached[room_id], UTC)
            else:
                last_activity = stored.get(room_id, created_at)
            if last_activity <= deadline:
                idle.append(room_id)
        return idle

    async def close_if_idle(self, room_id: int) -> RoomDTO | None:
        """Close the room if it has had no messages for the idle timeout."""
        async with self._sessions.begin() as session:
            room = await RoomRepository(session).get(room_id, lock="update")
            if room is None or room.status is not RoomStatus.OPEN:
                return None
            # Senders hold a shared lock on the room until Redis knows about
            # their message, so the time read here cannot miss one.
            last_activity = await self._last_activity(session, room)
            if datetime.now(UTC) - last_activity < timedelta(seconds=self._idle_timeout):
                return None
            dto = _close(room, CloseReason.IDLE)
        await self._cache.put_closed(dto)
        return dto

    async def _last_activity(self, session: AsyncSession, room: Room) -> datetime:
        cached = await self._cache.last_message_at(room.id)
        if cached is not None:
            return datetime.fromtimestamp(cached, UTC)
        stored = await MessageRepository(session).last_created_at(room.id)
        return stored or room.created_at


def _close(room: Room, reason: CloseReason, closed_by: int | None = None) -> RoomDTO:
    room.status = RoomStatus.CLOSED
    room.close_reason = reason
    room.closed_by = closed_by
    room.closed_at = datetime.now(UTC)
    return RoomDTO.from_model(room)
