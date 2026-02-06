from typing import Annotated

from fastapi import APIRouter, Depends
from config import logger
from db.database import get_bitrix_auth
from config import settings
from depends import verify_api_key
from services.bitrix import BitrixService

app_user = APIRouter()


@app_user.post('/invite_an_employee/', tags=['USER'], summary="Приглашение сотрудников")
@logger.catch
async def invite_an_employee(
    email: str,
    bitrix_service: Annotated[BitrixService, Depends(BitrixService)],
    name: str | None = None,
    last_name: str | None = None,
    work_position: str | None = None,
    uf_department: str | None = None,
    adaptation_id: str | None = None,
    authorized: bool = Depends(verify_api_key),
):
    new_user = await bitrix_service.send_request(
        'user.add.json',
        json={
            'NAME': name,
            'LAST_NAME': last_name,
            'WORK_POSITION': work_position,
            'EMAIL': email,
            'UF_DEPARTMENT': uf_department
        }
    )

    if 'error' in new_user:
        await bitrix_service.send_request(
            'im.message.add.json',
            json={
                'DIALOG_ID': 77297,
                'MESSAGE': (
                    f"Ошибка при приглашении: [url={settings.portal_url}page/hr/protsess_adaptatsii_sotrudnika_2/"
                    f"type/191/details/{adaptation_id}/]Процесс: [/url]{new_user['error_description']}"
                )
            }
        )
        return new_user

    await bitrix_service.send_request(
        'crm.item.update',
        json={
            'entityTypeId': 191,
            'id': adaptation_id,
            'fields[ufCrm19_1713532729]': new_user['result']
        }
    )
    return new_user


@app_user.post("/task_delegate/", tags=['USER'], summary="Делегирование задач на руководителя")
@logger.catch
async def task_delegate(
    user_id: int,
    bitrix_service: Annotated[BitrixService, Depends(BitrixService)],
    authorized: bool = Depends(verify_api_key),
):
    """
    Метод для делегирования всех задач сотрудника на руководителя при его увольнении
    """
    list_task = await bitrix_service.send_request(
        'tasks.task.list',
        json={
            'filter': {
                '<REAL_STATUS': 5,
                'RESPONSIBLE_ID': user_id,
            },
            'select': ['ID']
        }
    )

    user = await bitrix_service.send_request(
        'user.get',
        params={'ID': user_id},
    )

    department = await bitrix_service.send_request(
        'department.get',
        params={
            'ID': user['result'][0]['UF_DEPARTMENT'][0]
        }
    )
    for task in list_task['result']['tasks']:
        await bitrix_service.send_request(
            'tasks.task.update',
            json={
                'taskId': task['id'],
                'fields': {
                    'RESPONSIBLE_ID': department['result'][0]['UF_HEAD'],
                }
            }
        )
    return {"status_code": 200, "list id task": list_task}
