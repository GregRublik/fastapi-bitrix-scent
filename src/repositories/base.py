from abc import ABC, abstractmethod

from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update, delete, inspect
from sqlalchemy.exc import IntegrityError, NoResultFound, MultipleResultsFound

from src.exceptions import ModelAlreadyExistsException, ModelNoFoundException, ModelMultipleResultsFoundException

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
            return result
        except NoResultFound:
            raise ModelNoFoundException

    async def add_one(self, session: AsyncSession, data: dict):
        dialect = session.get_bind().dialect.name

        if dialect == 'postgresql':
            # PostgreSQL поддерживает RETURNING
            stmt = insert(self.model).values(**data).returning(self.model)
            try:
                res = await session.execute(stmt)
                return res.scalar_one()
            except IntegrityError:
                raise ModelAlreadyExistsException

        elif dialect == 'mysql':
            # MySQL не поддерживает RETURNING
            stmt = insert(self.model).values(**data)
            try:
                await session.execute(stmt)
                await session.flush()

                # Получаем созданную запись (если есть ID)
                if hasattr(self.model, 'id'):
                    result = await session.execute(
                        select(self.model).order_by(self.model.id.desc()).limit(1)
                    )
                    return result.scalar_one()
                else:
                    # Если нет ID, возвращаем None или ищем по другим полям
                    return None

            except IntegrityError:
                raise ModelNoFoundException

    async def change_one(self, session: AsyncSession, object_id: int | UUID4, data: dict):
        pk = inspect(self.model).primary_key[0]
        dialect = session.get_bind().dialect.name

        if dialect == 'postgresql':
            # PostgreSQL поддерживает RETURNING
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

        else:  # MySQL и другие
            # Выполняем UPDATE
            stmt = (
                update(self.model)
                .where(pk == object_id)
                .values(**data)
            )

            result = await session.execute(stmt)

            if result.rowcount == 0:
                raise ModelNoFoundException

            # Получаем обновленную запись
            select_stmt = select(self.model).where(pk == object_id)
            res = await session.execute(select_stmt)
            updated_obj = res.scalar_one_or_none()

            if updated_obj is None:
                raise ModelNoFoundException

            return updated_obj

    async def delete_by_id(self, session: AsyncSession, object_id: int | UUID4):
        pk = inspect(self.model).primary_key[0]
        dialect = session.get_bind().dialect.name

        if dialect == 'postgresql':
            # PostgreSQL поддерживает RETURNING
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

        else:  # MySQL и другие
            # Сначала получаем объект
            select_stmt = select(self.model).where(pk == object_id)
            res = await session.execute(select_stmt)
            obj = res.scalar_one_or_none()

            if obj is None:
                raise ModelNoFoundException

            # Затем удаляем
            delete_stmt = delete(self.model).where(pk == object_id)
            await session.execute(delete_stmt)

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
