import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from chatroullete.cache import RedisCache, RoomCache, UserCache
from chatroullete.commands import bot_commands
from chatroullete.config import Settings
from chatroullete.db import create_engine, create_session_factory
from chatroullete.fsm_storage import FallbackStorage
from chatroullete.i18n import TELEGRAM_LANGUAGES, Translator
from chatroullete.middlewares import UserLockMiddleware, UserMiddleware
from chatroullete.routers import build_router
from chatroullete.services import (
    BlockService,
    ChatService,
    ConversationService,
    IdleWatcher,
    MatchmakingService,
    Notifier,
    ReviewService,
    RoomService,
    UserService,
)

logger = logging.getLogger(__name__)

# Redis must fail fast for the database fallback to be usable
REDIS_TIMEOUT = 1.5
FSM_TTL = 60 * 60


async def _healthz(_: web.Request) -> web.Response:
    return web.Response(text="ok")


def create_dispatcher(config: Settings, bot: Bot) -> Dispatcher:
    engine = create_engine(config)
    sessions = create_session_factory(engine)
    redis = Redis(
        host=config.redis_host,
        port=config.redis_port,
        db=config.redis_db,
        decode_responses=True,
        socket_timeout=REDIS_TIMEOUT,
        socket_connect_timeout=REDIS_TIMEOUT,
        retry=Retry(NoBackoff(), 1),
    )
    cache = RedisCache(redis)
    room_cache = RoomCache(cache)

    storage = FallbackStorage(RedisStorage(redis, state_ttl=FSM_TTL, data_ttl=FSM_TTL), cache)
    dispatcher = Dispatcher(storage=storage)

    idle_timeout = config.room_idle_timeout_seconds
    user_service = UserService(sessions, UserCache(cache), config.default_language)
    room_service = RoomService(sessions, room_cache, idle_timeout)
    matchmaking = MatchmakingService(sessions, room_cache)
    review_service = ReviewService(sessions)
    notifier = Notifier(bot, user_service, review_service, storage, idle_timeout)
    conversation = ConversationService(matchmaking, room_service, notifier)
    idle_watcher = IdleWatcher(conversation, config.room_idle_check_interval_seconds)

    # Handlers and filters receive these by argument name
    dispatcher.workflow_data.update(
        config=config,
        user_service=user_service,
        room_service=room_service,
        matchmaking=matchmaking,
        review_service=review_service,
        block_service=BlockService(sessions),
        chat_service=ChatService(sessions, room_cache, user_service, bot),
        conversation=conversation,
    )
    dispatcher.update.outer_middleware(UserLockMiddleware())
    dispatcher.update.outer_middleware(UserMiddleware(user_service))
    dispatcher.include_router(build_router())

    async def on_startup() -> None:
        default = Translator(config.default_language)
        await bot.set_my_commands(bot_commands(default))
        for code, language in TELEGRAM_LANGUAGES.items():
            await bot.set_my_commands(bot_commands(Translator(language)), language_code=code)
        await bot.set_webhook(
            config.webhook_url,
            secret_token=config.webhook_secret.get_secret_value(),
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        idle_watcher.start()
        logger.info("Webhook set to %s", config.webhook_url)

    async def on_shutdown() -> None:
        await idle_watcher.stop()
        await redis.aclose()
        await engine.dispose()

    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
    return dispatcher


def create_app(config: Settings) -> web.Application:
    bot = Bot(config.bot_token.get_secret_value())
    dispatcher = create_dispatcher(config, bot)

    app = web.Application()
    app.router.add_get("/healthz", _healthz)
    SimpleRequestHandler(
        dispatcher, bot, secret_token=config.webhook_secret.get_secret_value()
    ).register(app, path=config.webhook_path)
    setup_application(app, dispatcher, bot=bot)
    return app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    config = Settings()
    web.run_app(create_app(config), host=config.webapp_host, port=config.webapp_port)
