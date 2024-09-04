from fastapi import FastAPI, Body
from urllib.parse import parse_qs
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from os import getenv
import aiohttp
import datetime


load_dotenv()
app = FastAPI()
session = aiohttp.ClientSession()
portal_url = getenv('PORTAL_URL')


@app.post("/activity_update/")  # исходящий вебхук 387
async def activity_update(
    data: str = Body()
):
    """
    Обработчик для дела. При изменении дела он проверяет принадлежит ли оно
    воронке "закуп ВЭД" и если да то записывает "дату прихода на наш склад"
    в историю. Надо еще добавить проверку что дело соответствует определенному
    шаблону
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
                    new_recording = f"Дата мониторинга: {datetime.date.today().isoformat()} |\
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


@app.post("/authorization/")
async def auth(
    data: str = Body()
):
    data_parsed = parse_qs(data)
    with open('auth/refresh_token.txt', 'w') as file:
        file.write(data_parsed["auth[refresh_token]"][0])
    with open('auth/access_token.txt', 'w') as file:
        file.write(data_parsed["auth[access_token]"][0])
    return {"status_code": 200}


@app.post("/reboot_tokens/")
async def reboot_tokens(
    client_secret: str
):
    with open('auth/refresh_token.txt', 'r') as file:
        refresh_token = file.read()
    with open('auth/client_id.txt', 'r') as file:
        client_id = file.read()
    with open('auth/client_secret.txt', 'r') as file:
        client_secret_file = file.read()
    if f"{client_secret}\n" == client_secret_file:
        async with session.get(
            url=f"https://oauth.bitrix.info/oauth/token/?grant_type=refresh_token&\
            client_id={client_id}&\
            client_secret={client_secret}&\
            refresh_token={refresh_token}"
        ) as update_tokens:
            result_update_tokens = await update_tokens.json()
            with open('auth/refresh_token.txt', 'w') as file:
                file.write(result_update_tokens["refresh_token"])
            with open('auth/access_token.txt', 'w') as file:
                file.write(result_update_tokens["access_token"])
            return {'status_code': 200, 'result': result_update_tokens}
    return {'status_code': 400, 'Bad Request': 'Invalid client_secret'}


@app.post("/handler/")
async def handler(
    id_element: str,
    date_old: str,
    date_new: str,
    link_element: str,
    name_element: str
):

    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()

#     url=f"""{portal_url}rest/imbot.message.add?auth={access_token}
# &MESSAGE=Подтвердите получение информации о смене даты прихода
# c {date_old} на новую {date_new}
# &KEYBOARD[0][TEXT]=Подтвердить
# &KEYBOARD[0][COMMAND]=confirm_date_coming
# &KEYBOARD[0][BG_COLOR_TOKEN]=alert
# &KEYBOARD[0][COMMAND_PARAMS]={id_element}
# &DIALOG_ID=77297
# &KEYBOARD[0][BLOCK]=Y
# """
    url = f"""
    {portal_url}rest/im.message.add?auth={access_token}
&MESSAGE=Подтвердите получение информации о смене даты прихода 
c {date_old} на новую {date_new} по сделке: [URL={link_element}]{name_element}[/URL]
&KEYBOARD[0][TEXT]=Подтвердить
&KEYBOARD[0][LINK]=https://85a9-81-195-149-162.ngrok-free.app/test/?ID={id_element}
&KEYBOARD[0][BG_COLOR_TOKEN]=alert
&DIALOG_ID=77297
&KEYBOARD[0][BLOCK]=Y
    """

    async with session.get(url=url) as result:
        message = await result.json()
        id_message = message['result']
        async with session.get(url=f"{portal_url}rest/crm.item.update?auth={access_token}&entityTypeId=1058&id={id_element}&fields[ufCrm41_1725274475524]={id_message}") as element:
            el = await element.json()
        return {"status_code": 200, 'result': await result.json()}
# im.message.add   MESSAGE=Подтвердите получение&KEYBOARD[0][TEXT]=Подтвердить&KEYBOARD[0][COMMAND]=confirm_date_coming&KEYBOARD[0][BG_COLOR_TOKEN]=alert&KEYBOARD[0][COMMAND_PARAMS]=107&DIALOG_ID=77297
# &FROM_USER_ID=55810
# &TO_USER_ID=77297
# &BOT_ID=77853


@app.post('/main_handler/')
async def main_handler(
    method: str,
    client_secret: str,
    params: str | None = None,
):
    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()
    with open('auth/client_secret.txt', 'r') as file:
        secret = file.read()

    if f"{client_secret}\n" == secret:
        url = f"{portal_url}rest/{method}?auth={access_token}&{params}"
        async with session.get(url=url) as result:
            result = await result.json()
        return {'status_code': 200, 'result': result}
    return {'status_code': 400, 'Bad Request': 'Invalid client_secret'}


@app.post('/handler_command/')
async def handler_command(
    data: str = Body()
):
    data_parsed = parse_qs(data)
    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()
    url = f"""{portal_url}rest/crm.timeline.comment.add?auth={access_token}&fields[AUTHOR_ID]=77297&fields[ENTITY_TYPE]=DYNAMIC_1058&fields[ENTITY_ID]={data_parsed['data[COMMAND][113][COMMAND_PARAMS]'][0]}&fields[COMMENT]=Инициатор ознакомлен с новой датой прихода! Дата ознакомления: {datetime.date.today().isoformat()}"""
    async with session.get(url=url) as res:
        result = await res.json()
    async with session.get(url=f"""{portal_url}rest/imbot.message.update?BOT_ID=78051&MESSAGE_ID={data_parsed['data[PARAMS][MESSAGE_ID]'][0]}&auth={access_token}&KEYBOARD=0""") as res:
        update_message = await res.json()
    return RedirectResponse(url=f"https://sporbita.bitrix24.ru/crm/type/1058/details/{data_parsed['data[COMMAND][113][COMMAND_PARAMS]'][0]}/")


@app.get('/test/')
async def handler_command(
    ID: int
):
    with open('auth/access_token.txt', 'r') as file:
        access_token = file.read()
    async with session.get(url=f"{portal_url}rest/crm.item.get?auth={access_token}&entityTypeId=1058&id={ID}") as element:
        el = await element.json()
        print(el)
    url = f"""{portal_url}rest/crm.timeline.comment.add?auth={access_token}&fields[AUTHOR_ID]=77297&fields[ENTITY_TYPE]=DYNAMIC_1058&fields[ENTITY_ID]={ID}&fields[COMMENT]=Инициатор ознакомлен с новой датой прихода! Дата ознакомления: {datetime.date.today().isoformat()}"""
    async with session.get(url=url) as res:
        result = await res.json()
    async with session.get(url=f"""{portal_url}rest/im.message.update?BOT_ID=78051&MESSAGE_ID={el['result']['item']['ufCrm41_1725274475524']}&auth={access_token}&KEYBOARD=0""") as res:
        update_message = await res.json()

    return RedirectResponse(url=f"https://sporbita.bitrix24.ru/crm/type/1058/details/{ID}/")
