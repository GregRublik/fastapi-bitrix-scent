from fastapi import APIRouter
from core.config import logger, check_token
from db.database import get_bitrix_auth
from session_manager import session_manager
from core.config import settings

app_user = APIRouter()


@app_user.post('/invite_an_employee/', tags=['USER'], summary="Приглашение сотрудников")
@logger.catch
async def invite_an_employee(
    email: str,
    client_secret: str,
    name: str | None = None,
    last_name: str | None = None,
    work_position: str | None = None,
    uf_department: str | None = None,
    adaptation_id: str | None = None,
):
    check_token(client_secret)
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    new_user = await session.post(
        url=f"{settings.portal_url}rest/user.add.json",
        params={
            'auth': access[0],
            'NAME': name,
            'LAST_NAME': last_name,
            'WORK_POSITION': work_position,
            'EMAIL': email,
            'UF_DEPARTMENT': uf_department
        }
    )
    new_user = await new_user.json()

    if 'error' in new_user:
        await session.get(
            url=f"{settings.hosting_url}send_message/",
            params={
                'client_secret': settings.client_secret,
                'message': (
                    f"Ошибка при приглашении: [url={settings.portal_url}page/hr/protsess_adaptatsii_sotrudnika_2/"
                    f"type/191/details/{adaptation_id}/]Процесс: [/url]{new_user['error_description']}"
                ),
                'recipient': 77297
            })
        return new_user

    await session.post(
        url=f"{settings.portal_url}rest/crm.item.update",
        params={
            'auth': access[0],
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
    client_secret: str
):
    """
    Метод для делегирования всех задач сотрудника на руководителя при его увольнении
    """
    check_token(client_secret)
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    list_task = await session.get(url=f"{settings.portal_url}rest/tasks.task.list",
                                  params={
                                      'auth': access[0],
                                      'filter[<REAL_STATUS]': 5,
                                      'filter[RESPONSIBLE_ID]': user_id,
                                      'select[0]': 'ID'})
    list_task = await list_task.json()
    user = await session.get(url=f"{settings.portal_url}rest/user.get",
                             params={'auth': access[0], 'ID': user_id})
    user = await user.json()

    department = await session.get(url=f"{settings.portal_url}rest/department.get",
                                   params={'auth': access[0], 'ID': user['result'][0]['UF_DEPARTMENT'][0]})
    department = await department.json()
    for task in list_task['result']['tasks']:
        await session.get(
            url=f"{settings.portal_url}rest/tasks.task.update?",
            params={
                'auth': access[0],
                'taskId': task['id'],
                'fields[RESPONSIBLE_ID]': department['result'][0]['UF_HEAD'],
            }
        )
    return {"status_code": 200, "list id task": list_task}
