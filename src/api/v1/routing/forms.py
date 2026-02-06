from typing import Annotated

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from config import logger
from repositories.form import FormsTestsRepository
# from db.database import get_bitrix_auth, get_forms, add_test, add_department, del_test
from schemas.models import FormRequest
from config import settings, templates
import datetime
import json
from depends import get_bitrix_service, get_form_service

from services.bitrix import BitrixService
from services.form import FormService

app_forms = APIRouter()


@app_forms.post('/form_to_sp/', tags=['FORMS'], summary="Создание элемента СП Тестирования")
@logger.catch
async def form_to_sp(
    request: FormRequest,
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
):
    params = request.params

    answers = ''
    for name_answer, answer in params.answers.items():
        answers += f"{name_answer}: {answer}\n"

    result = await bitrix_service.send_request(
        'crm.item.add.json',
        json = {
            'entityTypeId': 1098,
            'fields': {
                'ufCrm59_1738313884': params.points,
                'ufCrm59_1756812190971': params.max_points,
                'ufCrm59_1738323186': params.user_id,
                'ufCrm59_1738323573': params.form_id,
                'ufCrm59_1738648993': params.answer_id,
                'ufCrm59_1739453357': answers,
                'ufCrm59_1756449763': params.result,
                'title': params.form_name
            }
        }
    )


@app_forms.post('/employee_testing/', tags=['FORMS'], summary="Панель разрешенных тестов")
@logger.catch
async def employee_testing(
    request: Request,
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
    form_service: Annotated[FormService, Depends(get_form_service)],
    AUTH_ID: str = Form(...), # noqa
    PLACEMENT_OPTIONS: str = Form(...) # noqa
):
    """Список тестов к которым есть доступ, а также информация о завершении последних"""
    forms = await form_service.get_forms() # TODO проверить работает ли
    params = json.loads(PLACEMENT_OPTIONS)

    user = await bitrix_service.send_request(
        'user.current',
        auth=AUTH_ID
    )

    if 'test_id' in params:
        return RedirectResponse(
            status_code=303,
            url=f"https://forms.yandex.ru/u/{params['test_id']}/?user_id={user['result']['ID']}"
        )

    list_tests = await bitrix_service.send_request(
        'crm.item.list.json',
        json={
            'entityTypeId': 1098,
            'filter': {
                'ufCrm59_1738323186': user['result']['ID']
            }
        }
    )

    list_end_test = {}
    for test in list_tests['result']['items']:
        if test['ufCrm59_1738323573'] in list_end_test:
            a = datetime.datetime.strptime(list_end_test[test['ufCrm59_1738323573']]['date'], "%d.%m.%Y %H:%M:%S")
            b = datetime.datetime.fromisoformat(test['createdTime'])
            if a < b.replace(tzinfo=None):
                list_end_test[test['ufCrm59_1738323573']] = {
                    'id': test['ufCrm59_1738323573'],
                    'date': datetime.datetime.fromisoformat(test['createdTime']).strftime("%d.%m.%Y %H:%M:%S"),
                    'points': test['ufCrm59_1738313884'],
                    'max_points': test['ufCrm59_1756812190971'],
                    'result': test['ufCrm59_1756449763'],
                    'count': list_end_test[test['ufCrm59_1738323573']]['count'] + 1}
            else:
                list_end_test[test['ufCrm59_1738323573']]['count'] += 1
        else:
            list_end_test[test['ufCrm59_1738323573']] = {
                'id': test['ufCrm59_1738323573'],
                'date': datetime.datetime.fromisoformat(test['createdTime']).strftime("%d.%m.%Y %H:%M:%S"),
                'points': test['ufCrm59_1738313884'],
                'max_points': test['ufCrm59_1756812190971'],
                'result': test['ufCrm59_1756449763'],
                'count': 1}
    forms_access = []
    for department_id in user['result']['UF_DEPARTMENT']:
        forms_access = [form for form in forms if form[3] and str(department_id) in form[3]]
    return templates.TemplateResponse(
        request,
        name="employee_testing.html",
        context={
            "hosting_url": settings.hosting_url,
            "forms": forms_access,
            'user_id': user['result']['ID'],
            'list_end_test': list_end_test
        }
    )


@app_forms.post('/create_forms/', tags=['FORMS'], summary="Панель тестов")
@logger.catch
async def create_forms(
    request: Request,
    bitrix_service: Annotated[BitrixService, Depends(get_bitrix_service)],
    form_service: Annotated[FormService, Depends(get_form_service)]
):
    count = 0
    list_all_department = []
    while True:
        list_department = await bitrix_service.send_request(
            'department.get.json',
            json={
                'sort': 'ID',
                'start': count
            }
        )
        list_all_department += list_department['result']
        if 'next' in list_department:
            count = list_department['next']
        else:
            break
    forms = await form_service.get_forms()
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
            "hosting_url": settings.hosting_url
        }
    )


@app_forms.post("/control_forms/", tags=['FORMS'], summary="Обработчик доступов к тестам")
async def control_forms(
        request: Request,
        form_service: Annotated[FormService, Depends(get_form_service)]
):
    data = await request.body()

    body = json.loads(data.decode())
    if body['type'] == 'add_test':
        body['form_id'] = body['url'][26:50:]
        await form_service.add_form_if_not_exists(body)
    elif body['type'] == 'add_access':
        await add_department(body)
    elif body['type'] == 'test_delete':
        await del_test(body)
