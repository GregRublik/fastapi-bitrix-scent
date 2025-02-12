import ast
import platform
import uvicorn
import datetime
from contextlib import asynccontextmanager
from loguru import logger
from urllib.parse import parse_qs
from functions import check_token
from a2wsgi import ASGIMiddleware
from fastapi import FastAPI, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import portal_url, hosting_url, client_id, secret, key_405
from session_manager import SessionManager
from db.database import update_tokens, get_bitrix_auth, get_forms, add_test, del_test, add_department
import json


session_manager = SessionManager.get_instance()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await session_manager.close_session()


logger.add("logs/debug.log", format="{time} - {level} - {message}", level="INFO", rotation="5 MB", compression="zip")
app = FastAPI(lifespan=lifespan)
application = ASGIMiddleware(app)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
scheduler = AsyncIOScheduler()


@app.get("/", tags=['MAIN'])
@logger.catch
async def main(
    request: Request
):
    return templates.TemplateResponse(request, name="main.html")


@app.post("/", tags=['MAIN'])
@logger.catch
async def main(
    request: Request
):
    return templates.TemplateResponse(request, name="main.html")


@app.post("/install/", tags=['AUTHENTICATION'])
@logger.catch
async def app_install(
    request: Request
):
    """Обработчик для установки приложения"""
    data = await request.body()
    data_parsed = parse_qs(data.decode())
    await update_tokens(access=data_parsed["AUTH_ID"][0], refresh=data_parsed["REFRESH_ID"][0])
    await reboot_tokens(client_secret=secret)
    return templates.TemplateResponse(request, name="install.html")


@app.post("/reboot_tokens/", tags=['AUTHENTICATION'])
@logger.catch
async def reboot_tokens(client_secret: str) -> dict:
    """С помощью client_secret приложения можно обновить токены для дальнейшей работы приложения"""
    check_token(client_secret)
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    response = await session.get(
        url=f"https://oauth.bitrix.info/oauth/token/",
        params={
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': access[1]

        }
    )
    if response.status != 200:
        return {'status_code': response.status, 'error': 'Failed to update tokens.'}
    result = await response.json()
    await update_tokens(access=result["access_token"], refresh=result["refresh_token"])
    return {'status_code': 200, 'result': result}


@app.get("/send_message/", tags=['UNIVERSAL'])
@logger.catch
async def send_message(
    client_secret: str,
    message: str,
    recipient: int
):
    check_token(client_secret)
    session = await session_manager.get_session()
    result = await session.get(
        url=f"{portal_url}rest/55810/{key_405}/im.message.add.json",
        params={
            'DIALOG_ID': recipient,
            'MESSAGE': message
        }
    )
    result = await result.json()
    return result


@app.post('/main_handler/', tags=["UNIVERSAL"])
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
    result = await session.get(url=f"{portal_url}rest/{method}?{params}",
                               params={
                                   'auth': access[0]
                               })
    result = await result.json()
    return {'status_code': 200, 'result': result}


