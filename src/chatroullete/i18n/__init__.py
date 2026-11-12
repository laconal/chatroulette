from chatroullete.enums import Language
from chatroullete.i18n.locales import en, ru, uz, uz_cyrl

TEXTS: dict[Language, dict[str, str]] = {
    Language.RU: ru.TEXTS,
    Language.EN: en.TEXTS,
    Language.UZ: uz.TEXTS,
    Language.UZ_CYRL: uz_cyrl.TEXTS,
}

# Shown in their own language regardless of the interface language
LANGUAGE_NAMES: dict[Language, str] = {
    Language.RU: "Русский",
    Language.EN: "English",
    Language.UZ: "O‘zbekcha",
    Language.UZ_CYRL: "Ўзбекча",
}

# Telegram client language -> interface language for new users
TELEGRAM_LANGUAGES: dict[str, Language] = {
    "ru": Language.RU,
    "en": Language.EN,
    "uz": Language.UZ,
}


class Translator:
    def __init__(self, language: Language) -> None:
        self.language = language

    def __call__(self, key: str, **params: object) -> str:
        text = TEXTS[self.language][key]
        return text.format(**params) if params else text


def variants(key: str) -> frozenset[str]:
    """The text of ``key`` in every language, for matching reply-keyboard buttons."""
    return frozenset(texts[key] for texts in TEXTS.values())
