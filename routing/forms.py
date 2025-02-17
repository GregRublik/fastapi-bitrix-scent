from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from core.config import logger
from db.database import get_bitrix_auth, get_forms, add_test, add_department, del_test
from models.models import FormRequest
from session_manager import session_manager
from core.config import settings, templates
import datetime
import json


app_forms = APIRouter()


@app_forms.post('/form_to_sp/', tags=['FORMS'], summary="Создание элемента СП Тестирования")
@logger.catch
async def form_to_sp(
    request: FormRequest,
):
    params = request.params

    answers = ''
    for name_answer, answer in params.answers.items():
        answers += f"{name_answer}: {answer}\n"
    print(answers)

    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    result = await session.post(
        url=f"{settings.portal_url}rest/crm.item.add.json?",
        json={
            'auth': access[0],
            'entityTypeId': 1098,
            'fields': {
                'ufCrm59_1738313884': params.points,
                'ufCrm59_1738322964': params.max_points,
                'ufCrm59_1738323186': params.user_id,
                'ufCrm59_1738323573': params.form_id,
                'ufCrm59_1738648993': params.answer_id,
                'ufCrm59_1739453357': answers,
                'ufCrm59_1739788661061': params.result,
                'title': params.form_name
            }
        }
    )
    print(await result.text())


@app_forms.post('/employee_testing/', tags=['FORMS'], summary="Панель разрешенных тестов")
@logger.catch
async def employee_testing(
    request: Request,
    AUTH_ID: str = Form(...),
    PLACEMENT_OPTIONS: str = Form(...)

):
    """Список тестов к которым есть доступ, а также информация о завершении последних"""
    forms = await get_forms()
    session = await session_manager.get_session()
    params = json.loads(PLACEMENT_OPTIONS)

    user = await session.post(
        url=f"{settings.portal_url}rest/user.current?",
        params={
            'auth': AUTH_ID
        }
    )
    user = await user.json()

    if 'test_id' in params:
        return RedirectResponse(
            status_code=303,
            url=f"https://forms.yandex.ru/u/{params['test_id']}/?user_id={user['result']['ID']}"
        )

    list_tests = await session.post(
        url=f"{settings.portal_url}rest/crm.item.list?",
        params={
            'auth': AUTH_ID,
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
            "hosting_url": settings.hosting_url,
            "forms": forms_access,
            'user_id': user['result']['ID'],
            'list_end_test': list_end_test
        }
    )


@app_forms.post('/create_forms/', tags=['FORMS'], summary="Панель тестов")
@logger.catch
async def create_forms(
    request: Request
):
    # return templates.TemplateResponse(request, name="install.html")
    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    count = 0
    list_all_department = []
    while True:
        list_department = await session.get(
            url=f"{settings.portal_url}rest/department.get/",
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
            "hosting_url": settings.hosting_url
        }
    )


@app_forms.post("/control_forms/", tags=['FORMS'], summary="Обработчик доступов к тестам")
async def control_forms(
        request: Request
):
    data = await request.body()

    body = json.loads(data.decode())
    if body['type'] == 'add_test':
        body['form_id'] = body['url'][26:50:]
        await add_test(body)
    elif body['type'] == 'add_access':
        await add_department(body)
    elif body['type'] == 'test_delete':
        await del_test(body)


@app_forms.post('/test_form/', tags=['FORMS'], summary="Создание элемента СП Тестирования")
@logger.catch
async def form_to_sp(
    request: FormRequest,
):
    params = request.params

    answers = ''
    for name_answer, answer in params.answers.items():
        answers += f"{name_answer}: {answer}\n"
    print(answers)

    session = await session_manager.get_session()
    access = await get_bitrix_auth()
    result = await session.post(
        url=f"{settings.portal_url}rest/crm.item.add.json?",
        json={
            'auth': access[0],
            'entityTypeId': 1098,
            'fields': {
                'ufCrm59_1738313884': params.points,
                'ufCrm59_1738322964': params.max_points,
                'ufCrm59_1738323186': params.user_id,
                'ufCrm59_1738323573': params.form_id,
                'ufCrm59_1738648993': params.answer_id,
                'ufCrm59_1739453357': answers,
                'ufCrm59_1739788661061': params.result,
                'title': params.form_name
            }
        }
    )
    print(await result.text())