@app.post("/activity_update/", tags=['PURCHASE VED'])
@logger.catch
async def activity_update(
    data: str = Body()
):
    """
    Обработчик для дела. При изменении дела он проверяет, принадлежит ли оно
    воронке "закуп ВЭД" и если да то записывает "дату прихода на наш склад"
    в историю. Также он проверяет, что дело начинается на "подтвердите дату"
    """
    data_parsed = parse_qs(data)
    activity_id = data_parsed['data[FIELDS][ID]'][0]
    access = await get_bitrix_auth()
    session = await session_manager.get_session()
    activity = await session.get(url=f"{portal_url}rest/crm.activity.get",
                                 params={
                                     'auth': access[0],
                                     'ID': activity_id
                                 })
    activity = await activity.json()
    if (activity['result']['OWNER_TYPE_ID'] == '1058' and activity['result']['COMPLETED'] == 'Y'
            and 'Подтвердите дату' in activity['result']['DESCRIPTION']):
        element = await session.get(
                url=f"{portal_url}rest/crm.item.get",
                params={'auth': access[0],
                        'entityTypeId': 1058,
                        'id': activity['result']['OWNER_ID']
                        })
        element = await element.json()
        field_history = element['result']['item']['ufCrm41_1724744699216']
        if element['result']['item']['stageId'] in ['DT1058_69:UC_1CO49M',
                                                    'DT1058_69:UC_D22INS',
                                                    'DT1058_69:UC_74Q414']:
            fields_to_url = ''
            if field_history:
                pass
            else:
                field_history.append('')
            index, new_recording = '', ''
            for index, v in enumerate(field_history):
                fields_to_url += f"fields[ufCrm41_1724744699216][{index}]=" + str(v) + "&"
                new_recording = f"Дата мониторинга: {datetime.date.today().isoformat()} | \
                Дата прихода на наш склад: {element['result']['item']['ufCrm41_1724228599427'][:10]}"
            fields_to_url += f"fields[ufCrm41_1724744699216][{index + 1}]={new_recording}"
            update_element = await session.get(
                    url=f"{portal_url}rest/crm.item.update?{fields_to_url}",
                    params={'auth': access[0],
                            'entityTypeId': 1058,
                            'id': activity['result']['OWNER_ID']}
            )
            final_result = await update_element.json()
            return {"status_code": 200, 'result': final_result}
    return {'status_code': 400, 'result': 'you invalid'}


@app.post("/task_delegate/", tags=['USER'])
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
    list_task = await session.get(url=f"{portal_url}rest/tasks.task.list",
                                  params={
                                      'auth': access[0],
                                      'filter[<REAL_STATUS]': 5,
                                      'filter[RESPONSIBLE_ID]': user_id,
                                      'select[0]': 'ID'})
    list_task = await list_task.json()
    user = await session.get(url=f"{portal_url}rest/user.get",
                             params={'auth': access[0], 'ID': user_id})
    user = await user.json()

    department = await session.get(url=f"{portal_url}rest/department.get",
                                   params={'auth': access[0], 'ID': user['result'][0]['UF_DEPARTMENT'][0]})
    department = await department.json()
    for task in list_task['result']['tasks']:
        await session.get(
            url=f"{portal_url}rest/tasks.task.update?",
            params={
                'auth': access[0],
                'taskId': task['id'],
                'fields[RESPONSIBLE_ID]': department['result'][0]['UF_HEAD'],
            }
        )
    return {"status_code": 200, "list id task": list_task}


@app.post("/handler/", tags=['PURCHASE VED'])
@logger.catch
async def handler(
    id_element: str,
    date_old: str,
    date_new: str,
    link_element: str,
    name_element: str,
    client_secret: str
):
    check_token(client_secret)
    """
    Создание сообщения с кнопкой, для подтверждения об ознакомлении.
    """
    access = await get_bitrix_auth()
    session = await session_manager.get_session()
    result = await session.get(
        url=f"{portal_url}rest/im.message.add",
        params={
            'auth': access[0],
            'MESSAGE': f"""[SIZE=16][B]⚠️Подтвердите получение информации о смене даты прихода 
c {date_old} на новую {date_new} по сделке: [URL={link_element}]{name_element}[/URL][/B][/SIZE]""",
            'KEYBOARD[0][TEXT]': 'Подтвердить',
            'KEYBOARD[0][LINK]': f'{hosting_url}handler_button/?item_id={id_element}&client_secret={client_secret}',
            'KEYBOARD[0][BG_COLOR_TOKEN]': 'alert',
            'DIALOG_ID': 77297,
            'KEYBOARD[0][BLOCK]': 'Y'
        }
    )
    message = await result.json()
    id_message = message['result']
    element = await session.get(
            url=f"{portal_url}rest/crm.item.get",
            params={
                'auth': access[0],
                'entityTypeId': 1058,
                'id': id_element
            }
    )
    update_element = await element.json()
    url_new_id_message = ''
    if update_element['result']['item']['ufCrm41_1725436565']:
        for i, v in enumerate(update_element['result']['item']['ufCrm41_1725436565']):
            url_new_id_message += f'fields[ufCrm41_1725436565][{i + 1}]={v}&'
    url_new_id_message += f'fields[ufCrm41_1725436565][0]={id_message}&'
    await session.get(
        url=f"{portal_url}rest/crm.item.update?{url_new_id_message}",
        params={
            'auth': access[0],
            'entityTypeId': 1058,
            'id': id_element,
        }
    )
    return {"status_code": 200, 'result': await result.json()}


