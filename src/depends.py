from fastapi import HTTPException, status, security, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from aiohttp import ClientSession

from src.repositories.bitrix import BitrixRepository
from src.repositories.form import FormsTestsRepository
from src.services import bitrix, form, uow
from src.db.database import get_db_session
from src.config import settings, SessionManager


def verify_api_key(credentials: security.HTTPAuthorizationCredentials = Depends(security.HTTPBearer())) -> bool:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")

    try:
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")
        if credentials.credentials != settings.bitrix.client_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")
        return True
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

def get_bitrix_repository(session: AsyncSession = Depends(get_db_session)) -> BitrixRepository:
    return BitrixRepository()

def get_uow(
    session: AsyncSession = Depends(get_db_session),
) -> uow.UnitOfWorkService:
    return uow.UnitOfWorkService(session)

def get_bitrix_service(
    http_session: ClientSession = Depends(SessionManager.get_session),
    repository: BitrixRepository = Depends(get_bitrix_repository),
    unit_of_work_service: uow.UnitOfWorkService = Depends(get_uow),
) -> bitrix.BitrixService:
    return bitrix.BitrixService(http_session, repository, unit_of_work_service)

def get_form_repository() -> FormsTestsRepository:
    return FormsTestsRepository()

def get_uow_service(
    session: AsyncSession = Depends(get_db_session),
) -> uow.UnitOfWorkService:
    return uow.UnitOfWorkService(session)

def get_form_service(
    repository: FormsTestsRepository = Depends(get_form_repository),
    unit_of_work_service: uow.UnitOfWorkService = Depends(get_uow_service),
) -> form.FormService:
    return form.FormService(repository, unit_of_work_service)

def get_http_session(
        http_session: ClientSession = Depends(SessionManager.get_session),
) -> ClientSession:
    return http_session
