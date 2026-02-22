from src.repositories.base import SQLAlchemyRepository
from src.models.form import FormsTests

class FormsTestsRepository(SQLAlchemyRepository):
    model = FormsTests