@app.get('/handler_button/', tags=['PURCHASE VED'])
@logger.catch
async def handler_button(
    item_id: int,
    client_secret: str
):
    """
    Срабатывает при нажатии на кнопку "Подтвердить в сообщении."
    """
    check_token(client_secret)
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    element = await session.get(
        url=f"{portal_url}rest/crm.item.get",
        params={
            'auth': access[0],
            'entityTypeId': 1058,
            'id': item_id
        }
    )
    element = await element.json()

    await session.get(
        url=f"{portal_url}rest/crm.timeline.comment.add?",
        params={
            'auth': access[0],
            'fields[AUTHOR_ID]': 77297,
            'fields[ENTITY_TYPE]': 'DYNAMIC_1058',
            'fields[ENTITY_ID]': item_id,
            'fields[COMMENT]': (f'Инициатор ознакомлен с новой датой прихода! Дата ознакомления: '
                                f'{datetime.date.today().isoformat()}'),

        }
    )
    for i in element['result']['item']['ufCrm41_1725436565']:
        if i != 0:
            await session.get(
                url=f"{portal_url}rest/im.message.update?",
                params={
                    'BOT_ID': 78051,
                    'MESSAGE_ID': i,
                    'auth': access[0],
                    'KEYBOARD': 0,
                    'MESSAGE': f"""[SIZE=16][B]✔️Подтверждено получение информации о смене даты прихода на новую 
{element['result']['item']['ufCrm41_1724228599427'][:10]} по сделке: 
[URL={portal_url}crm/type/1058/details/{item_id}/]{element['result']['item']['title']}[/URL][/B][/SIZE]"""
                }
            )

    await session.get(
        url=f"{portal_url}rest/crm.item.update?",
        params={
            'auth': access[0],
            'entityTypeId': 1058,
            'id': item_id,
            'fields[ufCrm41_1725436565]': ''
        }
    )

    return RedirectResponse(url=f"{portal_url}crm/type/1058/details/{item_id}/")


@app.post('/form_to_sp/')
@logger.catch
async def form_to_sp(
    request: Request
):
    data = await request.body()
    data_parsed = json.loads(data.decode())
    params = data_parsed['params']
    session = await session_manager.get_session()
    access = await get_bitrix_auth()

    await session.post(
        url=f"{portal_url}rest/crm.item.add?",
        params={
            'auth': access[0],
            'entityTypeId': 1098,
            'fields[ufCrm59_1738313884]': params['points'],
            'fields[ufCrm59_1738322964]': params['max_points'],
            'fields[ufCrm59_1738323186]': params['user_id'],
            'fields[ufCrm59_1738323573]': params['form_id'],
            'fields[ufCrm59_1738648993]': params['answer_id'],
            'fields[title]': params['form_name']
        }
    )


