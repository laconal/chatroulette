from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from chatroullete.config import DatabaseSettings

type SessionFactory = async_sessionmaker[AsyncSession]


def create_engine(config: DatabaseSettings) -> AsyncEngine:
    return create_async_engine(config.database_url, pool_size=20, max_overflow=20, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    return async_sessionmaker(engine, expire_on_commit=False)
