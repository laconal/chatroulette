from aiogram import Router
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated, Message

from chatroullete.i18n import Translator
from chatroullete.keyboards import reply
from chatroullete.schemas import UserDTO
from chatroullete.services import ConversationService, MatchmakingService, UserService

router = Router(name="menu")
# Included last: answers whatever no other router handled
fallback_router = Router(name="fallback")


@router.message(CommandStart())
async def start(
    message: Message,
    user: UserDTO,
    t: Translator,
    state: FSMContext,
    user_service: UserService,
    matchmaking: MatchmakingService,
) -> None:
    await state.clear()
    if message.from_user is not None:
        await user_service.update_profile(
            user.id, message.from_user.username, message.from_user.full_name
        )
    searching = await matchmaking.is_searching(user.id)
    await message.answer(
        t("start", find=t("btn_find")),
        reply_markup=reply.searching(t) if searching else reply.main_menu(t),
    )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def bot_blocked(
    event: ChatMemberUpdated,
    user: UserDTO,
    matchmaking: MatchmakingService,
    conversation: ConversationService,
) -> None:
    # The user can no longer be reached: free the queue slot and the partner
    await matchmaking.cancel(user.id)
    await conversation.leave(user.id)


@fallback_router.message()
async def unknown(
    message: Message, user: UserDTO, t: Translator, matchmaking: MatchmakingService
) -> None:
    if await matchmaking.is_searching(user.id):
        await message.answer(t("searching"), reply_markup=reply.searching(t))
    else:
        await message.answer(
            t("not_in_room", find=t("btn_find")), reply_markup=reply.main_menu(t)
        )
