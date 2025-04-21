from fastapi import APIRouter, Request, Form
from core.config import logger
from db.database import get_bitrix_auth
import datetime
from session_manager import session_manager
from core.config import settings, check_token
from fastapi.responses import RedirectResponse

contacts = APIRouter()


@contacts.post("/last_activity/", tags=['CONTACTS'], summary="Фиксация последней активности")
@logger.catch
async def activity_update(
    request: Request,
):
    """
    Обработчик для дела. Фиксирует последнюю активность с клиентом"
    """
    data = await request.form()
    activity_id = data.get('data[FIELDS][ID]')

    access = await get_bitrix_auth()
    session = await session_manager.get_session()
    activity = await session.get(
        url=f"{settings.portal_url}rest/crm.activity.get",
        params={
            'auth': access[0],
            'ID': activity_id
        })
    activity = await activity.json()

    case_id = activity['result']['ID']
    provider_type_id = activity['result']['PROVIDER_TYPE_ID']
    provider_id = activity['result']['PROVIDER_ID']
    owner_id = activity['result']['OWNER_ID']
    owner_type_id = activity['result']['OWNER_TYPE_ID']

    async def update_time_activity():
        # owner_type_id - 3 contact, 4 company
        if owner_type_id == '3':

            # список компаний которые привязаны к данному контакту
            list_company = await session.post(
                url=f"{settings.portal_url}rest/crm.contact.company.items.get.json",
                json={
                    'auth': access[0],
                    'id': owner_id,
                }
            )
            list_company= await list_company.json()
            # обновление "даты последнего контакта" во всех компаниях связанных с контактом
            for company in list_company['result']:
                await session.post(
                    url=f"{settings.portal_url}rest/crm.company.update.json",
                    json={
                        'auth': access[0],
                        'id': company['COMPANY_ID'],
                        'fields': {
                            'UF_CRM_1744886793': datetime.datetime.now().isoformat()
                        }
                    }
                )

            return await session.post(
                url=f"{settings.portal_url}rest/crm.contact.update.json",
                json={
                    'auth': access[0],
                    'id': owner_id,
                    'fields': {
                        'UF_CRM_1744886984': datetime.datetime.now().isoformat()
                    }
                }
            )
        elif owner_type_id == '4':
            return await session.post(
                url=f"{settings.portal_url}rest/crm.company.update.json",
                json={
                    'auth': access[0],
                    'id': owner_id,
                    'fields': {
                        'UF_CRM_1744886793': datetime.datetime.now().isoformat()
                    }
                }
            )

    if owner_type_id not in ['3', '4']:
        return {'status_code': 200, 'detail': 'owner not 3, 4'}

    # если это ненужное нам дело, то мы ничего не далаем
    if provider_type_id not in ['CALL', 'EMAIL'] and provider_id != 'IMOPENLINES_SESSION':
        return {'status_code': 200, 'detail': 'case is not call, email, message'}

    # звонок
    elif provider_type_id == 'CALL':
        # print(f"Phone activity: {case_id}")

        # если это пропущенный звонок, то мы ничего не делаем
        if activity['result']['SETTINGS'].get('MISSED_CALL', False):
            pass
        # если это входящий и его просто отметили как обработанный
        elif activity['result']['COMPLETED'] == 'Y' and activity['result']['DIRECTION'] == '1':
            pass
        # если это входящий или исходящий не пропущенный, то надо заполнить дату
        else:
            updated_owner = await update_time_activity( )

    # почта
    elif provider_type_id == 'EMAIL':
        # print(f"Email activity: {case_id}")

        # только если это новое письмо (вход, исход)
        if data.get('event') == 'ONCRMACTIVITYADD':
            updated_owner = await update_time_activity()

    # мессенджер
    elif provider_id == 'IMOPENLINES_SESSION':
        # print(f"Message activity: {case_id}")
        if activity['result']['COMPLETED'] == 'Y':
            pass
        else:
            updated_owner = await update_time_activity()
    return {'status_code': 200}
