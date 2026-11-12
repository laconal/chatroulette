from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from chatroullete.i18n import Translator


def _keyboard(*rows: list[str]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text) for text in row] for row in rows],
        resize_keyboard=True,
    )


def main_menu(t: Translator) -> ReplyKeyboardMarkup:
    return _keyboard([t("btn_find")], [t("btn_settings")])


def searching(t: Translator) -> ReplyKeyboardMarkup:
    return _keyboard([t("btn_cancel_search")])


def room(t: Translator) -> ReplyKeyboardMarkup:
    return _keyboard([t("btn_next"), t("btn_end")])
