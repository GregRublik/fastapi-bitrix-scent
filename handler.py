import os
import ast
import aiohttp
import datetime
import uvicorn
from os import getenv
from loguru import logger
from fastapi import FastAPI, Body, Request
from urllib.parse import parse_qs
from functions import check_token
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import portal_url, hosting_url, client_id, secret
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from a2wsgi import ASGIMiddleware


logger.add("logs/debug.log", format="{time} - {level} - {message}", level="DEBUG", rotation="5 MB", compression="zip")
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
scheduler = AsyncIOScheduler()


@app.post("/reboot_tokens/", tags=['Authentication'])
@logger.catch
async def reboot_tokens(
        client_secret: str
):
    """С помощью client_secret приложения можно обновить токены для дальнейшей работы приложения"""
    check_token(client_secret)
    session = aiohttp.ClientSession()
    with open("auth/refresh.txt", "r") as file:
        refresh_token = file.read()
        update_tokens = await session.get(
            url=f"https://oauth.bitrix.info/oauth/token/?grant_type=refresh_token&\
            client_id={client_id}&\
            client_secret={client_secret}&\
            refresh_token={refresh_token}"
        )

    result = await update_tokens.json()
    os.environ["ACCESS_TOKEN"] = result["access_token"]
    os.environ["REFRESH_TOKEN"] = result["refresh_token"]
    return {'status_code': 200, 'result': result}


def retry_with_default_args(func):
    def wrapper(*args):
        try:
            func(*args)
        except KeyError:
            with open("auth/refresh.txt", "r") as file:
                refresh_token = file.read()
            reboot_tokens(refresh_token)
    return wrapper


@app.post("/install/", tags=['Authentication'])
@logger.catch
async def app_install(
        request: Request
):
    """Обработчик для установки приложения"""
    data = await request.body()
    data_parsed = parse_qs(data.decode())
    os.environ["ACCESS_TOKEN"] = data_parsed["AUTH_ID"][0]
    os.environ["REFRESH_TOKEN"] = data_parsed["REFRESH_ID"][0]
    with open("auth/refresh.txt", "w") as file:
        file.write(data_parsed["REFRESH_ID"][0])
    await reboot_tokens(client_secret=secret)
    return templates.TemplateResponse(request, name="install.html")


@app.post('/main_handler/', tags=["Universal"])
@logger.catch
@retry_with_default_args
async def main_handler(
        method: str,
        client_secret: str,
        params: str | None = None,
):
    """
    Главный обработчик. Предназначен для отправки любых запросов согласно установленных прав приложения.
    """
    check_token(client_secret)

    url = f"{portal_url}rest/{method}?auth={getenv('ACCESS_TOKEN')}&{params}"
    session = aiohttp.ClientSession()
    async with session.get(url=url) as result:
        result = await result.json()
    return {'status_code': 200, 'result': result}


@app.post("/activity_update/", tags=['Purchase VED'])  # исходящий вебхук 387
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
    url = f"{portal_url}rest/crm.activity.get?auth={getenv('ACCESS_TOKEN')}&ID={activity_id}"
    session = aiohttp.ClientSession()
    activity = await session.get(url=url)
    activity = await activity.json()
    # print(activity)
    if (activity['result']['OWNER_TYPE_ID'] == '1058' and activity['result']['COMPLETED'] == 'Y'
            and 'Подтвердите дату' in activity['result']['DESCRIPTION']):

        async with session.get(
                url=f"""{portal_url}rest/crm.item.get?auth={getenv('ACCESS_TOKEN')}&entityTypeId=1058
            &id={activity['result']['OWNER_ID']}""") as element:
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
            print(element)
            for index, v in enumerate(field_history):
                fields_to_url += f"fields[ufCrm41_1724744699216][{index}]=" + str(v) + "&"
                new_recording = f"Дата мониторинга: {datetime.date.today().isoformat()} | \
                Дата прихода на наш склад: {element['result']['item']['ufCrm41_1724228599427'][:10]}"
            fields_to_url += f"fields[ufCrm41_1724744699216][{index + 1}]={new_recording}"
            url = f"{portal_url}rest/crm.item.update?auth={getenv('ACCESS_TOKEN')}&entityTypeId=1058&\
            id={activity['result']['OWNER_ID']}&{fields_to_url}"
            async with session.get(
                    url=url
            ) as update_element:
                final_result = await update_element.json()
                return {"status_code": 200, 'result': final_result}
    return {'status_code': 400, 'result': 'you invalid'}


