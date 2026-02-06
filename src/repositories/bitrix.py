from repositories.base import SQLAlchemyRepository
from models.bitrix import BitrixAuth

class BitrixRepository(SQLAlchemyRepository):
    model = BitrixAuth


# @session_manager
# async def get_bitrix_auth(session: AsyncSession):
#     stmt = select(BitrixAuth.access_token, BitrixAuth.refresh_token)
#     result = await session.execute(stmt)
#     return result.first()
#
#
# @session_manager
# async def update_tokens(session: AsyncSession, access: str, refresh: str):
#     stmt = (
#         update(BitrixAuth)
#         .where(BitrixAuth.name_app == 'Main')
#         .values(
#             access_token=access,
#             refresh_token=refresh
#         )
#     )
#     await session.execute(stmt)
#     await session.commit()
