from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.base import SQLAlchemyRepository
from src.models.form import FormsTests
from pydantic import UUID4
from sqlalchemy import inspect, select
from exceptions import ModelNoFoundException, ModelMultipleResultsFoundException
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

class FormsTestsRepository(SQLAlchemyRepository):
    model = FormsTests

    async def get_by_id(self, session: AsyncSession, object_id: int | UUID4):
        pk = inspect(self.model).primary_key[0]

        stmt = (
            select(self.model)
            .where(self.model.form_id == object_id)
            .limit(1)
        )

        try:
            res = await session.execute(stmt)
            return res.scalar_one()
        except NoResultFound:
            raise ModelNoFoundException
        except MultipleResultsFound:
            raise ModelMultipleResultsFoundException
