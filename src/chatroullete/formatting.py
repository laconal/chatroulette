from chatroullete.i18n import Translator
from chatroullete.schemas import Rating


def format_rating(t: Translator, rating: Rating) -> str:
    if rating.average is None:
        return t("no_reviews")
    return f"⭐ {rating.average:.1f} ({rating.count})"
