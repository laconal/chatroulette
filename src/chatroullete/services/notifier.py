import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from chatroullete.enums import CloseReason
from chatroullete.formatting import format_rating
from chatroullete.i18n import Translator
from chatroullete.keyboards import inline, reply
from chatroullete.schemas import RoomDTO, UserDTO
from chatroullete.services.reviews import ReviewService
from chatroullete.services.users import UserService

logger = logging.getLogger(__name__)


class Notifier:
    """Messages the bot sends to room members on its own behalf."""

    def __init__(
        self,
        bot: Bot,
        users: UserService,
        reviews: ReviewService,
        fsm_storage: BaseStorage,
        idle_timeout: float,
    ) -> None:
        self._bot = bot
        self._users = users
        self._reviews = reviews
        self._fsm_storage = fsm_storage
        self._idle_minutes = max(1, round(idle_timeout / 60))

    async def room_started(self, room: RoomDTO) -> bool:
        """Tell both members they are paired. False if either cannot be reached."""
        reached = await asyncio.gather(
            *(self._announce_start(room, user_id) for user_id in room.members)
        )
        return all(reached)

    async def room_closed(self, room: RoomDTO) -> None:
        await asyncio.gather(*(self._announce_close(room, user_id) for user_id in room.members))

    async def _announce_start(self, room: RoomDTO, user_id: int) -> bool:
        user = await self._users.get(user_id)
        if user is None:
            return False
        t = Translator(user.ui_language)
        # A half-finished settings input must not swallow chat messages later
        chat_id = user.telegram_user_id
        key = StorageKey(bot_id=self._bot.id, chat_id=chat_id, user_id=chat_id)
        await self._fsm_storage.set_state(key, None)

        rating = await self._reviews.get_rating(room.partner_of(user_id))
        text = f"{t('found')}\n\n{t('partner_rating', rating=format_rating(t, rating))}"
        return await self._send(user, text, reply.room(t))

    async def _announce_close(self, room: RoomDTO, user_id: int) -> None:
        user = await self._users.get(user_id)
        if user is None:
            return
        t = Translator(user.ui_language)
        if room.close_reason is CloseReason.IDLE:
            text = t("closed_idle", minutes=self._idle_minutes)
        elif room.close_reason is CloseReason.UNAVAILABLE:
            text = t("closed_unavailable")
        elif room.closed_by == user_id:
            text = t("closed_by_you")
        else:
            text = t("closed_by_partner")
        if await self._send(user, text, reply.main_menu(t)):
            await self._send(user, t("rate_prompt"), inline.review(t, room.id))

    async def _send(
        self, user: UserDTO, text: str, markup: ReplyKeyboardMarkup | InlineKeyboardMarkup
    ) -> bool:
        """False only if the user has blocked the bot or deleted their account."""
        try:
            await self._bot.send_message(user.telegram_user_id, text, reply_markup=markup)
        except TelegramForbiddenError:
            return False
        except TelegramAPIError:
            logger.exception("Failed to notify user %s", user.id)
        return True
