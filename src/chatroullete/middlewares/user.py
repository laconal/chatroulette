import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from weakref import WeakValueDictionary

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Chat, TelegramObject, User

from chatroullete.i18n import Translator
from chatroullete.services import UserService

type Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class UserLockMiddleware(BaseMiddleware):
    """Handles updates of one user strictly one after another.

    Webhook updates are processed concurrently; this keeps a user's messages
    in the order they were sent and makes double taps harmless.
    """

    def __init__(self) -> None:
        self._locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        lock = self._locks.get(user.id)
        if lock is None:
            lock = self._locks[user.id] = asyncio.Lock()
        async with lock:
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Registers the sender on first contact and passes ``user`` and the
    translator ``t`` for their interface language to handlers."""

    def __init__(self, users: UserService) -> None:
        self._users = users

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        tg_user: User | None = data.get("event_from_user")
        chat: Chat | None = data.get("event_chat")
        # The bot only works in private chats
        if tg_user is None or tg_user.is_bot or (chat and chat.type != ChatType.PRIVATE):
            return None
        user = await self._users.get_or_create(
            tg_user.id, tg_user.username, tg_user.full_name, tg_user.language_code
        )
        data["user"] = user
        data["t"] = Translator(user.ui_language)
        return await handler(event, data)
