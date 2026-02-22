from typing import Annotated
from fastapi import APIRouter, Depends, Request, Form

from config import templates
from services.bitrix import BitrixService
from depends import get_bitrix_service

router = APIRouter()


@router.post("/install/", tags=['AUTHENTICATION'], summary="Установка приложения на портал")
async def app_install(
    request: Request,
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
    AUTH_ID: str = Form(...), # noqa
    REFRESH_ID: str = Form(...), # noqa
):
    """Обработчик для установки приложения"""
    await bitrix_service.app_install(access=AUTH_ID, refresh=REFRESH_ID)

    return templates.TemplateResponse(request, name="install.html")
