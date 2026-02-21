import json

from fastapi import APIRouter, Request, Form, Depends
from config import templates, settings

from typing import Annotated
from services.bitrix import BitrixService
from depends import get_bitrix_service

router = APIRouter()


@router.post("/task_panel/", tags=['CONCORDING'], summary="Панель согласования для задач")
async def task_panel(
        request: Request,
        bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
        AUTH_ID: str = Form(), # noqa
        PLACEMENT_OPTIONS: str = Form(), # noqa
):
    """Панель для согласования договора в задаче"""

    placement_options = json.loads(PLACEMENT_OPTIONS)

    user = await bitrix_service.send_request(
        "user.current",
        "post",
        auth_token=AUTH_ID
    )
    user_admin = await bitrix_service.send_request(
        "user.admin",
        "post",
        auth_token=AUTH_ID
    )

    # получить привязанные элементы tasks.task.get | taskId=441215&select[0]=UF_CRM_TASK
    task = await bitrix_service.send_request(
        "tasks.task.get",
        json = {
            'taskId': placement_options['taskId'],
            'select': ['ACCOMPLICES', 'RESPONSIBLE_ID', 'UF_CRM_TASK', 'TITLE'],
        }
    )

    if 'ufCrmTask' not in task['result']['task']:
        return "Нет привязки элемента к CRM"
    if not task['result']['task']['ufCrmTask']:
        return "Нет привязки элемента к CRM"
    if task['result']['task']['ufCrmTask'][0][:4] != 'T83_':
        return "Нет привязки к процессу согласования договора"

    element_id = task['result']['task']['ufCrmTask'][0][4:]
    element = await bitrix_service.send_request(
        "crm.item.get",
        json={
            'entityTypeId': 131,
            'id': element_id,
            'select': [
                'ufCrm12_1709191865371',
                'ufCrm12_1709192259979',
                'ufCrm12_1708599567866',
                'ufCrm12_1708093511140',
                'CREATED_BY',
            ],
        }
    )
    accomplices = task['result']['task']['accomplices'][0]
    accountants = await bitrix_service.send_request(
        'user.search',
        json={
            'UF_DEPARTMENT': 114
        }
    )

    list_accountants = []
    for i in accountants["result"]:
        list_accountants.append(i["ID"])
    for a in task['result']['task']['accomplices']:
        if a in list_accountants:
            accomplices = a

    list_access = {
        '114': 'accountant',
        '94': 'lawyer',
        '0': 'admin'
    }  # бухгалтера, юристы
    if element['result']["item"]['ufCrm12_1712146917716']:
        attached_file = True
    else:
        attached_file = False
    approval_status = {
        "accountant": element['result']["item"]['ufCrm12_1709191865371'],
        "lawyer": element['result']["item"]['ufCrm12_1709192259979']
    }
    for i in user['result']['UF_DEPARTMENT']:  # перебираем все подразделения сотрудника
        if str(i) in list_access or user_admin['result']:  # Если есть разрешение
            if user_admin['result']:
                i = '0'
            return templates.TemplateResponse(
                request,
                name="task_panel.html",
                context={
                    'element_id': element_id,
                    'task_id': placement_options['taskId'],
                    'user_id': user['result']['ID'],
                    'access': list_access[str(i)],
                    'approval_status': approval_status,
                    'attached_file': attached_file,
                    'accomplices': accomplices,
                    'responsible': task['result']['task']['responsibleId'],
                    'title_task': task['result']['task']['title'],
                    'comment_accountant':
                        element['result']["item"]['ufCrm12_1708599567866'],
                    'created_by': element['result']["item"]['createdBy'],
                    'portal_url': settings.bitrix.portal_url,
                    'hosting_url': settings.hosting_url
                }
            )
    return "Доступ запрещен"
