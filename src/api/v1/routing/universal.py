from typing import Annotated

from fastapi import APIRouter, Request, Depends
from config import logger
from config import templates, settings
from asyncio import sleep
from depends import verify_api_key

from services.bitrix import BitrixService

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
    bitrix_service: Annotated[BitrixService, Depends(BitrixService)],
    message: str,
    recipient: int,
    authorized: bool = Depends(verify_api_key),
):
    return await bitrix_service.send_request(
        f'55810/{settings.bitrix.key_405}/im.message.add.json',
        params={
            'DIALOG_ID': recipient,
            'MESSAGE': message
        }
    )


@app_univers.post('/main_handler/', tags=["UNIVERSAL"], summary="Главный обработчик")
@logger.catch
async def main_handler(
    bitrix_service: Annotated[BitrixService, Depends(BitrixService)],
    method: str,
    params: str | None = None,
    authorized: bool = Depends(verify_api_key),
):
    """
    Главный обработчик. Предназначен для отправки любых запросов согласно установленных прав приложения.
    """

    result = await bitrix_service.send_request(
        f'{method}?{params}'
        'get'
    )

    return {'result': result, "methods": dir(result)}


@app_univers.post('/activity_close/', tags=["UNIVERSAL"], summary="Главный обработчик")
@logger.catch
async def main_handler(
    owner_id: int,
    bitrix_service: Annotated[BitrixService, Depends(BitrixService)],
    authorized: bool = Depends(verify_api_key),
):
    list_activity = await bitrix_service.send_request(
        'crm.activity.list.json'
        'post',
        json={
            'filter': {
                'OWNER_ID': owner_id,
                'COMPLETED': 'N',
            },
            'select': ['ID', 'OWNER_ID', 'OWNER_TYPE_ID', 'TYPE_ID'],
        }
    )
    for activity in list_activity["result"]:
        if activity["TYPE_ID"] == '4':
            await sleep(0.01)
            result = await bitrix_service.send_request(
                'crm.activity.update',
                json={
                    'id': activity["ID"],
                    "fields": {
                        "TYPE_ID": activity['TYPE_ID'],
                        "COMPLETED": 'Y'
                    }
                }
            )
