from typing import Any

from aiogram.filters import Filter
from aiogram.types import Message

from chatroullete.schemas import UserDTO
from chatroullete.services import RoomService


class InRoom(Filter):
    """Passes when the sender is in an open room and hands it over as ``room``."""

    async def __call__(
        self, message: Message, user: UserDTO, room_service: RoomService
    ) -> bool | dict[str, Any]:
        room = await room_service.get_active_room(user.id)
        return {"room": room} if room is not None else False
