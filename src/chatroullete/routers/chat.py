from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from chatroullete.enums import CloseReason
from chatroullete.i18n import Translator, variants
from chatroullete.keyboards import reply
from chatroullete.routers.filters import InRoom
from chatroullete.routers.search import start_search
from chatroullete.schemas import RoomDTO, UserDTO
from chatroullete.services import ChatService, ConversationService, MatchmakingService
from chatroullete.services.chat import RelayResult

# Everything a user sends while in a room lands here
router = Router(name="chat")
router.message.filter(InRoom())


@router.message(Command("stop"))
@router.message(F.text.in_(variants("btn_end")))
async def end_chat(message: Message, user: UserDTO, conversation: ConversationService) -> None:
    await conversation.leave(user.id)


@router.message(Command("next"))
@router.message(F.text.in_(variants("btn_next")))
async def next_partner(
    message: Message,
    user: UserDTO,
    t: Translator,
    matchmaking: MatchmakingService,
    conversation: ConversationService,
) -> None:
    await conversation.leave(user.id)
    await start_search(message, user, t, matchmaking, conversation)


@router.message(Command("start", "search", "settings"))
@router.message(F.text.in_(variants("btn_find") | variants("btn_settings")))
async def busy(message: Message, t: Translator) -> None:
    await message.answer(t("in_room_hint"), reply_markup=reply.room(t))


@router.message()
async def relay(
    message: Message,
    user: UserDTO,
    t: Translator,
    room: RoomDTO,
    chat_service: ChatService,
    conversation: ConversationService,
) -> None:
    match await chat_service.relay(message, user.id, room.id):
        case RelayResult.ROOM_CLOSED:
            await message.answer(
                t("not_in_room", find=t("btn_find")), reply_markup=reply.main_menu(t)
            )
        case RelayResult.PARTNER_UNAVAILABLE:
            await conversation.close(room.id, CloseReason.UNAVAILABLE)
        case RelayResult.UNSUPPORTED:
            await message.reply(t("unsupported"))
        case RelayResult.FAILED:
            await message.reply(t("not_delivered"))
