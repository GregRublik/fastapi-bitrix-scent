from fastapi import APIRouter
from core.config import logger
from fastapi import Request, Form
from db.database import update_tokens, get_bitrix_auth, insert_tokens
from core.config import settings, templates, check_token
from session_manager import session_manager

app_auth = APIRouter()


@app_auth.post("/install/", tags=['AUTHENTICATION'], summary="Установка приложения на портал")
@logger.catch
async def app_install(
    request: Request,
    AUTH_ID: str = Form(...),
    REFRESH_ID: str = Form(...)
):
    """Обработчик для установки приложения"""
    print(await request.form())
    # await update_tokens(access=AUTH_ID, refresh=REFRESH_ID)
    await insert_tokens(access=AUTH_ID, refresh=REFRESH_ID)
    await reboot_tokens(client_secret=settings.client_secret)
    return templates.TemplateResponse(request, name="install.html")


@app_auth.post("/reboot_tokens/", tags=['AUTHENTICATION'], summary="Обновление токенов")
@logger.catch
async def reboot_tokens(
        client_secret: str
) -> dict:
    """С помощью client_secret приложения можно обновить токены для дальнейшей работы приложения"""
    check_token(client_secret)
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    response = await session.get(
        url=f"https://oauth.bitrix.info/oauth/token/",
        params={
            'grant_type': 'refresh_token',
            'client_id': settings.client_id,
            'client_secret': client_secret,
            'refresh_token': access[1]

        }
    )
    if response.status != 200:
        return {'status_code': response.status, 'error': 'Failed to update tokens.'}
    result = await response.json()
    await update_tokens(access=result["access_token"], refresh=result["refresh_token"])
    return {'status_code': 200, 'result': result}
