class ModelAlreadyExistsException(BaseException):
    """Объект уже существует"""

class ModelNoFoundException(BaseException):
    """Объект не найден"""

class ModelMultipleResultsFoundException(BaseException):
    """При ожидании одного объекта нашлось несколько экземпляров"""

class ErrorRequestBitrix(Exception):
    """Ошибка отправки запроса по api bitrix"""

    detail = "error sending a request bitrix api"
