from enum import Enum, auto

from chatroullete.db import SessionFactory
from chatroullete.enums import RoomStatus
from chatroullete.repository import ReviewRepository, RoomRepository
from chatroullete.schemas import Rating


class ReviewResult(Enum):
    SAVED = auto()
    DUPLICATE = auto()
    UNAVAILABLE = auto()


class ReviewService:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def rate(self, room_id: int, author_id: int, score: int) -> ReviewResult:
        """Rate the partner from a finished room, once per room."""
        if not 1 <= score <= 5:
            return ReviewResult.UNAVAILABLE
        async with self._sessions.begin() as session:
            room = await RoomRepository(session).get(room_id)
            if (
                room is None
                or room.status is not RoomStatus.CLOSED
                or author_id not in room.members
            ):
                return ReviewResult.UNAVAILABLE
            target_id = room.user2_id if author_id == room.user1_id else room.user1_id
            added = await ReviewRepository(session).add(room_id, author_id, target_id, score)
        return ReviewResult.SAVED if added else ReviewResult.DUPLICATE

    async def get_rating(self, user_id: int) -> Rating:
        async with self._sessions() as session:
            return await ReviewRepository(session).get_rating(user_id)
