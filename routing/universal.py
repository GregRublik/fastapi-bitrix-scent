from fastapi import APIRouter, Request
from core.config import logger, check_token
from db.database import get_bitrix_auth
from session_manager import session_manager
from core.config import templates, settings
from asyncio import sleep


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
    # client_secret: str,
    message: str,
    recipient: int
):
    # check_token(client_secret)
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
    response = await session.get(
        url=f"{settings.portal_url}rest/{method}?{params}",
        params={
            'auth': access[0]
        }
    )

    result = await response.json()
    return {'status_code': response.status, 'result': result, "methods": dir(result), }


@app_univers.post('/activity_close/', tags=["UNIVERSAL"], summary="Главный обработчик")
@logger.catch
async def main_handler(
    owner_id: int,
    type_owner_id: int,
    client_secret: str,
):
    check_token(client_secret)
    access = await get_bitrix_auth()
    session = await session_manager.get_session()
    list_activity = await session.get(
        url=(
            f"{settings.portal_url}rest/crm.activity.list?auth={access[0]}&"
            f"filter[OWNER_ID]={owner_id}]&filter[COMPLETED]=N&"
            f"select[0]=ID&select[1]=OWNER_ID&select[2]=OWNER_TYPE_ID&select[3]=TYPE_ID"
        ),
    )
    list_activity = await list_activity.json()
    for activity in list_activity["result"]:
        if activity["TYPE_ID"] == '4':
            await sleep(0.01)
            result = await session.post(
                url=f"{settings.portal_url}rest/crm.activity.update?",
                json={
                    "auth": access[0],
                    'id':activity["ID"],
                    "fields": {
                        # "OWNER_ID": activity['OWNER_ID'],
                        # "OWNER_TYPE_ID": activity['OWNER_TYPE_ID'],
                        "TYPE_ID": activity['TYPE_ID'],
                        "COMPLETED": 'Y'
                    }
                }
            )
