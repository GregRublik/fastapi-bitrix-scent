from fastapi import FastAPI, Body
from typing import Dict, Union
from models import MainHandler
from urllib.parse import parse_qs, urlencode
from auxiliary_functions import check_token
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from os import getenv
import aiohttp
import datetime


load_dotenv()
app = FastAPI()
session = aiohttp.ClientSession()
portal_url = getenv('PORTAL_URL')
hosting_url = getenv('HOSTING_URL')
scheduler = AsyncIOScheduler()


@app.post('/main_handler/', tags=["Universal"])
async def main_handler(
    method: str,
    client_secret: str,
    params: str,
):
    """
    Главный обработчик. Предназначен для отправки любых запросов согласно установленных прав приложения.
    """
    check_token(client_secret)

    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()
    with open('auth/client_secret.txt', 'r') as file:
        secret = file.read()

    if client_secret == secret:
        url = f"{portal_url}rest/{method}?auth={access_token}&{params}"
        async with session.get(url=url) as result:
            result = await result.json()
        return {'status_code': 200, 'result': result}
    return {'status_code': 400, 'Bad Request': 'Invalid client_secret'}


@app.post("/activity_update/",  tags=['Purchase VED'])  # исходящий вебхук 387
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
    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()

    async with session.get(url=f'{portal_url}rest/crm.activity.get?auth={access_token}&ID={activity_id}') as activity:

        activity = await activity.json()
        if (activity['result']['OWNER_TYPE_ID'] == '1058' and activity['result']['COMPLETED'] == 'Y'
                and 'Подтвердите дату' in activity['result']['DESCRIPTION']):
            async with session.get(
                url=f"""{portal_url}rest/crm.item.get?auth={access_token}&entityTypeId=1058
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
                for i, v in enumerate(field_history):
                    fields_to_url += f"fields[ufCrm41_1724744699216][{i}]=" + str(v) + "&"
                    new_recording = f"Дата мониторинга: {datetime.date.today().isoformat()} | \
                    Дата прихода на наш склад: {element['result']['item']['ufCrm41_1724228599427'][:10]}"
                fields_to_url += f"fields[ufCrm41_1724744699216][{i+1}]={new_recording}"
                url = f"{portal_url}rest/crm.item.update?auth={access_token}&entityTypeId=1058&\
                id={activity['result']['OWNER_ID']}&{fields_to_url}"
                async with session.get(
                    url=url
                ) as update_element:
                    final_result = await update_element.json()
                    return {"status_code": 200, 'result': final_result}
        return {'status_code': 400, 'result': 'you invalid'}


@app.post("/app_install/",  tags=['Authentication'])
async def app_install(
    data: str = Body()
):
    data_parsed = parse_qs(data)
    with open('auth/refresh_token.txt', 'w') as file:
        file.write(data_parsed["auth[refresh_token]"][0])
    with open('auth/access_token.txt', 'w') as file:
        file.write(data_parsed["auth[access_token]"][0])
    return {"status_code": 200}


@app.post("/task_delegate/")
async def task_delegate(
        ID: int,
        client_secret: str
):
    """
    Метод для делегирования всех задач сотрудника на руководителя при его увольнении
    """
    check_token(client_secret)
    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()

    list_task = await session.get(url=(f"{portal_url}rest/tasks.task.list"
                                       f"?auth={access_token}&filter[<REAL_STATUS]=5&filter[RESPONSIBLE_ID]={ID}"
                                       f"&select[0]=ID"))
    list_task = await list_task.json()
    user = await session.get(url=(f"{portal_url}rest/user.get"
                                  f"?auth={access_token}&ID={ID}"))
    user = await user.json()

    department = await session.get(url=(f"{portal_url}rest/department.get"
                                        f"?auth={access_token}&ID={user['result'][0]['UF_DEPARTMENT'][0]}"))
    department = await department.json()
    for task in list_task['result']['tasks']:
        await session.get(url=(f"{portal_url}rest/tasks.task.update?auth={access_token}"
                               f"&taskId={task['id']}&fields[RESPONSIBLE_ID]={department['result'][0]['UF_HEAD']}"))
    return {"status_code": 200, "list id task": list_task}


@app.post("/reboot_tokens/",  tags=['Authentication'])
async def reboot_tokens(
    client_secret: str
):
    check_token(client_secret)
    with open('auth/refresh_token.txt', 'r') as file:
        refresh_token = file.read()
    with open('auth/client_id.txt', 'r') as file:
        client_id = file.read()
    with open('auth/client_secret.txt', 'r') as file:
        client_secret = file.read()
    update_tokens = await session.get(
        url=f"https://oauth.bitrix.info/oauth/token/?grant_type=refresh_token&\
        client_id={client_id}&\
        client_secret={client_secret}&\
        refresh_token={refresh_token}"
    )
    result_update_tokens = await update_tokens.json()
    with open('auth/refresh_token.txt', 'w') as file:
        file.write(result_update_tokens["refresh_token"])
    with open('auth/access_token.txt', 'w') as file:
        file.write(result_update_tokens["access_token"])
    return {'status_code': 200, 'result': result_update_tokens}


@app.post("/handler/", tags=['Purchase VED'])
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

    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()

    url = f"""
    {portal_url}rest/im.message.add?auth={access_token}
&MESSAGE=[SIZE=16][B]⚠️Подтвердите получение информации о смене даты прихода 
c {date_old} на новую {date_new} по сделке: [URL={link_element}]{name_element}[/URL][/B][/SIZE]
&KEYBOARD[0][TEXT]=Подтвердить
&KEYBOARD[0][LINK]={hosting_url}handler_button/?ID={id_element}
&KEYBOARD[0][BG_COLOR_TOKEN]=alert
&DIALOG_ID=77297
&KEYBOARD[0][BLOCK]=Y
    """

    async with session.get(url=url) as result:
        message = await result.json()
        id_message = message['result']
        async with session.get(url=f"{portal_url}rest/crm.item.get?auth={access_token}&entityTypeId=1058\
        &id={id_element}") as element:
            update_element = await element.json()
            url_new_id_message = ''

            if update_element['result']['item']['ufCrm41_1725436565']:
                for i, v in enumerate(update_element['result']['item']['ufCrm41_1725436565']):
                    url_new_id_message += f'fields[ufCrm41_1725436565][{i+1}]={v}&'
            url_new_id_message += f'fields[ufCrm41_1725436565][0]={id_message}&'
        async with session.get(url=f"{portal_url}rest/crm.item.update?auth={access_token}&entityTypeId=1058\
        &id={id_element}&{url_new_id_message}") as element:
            el = await element.json()
        return {"status_code": 200, 'result': await result.json()}


# @app.post("/main_handler_test/")
# async def main_handler_test(
#     data: MainHandler
# ):
#     url_str = urlencode(data.params)
#     data_parsed = parse_qs(url_str)
#     # print(data.params)
#     # print(type(data.params['additionalProp2']))
#     print(url_str)
#     print(data_parsed)


@app.get('/handler_button/', tags=['Purchase VED'])
async def handler_button(
    ID: int
):
    """
    Срабатывает при нажатии на кнопку "Подтвердить в сообщении."
    """
    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()
    async with session.get(
            url=f"{portal_url}rest/crm.item.get?auth={access_token}&entityTypeId=1058&id={ID}"
    ) as element:
        el = await element.json()
    url = f"""{portal_url}rest/crm.timeline.comment.add?auth={access_token}
&fields[AUTHOR_ID]=77297&fields[ENTITY_TYPE]=DYNAMIC_1058&fields[ENTITY_ID]={ID}
&fields[COMMENT]=Инициатор ознакомлен с новой датой прихода! Дата ознакомления: {datetime.date.today().isoformat()}"""
    async with session.get(url=url) as res:
        result = await res.json()
    for i in el['result']['item']['ufCrm41_1725436565']:
        if i != 0:
            async with session.get(url=f"""{portal_url}rest/im.message.update?BOT_ID=78051
&MESSAGE_ID={i}&auth={access_token}&KEYBOARD=0&MESSAGE=[SIZE=16][B]✔️Подтверждено получение информации о смене даты прихода на новую \
{el['result']['item']['ufCrm41_1724228599427'][:10]} по сделке: \
[URL={portal_url}crm/type/1058/details/{ID}/]{el['result']['item']['title']}[/URL][/B][/SIZE]""") as res:
                update_message = await res.json()
    async with session.get(url=f"{portal_url}rest/crm.item.update?auth={access_token}&entityTypeId=1058&id={ID}\
    &fields[ufCrm41_1725436565]=''") as update_item:
        update_item = await update_item.json()

    return RedirectResponse(url=f"{portal_url}crm/type/1058/details/{ID}/")
