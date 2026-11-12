from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from chatroullete.enums import Gender, Language
from chatroullete.i18n import LANGUAGE_NAMES, Translator


class SettingsField(StrEnum):
    MENU = "menu"
    GENDER = "gender"
    AGE = "age"
    CHAT_LANGUAGE = "chat_language"
    UI_LANGUAGE = "ui_language"
    PREF_GENDER = "pref_gender"
    PREF_AGE = "pref_age"


# SettingsCallback.value: empty opens the field's screen, CLEAR resets the field
CLEAR = "-"


class SettingsCallback(CallbackData, prefix="set"):
    field: SettingsField
    value: str = ""


class RateCallback(CallbackData, prefix="rate"):
    room_id: int
    score: int


class BlockCallback(CallbackData, prefix="block"):
    room_id: int


def _button(text: str, callback: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback.pack())


def _back(t: Translator) -> list[InlineKeyboardButton]:
    return [_button(t("btn_back"), SettingsCallback(field=SettingsField.MENU))]


def review(t: Translator, room_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _button(f"{score} ⭐", RateCallback(room_id=room_id, score=score))
                for score in range(1, 6)
            ],
            [_button(t("btn_block"), BlockCallback(room_id=room_id))],
        ]
    )


def without_rows(markup: InlineKeyboardMarkup | None, prefix: str) -> InlineKeyboardMarkup | None:
    """Drop the rows whose buttons belong to the callback ``prefix``."""
    if markup is None:
        return None
    rows = [
        row
        for row in markup.inline_keyboard
        if not any((button.callback_data or "").startswith(f"{prefix}:") for button in row)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def settings_menu(t: Translator) -> InlineKeyboardMarkup:
    def open_field(field: SettingsField) -> InlineKeyboardButton:
        return _button(t(f"btn_set_{field}"), SettingsCallback(field=field))

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [open_field(SettingsField.GENDER), open_field(SettingsField.AGE)],
            [open_field(SettingsField.CHAT_LANGUAGE), open_field(SettingsField.UI_LANGUAGE)],
            [open_field(SettingsField.PREF_GENDER), open_field(SettingsField.PREF_AGE)],
        ]
    )


def gender_choice(t: Translator, field: SettingsField, clear_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _button(t(f"gender_{gender}"), SettingsCallback(field=field, value=gender))
                for gender in Gender
            ],
            [_button(clear_text, SettingsCallback(field=field, value=CLEAR))],
            _back(t),
        ]
    )


def language_choice(
    t: Translator, field: SettingsField, *, allow_any: bool
) -> InlineKeyboardMarkup:
    languages = [
        _button(LANGUAGE_NAMES[language], SettingsCallback(field=field, value=language))
        for language in Language
    ]
    rows = [languages[:2], languages[2:]]
    if allow_any:
        rows.append([_button(t("btn_any"), SettingsCallback(field=field, value=CLEAR))])
    rows.append(_back(t))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def input_prompt(t: Translator, field: SettingsField, clear_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button(clear_text, SettingsCallback(field=field, value=CLEAR))],
            _back(t),
        ]
    )
