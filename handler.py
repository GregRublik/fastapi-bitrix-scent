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
from config import portal_url, hosting_url, client_id, secret
from session_manager import SessionManager
from db.database import update_tokens, get_bitrix_auth


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
        url=f"https://oauth.bitrix.info/oauth/token/?grant_type=refresh_token&\
        client_id={client_id}&\
        client_secret={client_secret}&\
        refresh_token={access[1]}"
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
        url=(f"https://sporbita.bitrix24.ru/rest/55810/db0ku6gza9bt15jt/im.message.add.json?DIALOG_ID={recipient}"
             f"&MESSAGE={message}")
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
    url = f"{portal_url}rest/{method}?auth={access[0]}&{params}"
    session = await session_manager.get_session()
    async with session.get(url=url) as result:
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
    url = f"{portal_url}rest/crm.activity.get?auth={access[0]}&ID={activity_id}"
    session = await session_manager.get_session()
    activity = await session.get(url=url)
    activity = await activity.json()
    if (activity['result']['OWNER_TYPE_ID'] == '1058' and activity['result']['COMPLETED'] == 'Y'
            and 'Подтвердите дату' in activity['result']['DESCRIPTION']):
        async with session.get(
                url=(f"""{portal_url}rest/crm.item.get?auth={access[0]}&entityTypeId=1058
                &id={activity['result']['OWNER_ID']}""")) as element:
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
            url = f"{portal_url}rest/crm.item.update?auth={access[0]}&entityTypeId=1058&\
            id={activity['result']['OWNER_ID']}&{fields_to_url}"
            async with session.get(
                    url=url
            ) as update_element:
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
    list_task = await session.get(url=(f"{portal_url}rest/tasks.task.list"
                                       f"?auth={access[0]}&filter[<REAL_STATUS]=5&filter[RESPONSIBLE_ID]={user_id}"
                                       f"&select[0]=ID"))
    list_task = await list_task.json()
    user = await session.get(url=(f"{portal_url}rest/user.get"
                                  f"?auth={access[0]}&ID={user_id}"))
    user = await user.json()

    department = await session.get(url=(f"{portal_url}rest/department.get"
                                        f"?auth={access[0]}&ID={user['result'][0]['UF_DEPARTMENT'][0]}"))
    department = await department.json()
    for task in list_task['result']['tasks']:
        await session.get(url=(f"{portal_url}rest/tasks.task.update?auth={access[0]}"
                               f"&taskId={task['id']}&fields[RESPONSIBLE_ID]={department['result'][0]['UF_HEAD']}"))
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
    url = f"""
{portal_url}rest/im.message.add?auth={access[0]}
&MESSAGE=[SIZE=16][B]⚠️Подтвердите получение информации о смене даты прихода 
c {date_old} на новую {date_new} по сделке: [URL={link_element}]{name_element}[/URL][/B][/SIZE]
&KEYBOARD[0][TEXT]=Подтвердить
&KEYBOARD[0][LINK]={hosting_url}handler_button/?item_id={id_element}&client_secret={client_secret}
&KEYBOARD[0][BG_COLOR_TOKEN]=alert
&DIALOG_ID=77297
&KEYBOARD[0][BLOCK]=Y
    """
    session = await session_manager.get_session()
    async with session.get(url=url) as result:
        message = await result.json()
        id_message = message['result']
        async with session.get(url=f"{portal_url}rest/crm.item.get?auth={access[0]}&entityTypeId=1058\
        &id={id_element}") as element:
            update_element = await element.json()
            url_new_id_message = ''

            if update_element['result']['item']['ufCrm41_1725436565']:
                for i, v in enumerate(update_element['result']['item']['ufCrm41_1725436565']):
                    url_new_id_message += f'fields[ufCrm41_1725436565][{i + 1}]={v}&'
            url_new_id_message += f'fields[ufCrm41_1725436565][0]={id_message}&'
        async with session.get(url=f"{portal_url}rest/crm.item.update?auth={access[0]}&entityTypeId=1058\
        &id={id_element}&{url_new_id_message}") as element:
            el = await element.json()
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
    async with session.get(
            url=f"{portal_url}rest/crm.item.get?auth={access[0]}&entityTypeId=1058&id={item_id}"
    ) as element:
        el = await element.json()

    await session.get(url=f"{portal_url}rest/crm.timeline.comment.add?auth={access[0]}"
                          f"&fields[AUTHOR_ID]=77297"
                          f"&fields[ENTITY_TYPE]=DYNAMIC_1058&fields[ENTITY_ID]={item_id}"
                          f"&fields[COMMENT]=Инициатор ознакомлен с новой датой прихода! "
                          f"Дата ознакомления: {datetime.date.today().isoformat()}")
    for i in el['result']['item']['ufCrm41_1725436565']:
        if i != 0:
            await session.get(url=f"""{portal_url}rest/im.message.update?BOT_ID=78051
&MESSAGE_ID={i}&auth={access[0]}&KEYBOARD=0
&MESSAGE=[SIZE=16][B]✔️Подтверждено получение информации о смене даты прихода на новую \
{el['result']['item']['ufCrm41_1724228599427'][:10]} по сделке: \
[URL={portal_url}crm/type/1058/details/{item_id}/]{el['result']['item']['title']}[/URL][/B][/SIZE]""")

    await session.get(url=f"{portal_url}rest/crm.item.update?auth={access[0]}&entityTypeId=1058&id={item_id}\
    &fields[ufCrm41_1725436565]=''")

    return RedirectResponse(url=f"{portal_url}crm/type/1058/details/{item_id}/")


