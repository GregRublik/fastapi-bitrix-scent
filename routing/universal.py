from fastapi import APIRouter, Request
from core.config import logger
from db.database import get_bitrix_auth
from functions import check_token
from session_manager import session_manager
from core.config import templates, settings


app_univers = APIRouter()


@app_univers.get("/", tags=['UNIVERSAL'], summary="Главная страница")
@logger.catch
async def main(
    request: Request
):
    return templates.TemplateResponse(request, name="main.html")


@app_univers.get("/send_message/", tags=['UNIVERSAL'], summary="Отправить сообщение от лизы")
@logger.catch
async def send_message(
    client_secret: str,
    message: str,
    recipient: int
):
    check_token(client_secret)
    session = await session_manager.get_session()
    result = await session.get(
        url=f"{settings.portal_url}rest/55810/{settings.key_405}/im.message.add.json",
        params={
            'DIALOG_ID': recipient,
            'MESSAGE': message
        }
    )
    result = await result.json()
    return result


@app_univers.post('/main_handler/', tags=["UNIVERSAL"], summary="Главный обработчик")
@logger.catch
async def main_handler(
    method: str,
    client_secret: str,
    params: str | None = None,
):
    """
    Главный обработчик. Предназначен для отправки любых запросов согласно установленных прав приложения.
    """
    check_token(client_secret)
    access = await get_bitrix_auth()
    session = await session_manager.get_session()
    result = await session.get(
        url=f"{settings.portal_url}rest/{method}?{params}",
        params={
            'auth': access[0]
        }
    )
    result = await result.json()
    return {'status_code': 200, 'result': result}