@app.post('/employee_testing/', tags=['FORMS'])
@logger.catch
async def employee_testing(
    request: Request,
):
    """Список тестов к которым есть доступ, а также информация о завершении последних"""
    data = await request.body()
    data_parsed = parse_qs(data.decode())
    forms = await get_forms()
    session = await session_manager.get_session()

    user = await session.post(
        url=f"{portal_url}rest/user.current?",
        params={'auth': data_parsed['AUTH_ID'][0]}
    )
    user = await user.json()
    list_tests = await session.post(
        url=f"{portal_url}rest/crm.item.list?",
        params={
            'auth': data_parsed['AUTH_ID'][0],
            'entityTypeId': 1098,
            'filter[ufCrm59_1738323186]': user['result']['ID']
        }
    )
    list_tests = await list_tests.json()
    list_end_test = {}
    for i in list_tests['result']['items']:
        if i['ufCrm59_1738323573'] in list_end_test:
            a = datetime.datetime.strptime(list_end_test[i['ufCrm59_1738323573']]['date'], "%d.%m.%Y %H:%M:%S")
            b = datetime.datetime.fromisoformat(i['createdTime'])
            if a < b.replace(tzinfo=None):
                list_end_test[i['ufCrm59_1738323573']] = {
                    'date': datetime.datetime.fromisoformat(i['createdTime']).strftime("%d.%m.%Y %H:%M:%S"),
                    'points': i['ufCrm59_1738313884'],
                    'max_points': i['ufCrm59_1738322964'],
                    'count': list_end_test[i['ufCrm59_1738323573']]['count'] + 1}
            else:
                list_end_test[i['ufCrm59_1738323573']]['count'] += 1
        else:
            list_end_test[i['ufCrm59_1738323573']] = {
                'date': datetime.datetime.fromisoformat(i['createdTime']).strftime("%d.%m.%Y %H:%M:%S"),
                'points': i['ufCrm59_1738313884'],
                'max_points': i['ufCrm59_1738322964'],
                'count': 1}
    forms_access = []
    for department_id in user['result']['UF_DEPARTMENT']:
        forms_access = [form for form in forms if form[3] and str(department_id) in form[3]]
    return templates.TemplateResponse(
        request,
        name="employee_testing.html",
        context={
            "hosting_url": hosting_url,
            "forms": forms_access,
            'user_id': user['result']['ID'],
            'list_end_test': list_end_test
        }
    )


@app.post('/create_forms/', tags=['FORMS'])
@logger.catch
async def create_forms(
    request: Request
):
    # return templates.TemplateResponse(request, name="install.html")
    data = await request.body()
    data_parsed = parse_qs(data.decode())
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    count = 0
    list_all_department = []
    while True:
        list_department = await session.get(
            url=f"{portal_url}rest/department.get/",
            params={
                'auth': access[0],
                'sort': 'ID',
                'start': count
            }
        )
        list_department = await list_department.json()
        list_all_department += list_department['result']
        if 'next' in list_department:
            count = list_department['next']
        else:
            break
    forms = await get_forms()
    dict_department = {}
    for i in list_all_department:
        dict_department[i['ID']] = i['NAME']
    return templates.TemplateResponse(
        request,
        name="create_forms.html",
        context={
            "list_forms": forms,
            "list_department": list_all_department,
            "dict_department": dict_department,
            "hosting_url": hosting_url
        }
    )


@app.post("/control_forms/", tags=['FORMS'])
async def control_forms(request: Request):
    data = await request.body()

    body = json.loads(data.decode())
    if body['type'] == 'add_test':
        body['form_id'] = body['url'][26:50:]
        await add_test(body)
    elif body['type'] == 'add_access':
        await add_department(body)
    elif body['type'] == 'test_delete':
        await del_test(body)


@app.post('/invite_an_employee/', tags=['HR'])
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
        url=f"{portal_url}rest/user.add.json",
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
            url=f"{hosting_url}send_message/",
            params={
                'client_secret': secret,
                'message': f'''Ошибка при приглашении: [url={portal_url}page/hr/protsess_adaptatsii_sotrudnika_2/type/191/details/{adaptation_id}/]Процесс: [/url]{new_user['error_description']}''',
                'recipient': 77297
            })
        return new_user

    await session.post(
        url=f"{portal_url}rest/crm.item.update",
        params={
            'auth': access[0],
            'entityTypeId': 191,
            'id': adaptation_id,
            'fields[ufCrm19_1713532729]': new_user['result']
        }
    )
    return new_user


