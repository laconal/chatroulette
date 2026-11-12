from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from chatroullete.i18n import Translator, variants
from chatroullete.keyboards import reply
from chatroullete.schemas import UserDTO
from chatroullete.services import ConversationService, MatchmakingService
from chatroullete.services.matchmaking import EnqueueResult

router = Router(name="search")


async def start_search(
    message: Message,
    user: UserDTO,
    t: Translator,
    matchmaking: MatchmakingService,
    conversation: ConversationService,
) -> None:
    result = await matchmaking.enqueue(user.id)
    if result is EnqueueResult.IN_ROOM:
        await message.answer(t("in_room_hint"), reply_markup=reply.room(t))
        return
    # Sent before matching so that it always precedes "partner found"
    await message.answer(t("searching"), reply_markup=reply.searching(t))
    await conversation.match(user.id)


@router.message(Command("search", "next"))
@router.message(F.text.in_(variants("btn_find") | variants("btn_next")))
async def find(
    message: Message,
    user: UserDTO,
    t: Translator,
    state: FSMContext,
    matchmaking: MatchmakingService,
    conversation: ConversationService,
) -> None:
    await state.clear()
    await start_search(message, user, t, matchmaking, conversation)


@router.message(Command("stop"))
@router.message(F.text.in_(variants("btn_cancel_search") | variants("btn_end")))
async def cancel(
    message: Message, user: UserDTO, t: Translator, matchmaking: MatchmakingService
) -> None:
    if await matchmaking.cancel(user.id):
        text = t("search_cancelled")
    else:
        text = t("not_in_room", find=t("btn_find"))
    await message.answer(text, reply_markup=reply.main_menu(t))
