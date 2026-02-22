from typing import Annotated
import datetime
from fastapi import APIRouter, Request, Depends

from src.services.bitrix import BitrixService
from src.depends import get_bitrix_service

contacts = APIRouter()


@contacts.post("/last_activity/", tags=['CONTACTS'], summary="Фиксация последней активности")
async def activity_update(
    request: Request,
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
):
    """
    Обработчик для дела. Фиксирует последнюю активность с клиентом
    """
    data = await request.form()
    activity_id = data.get('data[FIELDS][ID]')

    activity = await bitrix_service.send_request(
        'crm.activity.get',
        'get',
        params={
            'ID': activity_id
        }
    )

    provider_type_id = activity['result']['PROVIDER_TYPE_ID']
    provider_id = activity['result']['PROVIDER_ID']

    # если это ненужное нам дело, то мы ничего не далаем
    if provider_type_id not in ['CALL', 'EMAIL'] and provider_id != 'IMOPENLINES_SESSION':
        return {'status_code': 200, 'detail': 'case is not call, email, message'}

    async def update_time_activity():
        # owner_type_id - 2 deal, 3 contact, 4 company

        list_owner = await bitrix_service.send_request(
            'crm.activity.binding.list',
            json={'activityId': activity_id,}
        )

        for owner in list_owner['result']:
            if owner['entityTypeId'] == 3:
                list_company = await bitrix_service.send_request(
                    'crm.contact.company.items.get',
                    json={
                        'id': owner['entityId'],
                    }
                )
                # обновление "даты последнего контакта" во всех компаниях связанных с контактом
                for company in list_company['result']:
                    await bitrix_service.send_request(
                        'crm.company.update',
                        json={
                            'id': company['COMPANY_ID'],
                            'fields': {
                                'UF_CRM_1744886793': datetime.datetime.now().isoformat()
                            }
                        }
                    )
                updated_contact = await bitrix_service.send_request(
                    'crm.contact.update',
                    json={
                        'id': owner['entityId'],
                        'fields': {
                            'UF_CRM_1744886984': datetime.datetime.now().isoformat()
                        }
                    }
                )
                return updated_contact
            elif owner['entityTypeId'] == 4:
                updated_company = await bitrix_service.send_request(
                    'crm.company.update',
                    json={
                        'id': owner['entityId'],
                        'fields': {
                            'UF_CRM_1744886793': datetime.datetime.now().isoformat()
                        }
                    }
                )
                return updated_company
    # звонок
    if provider_type_id == 'CALL':
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
        # только если это новое письмо (вход, исход)
        if data.get('event') == 'ONCRMACTIVITYADD':
            updated_owner = await update_time_activity()

    # мессенджер
    elif provider_id == 'IMOPENLINES_SESSION':

        if activity['result']['COMPLETED'] == 'Y':
            pass
        else:
            updated_owner = await update_time_activity()
    return {'status_code': 200}
