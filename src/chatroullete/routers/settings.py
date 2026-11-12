import re
from contextlib import suppress
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommandScopeChat, CallbackQuery, InlineKeyboardMarkup, Message

from chatroullete.commands import bot_commands
from chatroullete.config import Settings
from chatroullete.enums import Gender, Language
from chatroullete.formatting import format_rating
from chatroullete.i18n import LANGUAGE_NAMES, Translator, variants
from chatroullete.keyboards import inline, reply
from chatroullete.keyboards.inline import CLEAR, SettingsCallback, SettingsField
from chatroullete.schemas import UserDTO
from chatroullete.services import (
    ConversationService,
    MatchmakingService,
    ReviewService,
    UserService,
)

router = Router(name="settings")

DASH = "-–—"
AGE_RANGE = re.compile(rf"(\d{{1,3}})\s*[{DASH}]\s*(\d{{1,3}})")
AGE_FROM = re.compile(r"(\d{1,3})\s*\+")
AGE_TO = re.compile(rf"[{DASH}]\s*(\d{{1,3}})")
AGE_EXACT = re.compile(r"\d{1,3}")


class SettingsInput(StatesGroup):
    age = State()
    pref_age = State()


def parse_age_range(text: str, min_age: int, max_age: int) -> tuple[int | None, int | None] | None:
    """Parse "18-30", "18+", "-30" or "25" into (from, to); None if invalid."""
    text = text.strip()
    low: int | None = None
    high: int | None = None
    if match := AGE_RANGE.fullmatch(text):
        low, high = int(match[1]), int(match[2])
    elif match := AGE_FROM.fullmatch(text):
        low = int(match[1])
    elif match := AGE_TO.fullmatch(text):
        high = int(match[1])
    elif AGE_EXACT.fullmatch(text):
        low = high = int(text)
    else:
        return None
    if any(age is not None and not min_age <= age <= max_age for age in (low, high)):
        return None
    if low is not None and high is not None and low > high:
        return None
    return low, high


def _format_age_range(t: Translator, user: UserDTO) -> str:
    low, high = user.pref_age_min, user.pref_age_max
    if low is None and high is None:
        return t("value_any")
    if high is None:
        return t("age_from", min=low)
    if low is None:
        return t("age_to", max=high)
    return f"{low}–{high}"


async def _settings_text(t: Translator, user: UserDTO, review_service: ReviewService) -> str:
    def gender(value: Gender | None, unset: str) -> str:
        return t(f"gender_{value}") if value else t(unset)

    rating = await review_service.get_rating(user.id)
    return t(
        "settings",
        gender=gender(user.gender, "value_not_set"),
        age=user.age if user.age is not None else t("value_not_set"),
        chat_language=(
            LANGUAGE_NAMES[user.chat_language] if user.chat_language else t("value_any")
        ),
        ui_language=LANGUAGE_NAMES[user.ui_language],
        pref_gender=gender(user.pref_gender, "value_any"),
        pref_age=_format_age_range(t, user),
        rating=format_rating(t, rating),
    )


async def _edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    if isinstance(callback.message, Message):
        # Raised when the message already looks exactly like this
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.message(Command("settings"))
@router.message(F.text.in_(variants("btn_settings")))
async def open_settings(
    message: Message,
    user: UserDTO,
    t: Translator,
    state: FSMContext,
    review_service: ReviewService,
) -> None:
    await state.clear()
    await message.answer(
        await _settings_text(t, user, review_service), reply_markup=inline.settings_menu(t)
    )


@router.callback_query(SettingsCallback.filter(F.field == SettingsField.MENU))
async def back_to_menu(
    callback: CallbackQuery,
    user: UserDTO,
    t: Translator,
    state: FSMContext,
    review_service: ReviewService,
) -> None:
    await state.clear()
    await _edit(callback, await _settings_text(t, user, review_service), inline.settings_menu(t))


