from fastapi import APIRouter, Request
from config import logger
from db.database import get_bitrix_auth
import datetime
from session_manager import session_manager
from config import portal_url, hosting_url
from fastapi.responses import RedirectResponse
from functions import check_token

app_ved = APIRouter()


@app_ved.post("/activity_update/", tags=['PURCHASE VED'], summary="Записывает дату прихода на наш склад в историю")
@logger.catch
async def activity_update(
    request: Request,
):
    """
    Обработчик для дела. При изменении дела он проверяет, принадлежит ли оно
    воронке "закуп ВЭД" и если да то записывает "дату прихода на наш склад"
    в историю. Также он проверяет, что дело начинается на "подтвердите дату"
    """
    data = await request.form()
    activity_id = data.get('data[FIELDS][ID]')

    access = await get_bitrix_auth()
    session = await session_manager.get_session()
    activity = await session.get(
        url=f"{portal_url}rest/crm.activity.get",
        params={
            'auth': access[0],
            'ID': activity_id
        })
    activity = await activity.json()
    if (activity['result']['OWNER_TYPE_ID'] == '1058' and activity['result']['COMPLETED'] == 'Y'
            and 'Подтвердите дату' in activity['result']['DESCRIPTION']):
        element = await session.get(
            url=f"{portal_url}rest/crm.item.get",
            params={
                'auth': access[0],
                'entityTypeId': 1058,
                'id': activity['result']['OWNER_ID']
                }
        )
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
                    params={
                        'auth': access[0],
                        'entityTypeId': 1058,
                        'id': activity['result']['OWNER_ID']
                    }
            )
            final_result = await update_element.json()
            return {"status_code": 200, 'result': final_result}
    return {'status_code': 400, 'result': 'you invalid'}


@app_ved.post("/handler/", tags=['PURCHASE VED'], summary="Отправляет сообщение с кнопкой")
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


@app_ved.get('/handler_button/', tags=['PURCHASE VED'], summary="Обработчик нажатия на кнопку")
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
