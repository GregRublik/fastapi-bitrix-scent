from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select
from db.models import BitrixAuth, FormsTests
from core.config import settings
from sqlalchemy import update, insert, delete
from functools import wraps
from core.config import settings


engine = create_async_engine(
    url=settings.db.database_url_asyncpg,
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
async def insert_tokens(session: AsyncSession, access: str, refresh: str):
    stmt = (
        insert(BitrixAuth)
        .values(
            owner=77297,
            name_app="Main",
            access_token=access,
            refresh_token=refresh,
            client_secret=settings.client_secret,
            client_id=settings.client_id
        )
    )
    await session.execute(stmt)
    await session.commit()


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


@session_manager
async def get_forms(session: AsyncSession):
    stmt = select(FormsTests.form_id, FormsTests.title, FormsTests.url, FormsTests.accesses)
    result = await session.execute(stmt)
    return result.all()


@session_manager
async def add_test(session: AsyncSession, body):

    stmt = (
        select(FormsTests.form_id, FormsTests.title, FormsTests.url, FormsTests.accesses)
        .where(FormsTests.form_id == body['form_id'])
    )
    result = await session.execute(stmt)
    await session.commit()

    if not result.first():
        stmt = (
            insert(FormsTests)
            .values(
                form_id=body['form_id'],
                url=body['url'],
                title=body['title']
            )
        )
        await session.execute(stmt)
        await session.commit()
        return True
    else:
        return False


@session_manager
async def del_test(session: AsyncSession, body):
    stmt = (
        delete(FormsTests)
        .where(FormsTests.form_id == body['form_id'])
    )
    await session.execute(stmt)
    await session.commit()
    return True


@session_manager
async def add_department(session: AsyncSession, body):
    stmt = (
        select(FormsTests.form_id, FormsTests.title, FormsTests.url, FormsTests.accesses)
        .where(FormsTests.form_id == body['form_id'])
    )
    result = await session.execute(stmt)
    await session.commit()
    list_depatrment = result.first()
    print(list_depatrment)
    a = list_depatrment[3]
    if list_depatrment[3]:
        a.append(str(body['department']))
        print('da')
    else:
        a = [str(body['department'])]
    print(a)

    stmt = (
        update(FormsTests)
        .where(FormsTests.form_id == body['form_id'])
        .values(
            accesses=a,
        )
    )
    await session.execute(stmt)
    await session.commit()
    return True
