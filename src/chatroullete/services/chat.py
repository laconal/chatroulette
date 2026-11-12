import json
import logging
import time
from enum import Enum, auto
from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message, ReplyParameters
from sqlalchemy.ext.asyncio import AsyncSession

from chatroullete.cache import RoomCache
from chatroullete.db import SessionFactory
from chatroullete.enums import RoomStatus
from chatroullete.repository import MessageRepository, RoomRepository
from chatroullete.services.users import UserService

logger = logging.getLogger(__name__)

# The room stays share-locked while Telegram is called, keep that bounded
DELIVERY_TIMEOUT = 10

FILE_ATTRIBUTES = ("video", "animation", "audio", "voice", "video_note", "document", "sticker")


class RelayResult(Enum):
    DELIVERED = auto()
    FAILED = auto()
    UNSUPPORTED = auto()
    ROOM_CLOSED = auto()
    PARTNER_UNAVAILABLE = auto()


class ChatService:
    def __init__(
        self, sessions: SessionFactory, room_cache: RoomCache, users: UserService, bot: Bot
    ) -> None:
        self._sessions = sessions
        self._room_cache = room_cache
        self._users = users
        self._bot = bot

    async def relay(self, message: Message, sender_id: int, room_id: int) -> RelayResult:
        """Store the message and deliver a forward-protected copy to the partner.

        The room row is share-locked for the whole delivery: messages of both
        members pass concurrently, while closing the room (which needs the
        exclusive lock) waits, so nothing is delivered into a closed room.
        """
        async with self._sessions.begin() as session:
            result = await self._relay_locked(session, message, sender_id, room_id)
        if result is RelayResult.ROOM_CLOSED:
            await self._room_cache.forget_user_room(sender_id, room_id)
        return result

    async def _relay_locked(
        self, session: AsyncSession, message: Message, sender_id: int, room_id: int
    ) -> RelayResult:
        room = await RoomRepository(session).get(room_id, lock="share")
        if room is None or room.status is not RoomStatus.OPEN or sender_id not in room.members:
            return RelayResult.ROOM_CLOSED
        partner = await self._users.get(
            room.user2_id if sender_id == room.user1_id else room.user1_id
        )
        if partner is None:
            return RelayResult.FAILED

        messages = MessageRepository(session)
        reply_parameters = None
        if message.reply_to_message is not None:
            counterpart_id = await messages.find_counterpart_id(
                room_id, sender_id, message.reply_to_message.message_id
            )
            if counterpart_id is not None:
                reply_parameters = ReplyParameters(
                    message_id=counterpart_id, allow_sending_without_reply=True
                )

        text = message.text or message.caption
        content_type = ContentType(message.content_type).value
        record = await messages.add(
            room_id=room_id,
            sender_id=sender_id,
            content_type=content_type,
            text=text,
            file_id=_file_id(message),
            sender_message_id=message.message_id,
            raw=_dump(message),
        )

        try:
            copy = await self._bot.copy_message(
                chat_id=partner.telegram_user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                protect_content=True,
                reply_parameters=reply_parameters,
                request_timeout=DELIVERY_TIMEOUT,
            )
        except TelegramForbiddenError:
            return RelayResult.PARTNER_UNAVAILABLE
        except TelegramBadRequest as exc:
            logger.info("Message %s of room %s was not copied: %s", record.id, room_id, exc)
            if "can't be copied" in exc.message:
                return RelayResult.UNSUPPORTED
            return RelayResult.FAILED
        except TelegramAPIError:
            logger.exception("Failed to deliver message %s of room %s", record.id, room_id)
            return RelayResult.FAILED

        record.delivered_message_id = copy.message_id
        await self._room_cache.touch(
            room_id, sender_id, text or f"[{content_type}]", time.time()
        )
        return RelayResult.DELIVERED


def _file_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_id
    for attribute in FILE_ATTRIBUTES:
        media = getattr(message, attribute)
        if media is not None:
            return media.file_id
    return None


def _dump(message: Message) -> dict[str, Any]:
    return json.loads(message.model_dump_json(exclude_none=True))
