from contextlib import suppress

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from chatroullete.i18n import Translator
from chatroullete.keyboards.inline import BlockCallback, RateCallback, without_rows
from chatroullete.schemas import UserDTO
from chatroullete.services import BlockService, ReviewService
from chatroullete.services.blocks import BlockResult
from chatroullete.services.reviews import ReviewResult

router = Router(name="reviews")

RATE_TEXTS = {
    ReviewResult.SAVED: "rated",
    ReviewResult.DUPLICATE: "already_rated",
    ReviewResult.UNAVAILABLE: "review_unavailable",
}
BLOCK_TEXTS = {
    BlockResult.BLOCKED: "blocked",
    BlockResult.DUPLICATE: "already_blocked",
    BlockResult.UNAVAILABLE: "review_unavailable",
}


async def _remove_buttons(callback: CallbackQuery, prefix: str) -> None:
    if isinstance(callback.message, Message):
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(
                reply_markup=without_rows(callback.message.reply_markup, prefix)
            )


@router.callback_query(RateCallback.filter())
async def rate(
    callback: CallbackQuery,
    callback_data: RateCallback,
    user: UserDTO,
    t: Translator,
    review_service: ReviewService,
) -> None:
    result = await review_service.rate(callback_data.room_id, user.id, callback_data.score)
    await callback.answer(t(RATE_TEXTS[result]))
    await _remove_buttons(callback, RateCallback.__prefix__)


@router.callback_query(BlockCallback.filter())
async def block(
    callback: CallbackQuery,
    callback_data: BlockCallback,
    user: UserDTO,
    t: Translator,
    block_service: BlockService,
) -> None:
    result = await block_service.block_partner(callback_data.room_id, user.id)
    await callback.answer(t(BLOCK_TEXTS[result]), show_alert=result is BlockResult.BLOCKED)
    await _remove_buttons(callback, BlockCallback.__prefix__)