@app.post("/task_delegate/", tags=['User'])
@logger.catch
async def task_delegate(
        ID: int,
        client_secret: str
):
    """
    Метод для делегирования всех задач сотрудника на руководителя при его увольнении
    """
    check_token(client_secret)
    session = aiohttp.ClientSession()
    list_task = await session.get(url=(f"{portal_url}rest/tasks.task.list"
                                       f"?auth={getenv('ACCESS_TOKEN')}&filter[<REAL_STATUS]=5&filter[RESPONSIBLE_ID]={ID}"
                                       f"&select[0]=ID"))
    list_task = await list_task.json()
    user = await session.get(url=(f"{portal_url}rest/user.get"
                                  f"?auth={getenv('ACCESS_TOKEN')}&ID={ID}"))
    user = await user.json()

    department = await session.get(url=(f"{portal_url}rest/department.get"
                                        f"?auth={getenv('ACCESS_TOKEN')}&ID={user['result'][0]['UF_DEPARTMENT'][0]}"))
    department = await department.json()
    for task in list_task['result']['tasks']:
        await session.get(url=(f"{portal_url}rest/tasks.task.update?auth={getenv('ACCESS_TOKEN')}"
                               f"&taskId={task['id']}&fields[RESPONSIBLE_ID]={department['result'][0]['UF_HEAD']}"))
    return {"status_code": 200, "list id task": list_task}


@app.post("/handler/", tags=['Purchase VED'])
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

    url = f"""
{portal_url}rest/im.message.add?auth={getenv('ACCESS_TOKEN')}
&MESSAGE=[SIZE=16][B]⚠️Подтвердите получение информации о смене даты прихода 
c {date_old} на новую {date_new} по сделке: [URL={link_element}]{name_element}[/URL][/B][/SIZE]
&KEYBOARD[0][TEXT]=Подтвердить
&KEYBOARD[0][LINK]={hosting_url}handler_button/?ID={id_element}
&KEYBOARD[0][BG_COLOR_TOKEN]=alert
&DIALOG_ID=77297
&KEYBOARD[0][BLOCK]=Y
    """
    session = aiohttp.ClientSession()
    async with session.get(url=url) as result:
        message = await result.json()
        id_message = message['result']
        async with session.get(url=f"{portal_url}rest/crm.item.get?auth={getenv('ACCESS_TOKEN')}&entityTypeId=1058\
        &id={id_element}") as element:
            update_element = await element.json()
            url_new_id_message = ''

            if update_element['result']['item']['ufCrm41_1725436565']:
                for i, v in enumerate(update_element['result']['item']['ufCrm41_1725436565']):
                    url_new_id_message += f'fields[ufCrm41_1725436565][{i + 1}]={v}&'
            url_new_id_message += f'fields[ufCrm41_1725436565][0]={id_message}&'
        async with session.get(url=f"{portal_url}rest/crm.item.update?auth={getenv('ACCESS_TOKEN')}&entityTypeId=1058\
        &id={id_element}&{url_new_id_message}") as element:
            el = await element.json()
        return {"status_code": 200, 'result': await result.json()}


@app.get('/handler_button/', tags=['Purchase VED'])
@logger.catch
async def handler_button(
        ID: int
):
    """
    Срабатывает при нажатии на кнопку "Подтвердить в сообщении."
    """
    session = aiohttp.ClientSession()
    async with session.get(
            url=f"{portal_url}rest/crm.item.get?auth={getenv('ACCESS_TOKEN')}&entityTypeId=1058&id={ID}"
    ) as element:
        el = await element.json()

    await session.get(url=f"{portal_url}rest/crm.timeline.comment.add?auth={getenv('ACCESS_TOKEN')}"
                          f"&fields[AUTHOR_ID]=77297"
                          f"&fields[ENTITY_TYPE]=DYNAMIC_1058&fields[ENTITY_ID]={ID}"
                          f"&fields[COMMENT]=Инициатор ознакомлен с новой датой прихода! "
                          f"Дата ознакомления: {datetime.date.today().isoformat()}")
    for i in el['result']['item']['ufCrm41_1725436565']:
        if i != 0:
            await session.get(url=f"""{portal_url}rest/im.message.update?BOT_ID=78051
&MESSAGE_ID={i}&auth={getenv('ACCESS_TOKEN')}&KEYBOARD=0
&MESSAGE=[SIZE=16][B]✔️Подтверждено получение информации о смене даты прихода на новую \
{el['result']['item']['ufCrm41_1724228599427'][:10]} по сделке: \
[URL={portal_url}crm/type/1058/details/{ID}/]{el['result']['item']['title']}[/URL][/B][/SIZE]""")

    await session.get(url=f"{portal_url}rest/crm.item.update?auth={getenv('ACCESS_TOKEN')}&entityTypeId=1058&id={ID}\
    &fields[ufCrm41_1725436565]=''")

    return RedirectResponse(url=f"{portal_url}crm/type/1058/details/{ID}/")


