import asyncio
import logging

from chatroullete.enums import CloseReason
from chatroullete.services.matchmaking import MatchmakingService
from chatroullete.services.notifier import Notifier
from chatroullete.services.rooms import RoomService

logger = logging.getLogger(__name__)


class ConversationService:
    """Room lifecycle together with the notifications around it."""

    def __init__(
        self, matchmaking: MatchmakingService, rooms: RoomService, notifier: Notifier
    ) -> None:
        self._matchmaking = matchmaking
        self._rooms = rooms
        self._notifier = notifier

    async def match(self, user_id: int) -> bool:
        """Try to pair a waiting user and announce the room to both members."""
        room = await self._matchmaking.try_match(user_id)
        if room is None:
            return False
        if not await self._notifier.room_started(room):
            await self.close(room.id, CloseReason.UNAVAILABLE)
        return True

    async def leave(self, user_id: int) -> bool:
        """Close the user's room. Returns False if they were not in one."""
        room = await self._rooms.leave(user_id)
        if room is None:
            return False
        await self._notifier.room_closed(room)
        return True

    async def close(self, room_id: int, reason: CloseReason) -> None:
        room = await self._rooms.close(room_id, reason)
        if room is not None:
            await self._notifier.room_closed(room)

    async def close_idle_rooms(self) -> None:
        for room_id in await self._rooms.find_idle_candidates():
            room = await self._rooms.close_if_idle(room_id)
            if room is not None:
                await self._notifier.room_closed(room)


class IdleWatcher:
    """Background task closing rooms that have been silent for too long."""

    def __init__(self, conversation: ConversationService, interval: float) -> None:
        self._conversation = conversation
        self._interval = interval
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="idle-watcher")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self._conversation.close_idle_rooms()
            except Exception:
                logger.exception("Idle room check failed")
