from aiogram import Router

from chatroullete.routers import chat, menu, reviews, search, settings


def build_router() -> Router:
    root = Router(name="root")
    root.include_routers(
        # First: while the user is in a room their messages belong to the chat
        chat.router,
        menu.router,
        search.router,
        settings.router,
        reviews.router,
        menu.fallback_router,
    )
    return root
