from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select
from db.models import BitrixAuth
from db.config import settings
from sqlalchemy import update
from functools import wraps
import asyncio

engine = create_async_engine(
    url=settings.database_url_asyncmy,
    pool_size=5,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)


def session_manager(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with AsyncSessionLocal() as session:  # Открываем сессию
            return await func(session, *args, **kwargs)  # Передаем сессию в функцию
    return wrapper


@session_manager
async def get_bitrix_auth(session: AsyncSession):
    stmt = select(BitrixAuth.access_token, BitrixAuth.refresh_token)
    result = await session.execute(stmt)
    return result.first()
    

@session_manager
async def update_tokens(session: AsyncSession, access: str, refresh: str):
    stmt = (
        update(BitrixAuth)
        .where(BitrixAuth.name_app == 'Main')
        .values(
            access_token=access,
            refresh_token=refresh
        )
    )
    await session.execute(stmt)
    await session.commit()


