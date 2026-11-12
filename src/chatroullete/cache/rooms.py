from datetime import datetime

from redis.asyncio import Redis

from chatroullete.cache.client import RedisCache
from chatroullete.enums import RoomStatus
from chatroullete.schemas import RoomDTO

NO_ROOM = 0
NO_ROOM_TTL = 60
CLOSED_ROOM_TTL = 60 * 60
PREVIEW_LENGTH = 200

# Deletes the key only while it still holds the expected value
DELETE_IF_EQUAL = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end return 0"


def _room_key(room_id: int) -> str:
    return f"cr:room:{room_id}"


def _user_key(user_id: int) -> str:
    return f"cr:user:{user_id}:room"


class RoomCache:
    """Room state in Redis.

    ``cr:room:{id}`` is a hash with the room status, its members and the last
    message (text preview, sender, unix time). ``cr:user:{id}:room`` points a
    user to their open room. The database stays the source of truth.
    """

    def __init__(self, cache: RedisCache) -> None:
        self._cache = cache

    async def get_user_room_id(self, user_id: int) -> int | None:
        """Room id, ``NO_ROOM`` if the user is known to have none, ``None`` if unknown."""
        raw = await self._cache.read(lambda r: r.get(_user_key(user_id)))
        return int(raw) if raw is not None else None

    async def mark_no_room(self, user_id: int) -> None:
        key = _user_key(user_id)
        # NX: must not overwrite a room set by a concurrent match
        await self._cache.write([key], lambda r: r.set(key, NO_ROOM, ex=NO_ROOM_TTL, nx=True))

    async def forget_user_room(self, user_id: int, room_id: int) -> None:
        key = _user_key(user_id)
        await self._cache.write([key], lambda r: r.eval(DELETE_IF_EQUAL, 1, key, room_id))

    async def get_room(self, room_id: int) -> RoomDTO | None:
        data = await self._cache.read(lambda r: r.hgetall(_room_key(room_id)))
        if not data:
            return None
        try:
            return RoomDTO(
                id=room_id,
                user1_id=int(data["user1_id"]),
                user2_id=int(data["user2_id"]),
                status=RoomStatus(data["status"]),
                created_at=datetime.fromisoformat(data["created_at"]),
            )
        except (KeyError, ValueError):
            return None

    async def put_open(self, room: RoomDTO) -> None:
        room_key = _room_key(room.id)
        user_keys = [_user_key(user_id) for user_id in room.members]

        async def op(redis: Redis) -> None:
            pipe = redis.pipeline(transaction=True)
            pipe.hset(room_key, mapping=_room_fields(room))
            for key in user_keys:
                pipe.set(key, room.id)
            await pipe.execute()

        await self._cache.write([room_key, *user_keys], op)

    async def put_closed(self, room: RoomDTO) -> None:
        room_key = _room_key(room.id)
        user_keys = [_user_key(user_id) for user_id in room.members]

        async def op(redis: Redis) -> None:
            pipe = redis.pipeline(transaction=True)
            pipe.hset(room_key, mapping=_room_fields(room))
            pipe.expire(room_key, CLOSED_ROOM_TTL)
            for key in user_keys:
                pipe.eval(DELETE_IF_EQUAL, 1, key, room.id)
            await pipe.execute()

        await self._cache.write([room_key, *user_keys], op)

    async def touch(self, room_id: int, sender_id: int, preview: str, at: float) -> None:
        """Remember the last message of the room and when it was sent."""
        key = _room_key(room_id)
        fields = {
            "last_message": preview[:PREVIEW_LENGTH],
            "last_message_from": sender_id,
            "last_message_at": at,
        }
        await self._cache.write([key], lambda r: r.hset(key, mapping=fields))

    async def last_message_at(self, room_id: int) -> float | None:
        raw = await self._cache.read(lambda r: r.hget(_room_key(room_id), "last_message_at"))
        return float(raw) if raw is not None else None

    async def last_message_at_many(self, room_ids: list[int]) -> dict[int, float]:
        if not room_ids:
            return {}

        async def op(redis: Redis) -> list[str | None]:
            pipe = redis.pipeline(transaction=False)
            for room_id in room_ids:
                pipe.hget(_room_key(room_id), "last_message_at")
            return await pipe.execute()

        values = await self._cache.read(op) or []
        return {
            room_id: float(raw) for room_id, raw in zip(room_ids, values) if raw is not None
        }


def _room_fields(room: RoomDTO) -> dict[str, str | int]:
    return {
        "status": room.status.value,
        "user1_id": room.user1_id,
        "user2_id": room.user2_id,
        "created_at": room.created_at.isoformat(),
    }
