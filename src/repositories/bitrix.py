from src.repositories.base import SQLAlchemyRepository
from src.models.bitrix import BitrixAuth

class BitrixRepository(SQLAlchemyRepository):
    model = BitrixAuth
