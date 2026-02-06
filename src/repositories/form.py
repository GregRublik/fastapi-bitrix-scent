from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select

from repositories.base import SQLAlchemyRepository
from models.form import FormsTests

class FormsTestsRepository(SQLAlchemyRepository):
    model = FormsTests


@session_manager
async def del_test(session: AsyncSession, body):
    stmt = (
        delete(FormsTests)
        .where(FormsTests.form_id == body['form_id'])
    )
    result = await session.execute(stmt)
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
    result = await session.execute(stmt)
    await session.commit()
    return True
