from enum import Enum, auto

from chatroullete.cache import RoomCache
from chatroullete.db import SessionFactory
from chatroullete.models import User
from chatroullete.repository import (
    BlockRepository,
    RoomRepository,
    SearchQueueRepository,
    UserRepository,
)
from chatroullete.schemas import RoomDTO

# How many candidates may slip away (matched by someone else, changed their
# settings, ...) before the search gives up and leaves the user in the queue
MAX_ATTEMPTS = 20


class EnqueueResult(Enum):
    ENQUEUED = auto()
    ALREADY_SEARCHING = auto()
    IN_ROOM = auto()


def accepts(seeker: User, candidate: User) -> bool:
    """Whether ``candidate`` satisfies the preferences of ``seeker``.

    An unset preference accepts anyone; a set one requires a matching, known
    value on the candidate's side. The chat language is the exception: it only
    rules out a pair when both chose a language and the languages differ.
    """
    if seeker.pref_gender is not None and candidate.gender != seeker.pref_gender:
        return False
    if seeker.pref_age_min is not None and (
        candidate.age is None or candidate.age < seeker.pref_age_min
    ):
        return False
    if seeker.pref_age_max is not None and (
        candidate.age is None or candidate.age > seeker.pref_age_max
    ):
        return False
    if (
        seeker.chat_language is not None
        and candidate.chat_language is not None
        and candidate.chat_language != seeker.chat_language
    ):
        return False
    return True


def is_compatible(first: User, second: User) -> bool:
    return accepts(first, second) and accepts(second, first)


class MatchmakingService:
    """Search queue and pairing.

    Every change of a user's place in the queue happens under a lock on that
    user's row, and a pair is formed while holding both rows (always taken in
    ascending id order), so two searches can never claim the same user.
    """

    def __init__(self, sessions: SessionFactory, room_cache: RoomCache) -> None:
        self._sessions = sessions
        self._room_cache = room_cache

    async def enqueue(self, user_id: int) -> EnqueueResult:
        async with self._sessions.begin() as session:
            await UserRepository(session).get(user_id, for_update=True)
            room = await RoomRepository(session).get_open_by_user(user_id)
            if room is None:
                added = await SearchQueueRepository(session).add(user_id)
                return EnqueueResult.ENQUEUED if added else EnqueueResult.ALREADY_SEARCHING
            dto = RoomDTO.from_model(room)
        # The caller believed the user was free: Redis was out of date
        await self._room_cache.put_open(dto)
        return EnqueueResult.IN_ROOM

    async def cancel(self, user_id: int) -> bool:
        """Leave the queue. Returns False if the user was not waiting."""
        async with self._sessions.begin() as session:
            await UserRepository(session).get(user_id, for_update=True)
            return await SearchQueueRepository(session).remove([user_id]) > 0

    async def is_searching(self, user_id: int) -> bool:
        async with self._sessions() as session:
            return bool(await SearchQueueRepository(session).present([user_id]))

    async def try_match(self, user_id: int) -> RoomDTO | None:
        """Pair a waiting user with the longest-waiting compatible one.

        Returns the new room, or None if the user is not waiting any more
        (cancelled or already paired by the partner's search) or nobody fits
        yet, in which case they stay in the queue.
        """
        rejected: set[int] = set()
        for _ in range(MAX_ATTEMPTS):
            async with self._sessions.begin() as session:
                users = UserRepository(session)
                queue = SearchQueueRepository(session)

                me = await users.get(user_id)
                if me is None or not await queue.present([user_id]):
                    return None
                candidate_id = await queue.find_candidate(me, exclude=rejected)
                if candidate_id is None:
                    return None

                # The candidate was picked without a lock: lock both users and
                # make sure the pair is still valid.
                locked = await users.lock_many([user_id, candidate_id])
                waiting = await queue.present([user_id, candidate_id])
                if user_id not in waiting:
                    return None
                candidate = locked.get(candidate_id)
                if (
                    candidate is None
                    or candidate_id not in waiting
                    or not is_compatible(locked[user_id], candidate)
                    or await BlockRepository(session).exists_between(user_id, candidate_id)
                ):
                    rejected.add(candidate_id)
                    continue

                await queue.remove([user_id, candidate_id])
                room = await RoomRepository(session).create(user_id, candidate_id)
                dto = RoomDTO.from_model(room)
            await self._room_cache.put_open(dto)
            return dto
        return None
