from typing import Annotated
from asyncio import sleep
from fastapi import APIRouter, Request, Depends

from config import templates, settings
from depends import verify_api_key, get_bitrix_service
from services.bitrix import BitrixService


router = APIRouter(tags=["UNIVERSAL"])


@router.get("/", summary="Главная страница")
async def main(
    request: Request
):
    return templates.TemplateResponse(request, name="main.html")

@router.post("/", summary="Главная страница")
async def main(
    request: Request
):
    return templates.TemplateResponse(request, name="main.html")


@router.get("/send_message/", summary="Отправить сообщение от лизы")
async def send_message(
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
    message: str,
    recipient: int,
    authorized: bool = Depends(verify_api_key),
):
    return await bitrix_service.send_request(
        f'55810/{settings.bitrix.key_405}/im.message.add',
        params={
            'DIALOG_ID': recipient,
            'MESSAGE': message
        }
    )


@router.post('/main_handler/', summary="Главный обработчик")
async def main_handler(
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
    endpoint: str,
    json: dict | None = None,
    authorized: bool = Depends(verify_api_key),
):
    """
    Главный обработчик. Предназначен для отправки любых запросов согласно установленных прав приложения.
    """

    result = await bitrix_service.send_request(
        endpoint,
        'post',
        json=json
    )

    return {'result': result, "methods": dir(result)}



@router.post('/activity_close/', summary="Главный обработчик")
async def main_handler(
    owner_id: int,
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
    authorized: bool = Depends(verify_api_key),
):
    list_activity = await bitrix_service.send_request(
        'crm.activity.list'
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
