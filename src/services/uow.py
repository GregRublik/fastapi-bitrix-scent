from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWorkService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self._rollback()
        else:
            await self._commit()

    async def _commit(self):
        await self.session.commit()

    async def _rollback(self):
        await self.session.rollback()