@router.callback_query(SettingsCallback.filter(F.value == ""))
async def open_field(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    t: Translator,
    state: FSMContext,
    config: Settings,
) -> None:
    field = callback_data.field
    await state.clear()
    match field:
        case SettingsField.GENDER:
            text = t("choose_gender")
            markup = inline.gender_choice(t, field, t("btn_not_set"))
        case SettingsField.PREF_GENDER:
            text = t("choose_pref_gender")
            markup = inline.gender_choice(t, field, t("btn_any"))
        case SettingsField.CHAT_LANGUAGE:
            text = t("choose_chat_language")
            markup = inline.language_choice(t, field, allow_any=True)
        case SettingsField.UI_LANGUAGE:
            text = t("choose_ui_language")
            markup = inline.language_choice(t, field, allow_any=False)
        case SettingsField.AGE:
            await state.set_state(SettingsInput.age)
            text = t("ask_age", min=config.min_age, max=config.max_age)
            markup = inline.input_prompt(t, field, t("btn_not_set"))
        case SettingsField.PREF_AGE:
            await state.set_state(SettingsInput.pref_age)
            text = t("ask_pref_age")
            markup = inline.input_prompt(t, field, t("btn_any"))
        case _:
            await callback.answer()
            return
    await _edit(callback, text, markup)


def _parse_choice(field: SettingsField, value: str) -> dict[str, Any] | None:
    """Settings changed by pressing ``value`` on the screen of ``field``."""
    try:
        match field:
            case SettingsField.GENDER | SettingsField.PREF_GENDER:
                return {field.value: None if value == CLEAR else Gender(value)}
            case SettingsField.CHAT_LANGUAGE:
                return {field.value: None if value == CLEAR else Language(value)}
            case SettingsField.UI_LANGUAGE:
                return {field.value: Language(value)}
            case SettingsField.AGE if value == CLEAR:
                return {"age": None}
            case SettingsField.PREF_AGE if value == CLEAR:
                return {"pref_age_min": None, "pref_age_max": None}
    except ValueError:
        pass
    return None


@router.callback_query(SettingsCallback.filter())
async def choose_value(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    user: UserDTO,
    state: FSMContext,
    bot: Bot,
    user_service: UserService,
    review_service: ReviewService,
    matchmaking: MatchmakingService,
    conversation: ConversationService,
) -> None:
    changes = _parse_choice(callback_data.field, callback_data.value)
    if changes is None:
        await callback.answer()
        return
    await state.clear()
    updated = await user_service.update_settings(user.id, **changes)
    t = Translator(updated.ui_language)
    await _edit(callback, await _settings_text(t, updated, review_service), inline.settings_menu(t))

    if updated.ui_language != user.ui_language and isinstance(callback.message, Message):
        # The reply keyboard and the command list are still in the old language
        searching = await matchmaking.is_searching(user.id)
        await callback.message.answer(
            t("language_changed"),
            reply_markup=reply.searching(t) if searching else reply.main_menu(t),
        )
        with suppress(TelegramAPIError):
            await bot.set_my_commands(
                bot_commands(t), scope=BotCommandScopeChat(chat_id=user.telegram_user_id)
            )
    # New settings may fit someone who is already waiting
    await conversation.match(user.id)


@router.message(SettingsInput.age, F.text)
async def input_age(
    message: Message,
    user: UserDTO,
    t: Translator,
    state: FSMContext,
    config: Settings,
    user_service: UserService,
    review_service: ReviewService,
    conversation: ConversationService,
) -> None:
    text = (message.text or "").strip()
    if not (text.isascii() and text.isdigit() and config.min_age <= int(text) <= config.max_age):
        await message.answer(t("invalid_age", min=config.min_age, max=config.max_age))
        return
    await _save_input(
        message, user, t, state, user_service, review_service, conversation, age=int(text)
    )


@router.message(SettingsInput.pref_age, F.text)
async def input_pref_age(
    message: Message,
    user: UserDTO,
    t: Translator,
    state: FSMContext,
    config: Settings,
    user_service: UserService,
    review_service: ReviewService,
    conversation: ConversationService,
) -> None:
    age_range = parse_age_range(message.text or "", config.min_age, config.max_age)
    if age_range is None:
        await message.answer(t("invalid_pref_age", min=config.min_age, max=config.max_age))
        return
    await _save_input(
        message,
        user,
        t,
        state,
        user_service,
        review_service,
        conversation,
        pref_age_min=age_range[0],
        pref_age_max=age_range[1],
    )


async def _save_input(
    message: Message,
    user: UserDTO,
    t: Translator,
    state: FSMContext,
    user_service: UserService,
    review_service: ReviewService,
    conversation: ConversationService,
    **changes: Any,
) -> None:
    await state.clear()
    updated = await user_service.update_settings(user.id, **changes)
    await message.answer(
        await _settings_text(t, updated, review_service), reply_markup=inline.settings_menu(t)
    )
    await conversation.match(user.id)
