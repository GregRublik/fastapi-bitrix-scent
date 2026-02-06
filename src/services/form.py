from exceptions import ModelNoFoundException
from models.form import FormsTests
from repositories.base import SQLAlchemyRepository
from repositories.form import FormsTestsRepository
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from services.uow import UnitOfWorkService


class FormService:

    def __init__(self, repository: FormsTestsRepository, uow: UnitOfWorkService,):
        self.repository = repository
        self.uow = uow

    async def get_form_by_id(self, form_id: int) -> FormsTests:
        return await self.repository.get_by_id(self.uow.session, form_id)

    async def get_forms(self) -> List[FormsTestsRepository]:
        return await self.repository.get_all(self.uow.session)

    async def add_form_if_not_exists(self, body: dict) -> FormsTests:
        try:
            return await self.get_form_by_id(body.get('form_id'))
        except ModelNoFoundException:
            async with self.uow:
                return await self.repository.add_one(self.uow.session, body)