@app.post('/invite_an_employee/', tags=['HR'])
@logger.catch
async def invite_an_employee(
    email: str,
    client_secret: str,
    name: str | None = None,
    last_name: str | None = None,
    work_position: str | None = None,
    personal_phone: str | None = None,
    uf_department: str | None = None,
    adaptation_id: str | None = None,
):
    check_token(client_secret)
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    new_user = await session.post(url=f"{portal_url}rest/user.add.json?auth={access[0]}&NAME={name}"
                                      f"&LAST_NAME={last_name}&WORK_POSITION={work_position}"
                                      f"&PERSONAL_PHONE={personal_phone}&EMAIL={email}&UF_DEPARTMENT={uf_department}")
    new_user = await new_user.json()
    await session.post(url=(f"{portal_url}rest/crm.item.update?auth={access[0]}"
                            f"&entityTypeId=191&id={adaptation_id}"
                            f"&fields[ufCrm19_1713532729]={new_user['result']}"))


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
    user = await session.post(url=f"{portal_url}rest/user.current?auth={data_parsed['AUTH_ID'][0]}")
    user_admin = await session.post(url=f"{portal_url}rest/user.admin?auth={data_parsed['AUTH_ID'][0]}")
    task_id = ast.literal_eval(data_parsed['PLACEMENT_OPTIONS'][0])["taskId"]
    access = await get_bitrix_auth()
    task = await session.get(url=(
        f"{portal_url}rest/tasks.task.get/?auth={access[0]}"  # получить привязанные элементы tasks.task.get | taskId=441215&select[0]=UF_CRM_TASK
        f"&taskId={task_id}"
        f"&select[0]=ACCOMPLICES"
        f"&select[1]=RESPONSIBLE_ID"
        f"&select[2]=UF_CRM_TASK"
        f"&select[3]=TITLE"))
    task = await task.json()
    if 'ufCrmTask' not in task['result']['task']:
        return "Нет привязки элемента к CRM"
    if not task['result']['task']['ufCrmTask']:
        return "Нет привязки элемента к CRM"
    if task['result']['task']['ufCrmTask'][0][:4] != 'T83_':
        return "Нет привязки к процессу согласования договора"
    element_id = task['result']['task']['ufCrmTask'][0][4:]
    element = await session.post(url=(f"{portal_url}rest/crm.item.get?auth={access[0]}&entityTypeId=131"
                                      f"&id={element_id}"
                                      f"&select[0]=ufCrm12_1709191865371"
                                      f"&select[1]=ufCrm12_1709192259979"
                                      f"&select[2]=ufCrm12_1708599567866"
                                      f"&select[3]=ufCrm12_1708093511140"
                                      f"?select[4]=CREATED_BY"))
    accomplices = task['result']['task']['accomplices'][0]
    accountants = await session.get(url=f"{portal_url}rest/user.search?auth={access[0]}&UF_DEPARTMENT=114")
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
    list_access = {'114': 'accountant', '94': 'lawyer', '0': 'admin'}  # бухгалтера, юристы
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
            return templates.TemplateResponse(request,
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
                                              }
                                              )
    return f"Доступ запрещен"


if __name__ == "__main__":
    try:
        if platform.system() == "Windows":
            uvicorn.run(app, host="127.0.0.1", log_config="logs/log_config.json", use_colors=True, log_level="info",
                        loop="asyncio")
        else:
            uvicorn.run(application, host="0.0.0.0", log_config="logs/log_config.json", use_colors=True,
                        log_level="info", loop="asyncio")
    except Exception as e:
        logger.error(f"Error launch app: {e}")
