from abc import ABC, abstractmethod

from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update, delete, inspect
from sqlalchemy.exc import IntegrityError, NoResultFound, MultipleResultsFound

from exceptions import ModelAlreadyExistsException, ModelNoFoundException, ModelMultipleResultsFoundException

class AbstractRepository(ABC):
    """
    Абстрактный репозиторий нужен чтобы при наследовании определяли его базовые методы работы с бд
    """
    model = None

    @abstractmethod
    async def add_one(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_all(self, *args, **kwargs):
        raise NotImplementedError


class SQLAlchemyRepository(AbstractRepository):
    """
    Репозиторий для работы с sqlalchemy
    """
    model = None

    async def get_first(self, session: AsyncSession):
        stmt = select(self.model).limit(1)
        try:
            result = await session.scalar(stmt)
            if result is None:
                raise ModelNoFoundException
            return result.to_read_model()
        except NoResultFound:
            raise ModelNoFoundException

    async def add_one(self, session: AsyncSession, data: dict):
        stmt = insert(self.model).values(**data).returning(self.model)
        try:
            res = await session.execute(stmt)
            return res.scalar_one()
        except IntegrityError:
            raise ModelAlreadyExistsException

    async def change_one(self, session: AsyncSession, object_id: int | UUID4, data: dict):

        pk = inspect(self.model).primary_key[0]

        stmt = (
            update(self.model)
            .where(pk == object_id)
            .values(**data)
            .returning(self.model)
        )

        try:
            res = await session.execute(stmt)
            return res.scalar_one()
        except NoResultFound:
            raise ModelNoFoundException

    async def delete_by_id(
        self,
        session: AsyncSession,
        object_id: int | UUID4
    ):
        pk = inspect(self.model).primary_key[0]

        stmt = (
            delete(self.model)
            .where(pk == object_id)
            .returning(self.model)
        )

        res = await session.execute(stmt)

        obj = res.scalar_one_or_none()

        if obj is None:
            raise ModelNoFoundException

        return obj

    async def get_all(self, session: AsyncSession):
        stmt = select(self.model)
        try:
            res = await session.execute(stmt)
            return [row[0].to_read_model() for row in res.all()]
        except NoResultFound:
            raise ModelNoFoundException

    async def get_by_id(self, session: AsyncSession, object_id: int | UUID4):
        pk = inspect(self.model).primary_key[0]

        stmt = (
            select(self.model)
            .where(self.model.id == object_id)
            .limit(1)
        )

        try:
            res = await session.execute(stmt)
            return res.scalar_one()
        except NoResultFound:
            raise ModelNoFoundException
        except MultipleResultsFound:
            raise ModelMultipleResultsFoundException
