from aiogram.types import BotCommand

from chatroullete.i18n import Translator

COMMANDS = ("start", "search", "next", "stop", "settings")


def bot_commands(t: Translator) -> list[BotCommand]:
    return [BotCommand(command=name, description=t(f"cmd_{name}")) for name in COMMANDS]
