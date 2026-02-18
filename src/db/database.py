from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from config import settings
from typing import AsyncGenerator

Base = declarative_base()


def create_session_maker(db_url: str) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=create_async_engine(
            url=db_url,
            pool_size=5,
            max_overflow=10
        ),
        expire_on_commit=False,
        class_=AsyncSession
    )


async_session_maker = create_session_maker(settings.db.dsn_asyncpg)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
