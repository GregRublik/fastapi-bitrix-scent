from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select

from repositories.base import SQLAlchemyRepository
from models.form import FormsTests

class FormsTestsRepository(SQLAlchemyRepository):
    model = FormsTests
