from repositories.base import SQLAlchemyRepository
from models.bitrix import BitrixAuth

class BitrixRepository(SQLAlchemyRepository):
    model = BitrixAuth