@app.post('/invite_an_employee/', tags=['HR'])
@logger.catch
async def invite_an_employee(
        EMAIL: str,
        NAME: str | None = None,
        LAST_NAME: str | None = None,
        WORK_POSITION: str | None = None,
        PERSONAL_PHONE: str | None = None,
        UF_DEPARTMENT: str | None = None,
        ADAPTATION_ID: str | None = None,

):
    session = aiohttp.ClientSession()
    new_user = await session.post(url=f"{portal_url}rest/user.add.json?auth={getenv('ACCESS_TOKEN')}&NAME={NAME}"
                                      f"&LAST_NAME={LAST_NAME}&WORK_POSITION={WORK_POSITION}"
                                      f"&PERSONAL_PHONE={PERSONAL_PHONE}&EMAIL={EMAIL}&UF_DEPARTMENT={UF_DEPARTMENT}")
    new_user = await new_user.json()
    await session.post(url=(f"{portal_url}rest/crm.item.update?auth={getenv('ACCESS_TOKEN')}"
                            f"&entityTypeId=191&id={ADAPTATION_ID}"
                            f"&fields[ufCrm19_1713532729]={new_user['result']}"))


@app.post("/task_panel/")
@logger.catch
async def task_panel(
        request: Request,

):
    """Приложение встроенное в интерфейс задачи"""
    data = await request.body()
    data_parsed = parse_qs(data.decode())
    session = aiohttp.ClientSession()
    user = await session.post(url=f"{portal_url}rest/user.current?auth={data_parsed['AUTH_ID'][0]}")
    user_admin = await session.post(url=f"{portal_url}rest/user.admin?auth={data_parsed['AUTH_ID'][0]}")
    task_id = ast.literal_eval(data_parsed['PLACEMENT_OPTIONS'][0])["taskId"]
    task = await session.get(url=(
        f"{portal_url}rest/tasks.task.get/?auth={getenv('ACCESS_TOKEN')}"  # получить привязанные элементы tasks.task.get | taskId=441215&select[0]=UF_CRM_TASK
        f"&taskId={task_id}"
        f"&select[0]=ACCOMPLICES"
        f"&select[1]=RESPONSIBLE_ID"
        f"&select[2]=UF_CRM_TASK"
        f"&select[3]=UF_CRM_TASK"))
    task = await task.json()
    if 'ufCrmTask' not in task['result']['task']:
        return "Нет привязки элемента к CRM"
    if not task['result']['task']['ufCrmTask']:
        return "Нет привязки элемента к CRM"
    if task['result']['task']['ufCrmTask'][0][:4] != 'T83_':
        return "Нет привязки к процессу согласования договора"
    element_id = task['result']['task']['ufCrmTask'][0][4:]
    element = await session.post(url=(f"{portal_url}rest/crm.item.get?auth={getenv('ACCESS_TOKEN')}&entityTypeId=131"
                                      f"&id={element_id}"
                                      f"&select[0]=ufCrm12_1709191865371"
                                      f"&select[1]=ufCrm12_1709192259979"))

    element = await element.json()
    user = await user.json()
    user_admin = await user_admin.json()
    list_access = {'114': 'accountant', '94': 'lawyer', '0': 'admin'}  # бухгалтера, юристы
    if element['result']["item"]['ufCrm12_1712146917716']:
        attached_file = True
    else:
        attached_file = False
    approval_status = {"accountant": element['result']["item"]['ufCrm12_1709191865371'],
                       "lawyer": element['result']["item"]['ufCrm12_1709192259979']}
    for i in user['result']['UF_DEPARTMENT']:  # перебираем все подразделения сотрудника
        if i in list_access or user_admin['result']:  # Если есть разрешение
            if user_admin['result']:
                i = '0'
            return templates.TemplateResponse(request,
                                              name="task_panel.html",
                                              context={
                                                  'element_id': element_id,
                                                  'task_id': task_id,
                                                  'user_id': user['result']['ID'],
                                                  'access': list_access[i],
                                                  'approval_status': approval_status,
                                                  'attached_file': attached_file,
                                                  'accomplices': task['result']['task']['accomplices'][0],
                                                  'responsible': task['result']['task']['responsibleId'],
                                                  'auth': getenv('ACCESS_TOKEN')
                                              }
                                              )
    return "Доступ запрещен"


if __name__ == "__main__":
    uvicorn.run(app, host='127.0.0.1', log_config="log_config.json", use_colors=True, log_level="info")