@app.post("/task_panel/", tags=['CONCORDING'])
@logger.catch
async def task_panel(
    request: Request,
):
    # return templates.TemplateResponse(request, name="install.html")
    """Приложение встроенное в интерфейс задачи"""
    data = await request.body()
    data_parsed = parse_qs(data.decode())
    session = await session_manager.get_session()
    user = await session.post(
        url=f"{portal_url}rest/user.current",
        params={
            'auth': data_parsed['AUTH_ID'][0]
        }
    )
    user_admin = await session.post(
        url=f"{portal_url}rest/user.admin",
        params={
            'auth': data_parsed['AUTH_ID'][0]
        }
    )
    task_id = ast.literal_eval(data_parsed['PLACEMENT_OPTIONS'][0])["taskId"]
    access = await get_bitrix_auth()
    # получить привязанные элементы tasks.task.get | taskId=441215&select[0]=UF_CRM_TASK
    task = await session.get(
        url=f"{portal_url}rest/tasks.task.get/",
        params={
            'auth': access[0],
            'taskId': task_id,
            'select[0]': 'ACCOMPLICES',
            'select[1]': 'RESPONSIBLE_ID',
            'select[2]': 'UF_CRM_TASK',
            'select[3]': 'TITLE'
        }
    )
    task = await task.json()
    if 'ufCrmTask' not in task['result']['task']:
        return "Нет привязки элемента к CRM"
    if not task['result']['task']['ufCrmTask']:
        return "Нет привязки элемента к CRM"
    if task['result']['task']['ufCrmTask'][0][:4] != 'T83_':
        return "Нет привязки к процессу согласования договора"
    element_id = task['result']['task']['ufCrmTask'][0][4:]
    element = await session.post(
        url=f"{portal_url}rest/crm.item.get",
        params={
            'auth': access[0],
            'entityTypeId': 131,
            'id': element_id,
            'select[0]': 'ufCrm12_1709191865371',
            'select[1]': 'ufCrm12_1709192259979',
            'select[2]': 'ufCrm12_1708599567866',
            'select[3]': 'ufCrm12_1708093511140',
            'select[4]': 'CREATED_BY',
        }
    )
    accomplices = task['result']['task']['accomplices'][0]
    accountants = await session.get(
        url=f"{portal_url}rest/user.search",
        params={
            'auth': access[0],
            'UF_DEPARTMENT': 114
        }
    )
    accountants = await accountants.json()
    list_accountants = []
    for i in accountants["result"]:
        list_accountants.append(i["ID"])
    for a in task['result']['task']['accomplices']:
        if a in list_accountants:
            accomplices = a
    element = await element.json()
    user = await user.json()
    user_admin = await user_admin.json()
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
                    'task_id': task_id,
                    'user_id': user['result']['ID'],
                    'access': list_access[str(i)],
                    'approval_status': approval_status,
                    'attached_file': attached_file,
                    'accomplices': accomplices,
                    'responsible': task['result']['task']['responsibleId'],
                    'title_task': task['result']['task']['title'],
                    'auth': access[0],
                    'comment_accountant':
                        element['result']["item"]['ufCrm12_1708599567866'],
                    'created_by': element['result']["item"]['createdBy'],
                    'portal_url': portal_url,
                    'hosting_url': hosting_url
                }
            )
    return "Доступ запрещен"


if __name__ == "__main__":
    try:
        if platform.system() == "Windows":
            uvicorn.run(
                app,
                host="127.0.0.1",
                log_config="logs/log_config.json",
                use_colors=True,
                log_level="info",
                loop="asyncio"
            )
        else:
            uvicorn.run(
                application,
                host="0.0.0.0",
                log_config="logs/log_config.json",
                use_colors=True,
                log_level="info",
                loop="asyncio"
            )
    except Exception as e:
        logger.error(f"Error launch app: {e}")
