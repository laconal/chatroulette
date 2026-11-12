from enum import Enum, auto

from chatroullete.db import SessionFactory
from chatroullete.repository import BlockRepository, RoomRepository


class BlockResult(Enum):
    BLOCKED = auto()
    DUPLICATE = auto()
    UNAVAILABLE = auto()


class BlockService:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def block_partner(self, room_id: int, user_id: int) -> BlockResult:
        """Block the other member of a room the user took part in."""
        async with self._sessions.begin() as session:
            room = await RoomRepository(session).get(room_id)
            if room is None or user_id not in room.members:
                return BlockResult.UNAVAILABLE
            partner_id = room.user2_id if user_id == room.user1_id else room.user1_id
            added = await BlockRepository(session).add(user_id, partner_id)
        return BlockResult.BLOCKED if added else BlockResult.DUPLICATE
